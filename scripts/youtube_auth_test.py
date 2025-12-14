#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

try:
    from scripts._importlib_metadata_compat import ensure_importlib_metadata_compat  # type: ignore
except Exception:  # pragma: no cover
    ensure_importlib_metadata_compat = None  # type: ignore

if ensure_importlib_metadata_compat:
    ensure_importlib_metadata_compat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger YouTube OAuth flow without uploading.")
    parser.add_argument("--client-secrets", type=Path, required=True, help="Path to client_secrets.json")
    parser.add_argument(
        "--credentials",
        type=Path,
        required=True,
        help="Path to store OAuth credentials (pickle)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.client_secrets.exists():
        raise FileNotFoundError(f"client_secrets not found: {args.client_secrets}")

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import google.oauth2.credentials
        import pickle
    except ImportError as err:
        raise SystemExit(
            "google-auth / google-auth-oauthlib がインストールされていません。"
            "pip install google-auth google-auth-oauthlib"
        ) from err

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    if args.credentials.exists():
        try:
            with open(args.credentials, "rb") as fh:
                creds = pickle.load(fh)
        except Exception:
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(args.client_secrets), scopes)
            # Some versions do not provide run_console; run_local_server is more widely available.
            creds = flow.run_local_server(port=0)
        args.credentials.parent.mkdir(parents=True, exist_ok=True)
        with open(args.credentials, "wb") as fh:
            pickle.dump(creds, fh)
    print("YouTube OAuth authentication succeeded.")


if __name__ == "__main__":
    main()
