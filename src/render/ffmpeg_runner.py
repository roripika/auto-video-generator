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
    return text.replace("'", "\\'")


def _db_to_linear(value_db: float) -> float:
    return 10 ** (value_db / 20.0)


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


def _add_credits_overlay(
    base_label: str,
    script: ScriptModel,
    timeline: TimelineSummary,
) -> tuple[str, str]:
    credits = script.credits
    if not credits or not credits.enabled or not credits.text:
        return base_label, ""

    start = max(timeline.total_duration - 4.0, 0.0)
    end = timeline.total_duration + 0.5
    font_size = max(int(script.text_style.fontsize * 0.75), 32)
    text = _escape_text(credits.text)
    label = "[vcred]"
    filter_chain = (
        f"{base_label}drawtext="
        f"fontfile='{script.text_style.font}':"
        f"text='{text}':"
        f"fontsize={font_size}:"
        f"fontcolor=white:"
        f"borderw=2:"
        f"bordercolor=black:"
        f"x={_format_position(credits.position, 'x')}:"
        f"y={_format_position(credits.position, 'y')}:"
        f"enable='between(t,{start:.2f},{end:.2f})'{label}"
    )
    return label, filter_chain


def build_ffmpeg_command(
    script: ScriptModel,
    timeline: TimelineSummary,
    audio_dir: Path,
    output_path: Path,
    ffmpeg_path: str = "ffmpeg",
) -> List[str]:
    input_args: List[str] = []
    input_index = 0

    def add_input(args: List[str]) -> int:
        nonlocal input_index
        input_args.extend(args)
        idx = input_index
        input_index += 1
        return idx

    bg_path = script.video.bg
    total_duration = max(timeline.total_duration, 1.0)

    # Background video or image (always index 0)
    if Path(bg_path).suffix.lower() in IMAGE_EXTENSIONS:
        add_input(["-loop", "1", "-t", str(total_duration), "-i", bg_path])
    else:
        add_input(["-i", bg_path])

    # Section narration WAV inputs
    voice_indices: List[int] = []
    for section in timeline.sections:
        if section.audio_path and section.audio_path.exists():
            voice_indices.append(add_input(["-i", str(section.audio_path)]))

    # Optional BGM input
    bgm_index = None
    if script.bgm and script.bgm.file:
        bgm_path = Path(script.bgm.file)
        if bgm_path.exists():
            bgm_index = add_input(["-stream_loop", "-1", "-i", str(bgm_path)])

    # Optional watermark input (as image)
    watermark_index = None
    if script.watermark and script.watermark.file:
        wm_path = Path(script.watermark.file)
        if wm_path.exists():
            watermark_index = add_input(["-i", str(wm_path)])

    filter_parts: List[str] = []

    # Video – drawtext per section
    drawtext = _build_drawtext_filters(script.text_style, timeline)
    video_label = "[0:v]"
    if drawtext:
        filter_parts.append(f"{video_label}{drawtext}[vtext]")
        video_label = "[vtext]"
    else:
        filter_parts.append(f"{video_label}copy[vtext]")
        video_label = "[vtext]"

    # Watermark overlay (if available)
    if watermark_index is not None:
        x_pos = _format_position(script.watermark.position, "x")
        y_pos = _format_position(script.watermark.position, "y")
        watermark_label = f"[{watermark_index}:v]"
        filter_parts.append(
            f"{video_label}{watermark_label}overlay=x={x_pos}:y={y_pos}:format=auto:shortest=1[vwm]"
        )
        video_label = "[vwm]"

    # Credits overlay (appears near the end)
    credit_label, credit_filter = _add_credits_overlay(video_label, script, timeline)
    if credit_filter:
        filter_parts.append(credit_filter)
        video_label = credit_label

    # Audio – narration concat or silent fallback
    if voice_indices:
        labels = "".join(f"[{idx}:a]" for idx in voice_indices)
        filter_parts.append(f"{labels}concat=n={len(voice_indices)}:v=0:a=1[voice]")
        voice_label = "[voice]"
    else:
        filter_parts.append("anullsrc=channel_layout=stereo:sample_rate=44100[voice]")
        voice_label = "[voice]"

    audio_output_label = voice_label

    # BGM + ducking mix
    if bgm_index is not None:
        bgm_volume = _db_to_linear(script.bgm.volume_db)
        duration_pad = total_duration + 1.0
        filter_parts.append(
            f"[{bgm_index}:a]apad=pad_dur={duration_pad},atrim=duration={duration_pad},"
            f"asetpts=PTS-STARTPTS,volume={bgm_volume:.4f}[bgm]"
        )
        bgm_label = "[bgm]"
        if script.bgm.ducking_db:
            # Sidechain compress BGM using narration as sidechain source
            filter_parts.append(
                f"{bgm_label}{voice_label}sidechaincompress="
                f"threshold=-32dB:ratio=8:attack=5:release=250:makeup=0[bgmduck]"
            )
            bgm_label = "[bgmduck]"
        filter_parts.append(
            f"{bgm_label}{voice_label}amix=inputs=2:duration=longest:dropout_transition=0[aout]"
        )
        audio_output_label = "[aout]"

    filter_complex = ";".join(filter_parts)

    command = [
        ffmpeg_path,
        "-y",
        *input_args,
        "-filter_complex",
        filter_complex,
        "-map",
        video_label,
        "-map",
        audio_output_label,
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
