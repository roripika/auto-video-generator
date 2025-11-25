#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.audio.voicevox_client import VoicevoxClient, VoicevoxError
from src.script_io import load_config, load_script


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate narration WAV files using VOICEVOX")
    parser.add_argument("--script", required=True, type=Path, help="Path to script YAML")
    parser.add_argument("--config", type=Path, help="Optional config JSON path")
    args = parser.parse_args()

    script = load_script(args.script)
    config = load_config(args.config)

    work_audio_dir = config.work_dir / "audio"
    work_audio_dir.mkdir(parents=True, exist_ok=True)

    client = VoicevoxClient(
        base_url=config.voicevox_endpoint,
        timeout_sec=config.timeout_sec,
        retries=config.retries,
    )

    for idx, section in enumerate(script.sections, start=1):
        text = section.narration.strip()
        if not text:
            continue
        wav_bytes = client.synthesize(text, script.voice)
        out_path = work_audio_dir / f"{idx:02d}_{section.id}.wav"
        out_path.write_bytes(wav_bytes)
        print(f"[OK] {out_path}")

    print("All sections processed.")


if __name__ == "__main__":
    main()
