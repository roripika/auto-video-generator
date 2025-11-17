#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.assets import AssetFetcher, AssetKind, DownloadedAsset  # noqa: E402
from src.audio.voicevox_client import VoicevoxClient, VoicevoxError  # noqa: E402
from src.outputs import write_metadata, write_srt  # noqa: E402
from src.render.ffmpeg_runner import build_ffmpeg_command  # noqa: E402
from src.script_io import load_config, load_script  # noqa: E402
from src.timeline import build_timeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate full explainer video from ScriptModel YAML.")
    parser.add_argument("--script", required=True, type=Path, help="ScriptModel 互換 YAML ファイル")
    parser.add_argument("--config", type=Path, help="オプションの ConfigModel (JSON/YAML)")
    parser.add_argument("--skip-audio", action="store_true", help="既存 WAV を再利用し、VOICEVOX 合成をスキップ")
    parser.add_argument("--force-audio", action="store_true", help="既存 WAV があっても再生成する")
    parser.add_argument("--dry-run", action="store_true", help="ffmpeg を実行せずにコマンドのみ表示する")
    return parser.parse_args()


def ensure_background_asset(script) -> DownloadedAsset | None:
    """背景動画が存在しない場合、AssetFetcher で補完する。"""
    bg_path = Path(script.video.bg)
    if bg_path.exists():
        return None

    fetcher = AssetFetcher()
    keyword_candidates = [
        script.title,
        getattr(script, "project", None),
    ]
    for section in getattr(script, "sections", []):
        if section.on_screen_text:
            keyword_candidates.append(section.on_screen_text)
            break
        if section.narration:
            keyword_candidates.append(section.narration)
            break

    keyword = next((k for k in keyword_candidates if k), "ライフハック 背景")
    results = fetcher.fetch(keyword, kind=AssetKind.VIDEO, max_results=1, allow_ai=False)
    if results:
        script.video.bg = str(results[0].path)
        print(f"[INFO] 背景素材を自動取得: {script.video.bg}")
        return results[0]
    else:
        print(f"[WARN] 背景素材が見つかりませんでした（キーワード: {keyword}）。指定パスをそのまま使用します。")
    return None


def ensure_audio(
    script,
    config,
    *,
    skip_audio: bool,
    force_audio: bool,
) -> Path:
    audio_dir = config.work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    if skip_audio:
        return audio_dir

    client = VoicevoxClient(
        base_url=config.voicevox_endpoint,
        timeout_sec=config.timeout_sec,
        retries=config.retries,
    )

    for idx, section in enumerate(script.sections, start=1):
        text = (section.narration or "").strip()
        if not text:
            continue
        out_path = audio_dir / f"{idx:02d}_{section.id}.wav"
        if out_path.exists() and not force_audio:
            print(f"[SKIP] {out_path.name} (exists)")
            continue
        try:
            wav_bytes = client.synthesize(text, script.voice)
        except VoicevoxError as err:
            raise SystemExit(f"[ERROR] VOICEVOX synthesis failed for section {section.id}: {err}") from err
        out_path.write_bytes(wav_bytes)
        print(f"[OK] {out_path}")
    return audio_dir


def run_ffmpeg(command: list[str], dry_run: bool) -> None:
    cmd_str = " ".join(command)
    print(f"[FFmpeg] {cmd_str}")
    if dry_run:
        print("[DRY RUN] ffmpeg command was not executed.")
        return
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as err:
        raise SystemExit(f"[ERROR] ffmpeg failed with exit code {err.returncode}") from err


def main() -> None:
    args = parse_args()
    script = load_script(args.script)
    config = load_config(args.config)

    bg_asset = ensure_background_asset(script)

    audio_dir = ensure_audio(
        script,
        config,
        skip_audio=args.skip_audio,
        force_audio=args.force_audio,
    )

    timeline = build_timeline(script, audio_dir)
    print(f"[INFO] Total duration: {timeline.total_duration:.2f}s across {len(timeline.sections)} sections.")

    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    output_path = config.outputs_dir / script.output.filename

    ffmpeg_cmd = build_ffmpeg_command(
        script=script,
        timeline=timeline,
        audio_dir=audio_dir,
        output_path=output_path,
        ffmpeg_path=config.ffmpeg_path,
    )
    run_ffmpeg(ffmpeg_cmd, args.dry_run)

    if script.output.srt:
        srt_path = output_path.with_suffix(".srt")
        write_srt(timeline, srt_path)
        print(f"[OK] SRT: {srt_path}")

    metadata_path = output_path.with_suffix(".json")
    write_metadata(script, timeline, metadata_path, background_asset=bg_asset)
    print(f"[OK] Metadata: {metadata_path}")

    print(f"[DONE] Video written to {output_path}")


if __name__ == "__main__":
    main()
