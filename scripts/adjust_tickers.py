"""
テロップの幅を事前チェックし、自動でフォントサイズ縮小・改行・スケーリングを適用して YAML を保存するスクリプト。

3段階優先順位で調整:
  1. フォントサイズ縮小（min_fontsize=40 まで）
  2. 改行挿入（スペース/句読点で分割）
  3. スケーリング（全体 0.85 倍）

各段階の前後で verify_fit() で検証し、複数回確認。

Usage:
  python scripts/adjust_tickers.py --script <input_yaml> [--output <output_yaml>]
"""

import argparse
import logging
from pathlib import Path
from copy import deepcopy
from typing import Tuple

from scripts.generate_video import load_script
from src.render.ffmpeg_runner import _resolve_font_path, _fit_font_size
from src.models import TextStyle, ScriptModel, OnScreenSegment

logger = logging.getLogger(__name__)


def verify_fit(text: str, font_path: str, fontsize: int, max_width: int) -> Tuple[bool, float]:
    """
    テキストが max_width に収まるかを複数行対応で検証。
    
    戻り値: (is_fit: bool, max_line_width: float)
      - is_fit: True なら収まっている
      - max_line_width: 最長行の幅（px）。-1 はエラー
    """
    try:
        from PIL import ImageFont
    except Exception as e:
        logger.error(f"Pillow import failed: {e}")
        return True, 0

    try:
        font = ImageFont.truetype(font_path, size=fontsize)
        lines = text.split("\n")
        
        max_width_found = 0
        for idx, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                # 各行を個別に計測
                bbox = font.getbbox(line)
                line_width = bbox[2] - bbox[0]
                max_width_found = max(max_width_found, line_width)
                
                if line_width > max_width:
                    logger.debug(f"  Line {idx} exceeds: '{line[:20]}...' = {line_width}px > {max_width}px")
            except Exception as e:
                logger.warning(f"  getbbox failed for line: {line[:20]}..., error: {e}")
                return False, -1
        
        return max_width_found <= max_width, max_width_found
    
    except Exception as e:
        logger.error(f"verify_fit error: {e}")
        return False, -1


def split_text_for_wrap(text: str) -> str:
    """テキストをスペース/句読点で改行。"""
    if len(text) <= 20:
        return text
    
    # スペースで分割
    if " " in text:
        parts = text.split(" ")
        mid = len(parts) // 2
        return " ".join(parts[:mid]) + "\n" + " ".join(parts[mid:])
    
    # 句読点で分割
    for delim in ["。", "、", "，", "．", "！", "？"]:
        if delim in text:
            idx = text.find(delim)
            if idx > 0 and idx < len(text) - 1:
                return text[:idx + 1] + "\n" + text[idx + 1:]
    
    # 分割できない場合は中央で分割
    mid = len(text) // 2
    return text[:mid] + "\n" + text[mid:]


def ensure_segments(section):
    """on_screen_segments が無ければ on_screen_text を1要素として生成"""
    if getattr(section, "on_screen_segments", None):
        return
    text = getattr(section, "on_screen_text", "") or ""
    seg = {"text": text, "style": {}}
    section.on_screen_segments = [seg]


