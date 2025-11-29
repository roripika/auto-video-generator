#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def fetch_trending_keywords(geo: str) -> List[str]:
    """Fetch daily trending search keywords (up to 100) from Google Trends RSS."""
    url = f"https://trends.google.com/trendingsearches/daily/rss?geo={geo.upper()}"
    try:
        import requests

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        titles = [item.findtext("title") or "" for item in root.findall(".//item")]
        # First <title> is feed title; skip empty and deduplicate while preserving order.
        seen = set()
        keywords: List[str] = []
        for title in titles:
            title = title.strip()
            if not title or title in seen:
                continue
            seen.add(title)
            keywords.append(title)
            if len(keywords) >= 100:  # 固定で上位100件まで
                break
        return keywords
    except Exception as err:
        print(f"[WARN] Failed to fetch Google Trends RSS: {err}")
        return []


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
    return slug or "keyword"


def select_hot_keywords_via_llm(keywords: List[str], top_n: int) -> List[str]:
    """Ask LLM to pick promising topics from keyword list.

    Falls back to the first N keywords on any error.
    """
    top_n = max(1, min(top_n, len(keywords)))
    try:
        import requests
    except ImportError:
        return keywords[:top_n]

    api_key = sys.environ.get("OPENAI_API_KEY") or sys.environ.get("OPENAI_APIKEY")
    if not api_key:
        return keywords[:top_n]

    system_prompt = """
あなたはコンテンツ企画の編集者です。与えられたトレンドキーワード一覧から、日本語の動画にしたときに伸びそうなものを上位順に厳選してください。返答は JSON 配列で、キーワード文字列のみを含めてください。
"""
    user_prompt = "\n".join(f"- {kw}" for kw in keywords[:100])
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"候補から上位 {top_n} 件を返してください:\n{user_prompt}"},
        ],
        "max_tokens": 512,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if isinstance(parsed, list):
            picked = [kw for kw in parsed if isinstance(kw, str)]
        elif isinstance(parsed, dict):
            # accept {"keywords": [..]}
            arr = parsed.get("keywords") if isinstance(parsed.get("keywords"), list) else []
            picked = [kw for kw in arr if isinstance(kw, str)]
        else:
            picked = []
        picked = [kw for kw in picked if kw in keywords]
        if len(picked) < top_n:
            # fill from original order
            for kw in keywords:
                if kw not in picked:
                    picked.append(kw)
                if len(picked) >= top_n:
                    break
        return picked[:top_n]
    except Exception as err:
        print(f"[WARN] LLM keyword selection failed, falling back to first {top_n}: {err}")
        return keywords[:top_n]


