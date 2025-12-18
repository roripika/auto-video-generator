#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "settings" / "ai_settings.json"
LLM_ERROR_LOG_DIR = PROJECT_ROOT / "logs" / "llm_errors"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.script_generation import build_llm_client, LLMError  # noqa: E402


def load_saved_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        sys.stderr.write("Warning: settings/ai_settings.json が壊れているため無視します。\n")
        return {}


def resolve_provider(args: argparse.Namespace, saved_settings: dict) -> Tuple[str, dict]:
    provider = (
        args.provider
        or saved_settings.get("activeProvider")
        or saved_settings.get("provider")
        or "openai"
    )
    providers_map = saved_settings.get("providers") if isinstance(saved_settings.get("providers"), dict) else {}
    provider_cfg = providers_map.get(provider, {}) if isinstance(providers_map, dict) else {}
    return provider, provider_cfg


def build_client(args: argparse.Namespace) -> Any:
    saved_settings = load_saved_settings()
    provider, provider_cfg = resolve_provider(args, saved_settings)
    api_key = args.api_key or provider_cfg.get("apiKey") or saved_settings.get("apiKey")
    model = args.model or provider_cfg.get("model") or saved_settings.get("model")
    base_url = args.base_url or provider_cfg.get("baseUrl") or saved_settings.get("baseUrl")
    return build_llm_client(
        provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )


def build_messages(
    language: str,
    max_ideas: int,
    category: str | None = None,
    extra_keyword: str | None = None,
) -> List[Dict[str, str]]:
    categories = [
        "ライフハック",
        "時事ネタ",
        "統計話題",
        "科学トリビア",
        "健康常識（断定NG）",
        "歴史の豆知識",
        "宇宙・天文",
        "心理学・行動科学",
        "テクノロジー動向",
        "カルチャー・エンタメ",
    ]
    categories_str = " / ".join(categories)

    system_prompt = """あなたは YouTube 雑学・解説動画チャンネル向けの企画編集者AIです。
直近〜今後1ヶ月に日本で伸びそうな雑学/豆知識/ライフハックネタを考え、JSONだけを返してください。
炎上や誹謗中傷、危険行為、医療断定などセンシティブすぎる話題は避けてください。"""
    schema_hint = """
出力フォーマット（JSONのみ、コメントや説明は不要）:
{
  "generated_at": "2025-12-09T18:30:00+09:00",
  "language": "ja",
  "time_range": "last_30_days",
  "keywords": ["くしゃみが出る仕組み","ブラックホールの時間の進み方"],
  "briefs": [
    {
      "keyword": "くしゃみが出る仕組み",
      "brief": "鼻腔が異物を感知したときの神経反射を解説する",
      "keywords": ["くしゃみ", "反射", "鼻腔"],
      "seed_phrases": ["くしゃみは脳幹が制御する反射", "異物排出の防御反応", "0.1秒で全身が連動する"]
    }
  ],
  "ideas": [
    {
      "id": "20251209-001",
      "keyword": "ブラックホールの時間の進み方",
      "category": "宇宙・天文",
      "region": "JP",
      "title": "ブラックホール付近で時間が遅くなる理由",
      "brief": "重力による時空の歪みを日常例に置き換えて解説する",
      "seed_phrases": ["重力は時間を引き伸ばす", "イベントホライズンでは光も逃げない"],
      "tags": ["宇宙", "科学"],
      "suggested_theme_id": "space_trivia",
      "priority_score": 0.9,
      "estimated_lifespan_days": 30,
      "nsfw": false
    }
  ]
}
"""
    category_hint = f"カテゴリは「{category}」で固定してください。" if category else f"必ず category を次のリストから選択してください: {categories_str}"
    extra_hint = ""
    if extra_keyword:
        extra_hint = f"追加キーワード「{extra_keyword}」に関連した切り口を必ず混ぜてください。偏りすぎないように、全{max_ideas}件のうち一部は関連トピックで構成してください。"
    user_prompt = f"""日本向けショート雑学/解説動画のネタを最大 {max_ideas} 件返してください。
language="{language}"、region="JP" を前提に、priority_score が高い順になるようにしてください。
{category_hint}
{extra_hint}
各トピックには 12〜18 文字程度の短いタイトル、1〜2文の brief、そして 6〜10 個の短い断言フレーズ (seed_phrases) を含めてください。"""
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": schema_hint.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]


