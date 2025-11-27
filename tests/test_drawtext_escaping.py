from src.render.ffmpeg_runner import _escape_text


def test_escape_text_preserves_simple_text():
    assert _escape_text("シンプルな文字列") == "シンプルな文字列"


def test_escape_text_converts_literal_newline():
    raw = "第1位：\n市場分析でAI活用"
    assert _escape_text(raw) == raw


def test_escape_text_converts_backslash_n_sequence():
    raw = "第1位：\\n市場分析でAI活用"
    assert _escape_text(raw) == "第1位：\n市場分析でAI活用"


def test_escape_text_handles_special_characters():
    raw = "コロン:カンマ,シングル'バックスラッシュ\\"
    expected = "コロン\\:カンマ\\,シングル\\'バックスラッシュ\\\\"
    assert _escape_text(raw) == expected
