from __future__ import annotations

import contextlib
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.models import ScriptModel

_FALLBACK_WORDS_PER_SEC = 3.0
_DEFAULT_SECTION_DURATION = 5.0


@dataclass
class SectionTimeline:
    id: str
    index: int
    start_sec: float
    duration_sec: float
    on_screen_text: str
    narration: str
    audio_path: Optional[Path]


@dataclass
class TimelineSummary:
    sections: List[SectionTimeline]
    total_duration: float


def _wav_duration(path: Path) -> float:
    if not path.exists():
        raise FileNotFoundError(str(path))
    with contextlib.closing(wave.open(str(path), "rb")) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate == 0:
            return 0.0
        return frames / rate


def _estimate_from_text(text: str) -> float:
    words = max(len(text.strip()), 1)
    return max(_DEFAULT_SECTION_DURATION, words / (_FALLBACK_WORDS_PER_SEC * 3))


def build_timeline(script: ScriptModel, audio_dir: Path) -> TimelineSummary:
    sections: List[SectionTimeline] = []
    cursor = 0.0
    pause = script.voice.pause_msec / 1000.0

    for idx, section in enumerate(script.sections, start=1):
        audio_path = audio_dir / f"{idx:02d}_{section.id}.wav"
        if audio_path.exists():
            duration = _wav_duration(audio_path)
        else:
            duration = section.duration_hint_sec or _estimate_from_text(section.narration)
        sections.append(
            SectionTimeline(
                id=section.id,
                index=idx,
                start_sec=cursor,
                duration_sec=duration,
                on_screen_text=section.on_screen_text,
                narration=section.narration,
                audio_path=audio_path if audio_path.exists() else None,
            )
        )
        cursor += duration + pause

    total_duration = cursor - pause if sections else 0.0
    return TimelineSummary(sections=sections, total_duration=max(total_duration, 0.0))
