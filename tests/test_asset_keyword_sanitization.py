from __future__ import annotations

import re
from types import SimpleNamespace

from scripts import generate_video


class StubFetcher:
    def __init__(self) -> None:
        self.keywords: list[str] = []

    def fetch(self, keyword: str, kind, max_results=1, allow_ai=False):
        self.keywords.append(keyword)
        return []


def _section(section_id: str, keyword: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=section_id,
        bg=None,
        bg_keyword=keyword,
        on_screen_text=None,
        narration=None,
    )


def test_bg_keywords_are_sanitized(monkeypatch, tmp_path):
    fetcher = StubFetcher()
    # New AssetFetcher takes keyword args (pexels/pixabay/ai_generator)
    monkeypatch.setattr(generate_video, "AssetFetcher", lambda **kwargs: fetcher)

    dummy_bg = tmp_path / "dummy.mp4"
    dummy_bg.write_bytes(b"00")
    long_keyword = "光に透かす紙, 和紙の繊維, 精密な模様のCG" * 3

    script = SimpleNamespace(
        title="蚊に刺されやすい人の特徴",
        project="auto_trend",
        video=SimpleNamespace(bg=str(dummy_bg)),
        sections=[
            _section("intro", "夏の屋外や自然の映像 科学的な解説パートではシンプルなCG背景"),
            _section("section-1", "人物 呼吸 汗 サーモグラフィー CG"),
            _section("section-2", "黒い服と白い服の比較 足の裏の菌 CG"),
            _section("section-3", "血液型 イラスト 科学研究室"),
            _section("section-4", long_keyword),
        ],
    )

    generate_video.ensure_background_assets(script)

    # それぞれの bg_keyword に対して動画・静止画の両方が試行される
    assert len(fetcher.keywords) == len(script.sections) * 2
    allowed_pattern = re.compile(r"^[0-9A-Za-zぁ-んァ-ン一-龠ー ]+$")
    for keyword in fetcher.keywords:
        assert keyword, "sanitized keyword should not be empty"
        assert len(keyword) <= 50, "keyword should be truncated to 50 chars"
        assert allowed_pattern.match(keyword), f"keyword contains unsupported characters: {keyword}"

    # 取得できなかった場合でもセクションの背景は全体背景にフォールバックする
    for section in script.sections:
        assert section.bg == script.video.bg
