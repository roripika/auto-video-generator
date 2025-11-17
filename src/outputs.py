from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.assets.types import DownloadedAsset
from src.models import ScriptModel
from src.timeline import SectionTimeline, TimelineSummary


def _format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    millis = int(round(seconds * 1000))
    ms = millis % 1000
    secs = (millis // 1000) % 60
    mins = (millis // 60000) % 60
    hours = millis // 3600000
    return f"{hours:02}:{mins:02}:{secs:02},{ms:03}"


def write_srt(timeline: TimelineSummary, output_path: Path) -> None:
    lines: List[str] = []
    for index, section in enumerate(timeline.sections, start=1):
        start = _format_timestamp(section.start_sec)
        end = _format_timestamp(section.start_sec + section.duration_sec)
        caption_lines = []
        if section.on_screen_text:
            caption_lines.append(section.on_screen_text)
        if section.narration:
            caption_lines.append(section.narration)
        text = "\n".join(caption_lines) or "(no text)"
        lines.append(str(index))
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def write_metadata(
    script: ScriptModel,
    timeline: TimelineSummary,
    output_path: Path,
    *,
    background_asset: DownloadedAsset | None = None,
) -> None:
    data: Dict[str, Any] = {
        "project": script.project,
        "title": script.title,
        "locale": script.locale,
        "total_duration_sec": timeline.total_duration,
        "sections": [
            {
                "id": section.id,
                "index": section.index,
                "start_sec": section.start_sec,
                "duration_sec": section.duration_sec,
                "audio_path": str(section.audio_path) if section.audio_path else None,
                "on_screen_text": section.on_screen_text,
                "narration": section.narration,
            }
            for section in timeline.sections
        ],
    }
    if background_asset:
        bg_meta = None
        if background_asset.metadata_path and background_asset.metadata_path.exists():
            try:
                bg_meta = json.loads(background_asset.metadata_path.read_text(encoding="utf-8"))
            except Exception:
                bg_meta = None
        data["background_asset"] = {
            "path": str(background_asset.path),
            "metadata_path": str(background_asset.metadata_path),
            "metadata": bg_meta,
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
