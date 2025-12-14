from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.models import (
    OutputOptions,
    ScriptModel,
    Section,
    TextPosition,
    TextStyle,
    ThemeTemplate,
    UploadPrep,
    VideoConfig,
    VoiceSettings,
    StrokeStyle,
)


def build_script_skeleton(theme: Optional[ThemeTemplate], section_count: int) -> ScriptModel:
    """Create a ScriptModel with sensible defaults for later enrichment."""
    now = datetime.now()
    label = theme.label if theme else "汎用スクリプト"
    genre = theme.genre if theme else "general"
    layout = theme.layout if theme else "ranking"
    project_id = f"{(theme.id if theme else 'generic')}-{now.strftime('%Y%m%d%H%M%S')}"

    sections: list[Section] = []
    for idx in range(1, max(section_count, 1) + 1):
        if layout == "ranking":
            on_screen = f"第{idx}位：未設定"
            section_id = f"rank-{idx}"
        elif layout == "steps":
            on_screen = f"ステップ{idx}"
            section_id = f"step-{idx}"
        else:  # story
            on_screen = f"セクション{idx}"
            section_id = f"section-{idx}"
        sections.append(
            Section(
                id=section_id,
                on_screen_text=on_screen,
                narration="",
                hook=None,
                evidence=None,
                demo=None,
                bridge=None,
                cta=None,
                effects=[],
            )
        )

    script = ScriptModel(
        project=project_id,
        title=f"{label} ベスト{len(sections)}" if layout == "ranking" else f"{label} 解説",
        video=VideoConfig(
            width=1920,
            height=1080,
            fps=30,
            bg="assets/cache/default.mp4",
            bg_fit="cover",
        ),
        voice=VoiceSettings(
            engine="voicevox",
            speaker_id=13,
            speedScale=1.02,
            pitchScale=0.0,
            intonationScale=1.1,
            volumeScale=1.0,
            pause_msec=150,
        ),
        text_style=TextStyle(
            font="Noto Sans JP",
            fontsize=68,
            fill="#FFFFFF",
            stroke=StrokeStyle(color="#000000", width=4),
            position=TextPosition(x="center", y="center+120"),
            max_chars_per_line=18,
            lines=2,
        ),
        bgm=None,
        watermark=None,
        credits=None,
        sections=sections,
        output=OutputOptions(
            filename=f"{project_id}.mp4",
            srt=True,
            thumbnail_time_sec=1.0,
        ),
        upload_prep=UploadPrep(
            title="",
            tags=[genre, "ランキング", "ライフハック"],
            desc="",
        ),
    )
    return script
