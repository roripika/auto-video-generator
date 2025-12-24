from __future__ import annotations

import os
import subprocess
import hashlib
import tempfile
from pathlib import Path
from typing import List, Tuple

from src.models import ScriptModel, TextPosition, TextStyle
from src.timeline import TimelineSummary

_TEXT_LAYOUTS_CACHE = None
_FONT_CACHE = {}


def _load_text_layouts() -> dict:
    global _TEXT_LAYOUTS_CACHE
    if _TEXT_LAYOUTS_CACHE is not None:
        return _TEXT_LAYOUTS_CACHE
    layouts_path = Path(__file__).resolve().parents[2] / "configs" / "text_layouts.yaml"
    layouts = {}
    if layouts_path.exists():
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(layouts_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("id"):
                        layouts[item["id"]] = item
        except Exception:
            pass
    _TEXT_LAYOUTS_CACHE = layouts
    return _TEXT_LAYOUTS_CACHE


def _get_layout(layout_id: str | None) -> dict:
    layouts = _load_text_layouts()
    if layout_id and layout_id in layouts:
        return layouts[layout_id]
    return layouts.get("hero_center", {})


def _resolve_font_path(font_name: str) -> str:
    """Resolve font name to actual font file path for FFmpeg."""
    if font_name in _FONT_CACHE:
        return _FONT_CACHE[font_name]
    
    # If already a path, return as-is
    font_path = Path(font_name)
    if font_path.exists() and font_path.suffix.lower() in {".ttf", ".ttc", ".otf"}:
        _FONT_CACHE[font_name] = font_name
        return font_name
    
    # Try fc-match on Linux/macOS
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", font_name],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            resolved_path = result.stdout.strip()
            # If fc-match returned a non-Japanese font for Japanese font name, use fallback
            if Path(resolved_path).exists():
                # Check if the font looks like it's not appropriate (e.g., Verdana for "Noto Sans JP")
                if "Noto Sans" in font_name or "Hiragino" in font_name or "ヒラギノ" in font_name:
                    # If fc-match gave us Verdana/Arial for Japanese font, skip to fallback
                    if "Verdana" not in resolved_path and "Arial" not in resolved_path:
                        _FONT_CACHE[font_name] = resolved_path
                        return resolved_path
                else:
                    _FONT_CACHE[font_name] = resolved_path
                    return resolved_path
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback to common Japanese fonts on macOS
    macos_fallbacks = [
        f"/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
        f"/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        f"/System/Library/Fonts/Hiragino Sans GB.ttc",
        f"/Library/Fonts/Arial Unicode.ttf",
    ]
    
    for fallback in macos_fallbacks:
        if Path(fallback).exists():
            _FONT_CACHE[font_name] = fallback
            return fallback
    
    # Last resort: return as-is and let FFmpeg fail with a clear error
    _FONT_CACHE[font_name] = font_name
    return font_name


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def _fit_font_size(
    text: str,
    font_path: str,
    fontsize: int,
    max_width: int,
    min_fontsize: int = 40,
    stroke_width: int = 0,
) -> int:
    """
    Use Pillow to shrink fontsize until text fits within max_width.
    
    Args:
        text: テキスト（複数行対応: \n で分割）
        font_path: フォントファイルのパス
        fontsize: 初期フォントサイズ
        max_width: 最大幅（px）
        min_fontsize: 最小フォントサイズ（デフォルト: 40。視認性確保）
    
    戻り値: 調整後のフォントサイズ
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from PIL import ImageFont, Image, ImageDraw
    except Exception:
        return fontsize
    try:
        current = max(fontsize, min_fontsize)
        # Pillow can raise OSError if the font is invalid
        font = ImageFont.truetype(font_path, size=current)
        # textbbox requires a drawing context
        dummy = Image.new("RGB", (8, 8))
        draw = ImageDraw.Draw(dummy)
        lines = text.split("\n")
        
        iteration = 0
        logger.debug(f"[_fit_font_size] Starting: fontsize={current}pt max_width={max_width}px lines={len(lines)}")
        
        while current > min_fontsize:
            iteration += 1
            widths = []
            for line in lines:
                if not line.strip():
                    widths.append(0)
                    continue
                try:
                    # Include stroke width in measurement to avoid underestimation
                    bbox = draw.textbbox((0, 0), line, font=font, stroke_width=max(0, stroke_width))
                    widths.append(bbox[2] - bbox[0])
                except Exception:
                    widths.append(0)
            
            max_line = max(widths) if widths else 0
            logger.debug(f"[_fit_font_size] iter={iteration} fontsize={current}pt max_line_width={max_line:.1f}px")
            
            if max_line <= max_width:
                logger.info(f"✅ [_fit_font_size] Fits! fontsize={current}pt width={max_line:.1f}px <= {max_width}px")
                break
            
            current = max(min_fontsize, int(round(current * 0.9)))
            font = ImageFont.truetype(font_path, size=current)
        
        if current == min_fontsize:
            logger.warning(f"⚠️ [_fit_font_size] Reached min_fontsize={min_fontsize}pt, final width may exceed")
        
        return current
    except Exception:
        return fontsize


def _hex_to_rgba(color: str, alpha: int = 255) -> Tuple[int, int, int, int]:
    col = (color or "").strip().lstrip("#")
    if len(col) == 3:
        col = "".join(c * 2 for c in col)
    if len(col) == 6:
        col += "ff"
    try:
        r = int(col[0:2], 16)
        g = int(col[2:4], 16)
        b = int(col[4:6], 16)
        a = alpha if len(col) < 8 else int(col[6:8], 16)
        return (r, g, b, a)
    except Exception:
        return (255, 255, 255, alpha)


def _split_text_to_lines(text: str, max_lines: int = 3) -> str:
    """Smart text splitting to fit within max_lines by breaking at spaces or punctuation."""
    import logging
    logger = logging.getLogger(__name__)
    
    # Already has line breaks
    existing_lines = text.split("\n")
    if len(existing_lines) >= max_lines:
        logger.debug(f"[_split_text_to_lines] Text already has {len(existing_lines)} lines, keeping as-is")
        return text
    
    # Try to split into max_lines
    text_clean = text.replace("\n", "")
    target_len = len(text_clean) // max_lines
    
    # Find good break points (spaces, punctuation)
    break_chars = [" ", "、", "。", "，", "．", "！", "？", "・"]
    lines = []
    remaining = text_clean
    
    for i in range(max_lines - 1):
        if len(remaining) <= target_len:
            lines.append(remaining)
            remaining = ""
            break
        
        # Look for break point around target position
        search_start = max(0, target_len - 10)
        search_end = min(len(remaining), target_len + 10)
        best_pos = -1
        
        for pos in range(search_end, search_start, -1):
            if pos < len(remaining) and remaining[pos] in break_chars:
                best_pos = pos + 1
                break
        
        if best_pos > 0:
            lines.append(remaining[:best_pos].strip())
            remaining = remaining[best_pos:].strip()
        else:
            # No good break point, force split
            lines.append(remaining[:target_len])
            remaining = remaining[target_len:]
    
    if remaining:
        lines.append(remaining)
    
    result = "\n".join(lines)
    logger.info(f"📝 [_split_text_to_lines] Split text into {len(lines)} lines (max={max_lines})")
    return result


def _render_text_image(
    text: str,
    font_path: str,
    fontsize: int,
    fill: str,
    stroke_color: str,
    stroke_width: int,
    line_gap: int,
    max_width: int | None = None,
) -> tuple[str, int, int]:
    """Render text into a transparent PNG and return (path, w, h).
    
    Args:
        max_width: If provided, will reduce fontsize to fit within this width
    """
    from PIL import Image, ImageDraw, ImageFont
    import logging
    logger = logging.getLogger(__name__)

    original_fontsize = fontsize
    original_text = text

    # If max_width specified, ensure text fits by reducing fontsize if needed
    if max_width:
        logger.debug(f"[_render_text_image] Input: fontsize={fontsize}pt max_width={max_width}px text_len={len(text)} lines={text.count(chr(10))+1}")
        
        # First attempt: reduce fontsize with current line breaks
        fontsize = _fit_font_size(text, font_path, fontsize, max_width, min_fontsize=30, stroke_width=stroke_width)
        
        # Check if it actually fits
        font_test = ImageFont.truetype(font_path, fontsize)
        dummy_test = Image.new("RGBA", (8, 8))
        draw_test = ImageDraw.Draw(dummy_test)
        lines_test = [ln for ln in text.split("\n") if ln.strip()]
        if not lines_test:
            lines_test = [""]
        
        widths_test = []
        for ln in lines_test:
            bbox = draw_test.textbbox((0, 0), ln, font=font_test, stroke_width=max(0, stroke_width))
            widths_test.append(bbox[2] - bbox[0])
        
        max_line_width = max(widths_test) if widths_test else 0
        
        # If still exceeds and has fewer than 3 lines, try splitting
        if max_line_width > max_width and len(lines_test) < 3:
            logger.warning(f"⚠️ [_render_text_image] Still exceeds: {max_line_width:.1f}px > {max_width}px, trying 3-line split")
            text = _split_text_to_lines(text, max_lines=3)
            # Re-fit with split text
            fontsize = _fit_font_size(text, font_path, original_fontsize, max_width, min_fontsize=30, stroke_width=stroke_width)

    font = ImageFont.truetype(font_path, fontsize)
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if not lines:
        lines = [""]

    draw_dummy = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    widths = []
    heights = []
    for ln in lines:
        bbox = draw_dummy.textbbox((0, 0), ln, font=font, stroke_width=max(0, stroke_width))
        widths.append(bbox[2] - bbox[0])
        heights.append(bbox[3] - bbox[1])

    total_height = sum(heights) + line_gap * (len(lines) - 1)
    canvas_w = max(widths) if widths else 1
    canvas_h = total_height
    
    if max_width:
        fit_status = "✅ FITS" if canvas_w <= max_width else "❌ EXCEEDS"
        logger.info(
            f"{fit_status} [_render_text_image] Final: fontsize={original_fontsize}→{fontsize}pt "
            f"canvas={canvas_w}x{canvas_h}px max_width={max_width}px lines={len(lines)}"
        )

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 0
    fill_rgba = _hex_to_rgba(fill)
    stroke_rgba = _hex_to_rgba(stroke_color)
    for ln, h in zip(lines, heights):
        draw.text((0, y), ln, font=font, fill=fill_rgba, stroke_width=max(0, stroke_width), stroke_fill=stroke_rgba)
        y += h + line_gap

    # Include max_width in hash so different resolutions get separate cache entries
    hash_key = hashlib.sha1(
        f"{text}|{font_path}|{fontsize}|{fill}|{stroke_color}|{stroke_width}|{line_gap}|{max_width or 0}".encode("utf-8")
    ).hexdigest()[:16]
    
    # Use outputs/cache/text/ as persistent cache (prefer project-local)
    # Fall back to /tmp if project root not available
    try:
        project_root = Path(__file__).resolve().parents[2]
        out_dir = project_root / "outputs" / "cache" / "text"
    except Exception:
        # Fall back to /tmp if we can't determine project root
        out_dir = Path(tempfile.gettempdir()) / "avgen_text_cache"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"text_{hash_key}.png"
    img.save(out_path, format="PNG")
    return str(out_path), canvas_w, canvas_h


def _format_position(value: TextPosition, axis: str, scale: float = 1.0) -> str:
    raw = value.x if axis == "x" else value.y
    if isinstance(raw, int):
        return str(int(round(raw * scale)))
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
        try:
            offset_val = int(offset)
        except ValueError:
            offset_val = 0
        scaled_offset = int(round(offset_val * scale))
        sign = "+" if scaled_offset >= 0 else "-"
        scaled_abs = abs(scaled_offset)
        if anchor == "center":
            base = f"({dim_var}-{text_var})/2"
            return f"{base}{sign}{scaled_abs}"
        if anchor in {"left", "top"}:
            base = "0"
            return f"{base}{sign}{scaled_abs}"
        if anchor in {"right", "bottom"}:
            base = f"{dim_var}-{text_var}"
            return f"{base}{sign}{scaled_abs}"

    return raw


def _escape_text(text: str) -> str:
    """Normalize newlines and escape characters that break drawtext."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\\n", "\n")
    return (
        normalized.replace("\\", "\\\\")  # backslash first
        .replace(":", r"\:")
        .replace(",", r"\,")
        .replace("'", "\\'")
    )


