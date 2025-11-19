from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml

from src.models import ScriptModel, Section, ThemeTemplate

from .llm import LLMError, OpenAIChatClient
from .skeletons import build_script_skeleton


class ScriptGenerationError(RuntimeError):
    """Raised when the script generator cannot build a valid ScriptModel."""


@dataclass
class ScriptFromBriefGenerator:
    """Generate ScriptModel instances from natural language briefs."""

    llm: OpenAIChatClient
    theme: Optional[ThemeTemplate]
    section_count: int

    def generate(self, brief: str) -> ScriptModel:
        if not brief or not brief.strip():
            raise ScriptGenerationError("Input brief is empty.")

        skeleton = build_script_skeleton(self.theme, self.section_count)
        messages = self._build_messages(brief.strip())
        try:
            raw_response = self.llm.generate_json(messages)
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
            "text_style": {
                "font": "Noto Sans JP",
                "fontsize": 60,
                "fill": "#FFFFFF",
                "position": {"x": "center", "y": "bottom-180"},
                "stroke": {"color": "#000000", "width": 4},
            },
            "sections": [
                {
                    "id": "section-1",
                    "rank": "1",
                    "on_screen_text": "セクションタイトル",
                    "hook": "視聴者の悩みを喚起する一言",
                    "evidence": "信頼できる根拠文",
                    "demo": "手順やビフォーアフター",
                    "bridge": "次の話題への繋ぎ",
                    "cta": "試してコメントを促す",
                    "narration": "ナレーション全文（60〜80文字目安）",
                    "effects": ["zoom_in", "blur"],
                    "bg_keyword": "背景に使いたいキーワード（例: 名古屋 夜景 工場）",
                }
            ],
            "global_cta": cta,
        }

        system_msg = (
            "あなたは日本語で雑学/ライフハック動画の台本を書くプロの構成作家です。"
            "ライフハック動画のテンプレート（フック→根拠→実演→ブリッジ）に沿って、"
            f"{section_count}個の{'ランキング項目' if layout == 'ranking' else 'セクション'}を必ず作成してください。"
            "出力は有効な JSON オブジェクトのみです。説明文や余計な文章を先頭や末尾に加えないでください。"
            "各セクションには必要に応じて画面効果 (effects) を配列で指定してください。利用可能な効果:"
            " blur / grayscale / vignette / contrast / zoom_in / zoom_out / zoom_pan_left / zoom_pan_right。"
            "背景 (video.bg) に関して、雰囲気に合うキーワードや具体的素材案があれば bg フィールドに記入してください"
            "（例: pexelsの夕景動画、統計ならシンプルなチャート背景など）。"
            "テロップ位置(font/position)の提案があれば text_style に反映してください。"
            "各セクションには背景素材検索に使えるキーワード (bg_keyword) を書いてください。"
            "最初に導入セクションを1本入れ、動画全体で何を紹介するかを1〜2文で説明してください。"
        )

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
- 各セクションは 80〜120 文字程度のナレーションを含める。
- { ' `rank` は降順（例: 5→1）。`on_screen_text` に「第X位：タイトル」を含める。' if layout == 'ranking' else '構成は導入→展開→例→まとめの流れを意識し、セクション見出しと要点を入れる。' }
- `bridge` は次の{ '順位' if layout == 'ranking' else 'セクション' }への期待や話題転換を意識する。
- `cta` は視聴者にコメント/高評価/登録を促す短い文。
- `effects` は必要に応じて上記リストから選び配列で記載する（無い場合は空配列可）。
- `video.bg` には背景キーワード/素材案を入れる（URL/ファイル名/キーワードいずれでも可）。
- `text_style` はフォント/サイズ/色/位置の推奨値があれば記載する。
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
        raise ScriptGenerationError("LLM response could not be parsed as JSON/YAML.")

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

        new_sections: List[Section] = []

        # 導入セクション追加
        intro_text = summary or payload.get("intro") or f"{script.title}を紹介します。"
        new_sections.append(
            Section(
                id="intro",
                on_screen_text=script.title,
                narration=intro_text,
                duration_hint_sec=None,
                bg=None,
                bg_keyword=payload.get("bg_keyword"),
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
            on_screen = section_payload.get("on_screen_text") or section_payload.get("title")
            if not on_screen:
                on_screen = f"第{idx}位：注目ハック"
            narration = section_payload.get("narration") or section_payload.get("script")
            if not narration:
                raise ScriptGenerationError(f"Section {section_id} is missing 'narration'.")

            new_sections.append(
                Section(
                    id=section_id,
                    on_screen_text=on_screen,
                    narration=narration,
                    duration_hint_sec=None,
                    bg_keyword=section_payload.get("bg_keyword"),
                    hook=section_payload.get("hook"),
                    evidence=section_payload.get("evidence"),
                    demo=section_payload.get("demo"),
                    bridge=section_payload.get("bridge"),
                    cta=section_payload.get("cta"),
                    effects=section_payload.get("effects") or [],
                )
            )

        if len(new_sections) - 1 < self.section_count:  # minus intro
            raise ScriptGenerationError(
                f"Expected {self.section_count} sections but received {len(new_sections)-1} from LLM."
            )

        script.sections = new_sections
        if script.upload_prep:
            if summary:
                script.upload_prep.desc = f"{summary}\n\n{script.upload_prep.desc or ''}".strip()
            if global_cta:
                script.upload_prep.desc = f"{script.upload_prep.desc}\n{global_cta}".strip()
                if script.upload_prep and not script.upload_prep.title:
                    script.upload_prep.title = script.title
        return script
