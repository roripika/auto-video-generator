#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.script_io import load_config, load_script  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract upload_prep (title/tags/desc) for manual uploads.")
    parser.add_argument("--script", required=True, type=Path, help="ScriptModel YAML ファイル")
    parser.add_argument("--config", type=Path, help="オプションの ConfigModel (JSON/YAML)")
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "txt"],
        default="json",
        help="出力形式（デフォルト: json）",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        help="出力ディレクトリ（省略時は config.outputs_dir/upload）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script = load_script(args.script)
    config = load_config(args.config)

    if not script.upload_prep:
        raise SystemExit("[ERROR] upload_prep が script で設定されていません。")

    outdir = args.outdir or (config.outputs_dir / "upload")
    outdir.mkdir(parents=True, exist_ok=True)

    payload = {
        "title": script.upload_prep.title,
        "tags": script.upload_prep.tags,
        "desc": script.upload_prep.desc,
    }
    stem = args.script.stem or getattr(script, "project", "upload")
    if args.format == "json":
        out_path = outdir / f"{stem}_upload.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    elif args.format == "yaml":
        out_path = outdir / f"{stem}_upload.yaml"
        out_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    else:
        out_path = outdir / f"{stem}_upload.txt"
        lines = [
            f"Title: {payload['title'] or ''}",
            f"Tags: {', '.join(payload['tags'] or [])}",
            "Desc:",
            payload["desc"] or "",
        ]
        out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"[OK] upload_prep written to {out_path}")


if __name__ == "__main__":
    main()