def _db_to_linear(value_db: float) -> float:
    return 10 ** (value_db / 20.0)


def _short_scale(script: ScriptModel) -> float:
    """Return scale factor for text/layout when vertical short mode."""
    try:
        w = getattr(script.video, "width", 0) or 0
        h = getattr(script.video, "height", 0) or 0
        if h > w and h >= 1500:  # assume 1080x1920など縦長
            # より強めに縮小して画面外にはみ出しにくくする
            return 0.65
    except Exception:
        pass
    return 1.0


def _segment_style(base: TextStyle, segment_style: TextStyle | None) -> TextStyle:
    if not segment_style:
        return base
    merged = base.model_copy(deep=True)
    for field in ["font", "fontsize", "fill", "stroke", "position", "max_chars_per_line", "lines", "animation"]:
        value = getattr(segment_style, field, None)
        if value is not None:
            setattr(merged, field, value)
    return merged


def _apply_tier_style(style: TextStyle, tier: str) -> TextStyle:
    styled = style.model_copy(deep=True)
    if tier == "emphasis":
        styled.fontsize = max(styled.fontsize or 0, 96)
        styled.fill = "#FFE65A"
        styled.stroke.color = "#000000"
        styled.stroke.width = max(styled.stroke.width or 0, 6)
    elif tier == "connector":
        styled.fontsize = max(styled.fontsize or 0, 72)
        styled.fill = "#FFFFFF"
        styled.stroke.color = "#000000"
        styled.stroke.width = max(styled.stroke.width or 0, 4)
    else:  # body
        styled.fontsize = max(styled.fontsize or 0, 64)
        styled.fill = "#FFFFFF"
        styled.stroke.color = "#000000"
        styled.stroke.width = max(styled.stroke.width or 0, 4)
    return styled


