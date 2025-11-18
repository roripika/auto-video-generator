#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.assets import (  # noqa: E402
    AssetCache,
    AssetFetcher,
    AssetKind,
    PexelsClient,
    PixabayClient,
    StableDiffusionClient,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search and download background assets into assets/cache.",
    )
    parser.add_argument("--keyword", required=True, help="Search keyword (genre + hook).")
    parser.add_argument(
        "--kind",
        choices=[AssetKind.VIDEO.value, AssetKind.IMAGE.value],
        default=AssetKind.VIDEO.value,
        help="Type of asset to fetch.",
    )
    parser.add_argument("--max-results", type=int, default=3)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("assets/cache"),
    )
    parser.add_argument(
        "--pexels-key",
        default=os.getenv("PEXELS_API_KEY"),
        help="Override Pexels API key (otherwise uses env).",
    )
    parser.add_argument(
        "--pixabay-key",
        default=os.getenv("PIXABAY_API_KEY"),
        help="Override Pixabay API key (otherwise uses env).",
    )
    parser.add_argument(
        "--sd-key",
        default=os.getenv("STABILITY_API_KEY"),
        help="Override Stable Diffusion API key (otherwise uses env).",
    )
    parser.add_argument(
        "--disable-ai",
        action="store_true",
        help="Do not fall back to AI image generation.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (default: INFO).",
    )
    parser.add_argument(
        "--provider-order",
        help="Comma-separated provider order (default: pexels,pixabay).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="結果を JSON 配列で標準出力へ書き出す（ログ出力は抑制）。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    cache = AssetCache(base_dir=args.cache_dir)

    ai_generator = None
    if not args.disable_ai and args.sd_key:
        ai_generator = StableDiffusionClient(api_key=args.sd_key)

    fetcher = AssetFetcher(
        cache=cache,
        pexels=PexelsClient(api_key=args.pexels_key),
        pixabay=PixabayClient(api_key=args.pixabay_key),
        ai_generator=ai_generator,
    )

    downloads = fetcher.fetch(
        args.keyword,
        kind=AssetKind(args.kind),
        max_results=args.max_results,
        allow_ai=not args.disable_ai,
        provider_order=[p.strip() for p in args.provider_order.split(",")] if args.provider_order else None,
    )

    if args.json:
        payload = [
            {
                "path": str(item.path),
                "metadata_path": str(item.metadata_path),
                "provider": item.asset.provider,
                "kind": item.asset.kind.value,
                "url": item.asset.url,
                "preview_url": item.asset.preview_url,
                "width": item.asset.width,
                "height": item.asset.height,
                "duration": item.asset.duration,
            }
            for item in downloads
        ]
        print(json.dumps(payload, ensure_ascii=False))
        return

    if not downloads:
        print("No assets were downloaded. Check API keys or try another keyword.")
        return

    for item in downloads:
        print(f"Saved {item.asset.kind.value} from {item.asset.provider}: {item.path}")
        print(f"  metadata -> {item.metadata_path}")


if __name__ == "__main__":
    main()
