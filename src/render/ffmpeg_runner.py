from __future__ import annotations

import os
from pathlib import Path
from typing import List

from src.models import ScriptModel, TextPosition, TextStyle
from src.timeline import TimelineSummary

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def _format_position(value: TextPosition, axis: str) -> str:
    raw = value.x if axis == "x" else value.y
    if isinstance(raw, int):
        return str(raw)
    return raw


def _escape_text(text: str) -> str:
    return text.replace("'", "\\'" )


def _build_drawtext_filters(style: TextStyle, timeline: TimelineSummary) -> str:
    filters = []
    for section in timeline.sections:
        text = _escape_text(section.on_screen_text)
        start = max(section.start_sec, 0.0)
        end = max(section.start_sec + section.duration_sec, start + 0.1)
        filters.append(
            "drawtext="
            f"fontfile='{style.font}':"
            f"text='{text}':"
            f"fontsize={style.fontsize}:"
            f"fontcolor={style.fill}:"
            f"borderw={style.stroke.width}:"
            f"bordercolor={style.stroke.color}:"
            f"x={_format_position(style.position, 'x')}:"
            f"y={_format_position(style.position, 'y')}:"
            f"enable='between(t,{start:.2f},{end:.2f})'"
        )
    return ",".join(filters)


def build_ffmpeg_command(
    script: ScriptModel,
    timeline: TimelineSummary,
    audio_dir: Path,
    output_path: Path,
    ffmpeg_path: str = "ffmpeg",
) -> List[str]:
    inputs: List[str] = []
    bg_path = script.video.bg
    total_duration = max(timeline.total_duration, 1.0)

    if Path(bg_path).suffix.lower() in IMAGE_EXTENSIONS:
        inputs.extend(["-loop", "1", "-t", str(total_duration), "-i", bg_path])
    else:
        inputs.extend(["-i", bg_path])

    audio_inputs = []
    for section in timeline.sections:
        if section.audio_path and section.audio_path.exists():
            inputs.extend(["-i", str(section.audio_path)])
            audio_inputs.append(section)

    filter_parts = []
    drawtext = _build_drawtext_filters(script.text_style, timeline)
    if drawtext:
        filter_parts.append(f"[0:v]{drawtext}[vout]")
    else:
        filter_parts.append("[0:v]copy[vout]")

    if audio_inputs:
        labels = "".join(f"[{i + 1}:a]" for i in range(len(audio_inputs)))
        filter_parts.append(f"{labels}concat=n={len(audio_inputs)}:v=0:a=1[aout]")
    else:
        filter_parts.append("anullsrc=channel_layout=stereo:sample_rate=44100[aout]")

    filter_complex = ";".join(filter_parts)

    command = [
        ffmpeg_path,
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    return command
