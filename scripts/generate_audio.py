#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from src.audio.voicevox_client import VoicevoxClient, VoicevoxError
from src.models import ConfigModel, ScriptModel


def load_script(path: Path) -> ScriptModel:
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return ScriptModel(**data)


def load_config(path: Path | None) -> ConfigModel:
    if path is None:
        return ConfigModel()
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        raw = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    return ConfigModel(**raw)


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
