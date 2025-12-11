#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PRIVACY_CHOICES = ('private', 'unlisted', 'public')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload a video file to YouTube (private).")
    parser.add_argument("--video", type=Path, required=True, help="動画ファイルパス")
    parser.add_argument("--title", required=True, help="動画タイトル")
    parser.add_argument("--description", default="", help="動画説明文")
    parser.add_argument("--tags", nargs="*", default=[], help="タグ（空白区切り）")
    parser.add_argument("--client-secrets", type=Path, required=True, help="client_secrets.json")
    parser.add_argument(
        "--credentials",
        type=Path,
        required=True,
        help="OAuth 認証トークンの保存先（pickle）",
    )
    parser.add_argument(
      "--privacy-status",
      choices=PRIVACY_CHOICES,
      default="private",
      help="公開範囲 (default: private)",
    )
    return parser.parse_args()


def ensure_creds(client_secrets: Path, credentials: Path):
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import google.oauth2.credentials
        import pickle
    except ImportError:
        raise SystemExit(
            "google-api-python-client / google-auth / google-auth-oauthlib が必要です。"
            "pip install google-api-python-client google-auth google-auth-oauthlib"
        )

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if credentials.exists():
        try:
            with open(credentials, "rb") as token:
                creds = pickle.load(token)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
            creds = flow.run_console()
        credentials.parent.mkdir(parents=True, exist_ok=True)
        with open(credentials, "wb") as token:
            pickle.dump(creds, token)
    return creds


def upload(video_path: Path, title: str, desc: str, tags, creds, privacy_status: str):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    privacy = privacy_status if privacy_status in PRIVACY_CHOICES else 'private'
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": list(tags),
            "categoryId": "22",  # People & Blogs
        },
        "status": {"privacyStatus": privacy},
    }
    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    print(f"[INFO] Uploading {video_path} ...")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"[INFO] Upload progress: {pct}%")
    video_id = response.get("id")
    print(f"[OK] Upload completed: https://youtube.com/watch?v={video_id}")
    return video_id


def main() -> None:
    args = parse_args()
    if not args.video.exists():
        raise SystemExit(f"Video file not found: {args.video}")
    if not args.client_secrets.exists():
        raise SystemExit(f"client_secrets not found: {args.client_secrets}")
    creds = ensure_creds(args.client_secrets, args.credentials)
    upload(args.video, args.title, args.description, args.tags, creds, args.privacy_status)


if __name__ == "__main__":
    main()
