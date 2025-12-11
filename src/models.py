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
    animation: Optional[str] = None


class OnScreenSegment(BaseModel):
    text: str
    style: Optional[TextStyle] = None


class OverlayImage(BaseModel):
    file: str
    position: TextPosition = TextPosition(x="center", y="center")
    scale: Optional[float] = None  # 1.0 = 100%, 倍率指定
    opacity: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class BGMAudio(BaseModel):
    file: str
    volume_db: float = -16
    ducking_db: float = 0
    license: Optional[str] = None


class Watermark(BaseModel):
    file: Optional[str] = None
    text: Optional[str] = None
    font: str = "Noto Sans JP"
    fontsize: int = 32
    fill: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 2
    duration_sec: float = 8.0
    position: TextPosition = TextPosition(x="right-40", y="top+40")


class CreditsConfig(BaseModel):
    enabled: bool = True
    text: str
    position: TextPosition = TextPosition(x="left+40", y="bottom-40")


class Section(BaseModel):
    id: str
    on_screen_text: str
    on_screen_segments: List[OnScreenSegment] = Field(default_factory=list)
    text_layout: Optional[str] = None
    overlays: List[OverlayImage] = Field(default_factory=list)
    narration: str
    duration_hint_sec: Optional[float] = None
    bg: Optional[str] = None
    bg_keyword: Optional[str] = None
    hook: Optional[str] = None
    evidence: Optional[str] = None
    demo: Optional[str] = None
    bridge: Optional[str] = None
    cta: Optional[str] = None
    effects: List[str] = Field(default_factory=list)


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


class RankingSettings(BaseModel):
    min_items: int = 5
    max_items: int = 7
    default_items: int = 5


class CTAConfig(BaseModel):
    primary: str = "コメントでお気に入りを教えてください！"
    secondary: Optional[str] = "チャンネル登録と高評価もよろしくお願いします。"


class ThumbnailStyle(BaseModel):
    width: int = 1280
    height: int = 720
    background_color: str = "#050505"
    overlay_opacity: float = 0.35
    primary_color: str = "#FFE65A"
    accent_color: str = "#FF4D6D"
    stroke_color: str = "#000000"
    stroke_width: int = 6
    font_heading: Optional[str] = None
    font_subheading: Optional[str] = None
    icon_path: Optional[str] = None


class ThemeTemplate(BaseModel):
    id: str
    label: str
    genre: str
    description: Optional[str] = None
    layout: Literal["ranking", "story", "steps"] = "ranking"
    hook_phrases: List[str] = []
    ranking: RankingSettings = RankingSettings()
    cta: CTAConfig = CTAConfig()
    script_guidelines: List[str] = []
    thumbnail_keywords: List[str] = []
    thumbnail: Optional[ThumbnailStyle] = None
