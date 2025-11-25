#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.script_io import load_config, load_script  # noqa: E402
from src.timeline import build_timeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Describe timeline durations as JSON.")
    parser.add_argument("--script", required=True, type=Path, help="ScriptModel YAML path")
    parser.add_argument("--config", type=Path, help="Optional ConfigModel path")
    parser.add_argument("--json", action="store_true", help="Output JSON (default)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script = load_script(args.script)
    config = load_config(args.config)
    audio_dir = config.work_dir / "audio"
    timeline = build_timeline(script, audio_dir)

    payload = {
        "total_duration": timeline.total_duration,
        "sections": [
            {
                "id": section.id,
                "index": section.index,
                "start": section.start_sec,
                "duration": section.duration_sec,
                "audio_path": str(section.audio_path) if section.audio_path else None,
                "has_audio": bool(section.audio_path and section.audio_path.exists()),
            }
            for section in timeline.sections
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
