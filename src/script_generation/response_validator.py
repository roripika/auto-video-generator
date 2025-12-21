"""Utilities to sanitize and validate LLM responses expected to be JSON.

This module attempts to salvage common issues (extraneous text, trailing tokens)
and optionally validate against a JSON schema if `jsonschema` is installed.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple


def extract_json_text(raw: str) -> Optional[str]:
    """Try to extract a JSON substring from raw text.

    - Strip code fences (```, ````, etc.) first
    - First attempt a direct json.loads.
    - If that fails, look for the first {...} or [...] block and return it.
    - Returns the JSON string or None if nothing found.
    """
    if not raw:
        return None
    raw = raw.strip()
    
    # Remove code fences (handles multiple layers like ````plaintext + ```json + ... + ``` + ````)
    stripped = _strip_markdown_fences(raw)
    
    try:
        json.loads(stripped)
        return stripped
    except Exception:
        pass

    # Find first balanced brace/bracket block (simple approach)
    brace_match = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", stripped)
    if brace_match:
        candidate = brace_match.group(0)
        # quick heuristic: remove trailing punctuation
        candidate = candidate.rstrip('\n\r \t ')
        # Try load
        try:
            json.loads(candidate)
            return candidate
        except Exception:
            # attempt to strip common garbage at the end
            candidate = re.sub(r"[\uFFFD%]+$", "", candidate)
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                return None
    return None


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences like ```json ... ``` or ````plaintext ... ````.
    Handles multiple nested layers (up to 10 iterations).
    """
    stripped = text.strip()
    
    for _ in range(10):
        before = stripped
        
        # Remove opening fence: ``` or ```` + optional language + newline
        if stripped.startswith("`"):
            fence_match = re.match(r'^`+(?:[a-z]+)?\s*\n', stripped, re.IGNORECASE)
            if fence_match:
                stripped = stripped[fence_match.end():]
        
        # Remove closing fence: newline + ``` or ````
        if stripped.endswith("`"):
            fence_match = re.search(r'\n`+\s*$', stripped)
            if fence_match:
                stripped = stripped[:fence_match.start()]
        
        stripped = stripped.strip()
        
        # No change, done
        if stripped == before:
            break
    
    return stripped


def validate_json_structure(json_text: str, schema: Optional[Dict] = None) -> Tuple[bool, Optional[Any]]:
    """Validate json_text and optionally check against a JSON Schema.

    Returns (is_valid, parsed_object_or_error).
    If `jsonschema` is available and a schema is provided, the function will use it.
    """
    try:
        parsed = json.loads(json_text)
    except Exception as e:
        return False, f"invalid-json: {e}"

    if schema is None:
        return True, parsed

    try:
        import jsonschema  # type: ignore

        jsonschema.validate(instance=parsed, schema=schema)
        return True, parsed
    except ModuleNotFoundError:
        # jsonschema が未インストールの場合はスキップして通す
        return True, parsed
    except ImportError:
        # jsonschema が未インストールの場合はスキップして通す
        return True, parsed
    except Exception as e:
        return False, f"schema-validation-failed: {e}"


def sanitize_and_validate(raw: str, schema: Optional[Dict] = None) -> Tuple[bool, Optional[Any], Optional[str]]:
    """Attempt to extract JSON, validate it, and return (ok, parsed, error_message).

    - ok: True if valid and (optionally) schema-conformant
    - parsed: the parsed JSON object when ok is True
    - error_message: diagnostic when ok is False
    """
    candidate = extract_json_text(raw)
    if candidate is None:
        # Try one more aggressive attempt: just look for the first { and last }
        stripped = _strip_markdown_fences(raw.strip())
        if stripped.startswith("{") and stripped.endswith("}"):
            candidate = stripped
        else:
            return False, None, "no-json-found"

    ok, parsed_or_err = validate_json_structure(candidate, schema=schema)
    if ok:
        return True, parsed_or_err, None
    return False, None, str(parsed_or_err)
