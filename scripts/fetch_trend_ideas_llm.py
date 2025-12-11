#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "settings" / "ai_settings.json"
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


def build_messages(language: str, max_ideas: int) -> List[Dict[str, str]]:
    system_prompt = """あなたは YouTube 雑学・解説動画チャンネル向けの企画編集者AIです。
直近および今後1ヶ月程度に日本で伸びそうなトピックを考え、JSONだけを返してください。
ゴシップ過多、誹謗中傷、過度にセンシティブな話題は避けてください。"""
    schema_hint = """
出力フォーマット（JSONのみ、コメントや説明は不要）:
{
  "generated_at": "2025-12-09T18:30:00+09:00",
  "language": "ja",
  "time_range": "last_30_days",
  "ideas": [
    {
      "id": "20251209-001",
      "keyword": "ミャクミャク",
      "category": "ネット流行語",
      "region": "JP",
      "title": "大阪万博キャラ『ミャクミャク』が炎上した本当の理由3選",
      "brief": "動画全体の趣旨・切り口が分かるブリーフ（日本語）",
      "thumbnail": { "headline": "ミャクミャク炎上の裏側", "subhead": "大阪万博キャラに何が？" },
      "tags": ["雑学", "ネット文化", "大阪万博"],
      "suggested_theme_id": "trivia_social",
      "priority_score": 0.9,
      "estimated_lifespan_days": 30,
      "nsfw": false
    }
  ]
}
"""
    user_prompt = f"""直近のトレンドから、YouTube向け雑学/解説動画で伸びそうなネタを最大 {max_ideas} 件返してください。
language="{language}"、region="JP"を前提に、priority_score が高い順になるようにしてください。"""
    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": schema_hint.strip()},
        {"role": "user", "content": user_prompt.strip()},
    ]


def parse_and_validate(json_text: str, max_ideas: int) -> Dict[str, Any]:
    data = json.loads(json_text)
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
    return data


def save_output(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch trend ideas via LLM and save as JSON.")
    parser.add_argument("--output", type=Path, help="出力先 JSON パス。未指定なら scripts/generated/trend_ideas_<timestamp>.json")
    parser.add_argument("--max-ideas", type=int, default=50, help="取得するアイデアの最大数")
    parser.add_argument("--language", default="ja", help="言語ヒント (default: ja)")
    parser.add_argument("--provider", choices=["openai", "anthropic", "gemini"], help="LLM プロバイダ")
    parser.add_argument("--api-key", help="API キー（未指定時は設定ファイル/環境変数）")
    parser.add_argument("--model", help="モデル ID")
    parser.add_argument("--base-url", help="OpenAI 互換エンドポイントのベース URL")
    parser.add_argument("--temperature", type=float, default=0.4)
    parser.add_argument("--max-tokens", type=int, default=6000)
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
        )
        output_path = resolve_output_path(args)
        save_output(data, output_path)
        ideas_len = len(data.get("ideas", []))
        print(f"[OK] Saved {ideas_len} ideas to {output_path}")
    except (LLMError, ValueError, json.JSONDecodeError) as err:
        raise SystemExit(f"[ERROR] {err}") from err


def fetch_trend_ideas_via_llm(
    *,
    max_ideas: int = 50,
    language: str = "ja",
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 6000,
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
    messages = build_messages(language, max_ideas)
    response_text = client.generate_json(messages)
    return parse_and_validate(response_text, max_ideas)


if __name__ == "__main__":
    main()
