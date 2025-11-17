from __future__ import annotations

from pathlib import Path

from src.models import ScriptModel, Section, OutputOptions, VideoConfig, VoiceSettings, TextStyle, StrokeStyle
from src.outputs import write_metadata, write_srt
from src.timeline import SectionTimeline, TimelineSummary


def _dummy_script() -> ScriptModel:
    return ScriptModel(
        project="proj",
        title="タイトル",
        video=VideoConfig(bg="bg.mp4"),
        voice=VoiceSettings(speaker_id=1),
        text_style=TextStyle(font="Arial", stroke=StrokeStyle()),
        sections=[Section(id="one", on_screen_text="画面文", narration="ナレーション")],
        output=OutputOptions(filename="video.mp4"),
    )


def test_write_outputs(tmp_path: Path) -> None:
    timeline = TimelineSummary(
        sections=[
            SectionTimeline(
                id="one",
                index=1,
                start_sec=0.0,
                duration_sec=2.5,
                on_screen_text="画面文",
                narration="ナレーション",
                audio_path=None,
            )
        ],
        total_duration=2.5,
    )
    script = _dummy_script()

    srt_path = tmp_path / "sample.srt"
    meta_path = tmp_path / "meta.json"

    write_srt(timeline, srt_path)
    write_metadata(script, timeline, meta_path)

    srt_text = srt_path.read_text(encoding="utf-8")
    meta_text = meta_path.read_text(encoding="utf-8")

    assert "00:00:00,000 --> 00:00:02,500" in srt_text
    assert "画面文" in srt_text and "ナレーション" in srt_text
    assert '"title": "タイトル"' in meta_text
    assert '"total_duration_sec": 2.5' in meta_text
