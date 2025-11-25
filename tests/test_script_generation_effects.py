from __future__ import annotations

from src.script_generation.generator import ScriptFromBriefGenerator
from src.script_generation.skeletons import build_script_skeleton


def test_apply_to_script_preserves_effects():
    gen = ScriptFromBriefGenerator(llm=None, theme=None, section_count=1)  # llm unused in _apply_to_script
    skeleton = build_script_skeleton(theme=None, section_count=1)
    payload = {
        "title": "テスト",
        "sections": [
            {
                "id": "rank-1",
                "on_screen_text": "第1位",
                "narration": "ナレーション",
                "effects": ["zoom_in", "blur"],
            }
        ],
    }
    script = gen._apply_to_script(skeleton, payload)
    assert script.sections[0].effects == ["zoom_in", "blur"]
