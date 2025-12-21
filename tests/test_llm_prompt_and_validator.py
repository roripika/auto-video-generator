import os
import sys
import json
import pytest

# Ensure repository root is on sys.path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.script_generation import llm as llm_mod
from src.script_generation import response_validator as rv


class DummyClient:
    def __init__(self, responses):
        # responses can be list of strings or exceptions to raise
        self._responses = list(responses)

    def generate_json(self, messages):
        if not self._responses:
            raise RuntimeError("no more responses")
        next_item = self._responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


def test_prepare_strict_messages_inserts_system():
    msgs = [{"role": "user", "content": "please produce a script"}]
    schema = {"title": "string"}
    out = llm_mod.prepare_strict_json_messages(msgs, schema=schema, instructions="keep short")
    assert isinstance(out, list)
    assert out[0]["role"] == "system"
    assert "strict JSON" in out[0]["content"]


def test_extract_json_text_basic():
    raw = "Some preamble\n{" + '"a":1}'
    extracted = rv.extract_json_text(raw)
    assert extracted is not None
    assert json.loads(extracted)["a"] == 1


def test_generate_and_validate_success():
    schema = {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
    valid = json.dumps({"title": "Hello"}, ensure_ascii=False)
    client = DummyClient([valid])
    out = llm_mod.generate_and_validate(client, [{"role": "user", "content": "gen"}], schema=schema)
    parsed = json.loads(out)
    assert parsed["title"] == "Hello"


def test_generate_and_validate_salvage_extraneous():
    schema = {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
    raw = "Here is the JSON: {\"title\": \"X\"} Thank you"
    client = DummyClient([raw])
    out = llm_mod.generate_and_validate(client, [{"role": "user", "content": "gen"}], schema=schema)
    parsed = json.loads(out)
    assert parsed["title"] == "X"


def test_generate_and_validate_retry_on_invalid_then_valid():
    schema = {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}
    bad = "{title: unquoted}"
    good = json.dumps({"title": "Recovered"}, ensure_ascii=False)
    client = DummyClient([bad, good])
    out = llm_mod.generate_and_validate(client, [{"role": "user", "content": "gen"}], schema=schema, retries=2)
    parsed = json.loads(out)
    assert parsed["title"] == "Recovered"
