from __future__ import annotations

from typing import Dict


def script_payload_schema() -> Dict:
    """Minimal schema to ensure model returns sections array."""
    return {
        "type": "object",
        "required": ["sections"],
        "properties": {
            "sections": {"type": "array"},
        },
    }


def trend_ideas_schema() -> Dict:
    """Minimal schema to ensure model returns ideas array."""
    return {
        "type": "object",
        "required": ["ideas"],
        "properties": {
            "ideas": {"type": "array"},
        },
    }
