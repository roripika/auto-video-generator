from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import yaml

from pathlib import Path

from src.models import BGMAudio, ScriptModel, Section, TextStyle, ThemeTemplate

from .llm import LLMError, OpenAIChatClient, generate_and_validate
from .schemas import script_payload_schema
from .skeletons import build_script_skeleton


BG_KEYWORD_MAX_LEN = 30


def _normalize_linebreaks(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.replace("\\r\\n", "\n").replace("\\r", "\n")
    # allow literal backslash-n sequences from LLM output to become actual newlines
    normalized = normalized.replace("\\n", "\n")
    return normalized


class ScriptGenerationError(RuntimeError):
    """Raised when the script generator cannot build a valid ScriptModel."""


@dataclass
class ScriptFromBriefGenerator:
    """Generate ScriptModel instances from natural language briefs."""

    llm: OpenAIChatClient
    theme: Optional[ThemeTemplate]
    section_count: int
    target_seconds: Optional[int] = None

    def generate(self, brief: str) -> ScriptModel:
        if not brief or not brief.strip():
            raise ScriptGenerationError("Input brief is empty.")

        skeleton = build_script_skeleton(self.theme, self.section_count)
        messages = self._build_messages(brief.strip())
        # Use a minimal schema to encourage strict JSON output from the model.
        schema = script_payload_schema()
        try:
            raw_response = generate_and_validate(self.llm, messages, schema=schema, retries=2)
        except LLMError as err:
            raise ScriptGenerationError(str(err)) from err
        payload = self._parse_payload(raw_response)
        return self._apply_to_script(skeleton, payload)

    def _build_messages(self, brief: str) -> List[Dict[str, str]]:
        theme = self.theme
        section_count = max(self.section_count, 1)
        layout = theme.layout if theme else "ranking"
        hook_phrases = ", ".join(theme.hook_phrases) if theme and theme.hook_phrases else "驚き/損している日常"
        keywords = ", ".join(theme.thumbnail_keywords) if theme and theme.thumbnail_keywords else ""
        cta = theme.cta.primary if theme and theme.cta else "コメントで感想をシェアしてください！"

        format_hint = {
            "title": "動画タイトル（20〜35文字）",
            "summary": "動画全体の要約。2文以内。",
            "video": {
                "bg": "背景候補の説明 or URL or ファイル名（例: pexels「夕景」）",
                "bg_fit": "cover",
            },
            "bgm": {
                "file": "BGM候補（ファイル名 or URL or ジャンルキーワード例: 背景: lo-fi クイズ風）",
                "volume_db": -10,
                "ducking_db": 0,
                "license": "必要な場合、出典/ライセンス表記のメモ（例: Pixabay License, CC-BY 表記など）",
            },
            "text_style": {
                "font": "Noto Sans JP",
                "fontsize": 100,
                "fill": "#FFFFFF",
                "position": {"x": "center", "y": "center"},
                "stroke": {"color": "#000000", "width": 4},
            },
            "sections": [
                {
                    "id": "section-1",
                    "rank": "1",
                    "on_screen_text": "セクションタイトル＋要点キーワード（例: 第1位：○○ / 要約: ○○が驚き）",
                    "on_screen_segments": [
                        {
                            "text": "第1位：",
                            "style": {"fontsize": 64, "fill": "#FFE65A", "stroke": {"color": "#000000", "width": 6}},
                        },
                        {
                            "text": "営業職\\n年収は約500万円",
                            "style": {"fontsize": 60, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 6}},
                        },
                    ],
                    "hook": "視聴者の悩みを喚起する一言",
                    "evidence": "信頼できる根拠文",
                    "demo": "手順やビフォーアフター",
                    "bridge": "次の話題への繋ぎ",
                    "cta": "試してコメントを促す",
                    "narration": "ナレーション全文（60〜80文字目安）",
                    "effects": ["zoom_in"],
                    "bg_keyword": "背景に使いたいキーワード（例: 名古屋 夜景 工場）",
                    "overlays": [
                        {
                            "file": "商品の参考画像ファイル名やURL",
                            "position": {"x": "right-120", "y": "center"},
                            "scale": 0.6,
                            "opacity": 0.95,
                        }
                    ],
                }
            ],
            "global_cta": cta,
            "outro": {
                "on_screen_text": "まとめ / CTA",
                "on_screen_segments": [
                    {
                        "text": "まとめ",
                        "style": {"fontsize": 58, "fill": "#FFE65A", "stroke": {"color": "#000000", "width": 4}},
                    },
                    {
                        "text": "最後に強調したい一言",
                        "style": {"fontsize": 54, "fill": "#FFFFFF", "stroke": {"color": "#000000", "width": 4}},
                    },
                ],
                "narration": "締めのナレーション（50〜80文字）",
                "cta": "コメントやチャンネル登録を促す一言",
            },
        }

        # Compute optional short constraints
        short_constraints = ""
        if self.target_seconds and self.target_seconds > 0:
            total_chars = int(max(120, min(1200, self.target_seconds * 7 * 0.9)))
            intro_c = max(30, min(60, int(total_chars * 0.15)))
            outro_c = max(30, min(60, int(total_chars * 0.15)))
            per_c = max(45, min(90, int((total_chars - intro_c - outro_c) / max(1, section_count))))
            total_low = max(200, total_chars - 40)
            short_constraints = (
                f"\n\n[短尺制約]\n"
                f"- 総ナレーション文字数は概ね {total_low}〜{total_chars} 文字。\n"
                f"- 導入 {intro_c-10}〜{intro_c}、各セクション {per_c-10}〜{per_c}、締め {outro_c-10}〜{outro_c}。\n"
                f"- 文字数制約は厳守し、冗長な言い換えや重複は避ける。\n"
            )
        system_msg = (
            "あなたは日本語で雑学/ライフハック動画の台本を書くプロの構成作家です。"
            "ライフハック動画のテンプレート（フック→根拠→実演→ブリッジ）に沿って、"
            f"{section_count}個の{'ランキング項目' if layout == 'ranking' else 'セクション'}を必ず作成してください。"
            "出力は有効な JSON オブジェクトのみです。説明文や余計な文章を先頭や末尾に加えないでください。"
            "各セクションには必要に応じて画面効果 (effects) を配列で指定してください。利用可能な効果:"
            " blur / grayscale / vignette / contrast / zoom_in / zoom_out / zoom_pan_left / zoom_pan_right。"
            "背景 (video.bg) に関して、雰囲気に合うキーワードや具体的素材案があれば bg フィールドに記入してください"
            "（例: pexelsの夕景動画、統計ならシンプルなチャート背景など）。"
            "テロップ位置(font/position)やフォント/色の提案があれば text_style に反映してください（読みやすさ重視の色・位置を選んでください）。"
            "各セクションには背景素材検索に使えるキーワード (bg_keyword) を書いてください。"
            "必ず全セクション（intro/outro含む）に bg_keyword を入れ、10〜30文字程度の短いキーワードで指定してください。"
            "最初に導入セクションを1本入れ、動画全体で何を紹介するかを1〜2文で説明してください。"
            "特にテロップは『中央寄せのヒーロータイトル型』を推奨します。on_screen_textには改行(\\n)を含めて3〜4行に分割し、1行15〜18文字以内を目安に中央に積み重ねてください。"
            "text_style.positionはデフォルトで x:center, y:center（または center-100 など少し上）を選び、背景の主要被写体を避けるレイアウトを提案してください。"
            "BGM も提案してください。具体的なファイル名/URLがなければ、ジャンルやムードキーワード（例: lo-fi クイズ系, 軽快トリビア）を `bgm.file` に書いてください。音量(dB)やナレーション時の ducking(dB)を指定し、必要ならライセンス表記メモを `bgm.license` に書いてください。デフォルトの ducking は 0 です。"
            "Blur（ぼかし）はテキスト可読性を著しく落とすため、基本は付けないでください。どうしても必要な場合は弱い強度で部分的に限定してください。"
            "テロップはセグメント分割して、強調したいキーワードごとに `on_screen_segments` で色・サイズ・フォントを変えてください。各セクションは最低2つのセグメント（例: タグ/見出し＋要約）を含め、改行を使って中央に積み重ねてください。"
            "テロップの配置はテンプレート化します。`text_layout` は hero_center / hero_middle / lower_third / side_left / side_right のいずれかを設定し、"
            "rank（強調キーワード）は大きめ（例: 96以上、黄色+黒縁）、本文はやや小さめ（例: 64〜80、白+黒縁）にしてください。"
            "商品の参考画像や図版がある場合は、セクションに `overlays` を入れてください。file（パス/URL）、position（x,y）、必要なら scale/opacity を指定してください。"
            "最後に「まとめ/締め」のアウトロセクション (`outro`) を必ず書き、スクリーンテキストとナレーションを用意してください。"
            "固有名詞・作品名がローマ字や英語表記の場合、ナレーションでは誤読を避けるためカタカナ表記に置き換えてください。"
            "\\n\\n重要: 出力は必ず有効な JSON オブジェクト1つのみで、前後に説明文やコードフェンス（```）を入れないでください。"
        )
        system_msg += short_constraints

        user_msg = f"""
テーマ: {theme.label if theme else '汎用ライフハック'}
ジャンル: {theme.genre if theme else 'general'}
説明: {(theme.description or '驚きと再現性のある豆知識を紹介します。') if theme else '視聴者の日常課題を解決するライフハック'}
推奨フック語: {hook_phrases}
サムネ候補キーワード: {keywords or '知らないと損, すぐ試せる'}
ランキング項目数: {section_count}
CTA: {cta}

入力ブリーフ:
\"\"\"
{brief}
\"\"\"

制約:
- すべて日本語で記述する。
- {('各セクションは 80〜120 文字程度のナレーションを含める。') if not self.target_seconds else '文字数制約を厳守し、冗長表現は避ける（上の短尺制約を参照）。'}
- { ' `rank` は降順（例: 5→1）。`on_screen_text` に「第X位：タイトル」を含める。' if layout == 'ranking' else '構成は導入→展開→例→まとめの流れを意識し、セクション見出しと要点を入れる。' }
- `bridge` は次の{ '順位' if layout == 'ranking' else 'セクション' }への期待や話題転換を意識する。
- `cta` は視聴者にコメント/高評価/登録を促す短い文。
- `effects` は必要に応じて上記リストから選び配列で記載する（無い場合は空配列可）。
- `video.bg` には背景キーワード/素材案を入れる（URL/ファイル名/キーワードいずれでも可）。
- `text_style` はフォント/サイズ/色/位置の推奨値があれば記載する（読みやすさと強調を考慮）。
- テロップのフォントサイズは最低でも 100pt 以上を推奨し、`on_screen_segments` では重ならないよう十分な行間やずれを持たせた位置指定を記述する。
- `bg_keyword` は各セクションの背景検索用キーワードを書いてください。

出力フォーマットの例:
{json.dumps(format_hint, ensure_ascii=False, indent=2)}
"""
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

    def _parse_payload(self, raw: str) -> Dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            # Remove Markdown fences if the model included them.
            text = re.sub(r"^```(?:json)?", "", text).strip()
            text = re.sub(r"```$", "", text).strip()
        for loader in (json.loads, yaml.safe_load):
            try:
                data = loader(text)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
        self._log_invalid_response(text)
        raise ScriptGenerationError("LLM response could not be parsed as JSON/YAML.")

    def _log_invalid_response(self, text: str) -> None:
        try:
            log_dir = Path("logs/llm_errors")
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_path = log_dir / f"invalid_llm_response_{timestamp}.txt"
            log_path.write_text(text)
            print(f"[WARN] LLM response saved to {log_path}")
        except Exception as err:  # pragma: no cover
            print(f"[WARN] Failed to log LLM response: {err}")

    def _apply_to_script(self, script: ScriptModel, payload: Dict[str, Any]) -> ScriptModel:
        sections_data = payload.get("sections")
        if not isinstance(sections_data, list) or not sections_data:
            raise ScriptGenerationError("LLM response missing 'sections' list.")

        script.title = payload.get("title") or script.title
        summary = payload.get("summary")
        global_cta = payload.get("global_cta")

        # Optional overrides from payload
        video_payload = payload.get("video") or {}
        if video_payload.get("bg"):
            script.video.bg = video_payload["bg"]
        if video_payload.get("bg_fit"):
            script.video.bg_fit = video_payload["bg_fit"]

        text_style_payload = payload.get("text_style") or {}
        if text_style_payload:
            for key in ["font", "fontsize", "fill", "animation"]:
                if key in text_style_payload and text_style_payload[key] is not None:
                    setattr(script.text_style, key, text_style_payload[key])
            if "stroke" in text_style_payload and isinstance(text_style_payload["stroke"], dict):
                stroke = text_style_payload["stroke"]
                if "color" in stroke:
                    script.text_style.stroke.color = stroke["color"]
                if "width" in stroke and stroke["width"] is not None:
                    script.text_style.stroke.width = stroke["width"]
            if "position" in text_style_payload and isinstance(text_style_payload["position"], dict):
                pos = text_style_payload["position"]
                if "x" in pos:
                    script.text_style.position.x = pos["x"]
                if "y" in pos:
                    script.text_style.position.y = pos["y"]

        bgm_payload = payload.get("bgm")
        if isinstance(bgm_payload, dict):
            file_val = bgm_payload.get("file")
            if file_val:
                script.bgm = script.bgm or BGMAudio(file=file_val)
                script.bgm.file = file_val
                if bgm_payload.get("volume_db") is not None:
                    script.bgm.volume_db = float(bgm_payload["volume_db"])
                # ducking はユーザーが明示変更しない限り 0 に固定する
                script.bgm.ducking_db = 0.0
                script.bgm.license = bgm_payload.get("license") or script.bgm.license
            elif not file_val:
                script.bgm = None

        base_style = script.text_style

        def base_segment_style() -> dict:
            return {
                "font": base_style.font,
                "fontsize": base_style.fontsize,
                "fill": base_style.fill,
                "stroke": {"color": base_style.stroke.color, "width": base_style.stroke.width},
                "position": {"x": base_style.position.x, "y": base_style.position.y},
                "animation": base_style.animation,
            }

        def build_fallback_segments(text: str) -> List[dict]:
            clean = _normalize_linebreaks(text).strip()
            if not clean:
                clean = script.title or "注目ポイント"
            parts = [p.strip() for p in re.split(r"[\n]+", clean) if p.strip()]
            if len(parts) < 2 and "：" in clean:
                prefix, rest = clean.split("：", 1)
                parts = [f"{prefix.strip()}：", rest.strip()]
            if len(parts) < 2 and len(clean) > 12:
                midpoint = len(clean) // 2
                parts = [clean[:midpoint].strip(), clean[midpoint:].strip()]
                parts = [p for p in parts if p]
            if len(parts) < 2 and clean:
                parts = [clean, clean]
            segments: List[dict] = []
            for idx, chunk in enumerate(parts[:4]):
                style = base_segment_style()
                if idx == 0:
                    style["fontsize"] = (base_style.fontsize or 60) + 6
                    style["fill"] = "#FFE65A"
                segments.append({"text": chunk, "style": style})
            return segments

        def merge_style(style_payload: dict | None) -> dict:
            style = base_segment_style()
            payload = style_payload or {}
            for key in ["font", "fontsize", "fill", "animation"]:
                if key in payload and payload[key] is not None:
                    style[key] = payload[key]
            if "stroke" in payload and isinstance(payload["stroke"], dict):
                stroke = payload["stroke"]
                if "color" in stroke and stroke["color"]:
                    style["stroke"]["color"] = stroke["color"]
                if "width" in stroke and stroke["width"] is not None:
                    style["stroke"]["width"] = stroke["width"]
            if "position" in payload and isinstance(payload["position"], dict):
                pos = payload["position"]
                if "x" in pos:
                    style["position"]["x"] = pos["x"]
                if "y" in pos:
                    style["position"]["y"] = pos["y"]
            return style

        def normalize_segments(raw_segments: List[dict], fallback_text: str) -> List[dict]:
            normalized: List[dict] = []
            for seg in raw_segments:
                if not isinstance(seg, dict):
                    continue
                text_value = _normalize_linebreaks(seg.get("text"))
                text_value = text_value.strip()
                if not text_value:
                    continue
                style_data = merge_style(seg.get("style"))
                normalized.append({"text": text_value, "style": style_data})
            if len(normalized) < 2:
                normalized = build_fallback_segments(fallback_text)
            return normalized

        new_sections: List[Section] = []

        # 導入セクション追加
        intro_text = summary or payload.get("intro") or f"{script.title}を紹介します。"
        intro_bg_kw = _infer_bg_keyword(
            {"bg_keyword": payload.get("bg_keyword"), "title": script.title, "narration": intro_text},
            script.title,
        )
        new_sections.append(
            Section(
                id="intro",
                on_screen_text=script.title,
                narration=intro_text,
                duration_hint_sec=None,
                bg=None,
                bg_keyword=intro_bg_kw,
                hook=None,
                evidence=None,
                demo=None,
                bridge=None,
                cta=global_cta or "最後までご覧ください。",
                effects=[],
            )
        )

        for idx, section_payload in enumerate(sections_data[: self.section_count], start=1):
            if not isinstance(section_payload, dict):
                continue
            section_id = section_payload.get("id") or f"rank-{idx}"
            on_screen = _normalize_linebreaks(
                section_payload.get("on_screen_text") or section_payload.get("title")
            )
            if not on_screen:
                on_screen = f"第{idx}位：注目ハック"
            narration = section_payload.get("narration") or section_payload.get("script")
            if not narration:
                raise ScriptGenerationError(f"Section {section_id} is missing 'narration'.")

            segments_payload = section_payload.get("on_screen_segments") or []
            segments_clean = normalize_segments(segments_payload, on_screen)

            bg_keyword = _infer_bg_keyword(section_payload, script.title)
            new_sections.append(
                Section(
                    id=section_id,
                    on_screen_text=on_screen,
                    on_screen_segments=segments_clean,
                    overlays=section_payload.get("overlays") or [],
                    narration=narration,
                    duration_hint_sec=None,
                    bg_keyword=bg_keyword,
                    hook=section_payload.get("hook"),
                    evidence=section_payload.get("evidence"),
                    demo=section_payload.get("demo"),
                    bridge=section_payload.get("bridge"),
                    cta=section_payload.get("cta"),
                    effects=section_payload.get("effects") or [],
                )
            )

        outro_payload = payload.get("outro")
        if isinstance(outro_payload, dict):
            outro_text = outro_payload.get("on_screen_text") or "まとめ"
            outro_narration = outro_payload.get("narration") or summary or global_cta or "最後にもう一度注目ポイントを振り返りましょう。"
            outro_segments = normalize_segments(outro_payload.get("on_screen_segments") or [], outro_text)
            outro_bg_kw = _infer_bg_keyword(outro_payload, script.title)
            new_sections.append(
                Section(
                    id="outro",
                    on_screen_text=outro_text,
                    on_screen_segments=outro_segments,
                    overlays=outro_payload.get("overlays") or [],
                    narration=outro_narration,
                    duration_hint_sec=None,
                    bg_keyword=outro_bg_kw,
                    hook=None,
                    evidence=None,
                    demo=None,
                    bridge=None,
                    cta=outro_payload.get("cta") or global_cta,
                    effects=outro_payload.get("effects") or [],
                )
            )

        if len(new_sections) - 1 < self.section_count:  # minus intro
            raise ScriptGenerationError(
                f"Expected {self.section_count} sections but received {len(new_sections)-1} from LLM."
            )

        # If short target is defined, trim narration to fit character budgets
        if self.target_seconds and self.target_seconds > 0:
            total_chars = int(max(120, min(1200, self.target_seconds * 7 * 0.9)))
            intro_c = max(30, min(60, int(total_chars * 0.15)))
            outro_c = max(30, min(60, int(total_chars * 0.15)))
            per_c = max(45, min(90, int((total_chars - intro_c - outro_c) / max(1, self.section_count))))

            def _trim(text: str, limit: int) -> str:
                t = (text or '').strip()
                if len(t) <= limit:
                    return t
                # Prefer trimming at sentence boundaries
                cut = t[: limit + 20]
                for sep in ['。', '！', '？', '\\n']:
                    pos = cut.rfind(sep)
                    if pos >= 0 and pos >= limit - 20:
                        return cut[: pos + 1].strip()
                return t[:limit].strip()

            for i, sec in enumerate(new_sections):
                if sec.id == 'intro':
                    sec.narration = _trim(sec.narration or '', intro_c)
                elif sec.id == 'outro':
                    sec.narration = _trim(sec.narration or '', outro_c)
                else:
                    sec.narration = _trim(sec.narration or '', per_c)

        script.sections = new_sections
        if script.upload_prep:
            desc_parts = []
            if summary:
                desc_parts.append(summary.strip())
            elif script.sections and script.sections[0].narration:
                desc_parts.append(script.sections[0].narration.strip())
            if script.upload_prep.desc:
                desc_parts.append(script.upload_prep.desc.strip())
            if global_cta:
                desc_parts.append(global_cta.strip())
            script.upload_prep.desc = "\n\n".join(part for part in desc_parts if part).strip()
            title_candidate = script.title or (script.sections[0].on_screen_text if script.sections else None)
            if title_candidate:
                script.upload_prep.title = title_candidate.strip()
        return script
def _pick_keyword_candidate(text: str | None) -> Optional[str]:
    if not text:
        return None
    chunks = re.split(r"[、。,/|（）()【】「」『』!！?？…・：:・\\-]+|\n+", text)
    for chunk in chunks:
        cleaned = chunk.strip()
        if not cleaned:
            continue
        if re.fullmatch(r"第?\d+位", cleaned):
            continue
        return cleaned[:BG_KEYWORD_MAX_LEN]
    return None


def _infer_bg_keyword(source: Dict[str, Any], fallback: Optional[str] = None) -> Optional[str]:
    explicit = source.get("bg_keyword")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()[:BG_KEYWORD_MAX_LEN]
    text_sources: List[str] = []
    for key in ("bg", "title", "on_screen_text", "hook", "narration"):
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            text_sources.append(value.strip())
    if fallback:
        text_sources.append(fallback)
    for text in text_sources:
        candidate = _pick_keyword_candidate(text)
        if candidate:
            return candidate
    return fallback[:BG_KEYWORD_MAX_LEN] if fallback else None
