"""Prompt templates for LLM interactions.

Provide helpers to build strict JSON-only prompts and example schemas.
"""
from typing import Dict, List


DEFAULT_JSON_EXAMPLE = {
    "title": "短い説明",
    "sections": [{"heading": "見出し1", "text": "本文..."}],
}


def build_json_only_messages(schema: Dict, instructions: str = "") -> List[Dict[str, str]]:
    """Return a messages list (system + user) that instructs the model to reply with pure JSON.

    - `schema` should be a JSON-serializable dict describing the expected output structure.
    - The returned messages are suitable for passing to the existing LLM client `generate_json`.
    """
    system = (
        """You are a strict JSON generator. Reply with valid JSON only — no explanations,
no comments, and no surrounding markdown. The JSON must conform to the schema provided by the user."""
    )

    schema_text = f"Schema (JSON): {schema}"
    user = (
        "Produce the response as pure JSON and exactly match the schema. "
        "If a field is optional, still include it with a sensible empty value. "
        "Do not include any text outside the JSON object.\n\n"
        f"{instructions}\n\n"
        f"{schema_text}\n\n"
        "Return only the JSON."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def example_script_schema() -> Dict:
    """An example schema for generated scripts/guides used in the pipeline."""
    return {
        "title": "string",
        "duration_seconds": "number",
        "sections": [
            {
                "heading": "string",
                "text": "string",
                "start_time": "number",
            }
        ],
    }
