from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

import requests
import json
from datetime import datetime
import time
import os
from .logging_utils import safe_append_log, save_llm_raw_error
from .prompt_templates import build_json_only_messages, example_script_schema
from .response_validator import extract_json_text, sanitize_and_validate

# Log file for outgoing LLM requests (avoid logging secrets)
LLM_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'logs', 'llm_requests.log')
os.makedirs(os.path.dirname(LLM_LOG_PATH), exist_ok=True)


class LLMError(RuntimeError):
    """Raised when the LLM client cannot complete a request."""


class LLMClient(Protocol):
    def generate_json(self, messages: List[Dict[str, str]]) -> str: ...


def _ensure_messages(messages: List[Dict[str, str]]) -> None:
    if not messages:
        raise LLMError("No messages were provided for the LLM request.")


def prepare_strict_json_messages(messages: List[Dict[str, str]], schema: Optional[Dict] = None, instructions: str = "") -> List[Dict[str, str]]:
    """If a schema is provided, prepend a strict JSON-only system/user message set.

    This helps enforce consistent JSON-only outputs from the model. If `schema` is None,
    the original messages are returned unchanged.
    """
    if not schema:
        return messages
    template_msgs = build_json_only_messages(schema, instructions=instructions)
    # Keep any existing system message after the strict system message so callers can still
    # set contextual info. User messages follow the template user message.
    remaining = [m for m in messages if m.get("role") != "system"]
    return template_msgs + remaining


def _resolve_default_gemini_max_output_tokens() -> int:
    raw_value = os.environ.get("GEMINI_MAX_OUTPUT_TOKENS")
    if raw_value:
        try:
            parsed = int(raw_value)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return 6144


DEFAULT_GEMINI_MAX_OUTPUT_TOKENS = _resolve_default_gemini_max_output_tokens()


@dataclass
class OpenAIChatClient:
    """OpenAI / OpenRouter 互換の Chat Completions クライアント。"""

    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    temperature: float = 0.4
    max_tokens: int = 6000
    session: requests.Session = field(default_factory=requests.Session, repr=False)

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set. Please export it before running this command.")

        if not self.model:
            self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        if not self.base_url:
            self.base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")

    def generate_json(self, messages: List[Dict[str, str]]) -> str:
        _ensure_messages(messages)
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.session.post(url, json=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
        except requests.HTTPError as err:
            detail = err.response.text if err.response is not None else str(err)
            raise LLMError(f"LLM request failed: {detail}") from err
        except requests.RequestException as err:
            raise LLMError(f"LLM request could not be sent: {err}") from err

        try:
            data: Dict[str, Any] = response.json()
        except ValueError as err:
            raise LLMError(f"LLM response was not JSON: {response.text}") from err

        try:
            choice: Dict[str, Any] = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError) as err:
            raise LLMError(f"Unexpected LLM response payload: {response.text}") from err

        if finish_reason == "length":
            usage = data.get("usage", {}) if isinstance(data, dict) else {}
            completion_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
            raise LLMError(
                "LLM response was truncated because max_tokens was too small. "
                "Increase --max-tokens or shorten the brief and try again. "
                f"(completion_tokens={completion_tokens}, max_tokens={self.max_tokens})"
            )

        if not isinstance(content, str):
            raise LLMError(f"Unexpected LLM response payload: {response.text}")

        return content


