from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from src.models import ThemeTemplate

THEME_DIR = Path("configs/themes")


def load_theme(path: Path) -> ThemeTemplate:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ThemeTemplate(**data)


def list_theme_templates(base_dir: Path = THEME_DIR) -> List[ThemeTemplate]:
    templates: List[ThemeTemplate] = []
    if not base_dir.exists():
        return templates
    for file_path in sorted(base_dir.glob("*.yaml")):
        try:
            templates.append(load_theme(file_path))
        except Exception as exc:  # pragma: no cover - diagnostic only
            print(f"[WARN] Failed to load theme template {file_path}: {exc}")
    return templates


def get_theme_by_id(theme_id: str, base_dir: Path = THEME_DIR) -> ThemeTemplate | None:
    for template in list_theme_templates(base_dir):
        if template.id == theme_id:
            return template
    return None
