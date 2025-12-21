from __future__ import annotations

import os
from datetime import datetime


def safe_append_log(file_path: str, line: str) -> None:
    """Append a single line to a log file, ignoring IO errors."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'a', encoding='utf-8') as lf:
            lf.write(f"{datetime.utcnow().isoformat()} {line}\n")
    except Exception:
        # Best-effort logging; swallow exceptions
        pass


def save_llm_raw_error(raw: str | None, *, prefix: str = "invalid_llm_response") -> str:
    """Save raw LLM response for inspection and return the saved file path.

    The file is stored under logs/llm_errors with timestamp-based name.
    """
    base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs', 'llm_errors')
    os.makedirs(base_dir, exist_ok=True)
    name = f"{prefix}_{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.txt"
    path = os.path.join(base_dir, name)
    try:
        with open(path, 'w', encoding='utf-8') as ef:
            ef.write(raw if raw is not None else '')
    except Exception:
        pass
    return path
