#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch render explainer videos")
    parser.add_argument("--glob", required=True, help="Glob pattern for script YAML files")
    parser.add_argument("--config", type=Path, help="Optional config file path")
    parser.add_argument(
        "--command",
        default="python scripts/generate_video.py",
        help="Render command to invoke per script",
    )
    args = parser.parse_args()

    scripts = list(Path(".").glob(args.glob))
    if not scripts:
        print("No scripts matched glob pattern.", file=sys.stderr)
        sys.exit(1)

    for script_path in scripts:
        command: List[str] = args.command.split()
        command.extend(["--script", str(script_path)])
        if args.config:
            command.extend(["--config", str(args.config)])
        print(f"[Batch] Running {' '.join(command)}")
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
