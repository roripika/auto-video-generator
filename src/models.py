from __future__ import annotations

from pathlib import Path
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class VideoConfig(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: int = 30
    bg: str
    bg_fit: Literal["cover", "contain", "stretch"] = "cover"


class VoiceSettings(BaseModel):
    engine: Literal["voicevox"] = "voicevox"
    speaker_id: int
    speedScale: float = 1.0
    pitchScale: float = 0.0
    intonationScale: float = 1.0
    volumeScale: float = 1.0
    pause_msec: int = 0


class TextPosition(BaseModel):
    x: Union[str, int] = "center"
    y: Union[str, int] = "bottom-160"


class StrokeStyle(BaseModel):
    color: str = "#000000"
    width: int = 3


class TextStyle(BaseModel):
    font: str
    fontsize: int = 54
    fill: str = "#FFFFFF"
    stroke: StrokeStyle = StrokeStyle()
    position: TextPosition = TextPosition()
    max_chars_per_line: int = 22
    lines: int = 3


class BGMAudio(BaseModel):
    file: str
    volume_db: float = -16
    ducking_db: float = -6


class Watermark(BaseModel):
    file: str
    position: TextPosition = TextPosition(x="right-40", y="top+40")


class CreditsConfig(BaseModel):
    enabled: bool = True
    text: str
    position: TextPosition = TextPosition(x="left+40", y="bottom-40")


class Section(BaseModel):
    id: str
    on_screen_text: str
    narration: str
    duration_hint_sec: Optional[float] = None


class OutputOptions(BaseModel):
    filename: str
    srt: bool = True
    thumbnail_time_sec: float = 1.0


class UploadPrep(BaseModel):
    title: Optional[str] = None
    tags: List[str] = []
    desc: Optional[str] = None


class ScriptModel(BaseModel):
    project: str
    title: str
    locale: str = "ja-JP"
    video: VideoConfig
    voice: VoiceSettings
    text_style: TextStyle
    bgm: Optional[BGMAudio] = None
    watermark: Optional[Watermark] = None
    credits: Optional[CreditsConfig] = None
    sections: List[Section]
    output: OutputOptions
    upload_prep: Optional[UploadPrep] = None

    @field_validator("sections", mode="before")
    @classmethod
    def ensure_sections(cls, value: List[dict]) -> List[dict]:
        if not value or not isinstance(value, list):
            raise ValueError("sections must be a non-empty list")
        return value


class ConfigModel(BaseModel):
    work_dir: Path = Path("work")
    outputs_dir: Path = Path("outputs/rendered")
    voicevox_endpoint: str = "http://localhost:50021"
    ffmpeg_path: str = "ffmpeg"
    timeout_sec: int = 60
    retries: int = 3
