from __future__ import annotations

import wave
from pathlib import Path

from src.models import (
    OutputOptions,
    ScriptModel,
    Section,
    StrokeStyle,
    TextPosition,
    TextStyle,
    VideoConfig,
    VoiceSettings,
)
from src.timeline import build_timeline


def _write_silence_wav(path: Path, duration_sec: float, sample_rate: int = 16000) -> None:
    frames = int(duration_sec * sample_rate)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * frames)


def _make_script(section_count: int = 2) -> ScriptModel:
    sections = [
        Section(id=f"s{idx}", on_screen_text=f"セクション{idx}", narration="テストナレーション")
        for idx in range(1, section_count + 1)
    ]
    return ScriptModel(
        project="test-project",
        title="テスト動画",
        video=VideoConfig(bg="assets/cache/default.mp4"),
        voice=VoiceSettings(speaker_id=3, pause_msec=200),
        text_style=TextStyle(font="Arial", stroke=StrokeStyle()),
        sections=sections,
        output=OutputOptions(filename="out.mp4"),
    )


def test_build_timeline_uses_wav_durations(tmp_path: Path) -> None:
    script = _make_script()
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    _write_silence_wav(audio_dir / "01_s1.wav", duration_sec=1.0)
    _write_silence_wav(audio_dir / "02_s2.wav", duration_sec=1.5)

    timeline = build_timeline(script, audio_dir)

    assert len(timeline.sections) == 2
    assert timeline.sections[0].start_sec == 0.0
    assert abs(timeline.sections[0].duration_sec - 1.0) < 0.01
    assert abs(timeline.sections[1].start_sec - 1.2) < 0.05  # includes pause_msec=200
    assert abs(timeline.total_duration - (1.0 + 0.2 + 1.5)) < 0.05