def _split_lines(text: str) -> List[str]:
    return [ln for ln in text.split("\n") if ln.strip()]



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
    target_w, target_h = script.video.width, script.video.height

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
        trimmed_label = f"[vsec{idx}]"
        filters.append(f"{base_label}trim=duration={duration:.3f},setpts=PTS-STARTPTS{trimmed_label}")

        # Scale/crop to target video dimensions upfront so drawtext uses final resolution.
        section_label = f"[vscaled{idx}]"
        filters.append(
            f"{trimmed_label}scale={target_w}:{target_h}:force_original_aspect_ratio=decrease:flags=lanczos+accurate_rnd+full_chroma_int,"
            f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2,setsar=1{section_label}"
        )

        # Drawtext for this section only (supports segments)
        style = script.text_style
        layout = _get_layout(getattr(section, "text_layout", None) if section else None)
        base_pos = TextPosition(
            x=str(layout.get("base_position", {}).get("x", "center")),
            y=str(layout.get("base_position", {}).get("y", "center-120")),
        )
        line_gap = int(layout.get("line_gap", 24))
        align = layout.get("align", "center")
        rank_offset = layout.get("rank_offset", {})
        body_offset = layout.get("body_offset", {})

        if section and section.on_screen_segments:
            current_label = section_label
            line_offset = 0
            for seg_idx, seg in enumerate(section.on_screen_segments):
                tier = "emphasis" if seg_idx == 0 else "body"
                # Normalize segment that may be a dict loaded from YAML
                if isinstance(seg, dict):
                    seg_text = str(seg.get("text", "") or "")
                    seg_style_raw = seg.get("style")
                    try:
                        seg_style_obj = TextStyle.model_validate(seg_style_raw) if seg_style_raw else None
                    except Exception:
                        seg_style_obj = None
                else:
                    seg_text = str(getattr(seg, "text", "") or "")
                    seg_style_obj = getattr(seg, "style", None)

                seg_style = _apply_tier_style(_segment_style(style, seg_style_obj), tier)
                offset = rank_offset if seg_idx == 0 else body_offset
                off_x = offset.get("x", 0)
                off_y = offset.get("y", 0)

                scale = _short_scale(script)
                if scale != 1.0:
                    seg_style.fontsize = int(round((seg_style.fontsize or 0) * scale))
                    if seg_style.stroke and seg_style.stroke.width is not None:
                        seg_style.stroke.width = max(1, int(round(seg_style.stroke.width * scale)))
                font_path = _resolve_font_path(seg_style.font)
                line_gap_px = int(round(8 * scale))
                
                # Ensure text fits within video width
                target_w = script.video.width
                max_text_width = int(target_w * 0.9)
                
                text_img, img_w, img_h = _render_text_image(
                    _escape_text(seg_text),
                    font_path,
                    seg_style.fontsize,
                    seg_style.fill,
                    seg_style.stroke.color,
                    seg_style.stroke.width or 0,
                    line_gap_px,
                    max_width=max_text_width,
                )
                if align == "left":
                    xpos = off_x + 60
                elif align == "right":
                    xpos = target_w - img_w - (off_x + 60)
                else:
                    xpos = int((target_w - img_w) / 2) + off_x

                base_y = 0
                if isinstance(base_pos.y, int):
                    base_y = int(round(base_pos.y * scale))
                elif isinstance(base_pos.y, str) and base_pos.y.startswith("center"):
                    delta = 0
                    token = base_pos.y[len("center"):]
                    if token:
                        try:
                            delta = int(token)
                        except Exception:
                            delta = 0
                    base_y = int(target_h / 2 - img_h / 2 + delta)
                else:
                    try:
                        base_y = int(float(base_pos.y))
                    except Exception:
                        base_y = 0
                ypos = base_y + line_offset + off_y

                img_idx = add_input(["-loop", "1", "-i", text_img])
                out_label = f"[vtxt{idx}_{seg_idx}_{line_offset}]"
                # Don't use enable= because each section is trimmed; overlay throughout section duration
                filters.append(
                    f"{current_label}[{img_idx}:v]overlay={xpos}:{ypos}:shortest=1{out_label}"
                )
                current_label = out_label
                line_offset += img_h + line_gap_px
            section_label = current_label
        else:
            scale = _short_scale(script)
            base_style = style.model_copy(deep=True)
            if scale != 1.0:
                base_style.fontsize = int(round((base_style.fontsize or 0) * scale))
                if base_style.stroke and base_style.stroke.width is not None:
                    base_style.stroke.width = max(1, int(round(base_style.stroke.width * scale)))
            font_path = _resolve_font_path(base_style.font)
            line_gap_px = int(round(8 * scale))
            text_img, img_w, img_h = _render_text_image(
                _escape_text(section_tl.on_screen_text),
                font_path,
                base_style.fontsize,
                base_style.fill,
                base_style.stroke.color,
                base_style.stroke.width or 0,
                line_gap_px,
            )
            if align == "left":
                xpos = 60
            elif align == "right":
                xpos = target_w - img_w - 60
            else:
                xpos = int((target_w - img_w) / 2)

            base_y = 0
            if isinstance(base_pos.y, int):
                base_y = int(round(base_pos.y * scale))
            elif isinstance(base_pos.y, str) and base_pos.y.startswith("center"):
                delta = 0
                token = base_pos.y[len("center"):]
                if token:
                    try:
                        delta = int(token)
                    except Exception:
                        delta = 0
                base_y = int(target_h / 2 - img_h / 2 + delta)
            else:
                try:
                    base_y = int(float(base_pos.y))
                except Exception:
                    base_y = 0

            img_idx = add_input(["-loop", "1", "-i", text_img])
            # Don't use enable= because each section is trimmed; overlay throughout section duration
            filters.append(
                f"{section_label}[{img_idx}:v]overlay={xpos}:{base_y}:shortest=1[vtxt{idx}]"
            )
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
        f"fontfile='{_resolve_font_path(script.text_style.font)}':"
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

    video_label, section_filters = _build_section_videos(script, timeline, add_input)
    filter_parts.extend(section_filters)

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
            font_path = _resolve_font_path(watermark_cfg.font or script.text_style.font)
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
        normalized_voice_labels: List[str] = []
        for v_idx in voice_indices:
            norm_label = f"[voice_norm{len(normalized_voice_labels)}]"
            filter_parts.append(
                f"[{v_idx}:a]asetpts=PTS-STARTPTS,aformat=sample_rates=44100:channel_layouts=mono{norm_label}"
            )
            normalized_voice_labels.append(norm_label)
        labels = "".join(normalized_voice_labels)
        filter_parts.append(f"{labels}concat=n={len(normalized_voice_labels)}:v=0:a=1[voice]")
        voice_label = "[voice]"
    else:
        filter_parts.append("anullsrc=channel_layout=stereo:sample_rate=44100[voice]")
        voice_label = "[voice]"

    audio_output_label = voice_label

    # BGM + ducking mix
    if bgm_index is not None:
        voice_mix_label = voice_label
        voice_side_label = voice_label
        bgm_volume = _db_to_linear(script.bgm.volume_db)
        duration_pad = total_duration + 1.0
        filter_parts.append(
            f"[{bgm_index}:a]apad=pad_dur={duration_pad},atrim=duration={duration_pad},"
            f"asetpts=PTS-STARTPTS,volume={bgm_volume:.4f}[bgm]"
        )
        bgm_label = "[bgm]"
        if script.bgm.ducking_db:
            filter_parts.append(f"{voice_label}asplit=2[voice_mix][voice_side]")
            voice_mix_label = "[voice_mix]"
            voice_side_label = "[voice_side]"
            # Sidechain compress BGM using narration as sidechain source.
            # Use a fixed threshold so narration reliably ducks the music.
            duck_threshold = _db_to_linear(-32.0)
            filter_parts.append(
                f"{bgm_label}{voice_side_label}sidechaincompress="
                f"threshold={duck_threshold}:ratio=8:attack=5:release=250:makeup=1[bgmduck]"
            )
            bgm_label = "[bgmduck]"
        filter_parts.append(
            f"{bgm_label}{voice_mix_label}amix=inputs=2:duration=longest:dropout_transition=0[aout]"
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