CODE_FENCE_RE = re.compile(r"^```[\w-]*\s*", re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """Gemini などが ```json ... ``` 形式で返してきた場合に備えて除去する。"""
    if not isinstance(text, str):
        return text
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = CODE_FENCE_RE.sub("", stripped, count=1)
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def parse_and_validate(json_text: str, max_ideas: int) -> Dict[str, Any]:
    cleaned = _strip_code_fences(json_text)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object.")
    ideas = data.get("ideas")
    if not isinstance(ideas, list) or not ideas:
        raise ValueError("LLM response does not contain 'ideas'.")
    # Normalize
    cleaned = []
    for item in ideas:
        if not isinstance(item, dict):
            continue
        if item.get("nsfw") is True:
            continue
        item["priority_score"] = float(item.get("priority_score") or 0.0)
        cleaned.append(item)
    cleaned.sort(key=lambda x: x.get("priority_score", 0.0), reverse=True)
    data["ideas"] = cleaned[:max_ideas]
    if "generated_at" not in data:
        data["generated_at"] = datetime.now(timezone(timedelta(hours=9))).isoformat()
    if "language" not in data:
        data["language"] = "ja"
    if "keywords" not in data or not isinstance(data.get("keywords"), list):
        data["keywords"] = [
            item.get("keyword") or item.get("title")
            for item in data["ideas"]
            if isinstance(item, dict) and (item.get("keyword") or item.get("title"))
        ]
    if "briefs" not in data or not isinstance(data.get("briefs"), list):
        briefs: List[dict] = []
        for item in data["ideas"]:
            if not isinstance(item, dict):
                continue
            brief = item.get("brief")
            if not brief:
                continue
            briefs.append(
                {
                    "keyword": item.get("keyword") or item.get("title"),
                    "brief": brief,
                    "keywords": item.get("related_keywords") or item.get("keywords") or [],
                    "seed_phrases": item.get("seed_phrases") or [],
                }
            )
        data["briefs"] = briefs
    return data


def log_invalid_response(raw_text: str, err: Exception) -> Path:
    """保存してデバッグしやすくする。"""
    LLM_ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = LLM_ERROR_LOG_DIR / f"trend_ideas_invalid_{ts}.txt"
    message = f"# Error: {err}\n# Saved at: {datetime.now().isoformat()}\n\n{raw_text}"
    path.write_text(message, encoding="utf-8", errors="ignore")
    return path


def save_output(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch trend ideas via LLM and save as JSON.")
    parser.add_argument("--output", type=Path, help="出力先 JSON パス。未指定なら scripts/generated/trend_ideas_<timestamp>.json")
    parser.add_argument("--max-ideas", type=int, default=50, help="取得するアイデアの最大数")
    parser.add_argument("--language", default="ja", help="言語ヒント (default: ja)")
    parser.add_argument("--extra-keyword", help="追加キーワード（関連トピックを混ぜるヒント）")
    parser.add_argument("--provider", choices=["openai", "anthropic", "gemini"], help="LLM プロバイダ")
    parser.add_argument("--api-key", help="API キー（未指定時は設定ファイル/環境変数）")
    parser.add_argument("--model", help="モデル ID")
    parser.add_argument("--base-url", help="OpenAI 互換エンドポイントのベース URL")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=6000)
    parser.add_argument("--stdout", action="store_true", help="JSON をファイルではなく標準出力へ書き出す")
    return parser.parse_args()


def resolve_output_path(args: argparse.Namespace) -> Path:
    if args.output:
        return args.output
    target_dir = PROJECT_ROOT / "scripts" / "generated"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return target_dir / f"trend_ideas_{timestamp}.json"


def main() -> None:
    args = parse_args()
    try:
        data = fetch_trend_ideas_via_llm(
            max_ideas=args.max_ideas,
            language=args.language,
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
            base_url=args.base_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            extra_keyword=args.extra_keyword,
        )
        output_path = resolve_output_path(args)
        if args.stdout:
            json.dump(data, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
            sys.stdout.flush()
        else:
            save_output(data, output_path)
            ideas_len = len(data.get("ideas", []))
            print(f"[OK] Saved {ideas_len} ideas to {output_path}")
    except (LLMError, ValueError, json.JSONDecodeError) as err:
        raise SystemExit(f"[ERROR] {err}") from err


def fetch_trend_ideas_via_llm(
    *,
    max_ideas: int = 50,
    language: str = "ja",
    category: str | None = None,
    extra_keyword: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 6000,
    retries: int = 2,
    _fallback: bool = False,
) -> Dict[str, Any]:
    """Programmatic API to fetch trend ideas as dict."""
    args = argparse.Namespace(
        max_ideas=max_ideas,
        language=language,
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    client = build_client(args)
    messages = build_messages(language, max_ideas, category, extra_keyword)
    attempts = max(1, retries)
    last_err: Exception | None = None
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        response_text = client.generate_json(messages)
        try:
            return parse_and_validate(response_text, max_ideas)
        except (ValueError, json.JSONDecodeError) as err:
            log_path = log_invalid_response(response_text, err)
            print(
                f"[WARN] LLM response parsing failed (attempt {attempt}/{attempts}). "
                f"Raw response saved to {log_path}. Error: {err}"
            )
            last_err = err
            if attempt < attempts:
                time.sleep(1)
                continue
    # retries exhausted
    if last_err:
        reduced = max(5, max_ideas // 2)
        if not _fallback and reduced < max_ideas:
            print(
                f"[WARN] LLM JSON parsing failed repeatedly; retrying with max_ideas={reduced} "
                "(レスポンスを短くして取得します)"
            )
            return fetch_trend_ideas_via_llm(
                max_ideas=reduced,
                language=language,
                provider=provider,
                api_key=api_key,
                model=model,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens,
                retries=retries,
                _fallback=True,
            )
        raise last_err
    if last_err:
        raise last_err
    raise RuntimeError("LLM response parsing failed without specific error.")


if __name__ == "__main__":
    main()
