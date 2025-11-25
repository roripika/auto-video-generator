#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.assets import ThumbnailRenderer
from src.models import ThumbnailStyle
from src.themes import get_theme_by_id, load_theme


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate thumbnails based on theme templates.")
    parser.add_argument("--theme-id", default="lifehack_surprise", help="ID of the theme to load.")
    parser.add_argument(
        "--theme-file",
        type=Path,
        help="Path to a custom theme YAML (overrides --theme-id).",
    )
    parser.add_argument("--headline", help="Main headline text. Defaults to theme thumbnail keywords.")
    parser.add_argument("--subhead", help="Subheading text. Defaults to theme genre or label.")
    parser.add_argument("--cta", help="CTA text. Defaults to theme CTA primary.")
    parser.add_argument(
        "--keyword",
        dest="keywords",
        action="append",
        help="Keyword badge text (repeatable). Defaults to theme thumbnail keywords.",
    )
    parser.add_argument(
        "--background",
        type=Path,
        help="Optional background image to composite (otherwise gradient).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output PNG path. Defaults to outputs/thumbnails/<theme>_<timestamp>.png",
    )
    return parser.parse_args()


def load_template(args: argparse.Namespace):
    if args.theme_file:
        return load_theme(args.theme_file)
    template = get_theme_by_id(args.theme_id)
    if not template:
        raise SystemExit(f"Theme '{args.theme_id}' was not found in configs/themes.")
    return template


def main() -> None:
    args = parse_args()
    template = load_template(args)

    headline = args.headline or (template.thumbnail_keywords[0] if template.thumbnail_keywords else template.label)
    subhead = args.subhead or template.genre or template.label
    cta = args.cta or template.cta.primary
    keywords = args.keywords or template.thumbnail_keywords
    output = args.output or Path("outputs/thumbnails") / f"{template.id}_{int(time.time())}.png"

    style = template.thumbnail or ThumbnailStyle()
    renderer = ThumbnailRenderer(style=style)
    renderer.render(
        headline=headline,
        subhead=subhead,
        cta=cta,
        keywords=keywords,
        output_path=output,
        background_image=args.background,
    )
    print(f"Thumbnail saved to {output}")


if __name__ == "__main__":
    main()
