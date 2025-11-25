from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol

import requests


class LLMError(RuntimeError):
    """Raised when the LLM client cannot complete a request."""


class LLMClient(Protocol):
    def generate_json(self, messages: List[Dict[str, str]]) -> str: ...


def _ensure_messages(messages: List[Dict[str, str]]) -> None:
    if not messages:
        raise LLMError("No messages were provided for the LLM request.")


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
) -> str:
    try:
        response = session.post(url, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
    except requests.HTTPError as err:
        detail = err.response.text if err.response is not None else str(err)
        raise LLMError(f"LLM request failed: {detail}") from err
    except requests.RequestException as err:
        raise LLMError(f"LLM request could not be sent: {err}") from err

    data: Any = response.json()
    try:
        for key in path:
            data = data[key]
        if not isinstance(data, str):
            raise TypeError("LLM response is not text.")
        return data
    except (KeyError, IndexError, TypeError) as err:
        raise LLMError(f"Unexpected LLM response payload: {response.text}") from err


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
