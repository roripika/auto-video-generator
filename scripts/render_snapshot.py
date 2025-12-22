"""
Render a single-frame preview (PNG) from a YAML script using the same FFmpeg pipeline.

Usage:
  python scripts/render_snapshot.py --script outputs/rendered/foo.yaml --output outputs/previews/foo.png

Notes:
  - 音声生成は行わず、既存の work/audio を利用します。
  - 背景/BGM の自動取得は generate_video と同じルールで ensure_background_assets/ensure_bgm_track を呼びます。
  - ffmpeg 実行は -frames:v 1 で 1 フレームのみ書き出します。
"""

import argparse
import os
from pathlib import Path

from scripts.generate_video import (
    ensure_background_assets,
    ensure_bgm_track,
    ensure_audio,
    build_timeline,
    build_ffmpeg_command,
    load_script,
    write_metadata,
)


def render_snapshot(script_path: Path, output_path: Path, ffmpeg_path: str = "ffmpeg"):
    script = load_script(script_path)
    bg_asset = ensure_background_assets(script)
    ensure_bgm_track(script)
    audio_dir = ensure_audio(script, skip_audio=True, force_audio=False)
    timeline = build_timeline(script, audio_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_cmd = build_ffmpeg_command(
        script=script,
        timeline=timeline,
        audio_dir=audio_dir,
        output_path=output_path,
        ffmpeg_path=ffmpeg_path,
    )
    # 1フレームだけ書き出す
    ffmpeg_cmd.extend(["-frames:v", "1", "-an"])
    print("[FFmpeg]", " ".join(ffmpeg_cmd))
    os.system(" ".join(ffmpeg_cmd))

    metadata_path = output_path.with_suffix(".json")
    write_metadata(script, timeline, metadata_path, background_asset=bg_asset)
    print(f"[DONE] Snapshot written to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Render single-frame snapshot from YAML script.")
    parser.add_argument("--script", required=True, help="YAML script path")
    parser.add_argument("--output", required=False, help="PNG output path")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg binary path")
    args = parser.parse_args()

    script_path = Path(args.script).expanduser().resolve()
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        previews_dir = script_path.parent.parent / "previews"
        previews_dir.mkdir(parents=True, exist_ok=True)
        output_path = previews_dir / f"{script_path.stem}_preview.png"

    render_snapshot(script_path, output_path, ffmpeg_path=args.ffmpeg)


if __name__ == "__main__":
    main()
