"""
テロップの幅を事前チェックし、自動でフォントサイズ縮小・改行を挿入して YAML を保存するスクリプト。

Usage:
  python scripts/adjust_tickers.py --script <input_yaml> [--output <output_yaml>]

挙動:
  - 各セクションの on_screen_segments (なければ on_screen_text) を対象に、
    Pillow で文字幅を計測し、video.width * 0.9 に収まるまでフォントサイズを縮小。
  - それ以上縮められない場合、簡易的にスペース/句読点で改行を挿入し再計測。
  - 調整後の YAML を指定の output パスに保存（未指定なら outputs/adjusted/ に保存）。
"""

import argparse
from pathlib import Path
from copy import deepcopy

from scripts.generate_video import load_script
from src.render.ffmpeg_runner import _resolve_font_path, _fit_font_size
from src.models import TextStyle, ScriptModel


def split_text_for_wrap(text: str):
  """スペースか句読点でざっくり2行に分割する簡易ラッパー。"""
  if " " in text:
    parts = text.split(" ")
    mid = len(parts) // 2
    return " ".join(parts[:mid]) + "\n" + " ".join(parts[mid:])
  # 句読点
  for delim in ["。", "、", "，", "．", "！", "？"]:
    if delim in text:
      idx = text.find(delim)
      return text[: idx + 1] + "\n" + text[idx + 1 :]
  return text


def ensure_segments(section):
  """on_screen_segments が無ければ on_screen_text を1要素として生成"""
  if getattr(section, "on_screen_segments", None):
    return
  text = getattr(section, "on_screen_text", "") or ""
  seg = {"text": text, "style": {}}
  section.on_screen_segments = [seg]


def adjust_section(section, video_width: int, min_fontsize: int = 18):
  ensure_segments(section)
  changed = False
  max_width = int(video_width * 0.9)
  for seg in section.on_screen_segments:
    text = seg.get("text") or ""
    style_dict = seg.get("style") or {}
    # build TextStyle for measurement
    style = TextStyle.model_validate(style_dict)
    font_path = _resolve_font_path(style.font)
    orig_size = style.fontsize or 64
    # まずフォントサイズをフィット
    fitted = _fit_font_size(text, font_path, orig_size, max_width, min_fontsize=min_fontsize)
    if fitted != orig_size:
      style.fontsize = fitted
      changed = True
    # まだはみ出すなら簡易改行
    fitted2 = _fit_font_size(text, font_path, style.fontsize or orig_size, max_width, min_fontsize=min_fontsize)
    if fitted2 > (style.fontsize or orig_size) * 0.95:  # これ以上縮まらない想定
      wrapped = split_text_for_wrap(text)
      wrapped_size = _fit_font_size(wrapped, font_path, style.fontsize or orig_size, max_width, min_fontsize)
      if wrapped_size <= style.fontsize:
        seg["text"] = wrapped
        style.fontsize = wrapped_size
        changed = True
    seg["style"] = style.model_dump()
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
  args = parser.parse_args()

  in_path = Path(args.script).expanduser().resolve()
  if not in_path.exists():
    raise FileNotFoundError(in_path)

  script = load_script(in_path)
  script_copy = deepcopy(script)
  changed = adjust_script(script_copy)
  out_path = Path(args.output).expanduser().resolve() if args.output else None
  if not out_path:
    out_dir = in_path.parent.parent / "adjusted"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{in_path.stem}_adjusted.yaml"

  from src.models import yaml_dump

  out_path.write_text(yaml_dump(script_copy), encoding="utf-8")
  if changed:
    print(f"[OK] 調整済みYAMLを出力しました: {out_path}")
  else:
    print(f"[OK] 調整不要でしたが YAML をコピーしました: {out_path}")


if __name__ == "__main__":
  main()
