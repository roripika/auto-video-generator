from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict

import requests

from src.models import VoiceSettings


class VoicevoxError(RuntimeError):
    """Raised when VOICEVOX API interaction fails."""


@dataclass
class VoicevoxClient:
    base_url: str = "http://localhost:50021"
    timeout_sec: int = 60
    retries: int = 3
    backoff_factor: float = 1.5

    def _post_json(self, path: str, params: Dict[str, Any] | None = None, json_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        attempt = 0
        while True:
            try:
                response = requests.post(url, params=params, json=json_data, timeout=self.timeout_sec)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # broad to surface context
                attempt += 1
                if attempt > self.retries:
                    raise VoicevoxError(f"VOICEVOX request failed ({url}): {exc}") from exc
                time.sleep(self.backoff_factor ** (attempt - 1))

    def _post_binary(self, path: str, params: Dict[str, Any] | None, json_data: Dict[str, Any]) -> bytes:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        attempt = 0
        while True:
            try:
                response = requests.post(url, params=params, json=json_data, timeout=self.timeout_sec)
                response.raise_for_status()
                return response.content
            except Exception as exc:
                attempt += 1
                if attempt > self.retries:
                    raise VoicevoxError(f"VOICEVOX synthesis failed ({url}): {exc}") from exc
                time.sleep(self.backoff_factor ** (attempt - 1))

    def synthesize(self, text: str, voice: VoiceSettings) -> bytes:
        """Generate WAV bytes for the given text."""
        if not text.strip():
            raise VoicevoxError("Cannot synthesize empty text")

        query = self._post_json(
            "/audio_query",
            params={"text": text, "speaker": voice.speaker_id},
        )
        query["speedScale"] = voice.speedScale
        query["pitchScale"] = voice.pitchScale
        query["intonationScale"] = voice.intonationScale
        query["volumeScale"] = voice.volumeScale

        return self._post_binary(
            "/synthesis",
            params={"speaker": voice.speaker_id},
            json_data=query,
        )
