#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import requests

from src.assets import AssetFetcher, AssetKind, DownloadedAsset  # noqa: E402
from src.audio.voicevox_client import VoicevoxClient, VoicevoxError  # noqa: E402
from src.models import BGMAudio  # noqa: E402
from src.outputs import write_metadata, write_srt  # noqa: E402
from src.render.ffmpeg_runner import build_ffmpeg_command  # noqa: E402
from src.script_io import load_config, load_script  # noqa: E402
from src.timeline import build_timeline  # noqa: E402

SETTINGS_PATH = PROJECT_ROOT / "settings" / "ai_settings.json"


def load_saved_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        sys.stderr.write("[WARN] settings/ai_settings.json が壊れているため、共有設定を無視します。\n")
        return {}


def resolve_bgm_directory(settings: dict) -> Path:
    raw = os.getenv("BGM_DIRECTORY") or settings.get("bgmDirectory") or ""
    raw = raw.strip()
    if not raw:
        return PROJECT_ROOT / "assets" / "bgm"
    path = Path(raw)
    if not path.is_absolute():
        path = (PROJECT_ROOT / raw).resolve()
    return path


SHARED_SETTINGS = load_saved_settings()

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg"}
BGM_SEARCH_DIR = resolve_bgm_directory(SHARED_SETTINGS)
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or SHARED_SETTINGS.get("youtubeApiKey")
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_DOWNLOAD_DIR = BGM_SEARCH_DIR / "youtube"
DEFAULT_BGM_KEYWORDS = ["雑学 BGM", "雑学bgm", "lofi bgm"]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate full explainer video from ScriptModel YAML.")
    parser.add_argument("--script", required=True, type=Path, help="ScriptModel 互換 YAML ファイル")
    parser.add_argument("--config", type=Path, help="オプションの ConfigModel (JSON/YAML)")
    parser.add_argument("--skip-audio", action="store_true", help="既存 WAV を再利用し、VOICEVOX 合成をスキップ")
    parser.add_argument("--force-audio", action="store_true", help="既存 WAV があっても再生成する")
    parser.add_argument("--dry-run", action="store_true", help="ffmpeg を実行せずにコマンドのみ表示する")
    return parser.parse_args()


def ensure_background_assets(script) -> DownloadedAsset | None:
    """背景動画/画像が存在しない場合、AssetFetcher で補完する。"""

    def needs_download(path_value) -> bool:
        if not path_value:
            return True
        try:
            return not Path(path_value).exists()
        except Exception:
            return True

    def choose_keyword(*candidates: str | None) -> str | None:
        for candidate in candidates:
            if candidate and isinstance(candidate, str):
                value = candidate.strip()
                if value:
                    return value
        return None

    fetcher = AssetFetcher()

    def fetch_asset(keyword: str | None) -> DownloadedAsset | None:
        if not keyword:
            return None
        for kind, allow_ai in ((AssetKind.VIDEO, False), (AssetKind.IMAGE, True)):
            results = fetcher.fetch(keyword, kind=kind, max_results=1, allow_ai=allow_ai)
            if results:
                return results[0]
        return None

    global_asset: DownloadedAsset | None = None
    if needs_download(getattr(script.video, "bg", None)):
        keyword = choose_keyword(
            getattr(script.video, "bg", None),
            script.title,
            getattr(script, "project", None),
        )
        asset = fetch_asset(keyword or "ライフハック 背景")
        if asset:
            script.video.bg = str(asset.path)
            global_asset = asset
            print(f"[INFO] 背景素材を自動取得しました（全体）: {asset.path}")
        else:
            print(f"[WARN] 背景素材が見つかりませんでした（全体, keyword={keyword}）。")

    for section in getattr(script, "sections", []):
        if not needs_download(getattr(section, "bg", None)):
            continue
        section_keyword = choose_keyword(
            getattr(section, "bg_keyword", None),
            getattr(section, "bg", None),
            getattr(section, "on_screen_text", None),
            getattr(section, "narration", None),
            script.title,
        )
        asset = fetch_asset(section_keyword)
        if asset:
            section.bg = str(asset.path)
            print(f"[INFO] 背景素材を自動取得しました（{section.id}）: {asset.path}")
        else:
            print(f"[WARN] 背景素材が見つかりませんでした（{section.id}, keyword={section_keyword}）。")

    return global_asset


