from __future__ import annotations

import json
from pathlib import Path

import yaml

from src.models import ConfigModel, ScriptModel


def load_script(path: Path) -> ScriptModel:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
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