def run_script_generation(keyword: str, brief_template: str, theme_id: str, sections: int, output_dir: Path) -> Optional[Path]:
    """Invoke generate_script_from_brief.py to produce a Script YAML for the keyword."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = slugify(keyword)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}_{ts}.yaml"

    brief = brief_template.format(keyword=keyword)
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_script_from_brief.py"),
        "--brief",
        brief,
        "--theme-id",
        theme_id,
        "--sections",
        str(sections),
        "--output",
        str(output_path),
    ]
    print(f"[INFO] Generating script for '{keyword}' -> {output_path}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Script generation failed for '{keyword}': {result.stderr or result.stdout}")
        return None
    return output_path


def run_video_generation(script_path: Path, config_path: Optional[Path]) -> Optional[Path]:
    """Invoke generate_video.py for the given script."""
    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "scripts" / "generate_video.py"),
        "--script",
        str(script_path),
    ]
    if config_path:
        cmd += ["--config", str(config_path)]
    print(f"[INFO] Generating video for {script_path}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] Video generation failed for {script_path}: {result.stderr or result.stdout}")
        return None

    # Best-effort: list newest mp4 under outputs/rendered
    rendered_dir = PROJECT_ROOT / "outputs" / "rendered"
    if not rendered_dir.exists():
        return None
    mp4s = sorted(rendered_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0] if mp4s else None


def clear_audio_cache(work_dir: Path) -> None:
    """Remove cached audio to avoid reuse across runs."""
    targets = [work_dir / "audio", work_dir / "video", work_dir / "tmp"]
    for target in targets:
        if target.exists():
            try:
                shutil.rmtree(target)
                print(f"[INFO] Cleared cache: {target}")
            except Exception as err:
                print(f"[WARN] Failed to clear cache {target}: {err}")


def maybe_upload_to_youtube(video_path: Path, title: str, description: str, tags: Iterable[str], client_secrets: Optional[Path], credentials_path: Optional[Path]) -> bool:
    """Upload video to YouTube if dependencies and credentials are present."""
    if not client_secrets:
        print("[INFO] YouTube upload skipped: --youtube-client-secrets not provided.")
        return False
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import google.oauth2.credentials
        import pickle
    except ImportError:
        print("[WARN] youtube upload skipped: google-api-python-client/google-auth not installed.")
        return False

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if credentials_path and credentials_path.exists():
        try:
            with open(credentials_path, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_console()
        if credentials_path:
            credentials_path.parent.mkdir(parents=True, exist_ok=True)
            with open(credentials_path, "wb") as token:
                pickle.dump(creds, token)

    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": list(tags),
            "categoryId": "22",  # People & Blogs
        },
        "status": {"privacyStatus": "private"},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    print(f"[INFO] Uploading {video_path} to YouTube...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"[INFO] Upload progress: {pct}%")
    print(f"[INFO] Upload completed: https://youtube.com/watch?v={response.get('id')}")
    return True


def run_once(args: argparse.Namespace) -> None:
    keywords = fetch_trending_keywords(args.geo)
    if not keywords:
        print("[WARN] No trending keywords fetched; skipping this cycle.")
        return
    picked_keywords = select_hot_keywords_via_llm(keywords, top_n=args.max_keywords)

    output_script_dir = PROJECT_ROOT / "scripts" / "generated" / "auto_trend"
    # Clear audio/cache before each cycle if requested
    if args.clear_cache:
        clear_audio_cache(PROJECT_ROOT / "work")

    for kw in picked_keywords:
        script_path = run_script_generation(
            keyword=kw,
            brief_template=args.brief_template,
            theme_id=args.theme_id,
            sections=args.sections,
            output_dir=output_script_dir,
        )
        if not script_path:
            continue
        video_path = run_video_generation(script_path, args.config)
        if not video_path:
            continue

        if args.youtube_client_secrets:
            title = f"{kw} トレンド解説"
            desc = f"{kw} に関する自動生成動画です。作成日時: {datetime.datetime.now():%Y-%m-%d %H:%M}"
            tags = [kw, "トレンド", "自動生成"]
            maybe_upload_to_youtube(
                video_path=video_path,
                title=title,
                description=desc,
                tags=tags,
                client_secrets=args.youtube_client_secrets,
                credentials_path=args.youtube_credentials,
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch Google Trends keywords -> generate script -> render video -> (optional) upload to YouTube."
    )
    parser.add_argument("--geo", default="JP", help="Google Trends geo code (e.g., JP, US).")
    parser.add_argument(
        "--max-keywords",
        type=int,
        default=100,
        help="Number of keywords to pass to AI selection (top N picked from fetched 100).",
    )
    parser.add_argument(
        "--brief-template",
        default="「{keyword}」について、視聴者が知りたいポイントをランキング形式で5つ紹介してください。驚きと実用性を意識した台本を作ってください。",
        help="Template for AI brief. '{keyword}' will be replaced with the trend keyword.",
    )
    parser.add_argument("--theme-id", default="lifehack_surprise", help="Theme ID under configs/themes/.")
    parser.add_argument("--sections", type=int, default=5, help="Number of sections per script.")
    parser.add_argument("--config", type=Path, help="Optional config YAML/JSON for generate_video.py.")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=0,
        help="If >0, repeat the cycle every N minutes (until --max-runs is reached or interrupted).",
    )
    parser.add_argument("--max-runs", type=int, default=0, help="If >0, stop after this many cycles when looping.")
    parser.add_argument("--youtube-client-secrets", type=Path, help="client_secrets.json for YouTube upload (optional).")
    parser.add_argument(
        "--youtube-credentials",
        type=Path,
        help="Path to store OAuth credentials for YouTube upload (optional but recommended when uploading).",
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear work/audio and related caches before each cycle.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runs = 0
    while True:
        runs += 1
        print(f"[INFO] === Auto trend cycle #{runs} ===")
        run_once(args)
        if args.interval_minutes <= 0:
            break
        if args.max_runs and runs >= args.max_runs:
            break
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    main()
