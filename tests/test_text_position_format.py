from __future__ import annotations

from src.models import TextPosition
from src.render.ffmpeg_runner import _format_position


def test_format_position_center_and_offsets():
    pos = TextPosition(x="center", y="bottom-180")
    assert _format_position(pos, "x") == "(w-text_w)/2"
    assert _format_position(pos, "y") == "h-text_h-180"


def test_format_position_keywords():
    pos = TextPosition(x="right-100", y="top+20")
    assert _format_position(pos, "x") == "w-text_w-100"
    assert _format_position(pos, "y") == "0+20"
