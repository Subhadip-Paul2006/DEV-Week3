"""OpenRouter Adapter for SDAT — Primary AI Adapter.

Connects to open-weight models via OpenRouter (primary model: Qwen3-Coder 480B A35B
with identifier `qwen/qwen3-coder:free`).

Conforms to AGENTS.md §11 (AI Layer Integration & Developer Invariants):
- Provider-agnostic interface via BaseAIAdapter / AIProvider.
- Model ID configurable through `AI_MODEL`, `OPENROUTER_MODEL`, or `SDAT_AI_MODEL`.
- API key resolved from `OPENROUTER_API_KEY` (never committed or hardcoded).
- Zero-dependency implementation using standard library urllib.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from sdat.ai.gateway import BaseAIAdapter

logger = logging.getLogger("sdat.ai.adapters.openrouter")

DEFAULT_OPENROUTER_MODEL = "qwen/qwen3-coder:free"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterAdapter(BaseAIAdapter):
    """Primary AI Adapter connecting to OpenRouter API."""

    provider_name: str = "openrouter"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 35.0,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> None:
        self.model = (
            model
            or os.environ.get("AI_MODEL")
            or os.environ.get("OPENROUTER_MODEL")
            or os.environ.get("SDAT_AI_MODEL")
            or DEFAULT_OPENROUTER_MODEL
        )
        self._api_key = (
            api_key
            or os.environ.get("OPENROUTER_API_KEY")
        )
        self.base_url = (
            base_url
            or os.environ.get("OPENROUTER_BASE_URL")
            or os.environ.get("SDAT_AI_BASE_URL")
            or DEFAULT_OPENROUTER_BASE_URL
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens

    def is_configured(self) -> bool:
        """Return True if an API key is present."""
        return bool(self._api_key and self._api_key.strip())

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Execute a text completion or chat generation via OpenRouter."""
        return self.generate_reasoning(prompt=prompt, system_instruction=system_prompt, timeout_seconds=self.timeout_seconds)

    def generate_reasoning(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        timeout_seconds: float = 35.0,
    ) -> str:
        """Execute a chat completion request to OpenRouter with system instructions."""
        if not self.is_configured():
            raise ValueError(
                "OpenRouter is not configured. "
                "Set OPENROUTER_API_KEY and optionally AI_MODEL in your environment."
            )

        endpoint = f"{self.base_url}/chat/completions"

        messages: list[dict[str, str]] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key.strip()}",
            "HTTP-Referer": "https://github.com/shubh06/sdat",
            "X-Title": "SDAT System Design Audit Tool",
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
                parsed = json.loads(body)

                choices = parsed.get("choices", [])
                if not choices:
                    logger.warning("OpenRouter returned empty choices: %s", body)
                    return ""

                content = choices[0].get("message", {}).get("content", "")
                return content or ""

        except urllib.error.HTTPError as exc:
            err_body = ""
            try:
                err_body = exc.read().decode("utf-8")
            except Exception:
                pass
            logger.warning("OpenRouter HTTP %d error (%s): %s", exc.code, self.model, err_body)
            raise RuntimeError(f"OpenRouter API returned HTTP {exc.code} for model {self.model}: {err_body}") from exc
        except urllib.error.URLError as exc:
            logger.warning("OpenRouter network error (%s): %s", self.model, exc.reason)
            raise RuntimeError(f"OpenRouter connection error: {exc.reason}") from exc
        except Exception as exc:
            logger.warning("OpenRouter request error (%s): %s", self.model, exc)
            raise RuntimeError(f"OpenRouter generation error: {exc}") from exc