def adjust_section(section, video_width: int, min_fontsize: int = 40, scale_factor: float = 0.85):
    """
    セクションのテロップを3段階優先順位で調整し、複数回検証。
    
    戻り値: True なら変更あり、False なら変更なし
    """
    ensure_segments(section)
    changed = False
    max_width = int(video_width * 0.9)
    
    for idx, seg in enumerate(section.on_screen_segments):
        # Pydantic オブジェクト or dict に対応
        if hasattr(seg, "model_dump"):
            seg_dict = seg.model_dump()
            seg_is_model = True
        elif isinstance(seg, dict):
            seg_dict = seg
            seg_is_model = False
        else:
            continue

        text = seg_dict.get("text") or ""
        style_dict = seg_dict.get("style") or {}
        
        # デフォルト補完
        if not style_dict.get("font"):
            style_dict["font"] = "Noto Sans JP"
        if "fontsize" not in style_dict or style_dict.get("fontsize") in (None, 0, ""):
            style_dict["fontsize"] = 64
        
        style = TextStyle.model_validate(style_dict)
        font_path = _resolve_font_path(style.font)
        orig_fontsize = style.fontsize or 64
        current_fontsize = orig_fontsize
        current_text = text
        
        # ===== 段階1: 初期判定 =====
        logger.debug(f"Segment: '{text[:30]}...' ({len(text)} chars)")
        is_fit, max_line_width = verify_fit(current_text, font_path, current_fontsize, max_width)
        
        if is_fit:
            logger.debug(f"  ✅ No adjustment needed (width={max_line_width:.0f}px)")
            continue
        
        logger.info(f"  ⚠️  Adjustment needed: width={max_line_width:.0f}px > {max_width}px")
        
        # ===== 段階2: 優先順位実行 =====
        
        # 優先順位1: フォントサイズ縮小
        logger.debug(f"  [P1] Trying font size reduction...")
        font_reduced = False
        while current_fontsize > min_fontsize:
            current_fontsize = max(min_fontsize, int(round(current_fontsize * 0.9)))
            is_fit, line_width = verify_fit(current_text, font_path, current_fontsize, max_width)
            if is_fit:
                logger.info(f"    ✅ [P1] Font size reduced to {current_fontsize}pt (fit={line_width:.0f}px)")
                changed = True
                font_reduced = True
                break
        
        if not font_reduced and current_fontsize == min_fontsize:
            # min_fontsize でもはみ出す
            logger.debug(f"  [P2] Font size reached minimum ({min_fontsize}pt), trying line wrapping...")
            
            # 優先順位2: 改行挿入
            wrapped = split_text_for_wrap(current_text)
            is_fit, line_width = verify_fit(wrapped, font_path, current_fontsize, max_width)
            
            if is_fit:
                current_text = wrapped
                logger.info(f"    ✅ [P2] Line wrapping OK (fit={line_width:.0f}px)")
                changed = True
            else:
                # 改行 + フォント再縮小
                logger.debug(f"  [P2+P1] Wrapped text still too long, retry font reduction...")
                wrapped_fontsize = current_fontsize
                while wrapped_fontsize > min_fontsize:
                    wrapped_fontsize = max(min_fontsize, int(round(wrapped_fontsize * 0.9)))
                    is_fit, _ = verify_fit(wrapped, font_path, wrapped_fontsize, max_width)
                    if is_fit:
                        current_text = wrapped
                        current_fontsize = wrapped_fontsize
                        logger.info(f"    ✅ [P2+P1] Wrapping + font reduced to {wrapped_fontsize}pt")
                        changed = True
                        break
                else:
                    # 優先順位3: スケーリング
                    logger.debug(f"  [P3] Trying scaling ({scale_factor}x)...")
                    scaled_fontsize = max(min_fontsize, int(current_fontsize * scale_factor))
                    is_fit, line_width = verify_fit(current_text, font_path, scaled_fontsize, max_width)
                    
                    if is_fit:
                        current_fontsize = scaled_fontsize
                        logger.info(f"    ✅ [P3] Scaling applied: {scaled_fontsize}pt (fit={line_width:.0f}px)")
                        changed = True
                    else:
                        # 全て失敗 → 警告
                        logger.warning(f"    ❌ All adjustments failed: '{text[:30]}...' ({len(text)} chars)")
                        if len(text) >= 36:
                            logger.warning(f"    💡 Suggestion: Text is too long ({len(text)} chars). Consider shortening to <18 chars.")
        
        # ===== 段階3: 最終検証 =====
        logger.debug(f"  [Stage3] Final verification...")
        is_fit_final, final_width = verify_fit(current_text, font_path, current_fontsize, max_width)
        
        if not is_fit_final:
            logger.error(f"    🚨 Final verification FAILED: width={final_width:.0f}px > {max_width}px")
        else:
            logger.info(f"    ✅ Final verification PASSED: fontsize={current_fontsize}pt, width={final_width:.0f}px")
        
        # ===== YAML に反映 =====
        style.fontsize = current_fontsize
        seg_dict["text"] = current_text
        seg_dict["style"] = style.model_dump()
        
        # 反映
        if seg_is_model:
            seg.text = current_text
            seg.style = style.model_dump()
        else:
            section.on_screen_segments[idx] = OnScreenSegment(**seg_dict)
    
    return changed

def adjust_script(script: ScriptModel):
    video_width = getattr(script.video, "width", 1920) or 1920
    changed_any = False
    for sec in script.sections:
        changed_any = adjust_section(sec, video_width) or changed_any
    return changed_any


def main():
    parser = argparse.ArgumentParser(description="テロップを自動調整してYAMLを出力")
    parser.add_argument("--script", required=True, help="入力 YAML パス")
    parser.add_argument("--output", help="出力 YAML パス（未指定なら outputs/adjusted 配下）")
    parser.add_argument("--log-level", default="INFO", help="ログレベル (DEBUG/INFO/WARNING)")
    args = parser.parse_args()
    
    # ログ設定
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )

    in_path = Path(args.script).expanduser().resolve()
    if not in_path.exists():
        raise FileNotFoundError(in_path)

    logger.info(f"Loading script: {in_path}")
    script = load_script(in_path)
    script_copy = deepcopy(script)
    
    logger.info(f"Adjusting tickers (min_fontsize=40, scale_factor=0.85)...")
    changed = adjust_script(script_copy)
    
    out_path = Path(args.output).expanduser().resolve() if args.output else None
    if not out_path:
        out_dir = in_path.parent.parent / "adjusted"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{in_path.stem}_adjusted.yaml"

    import yaml
    out_path.write_text(yaml.dump(script_copy.model_dump(), allow_unicode=True, sort_keys=False), encoding="utf-8")
    if changed:
        logger.info(f"✅ Adjusted YAML saved: {out_path}")
    else:
        logger.info(f"✅ No adjustment needed. YAML copied: {out_path}")


if __name__ == "__main__":
    main()