@dataclass
class AnthropicClient:
    """Anthropic Claude API クライアント。"""

    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    temperature: float = 0.4
    max_tokens: int = 1800
    session: requests.Session = field(default_factory=requests.Session, repr=False)
    anthropic_version: str = "2023-06-01"

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set. Please export it before running this command.")
        if not self.model:
            self.model = os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
        if not self.base_url:
            self.base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages")

    def generate_json(self, messages: List[Dict[str, str]]) -> str:
        _ensure_messages(messages)
        system_msgs = [msg["content"] for msg in messages if msg.get("role") == "system"]
        system_prompt = "\n\n".join(system_msgs) if system_msgs else None
        conversation = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            anthro_role = "user" if role == "user" else "assistant"
            conversation.append(
                {
                    "role": anthro_role,
                    "content": [{"type": "text", "text": msg.get("content", "")}],
                }
            )
        if not conversation:
            raise LLMError("Anthropic API requires at least one non-system message.")

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": conversation,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system_prompt:
            payload["system"] = system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
        }
        return _post_and_extract(
            self.base_url,
            payload,
            headers,
            self.session,
            ("content", 0, "text"),
            timeout=self.timeout,
        )


@dataclass
class GeminiClient:
    """Google Gemini (Generative Language) API クライアント。"""

    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    temperature: float = 0.4
    max_tokens: int = 1800
    session: requests.Session = field(default_factory=requests.Session, repr=False)

    def __post_init__(self) -> None:
        env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.api_key = self.api_key or env_key
        if not self.api_key:
            raise LLMError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. Please export it before running this command.")
        if not self.model:
            self.model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        if not self.base_url:
            self.base_url = os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

    def generate_json(self, messages: List[Dict[str, str]]) -> str:
        _ensure_messages(messages)
        system_msgs = [msg["content"] for msg in messages if msg.get("role") == "system"]
        system_instruction = (
            {"parts": [{"text": "\n\n".join(system_msgs)}], "role": "system"} if system_msgs else None
        )
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                continue
            gemini_role = "user" if role == "user" else "model"
            contents.append({"role": gemini_role, "parts": [{"text": msg.get("content", "")}]})
        if not contents:
            raise LLMError("Gemini API requires at least one user message.")

        effective_limit = DEFAULT_GEMINI_MAX_OUTPUT_TOKENS
        if self.max_tokens and self.max_tokens > 0:
            effective_limit = max(self.max_tokens, DEFAULT_GEMINI_MAX_OUTPUT_TOKENS)
        max_output_tokens = effective_limit
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction

        url = f"{self.base_url.rstrip('/')}/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        return _post_and_extract(
            url,
            payload,
            headers,
            self.session,
            ("candidates", 0, "content", "parts", 0, "text"),
            timeout=self.timeout,
        )


def _post_and_extract(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    session: requests.Session,
    path: tuple,
    *,
    timeout: int,
    retries: int = 2,
) -> str:
    # Minimal logging: record attempt and result (do not write API keys)
    safe_append_log(LLM_LOG_PATH, f"REQUEST {url} payload_keys={list(payload.keys())}")

    attempt = 0
    last_exception = None
    raw = None
    while attempt <= retries:
        attempt += 1
        try:
            response = session.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            safe_append_log(LLM_LOG_PATH, f"RESPONSE {response.status_code} {url}")
        except requests.HTTPError as err:
            detail = err.response.text if err.response is not None else str(err)
            safe_append_log(LLM_LOG_PATH, f"HTTP_ERROR {err} {url}")
            raise LLMError(f"LLM request failed: {detail}") from err
        except requests.RequestException as err:
            safe_append_log(LLM_LOG_PATH, f"REQUEST_EXCEPTION {err} {url}")
            raise LLMError(f"LLM request could not be sent: {err}") from err

        raw = response.text
        # Try JSON first, then YAML (if available). If neither parses, optionally retry.
        parsed = None
        try:
            parsed = response.json()
        except ValueError:
            try:
                import yaml as _yaml

                parsed = _yaml.safe_load(raw)
            except Exception:
                parsed = None

        # If still not parsed, attempt to extract a JSON substring heuristically.
        if parsed is None:
            try:
                candidate = extract_json_text(raw if raw is not None else "")
                if candidate:
                    try:
                        parsed = json.loads(candidate)
                    except Exception:
                        parsed = None
            except Exception:
                parsed = None

        if parsed is None:
            safe_append_log(LLM_LOG_PATH, f"PARSE_ATTEMPT_FAILED attempt={attempt} {url}")
            if attempt <= retries:
                time.sleep(1 * attempt)
                continue
            # final failure: save raw and raise
            err_file = save_llm_raw_error(raw, prefix="invalid_llm_response")
            safe_append_log(LLM_LOG_PATH, f"PARSE_ERROR saved={err_file} {url}")
            raise LLMError("LLM response could not be parsed as JSON or YAML; raw response saved.")

        # extraction
        try:
            part = parsed
            for key in path:
                part = part[key]
            if not isinstance(part, str):
                try:
                    part = json.dumps(part, ensure_ascii=False)
                except Exception:
                    part = str(part)
            return part
        except (KeyError, IndexError, TypeError) as err:
            last_exception = err
            safe_append_log(LLM_LOG_PATH, f"EXTRACT_ATTEMPT_FAILED attempt={attempt} {url}")
            if attempt <= retries:
                time.sleep(1 * attempt)
                continue
            # final failure: save raw and raise
            err_file = save_llm_raw_error(raw, prefix="invalid_llm_response")
            safe_append_log(LLM_LOG_PATH, f"EXTRACT_ERROR saved={err_file} {url}")
            raise LLMError(f"Unexpected LLM response payload: raw saved to {err_file}") from last_exception