def ensure_bgm_track(script) -> Path | None:
    """BGM が未設定の場合、ローカルの assets/bgm から候補を選択する。"""

    def is_existing_file(path_value: str | None) -> bool:
        if not path_value:
            return False
        try:
            return Path(path_value).exists()
        except Exception:
            return False

    if script.bgm and is_existing_file(getattr(script.bgm, "file", None)):
        return Path(script.bgm.file)

    keywords = [script.title or "", getattr(script, "project", "")]
    for section in getattr(script, "sections", []):
        if getattr(section, "bg_keyword", None):
            keywords.append(section.bg_keyword)
        if getattr(section, "on_screen_text", None):
            keywords.append(section.on_screen_text)
    keywords.extend(DEFAULT_BGM_KEYWORDS)

    youtube_candidate = fetch_youtube_bgm(keywords)
    if youtube_candidate:
        target = Path(youtube_candidate)
        if not script.bgm:
            script.bgm = BGMAudio(file=str(target))
        else:
            script.bgm.file = str(target)
        if script.bgm.volume_db is None:
            script.bgm.volume_db = -12
        if script.bgm.ducking_db is None:
            script.bgm.ducking_db = -18
        print(f"[INFO] BGM を YouTube Audio Library から自動取得しました: {target}")
        return target

    if not BGM_SEARCH_DIR.exists():
        print(f"[WARN] BGM ディレクトリが見つからないため自動選択をスキップします: {BGM_SEARCH_DIR}")
        return None

    candidates = [
        path for path in BGM_SEARCH_DIR.iterdir() if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    ]
    if not candidates:
        print("[WARN] assets/bgm に利用可能なオーディオファイルがありません。")
        return None

    def score(path: Path) -> int:
        name = path.stem.lower()
        score_val = 0
        for kw in keywords:
            if not kw:
                continue
            for token in str(kw).lower().split():
                if token and token in name:
                    score_val += 2
        if "bgm" in name or "loop" in name:
            score_val += 1
        return score_val

    selected = max(candidates, key=score)
    if not script.bgm:
        script.bgm = BGMAudio(file=str(selected))
    else:
        script.bgm.file = str(selected)
        if script.bgm.volume_db is None:
            script.bgm.volume_db = -12
        if script.bgm.ducking_db is None:
            script.bgm.ducking_db = -18
    print(f"[INFO] BGM を自動選択しました: {selected}")
    return selected


def fetch_youtube_bgm(keywords: List[str]) -> Optional[Path]:
    if not YOUTUBE_API_KEY:
        return None
    query = " ".join(filter(None, keywords)).strip() or "lofi study music"
    params = {
        "key": YOUTUBE_API_KEY,
        "part": "snippet",
        "type": "video",
        "videoCategoryId": "10",
        "maxResults": 5,
        "order": "relevance",
        "q": query,
        "videoDuration": "short",
    }
    try:
        resp = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as err:
        print(f"[WARN] YouTube API から BGM 検索に失敗しました: {err}")
        return None
    items = data.get("items", [])
    for item in items:
        video_id = item.get("id", {}).get("videoId")
        title = item.get("snippet", {}).get("title")
        if not video_id:
            continue
        path = download_youtube_audio(video_id, title or video_id)
        if path:
            return path
    return None


def download_youtube_audio(video_id: str, title: str) -> Optional[Path]:
    try:
        import yt_dlp  # type: ignore
    except ImportError:
        print("[WARN] yt-dlp がインストールされていないため、YouTube からの BGM 取得をスキップします。")
        return None
    YOUTUBE_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    output_tmpl = str(YOUTUBE_DOWNLOAD_DIR / f"{video_id}.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": output_tmpl,
        "quiet": True,
        "noplaylist": True,
        "ignoreerrors": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as err:
        print(f"[WARN] YouTube 音源のダウンロードに失敗しました ({title}): {err}")
        return None
    mp3_path = YOUTUBE_DOWNLOAD_DIR / f"{video_id}.mp3"
    if mp3_path.exists():
        return mp3_path
    for ext in AUDIO_EXTENSIONS:
        candidate = YOUTUBE_DOWNLOAD_DIR / f"{video_id}{ext}"
        if candidate.exists():
            return candidate
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

    bg_asset = ensure_background_assets(script)
    ensure_bgm_track(script)

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
