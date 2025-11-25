#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from datetime import datetime
import json
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = PROJECT_ROOT / "settings" / "ai_settings.json"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.script_generation import (  # noqa: E402
    build_llm_client,
    LLMError,
    ScriptFromBriefGenerator,
    ScriptGenerationError,
)
from src.themes import get_theme_by_id  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate ScriptModel-compatible YAML from natural language briefs using an LLM."
    )
    parser.add_argument("--brief", help="自然文/箇条書きのブリーフを直接指定。")
    parser.add_argument("--brief-file", type=Path, help="ブリーフが記載されたテキストファイル。")
    parser.add_argument("--theme-id", default="lifehack_surprise", help="configs/themes/ 内のテーマ ID。")
    parser.add_argument("--sections", type=int, help="ランキング項目数。未指定時はテーマ設定に従う。")
    parser.add_argument("--output", type=Path, help="生成した YAML の出力先。未指定時は scripts/generated/ 以下。")
    parser.add_argument("--stdout", action="store_true", help="生成結果をファイルではなく標準出力へ書き出す。")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "gemini"],
        help="利用する AI プロバイダ。未指定時は設定ファイルまたは openai。",
    )
    parser.add_argument("--api-key", help="LLM API キー（未指定時は各プロバイダの環境変数を参照）。")
    parser.add_argument("--model", help="使用するモデル ID（例: gpt-4o-mini）。未指定時は OPENAI_MODEL 環境変数を参照。")
    parser.add_argument("--base-url", help="OpenAI 互換エンドポイントのベース URL。")
    parser.add_argument("--temperature", type=float, default=0.4, help="LLM 温度。")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=6000,
        help="LLM 応答の最大トークン数（JSON が途中で切れる場合は増やす）。",
    )
    return parser.parse_args()


def load_brief(args: argparse.Namespace) -> str:
    if args.brief:
        return args.brief
    if args.brief_file:
        if not args.brief_file.exists():
            raise SystemExit(f"Brief file not found: {args.brief_file}")
        return args.brief_file.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("ブリーフが指定されていません。--brief / --brief-file もしくは標準入力を利用してください。")


def resolve_output_path(args: argparse.Namespace, project_id: str) -> Path:
    if args.output:
        return args.output
    target_dir = PROJECT_ROOT / "scripts" / "generated"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return target_dir / f"{project_id}_{timestamp}.yaml"


def load_saved_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        sys.stderr.write("Warning: settings/ai_settings.json が壊れているため無視します。\n")
        return {}


def main() -> None:
    args = parse_args()
    brief = load_brief(args)
    theme = get_theme_by_id(args.theme_id) if args.theme_id else None
    section_count = args.sections or (theme.ranking.default_items if theme else 5)
    saved_settings = load_saved_settings()

    provider = (
        args.provider
        or saved_settings.get("activeProvider")
        or saved_settings.get("provider")
        or "openai"
    )
    providers_map = saved_settings.get("providers") if isinstance(saved_settings.get("providers"), dict) else {}
    provider_cfg = providers_map.get(provider, {}) if isinstance(providers_map, dict) else {}
    api_key = args.api_key or provider_cfg.get("apiKey") or saved_settings.get("apiKey")
    model = args.model or provider_cfg.get("model") or saved_settings.get("model")
    base_url = args.base_url or provider_cfg.get("baseUrl") or saved_settings.get("baseUrl")

    try:
        client = build_llm_client(
            provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
    except LLMError as err:
        raise SystemExit(f"[ERROR] {err}") from err
    generator = ScriptFromBriefGenerator(llm=client, theme=theme, section_count=section_count)

    try:
        script = generator.generate(brief)
    except ScriptGenerationError as err:
        raise SystemExit(f"[ERROR] {err}") from err

    yaml_data = yaml.safe_dump(
        script.model_dump(mode="json"),
        allow_unicode=True,
        sort_keys=False,
    )
    if args.stdout:
        sys.stdout.write(yaml_data)
        sys.stdout.flush()
        return

    output_path = resolve_output_path(args, script.project)
    output_path.write_text(yaml_data, encoding="utf-8")
    print(f"[OK] Script saved to {output_path}")


if __name__ == "__main__":
    main()