def build_llm_client(
    provider: str,
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.4,
    max_tokens: int = 1800,
    timeout: int = 60,
) -> LLMClient:
    provider_key = (provider or "openai").lower()
    if provider_key in {"openai", "openrouter", "azure"}:
        return OpenAIChatClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    if provider_key == "anthropic":
        return AnthropicClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    if provider_key == "gemini":
        return GeminiClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
    raise LLMError(
        f"Unsupported provider '{provider}'. Supported providers: openai, anthropic, gemini."
    )


def generate_and_validate(
    client: LLMClient,
    messages: List[Dict[str, str]],
    *,
    schema: Optional[Dict] = None,
    instructions: str = "",
    retries: int = 2,
    backoff_seconds: int = 1,
) -> str:
    """Send messages through `client` while enforcing a strict JSON output (when `schema` provided).

    This helper will:
    - prepend a strict JSON-only template when `schema` is provided,
    - call `client.generate_json` and validate/sanitize the returned text,
    - retry on validation failures, and
    - save the raw response to `logs/llm_errors` on final failure.

    Returns a JSON string (compact) on success.
    """
    msgs = prepare_strict_json_messages(messages, schema=schema, instructions=instructions)

    attempt = 0
    last_exc: Optional[Exception] = None
    raw: Optional[str] = None
    while attempt <= retries:
        attempt += 1
        try:
            raw = client.generate_json(msgs)
        except Exception as e:
            last_exc = e
            safe_append_log(LLM_LOG_PATH, f"GENERATE_EXCEPTION attempt={attempt} {e}")
            if attempt <= retries:
                time.sleep(backoff_seconds * attempt)
                continue
            raise LLMError(f"LLM generate_json failed: {e}") from e

        # Validate / sanitize the returned text
        ok, parsed, err = sanitize_and_validate(raw if raw is not None else "", schema=schema)
        if ok and parsed is not None:
            try:
                return json.dumps(parsed, ensure_ascii=False)
            except Exception:
                return raw if raw is not None else ""

        safe_append_log(LLM_LOG_PATH, f"VALIDATION_FAILED attempt={attempt} err={err}")

        if attempt <= retries:
            time.sleep(backoff_seconds * attempt)
            continue

        # Final failure path: save raw response for inspection
        err_file = save_llm_raw_error(raw, prefix="invalid_llm_response")
        safe_append_log(LLM_LOG_PATH, f"FINAL_VALIDATION_FAILED saved={err_file}")

        raise LLMError(f"LLM response failed validation; raw saved to {err_file}") from last_exc
