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
    if not isinstance(raw, str):
        return "0"

    text_var = "text_w" if axis == "x" else "text_h"
    dim_var = "w" if axis == "x" else "h"
    token = raw.strip().lower()

    if token == "center":
        return f"({dim_var}-{text_var})/2"

    if token in {"left", "top"}:
        return "0"
    if token in {"right"}:
        return f"{dim_var}-{text_var}"
    if token in {"bottom"}:
        return f"{dim_var}-{text_var}"

    # Patterns like right-180, left+40, bottom-120, top+20
    import re

    m = re.match(r"^(left|right|top|bottom|center)([+-]\d+)$", token)
    if m:
        anchor, offset = m.groups()
        offset_val = offset
        if anchor == "center":
            base = f"({dim_var}-{text_var})/2"
            sign = "+" if offset.startswith("+") else "-"
            return f"{base}{sign}{offset[1:]}"
        if anchor in {"left", "top"}:
            base = "0"
            sign = "+" if offset.startswith("+") else "-"
            return f"{base}{sign}{offset[1:]}"
        if anchor in {"right", "bottom"}:
            base = f"{dim_var}-{text_var}"
            sign = "+" if offset.startswith("+") else "-"
            return f"{base}{sign}{offset[1:]}"

    return raw


def _escape_text(text: str) -> str:
    """Normalize newlines and escape characters that break drawtext."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    return (
        normalized.replace("\\", "\\\\")  # backslash first
        .replace("\n", r"\n")  # ffmpeg expects literal \n tokens for line breaks
        .replace(":", r"\:")
        .replace(",", r"\,")
        .replace("'", "\\'")
    )


def _db_to_linear(value_db: float) -> float:
    return 10 ** (value_db / 20.0)


def _segment_style(base: TextStyle, segment_style: TextStyle | None) -> TextStyle:
    if not segment_style:
        return base
    merged = base.model_copy(deep=True)
    for field in ["font", "fontsize", "fill", "stroke", "position", "max_chars_per_line", "lines", "animation"]:
        value = getattr(segment_style, field, None)
        if value is not None:
            setattr(merged, field, value)
    return merged


def _build_drawtext_filters(style: TextStyle, timeline: TimelineSummary, script: ScriptModel) -> str:
    filters = []
    section_map = {s.id: s for s in script.sections}
    for section in timeline.sections:
        section_model = section_map.get(section.id)
        segments = section_model.on_screen_segments if section_model else []
        if segments:
            line_offset = 0
            for seg in segments:
                seg_style = _segment_style(style, seg.style)
                text = _escape_text(seg.text)
                start = max(section.start_sec, 0.0)
                end = max(section.start_sec + section.duration_sec, start + 0.1)
                filters.append(
                    "drawtext="
                    f"fontfile='{seg_style.font}':"
                    f"text='{text}':"
                    f"fontsize={seg_style.fontsize}:"
                    f"fontcolor={seg_style.fill}:"
                    f"borderw={seg_style.stroke.width}:"
                    f"bordercolor={seg_style.stroke.color}:"
                    f"x={_format_position(seg_style.position, 'x')}:"
                    f"y={_format_position(seg_style.position, 'y')}+{line_offset}:"
                    f"enable='between(t,{start:.2f},{end:.2f})'"
                )
                line_offset += seg_style.fontsize + 8  # simple line spacing
        else:
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


def _effect_filter(effect: str, start: float, end: float) -> str | None:
    """Map a friendly effect name to a ffmpeg filter with enable window."""
    effect_lower = (effect or "").strip().lower()
    enable = f"enable='between(t,{start:.2f},{end:.2f})'"
    if effect_lower in {"blur", "soften"}:
        return f"gblur=sigma=12:{enable}"
    if effect_lower in {"grayscale", "mono", "bw"}:
        return f"hue=s=0:{enable}"
    if effect_lower in {"vignette"}:
        return f"vignette=PI/4:{enable}"
    if effect_lower in {"contrast"}:
        return f"eq=contrast=1.2:saturation=1.05:{enable}"
    # zoompan は環境依存でエラーになりやすいので一旦無効化（将来再検討）
    if effect_lower in {"zoom_in", "zoom-in"}:
        return None
    if effect_lower in {"zoom_out", "zoom-out"}:
        return None
    if effect_lower in {"zoom_pan_left", "zoompanleft"}:
        return None
    if effect_lower in {"zoom_pan_right", "zoompanright"}:
        return None
    return None


def _apply_section_effects(video_label: str, script: ScriptModel, timeline: TimelineSummary) -> tuple[str, List[str]]:
    """Apply per-section visual effects by chaining ffmpeg filters with enable windows."""
    filters: List[str] = []
    label = video_label
    section_map = {section.id: section for section in script.sections}
    for section_tl in timeline.sections:
        section = section_map.get(section_tl.id)
        if not section or not getattr(section, "effects", None):
            continue
        start = max(section_tl.start_sec, 0.0)
        end = max(section_tl.start_sec + section_tl.duration_sec, start + 0.1)
        for effect in section.effects:
            filt = _effect_filter(effect, start, end)
            if not filt:
                continue
            out_label = f"[vfx_{section_tl.id}_{effect}]"
            filters.append(f"{label}{filt}{out_label}")
            label = out_label
    return label, filters


def _build_section_videos(
    script: ScriptModel,
    timeline: TimelineSummary,
    add_input,
) -> tuple[str, List[str]]:
    filters: List[str] = []
    labels: List[str] = []
    section_map = {section.id: section for section in script.sections}

    for idx, section_tl in enumerate(timeline.sections):
        section = section_map.get(section_tl.id)
        bg_path = section.bg if section and section.bg else script.video.bg
        duration = max(section_tl.duration_sec, 0.1)
        input_idx = None

        if Path(bg_path).suffix.lower() in IMAGE_EXTENSIONS:
            input_idx = add_input(["-loop", "1", "-t", f"{duration:.2f}", "-i", bg_path])
        else:
            input_idx = add_input(["-stream_loop", "-1", "-i", bg_path])

        base_label = f"[{input_idx}:v]"
        # Trim/loop per section duration. Using trim to avoid excessive length.
        section_label = f"[vsec{idx}]"
        filters.append(f"{base_label}trim=duration={duration:.3f},setpts=PTS-STARTPTS{section_label}")

        # Drawtext for this section only (supports segments)
        style = script.text_style
        if section and section.on_screen_segments:
            line_offset = 0
            current_label = section_label
            for seg_idx, seg in enumerate(section.on_screen_segments):
                seg_style = _segment_style(style, seg.style)
                drawtext = (
                    "drawtext="
                    f"fontfile='{seg_style.font}':"
                    f"text='{_escape_text(seg.text)}':"
                    f"fontsize={seg_style.fontsize}:"
                    f"fontcolor={seg_style.fill}:"
                    f"borderw={seg_style.stroke.width}:"
                    f"bordercolor={seg_style.stroke.color}:"
                    f"x={_format_position(seg_style.position, 'x')}:"
                    f"y={_format_position(seg_style.position, 'y')}+{line_offset}:"
                    f"enable='between(t,0.00,{duration:.2f})'"
                )
                out_label = f"[vtxt{idx}_{seg_idx}]"
                filters.append(f"{current_label}{drawtext}{out_label}")
                current_label = out_label
                line_offset += seg_style.fontsize + 8
            section_label = current_label
        else:
            drawtext = (
                "drawtext="
                f"fontfile='{style.font}':"
                f"text='{_escape_text(section_tl.on_screen_text)}':"
                f"fontsize={style.fontsize}:"
                f"fontcolor={style.fill}:"
                f"borderw={style.stroke.width}:"
                f"bordercolor={style.stroke.color}:"
                f"x={_format_position(style.position, 'x')}:"
                f"y={_format_position(style.position, 'y')}:"
                f"enable='between(t,0.00,{duration:.2f})'"
            )
            filters.append(f"{section_label}{drawtext}[vtxt{idx}]")
            section_label = f"[vtxt{idx}]"

        # Effects per section (uses 0..duration window)
        if section and section.effects:
            current_label = section_label
            for effect in section.effects:
                filt = _effect_filter(effect, 0.0, duration)
                if not filt:
                    continue
                out_label = f"[vfx{idx}_{effect}]"
                filters.append(f"{current_label}{filt}{out_label}")
                current_label = out_label
            section_label = current_label

        # Overlay images (foreground) per section
        if section and section.overlays:
            for ov_idx, overlay in enumerate(section.overlays):
                ov_path = Path(overlay.file)
                if not ov_path.exists():
                    continue
                ov_input_idx = add_input(["-i", str(ov_path)])
                xpos = _format_position(overlay.position, "x")
                ypos = _format_position(overlay.position, "y")
                overlay_label = f"[{ov_input_idx}:v]"
                current = overlay_label
                if overlay.scale:
                    current_label = f"[ov{idx}_{ov_idx}_scaled]"
                    filters.append(f"{overlay_label}scale=iw*{overlay.scale}:ih*{overlay.scale}{current_label}")
                    current = current_label
                if overlay.opacity is not None:
                    alpha_label = f"[ov{idx}_{ov_idx}_alpha]"
                    filters.append(f"{current}format=rgba,colorchannelmixer=aa={overlay.opacity}{alpha_label}")
                    current = alpha_label
                out_label = f"[vov{idx}_{ov_idx}]"
                filters.append(f"{section_label}{current}overlay=x={xpos}:y={ypos}:format=auto:shortest=1{out_label}")
                section_label = out_label

        # Scale/crop to target video dimensions
        w, h = script.video.width, script.video.height
        crop_label = f"[vscaled{idx}]"
        filters.append(
            f"{section_label}scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1{crop_label}"
        )
        section_label = crop_label

        labels.append(section_label)

    if not labels:
        return "", []

    concat_label = "[vconcat]"
    filters.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0{concat_label}")
    return concat_label, filters


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

    has_section_bg = any(getattr(sec, "bg", None) for sec in script.sections)

    # Background video or image (global) only when no section-specific bg
    if not has_section_bg:
        if Path(bg_path).suffix.lower() in IMAGE_EXTENSIONS:
            add_input(["-loop", "1", "-t", str(total_duration), "-i", bg_path])
        else:
            add_input(["-stream_loop", "-1", "-i", bg_path])

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
    watermark_cfg = script.watermark
    watermark_index = None
    if watermark_cfg and watermark_cfg.file:
        wm_path = Path(watermark_cfg.file)
        if wm_path.exists():
            watermark_index = add_input(["-i", str(wm_path)])

    filter_parts: List[str] = []
    video_label = ""

    if has_section_bg:
        video_label, section_filters = _build_section_videos(script, timeline, add_input)
        filter_parts.extend(section_filters)
    else:
        # Video – drawtext per section
        drawtext = _build_drawtext_filters(script.text_style, timeline, script)
        video_label = "[0:v]"
        if drawtext:
            filter_parts.append(f"{video_label}{drawtext}[vtext]")
            video_label = "[vtext]"
        else:
            filter_parts.append(f"{video_label}copy[vtext]")
            video_label = "[vtext]"

        # Section visual effects (blur/grayscale/vignette/contrast etc.)
        vfx_label, vfx_filters = _apply_section_effects(video_label, script, timeline)
        filter_parts.extend(vfx_filters)
        video_label = vfx_label

        # Scale/crop to target resolution
        w, h = script.video.width, script.video.height
        filter_parts.append(
            f"{video_label}scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1[vscaled]"
        )
        video_label = "[vscaled]"

    # Watermark overlay (if available)
    if watermark_index is not None:
        x_pos = _format_position(watermark_cfg.position, "x")  # type: ignore[arg-type]
        y_pos = _format_position(watermark_cfg.position, "y")  # type: ignore[arg-type]
        watermark_label = f"[{watermark_index}:v]"
        filter_parts.append(
            f"{video_label}{watermark_label}overlay=x={x_pos}:y={y_pos}:format=auto:shortest=1[vwm]"
        )
        video_label = "[vwm]"

    if watermark_cfg:
        wm_text = watermark_cfg.text or (script.bgm.license if script.bgm and script.bgm.license else None)
        if wm_text:
            text = _escape_text(wm_text)
            font_path = watermark_cfg.font or script.text_style.font
            font_size = watermark_cfg.fontsize
            font_color = watermark_cfg.fill
            stroke_color = watermark_cfg.stroke_color or script.text_style.stroke.color
            stroke_width = watermark_cfg.stroke_width if watermark_cfg.stroke_width is not None else script.text_style.stroke.width
            x_pos = _format_position(watermark_cfg.position, "x")
            y_pos = _format_position(watermark_cfg.position, "y")
            end_time = min(max(watermark_cfg.duration_sec, 0.1), total_duration)
            filter_parts.append(
                f"{video_label}drawtext="
                f"fontfile='{font_path}':"
                f"text='{text}':"
                f"fontsize={font_size}:"
                f"fontcolor={font_color}:"
                f"borderw={stroke_width}:"
                f"bordercolor={stroke_color}:"
                f"x={x_pos}:"
                f"y={y_pos}:"
                f"enable='between(t,0.00,{end_time:.2f})'[vwmtext]"
            )
            video_label = "[vwmtext]"

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
