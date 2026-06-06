import logging
from typing import List, Optional

import httpx

from core.model_registry import ModelProfile

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified chat client for Ollama and OpenAI-compatible APIs."""

    def chat(
        self,
        profile: ModelProfile,
        messages: List[dict],
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> str:
        if profile.provider == "ollama":
            return self._chat_ollama(profile, messages, temperature, timeout)
        return self._chat_openai_compatible(profile, messages, temperature, timeout)

    def test_connection(self, profile: ModelProfile) -> tuple[bool, str]:
        try:
            reply = self.chat(
                profile,
                [{"role": "user", "content": "Reply with exactly: OK"}],
                temperature=0,
                timeout=30.0,
            )
            return True, reply[:200]
        except Exception as exc:
            logger.warning("Model test failed: %s", exc)
            return False, str(exc)

    def _chat_ollama(
        self,
        profile: ModelProfile,
        messages: List[dict],
        temperature: float,
        timeout: float,
    ) -> str:
        base = profile.base_url.rstrip("/")
        payload = {
            "model": profile.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(f"{base}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")

    def _chat_openai_compatible(
        self,
        profile: ModelProfile,
        messages: List[dict],
        temperature: float,
        timeout: float,
    ) -> str:
        base = profile.base_url.rstrip("/")
        url = f"{base}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if profile.api_key:
            headers["Authorization"] = f"Bearer {profile.api_key}"

        payload = {
            "model": profile.model,
            "messages": messages,
            "temperature": temperature,
        }
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
