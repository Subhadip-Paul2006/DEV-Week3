"""Gemma 4 / Google GenAI Adapter for SDAT.

Connects to Gemma 4 (or Gemini models) via the official Google GenAI SDK (`google-genai`).
Configurable model via `GEMMA_MODEL` or `GEMINI_MODEL`.
Configurable API key via `GEMINI_API_KEY` or `GOOGLE_API_KEY`.
"""

from __future__ import annotations

import os
from typing import Optional

from sdat.ai.gateway import BaseAIAdapter


class GemmaAdapter(BaseAIAdapter):
    """Adapter for Gemma 4 via the Google GenAI SDK."""

    provider_name: str = "google_genai"

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.model = (
            model
            or os.environ.get("GEMMA_MODEL")
            or os.environ.get("GEMINI_MODEL")
            or "gemini-2.5-flash"
        )
        self._api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self._client = None

    def is_configured(self) -> bool:
        """Return True if an API key is available."""
        return bool(self._api_key)

    def _get_client(self):
        if self._client is None and self.is_configured():
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception as exc:
                raise RuntimeError(f"Failed to initialize Google GenAI client: {exc}") from exc
        return self._client

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Execute text completion conforming to AIProvider protocol."""
        return self.generate_reasoning(prompt, system_instruction=system_prompt)

    def generate_reasoning(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        """Execute a text generation call against the configured model."""
        if not self.is_configured():
            raise ValueError(
                "Gemma 4 / Google GenAI is not configured. "
                "Set GEMINI_API_KEY (or GOOGLE_API_KEY) and optionally GEMMA_MODEL in your environment."
            )

        client = self._get_client()
        if client is None:
            raise RuntimeError("Google GenAI client could not be created.")

        try:
            from google.genai import types

            config = types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system_instruction if system_instruction else None,
            )

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            raise RuntimeError(f"Gemma 4 generation error ({self.model}): {exc}") from exc
