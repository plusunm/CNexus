from __future__ import annotations

from typing import List
from urllib.parse import urlparse

import httpx

from core.execution.types import ChatResult, EmbedResult, ProviderHealth


class OpenAICompatibleProvider:
    provider_id = "openai_compatible"
    capabilities = frozenset({"chat"})

    def chat(
        self,
        messages: List[dict],
        *,
        model: str,
        base_url: str,
        api_key: str = "",
        temperature: float = 0.7,
        timeout: float = 120.0,
    ) -> ChatResult:
        url = self._chat_completions_url(base_url)
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif "deepseek.com" in (urlparse(base_url).hostname or "").lower():
            raise ValueError("DeepSeek API Key 未配置 — 请在大模型 API 中保存 Key")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        host = (urlparse(base_url).hostname or "").lower()
        if "deepseek.com" in host:
            payload["thinking"] = {"type": "disabled"}

        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code >= 400:
                body = resp.text[:500]
                if resp.status_code == 401:
                    raise ValueError(
                        "API Key 无效或已过期 (401) — 请到 platform.deepseek.com 重新创建 Key 并保存"
                    )
                raise ValueError(f"HTTP {resp.status_code}: {body}")
            data = resp.json()
        content = self._extract_message_text(data)
        return ChatResult(content=content, provider=self.provider_id, model=model, raw=data)

    def embed(self, text: str, *, model: str, timeout: float = 8.0) -> EmbedResult:
        raise NotImplementedError("openai_compatible provider does not expose embed in LEP v1")

    def health(self, *, api_key_set: bool = False, base_url: str = "") -> ProviderHealth:
        issues: List[str] = []
        if not api_key_set and "deepseek.com" in (urlparse(base_url).hostname or "").lower():
            issues.append("api_key_missing")
        state = "ready" if not issues else "degraded"
        return ProviderHealth(
            provider_id=self.provider_id,
            capabilities=["chat"],
            state=state,
            reachable=True,
            issues=issues,
            details={"base_url": base_url, "api_key_set": api_key_set},
        )

    @staticmethod
    def _chat_completions_url(base_url: str) -> str:
        url = base_url.strip().rstrip("/")
        if url.startswith("http://"):
            url = "https://" + url[len("http://") :]
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").rstrip("/")
        if path.endswith("/chat/completions"):
            return url
        if path.endswith("/v1") or path.endswith("/v4"):
            return f"{url}/chat/completions"
        if not path:
            if "deepseek.com" in host:
                return f"{parsed.scheme}://{parsed.netloc}/chat/completions"
            return f"{url}/v1/chat/completions"
        return f"{url}/chat/completions"

    @staticmethod
    def _extract_message_text(data: dict) -> str:
        if data.get("error"):
            err = data["error"]
            msg = err.get("message") if isinstance(err, dict) else str(err)
            raise ValueError(f"LLM API error: {msg}")

        choices = data.get("choices") or []
        if not choices:
            raise ValueError("LLM API returned no choices")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        reasoning = message.get("reasoning_content")
        if isinstance(reasoning, str) and reasoning.strip():
            return reasoning.strip()

        if content is not None and not isinstance(content, str):
            text = str(content).strip()
            if text:
                return text

        raise ValueError(
            "LLM returned empty message content (check model id and API balance)"
        )
