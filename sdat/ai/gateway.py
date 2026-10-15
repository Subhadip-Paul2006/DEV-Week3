"""AI Gateway Abstraction Layer.

Implements AGENTS.md §11.2:
- AI Gateway Abstraction (`sdat/ai/gateway.py`).
- Agents and tools never bind directly to a single provider (OpenAI, Anthropic,
  Gemini, Groq, Ollama, Gemma 4, BYOK).
- Plug-and-play interchangeable providers with fail-open fallback semantics.
- Telemetry integration via AuditTelemetry.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

from sdat.ai.config import AIConfig
from sdat.telemetry.tracker import AuditTelemetry

logger = logging.getLogger("sdat.ai.gateway")


@dataclass
class RemediationItem:
    """Actionable remediation guidance for a specific architectural finding."""
    concept_id: str
    concept_name: str
    severity: str
    status: str
    confidence: float
    finding: str
    evidence: List[dict[str, Any]]
    why_it_matters: str
    architectural_impact: str
    recommended_solution: str
    implementation_steps: List[str]
    validation: str
    ai_reasoning: str = ""
    gemma_reasoning: str = ""
    diagram_before: Optional[str] = None
    diagram_after: Optional[str] = None
    trade_offs: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.ai_reasoning and self.gemma_reasoning:
            self.ai_reasoning = self.gemma_reasoning
        elif not self.gemma_reasoning and self.ai_reasoning:
            self.gemma_reasoning = self.ai_reasoning

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "severity": self.severity,
            "status": self.status,
            "confidence": self.confidence,
            "finding": self.finding,
            "evidence": self.evidence,
            "why_it_matters": self.why_it_matters,
            "architectural_impact": self.architectural_impact,
            "ai_reasoning": self.ai_reasoning,
            "gemma_reasoning": self.gemma_reasoning,
            "recommended_solution": self.recommended_solution,
            "implementation_steps": self.implementation_steps,
            "validation": self.validation,
            "diagram_before": self.diagram_before,
            "diagram_after": self.diagram_after,
            "trade_offs": self.trade_offs,
        }


@dataclass
class AIEnrichmentResult:
    """Outcome of AI reasoning pass over deterministic findings."""
    available: bool = False
    provider: str = "none"
    model: str = "none"
    executive_summary: str = ""
    remediations: List[RemediationItem] = field(default_factory=list)
    is_cached: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "provider": self.provider,
            "model": self.model,
            "executive_summary": self.executive_summary,
            "remediations": [r.to_dict() for r in self.remediations],
            "is_cached": self.is_cached,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
        }


class AIProvider(ABC):
    """Abstract base class for AI providers behind the gateway."""

    provider_id: str = "abstract"

    def __init__(self, config: AIConfig) -> None:
        self.config = config

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        """Execute a text completion or chat generation."""
        ...

    def is_configured(self) -> bool:
        """Return True if credentials and environment are set."""
        return self.config.is_available

    def generate_reasoning(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        """Execute text completion with system instruction."""
        return self.complete(prompt, system_prompt=system_instruction)


BaseAIAdapter = AIProvider


class GoogleGenAIProvider(AIProvider):
    """Google GenAI SDK provider (supporting Gemma 4 and Gemini)."""
    provider_id = "google-genai"

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.config.api_key)
            config = types.GenerateContentConfig(
                temperature=self.config.temperature,
                max_output_tokens=self.config.max_tokens,
                system_instruction=system_prompt if system_prompt else None,
            )
            response = client.models.generate_content(
                model=self.config.model or "gemini-2.5-flash",
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            logger.warning("Google GenAI / Gemma 4 request failed: %s", exc)
            raise


class NoneProvider(AIProvider):
    """Null provider: returns an empty string or fallback explanation. No LLM calls."""
    provider_id = "none"

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        return ""


class OllamaProvider(AIProvider):
    """Local provider for Ollama (supporting Gemma 4, Qwen, DeepSeek, etc.)."""
    provider_id = "ollama"

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            import urllib.error
            import urllib.request

            base_url = self.config.base_url or "http://localhost:11434"
            url = f"{base_url.rstrip('/')}/api/generate"
            model = self.config.model or "gemma4"

            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.temperature,
                    "num_predict": self.config.max_tokens,
                },
            }
            if system_prompt:
                payload["system"] = system_prompt

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "")
        except Exception as exc:
            logger.warning("Ollama provider request failed: %s", exc)
            raise


class OpenAICompatibleProvider(AIProvider):
    """OpenAI-compatible REST provider (OpenAI, Groq, Mistral, Local vLLM, etc.)."""
    provider_id = "openai-compatible"

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            import urllib.error
            import urllib.request

            base_url = self.config.base_url or "https://api.openai.com/v1"
            url = f"{base_url.rstrip('/')}/chat/completions"
            model = self.config.model or "gpt-4o-mini"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }

            headers = {"Content-Type": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
        except Exception as exc:
            logger.warning("OpenAI-compatible provider request failed: %s", exc)
            raise


class AnthropicProvider(AIProvider):
    """Anthropic Claude Messages API provider."""
    provider_id = "anthropic"

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        try:
            import urllib.error
            import urllib.request

            base_url = self.config.base_url or "https://api.anthropic.com/v1"
            url = f"{base_url.rstrip('/')}/messages"
            model = self.config.model or "claude-3-5-sonnet-latest"

            payload: dict[str, Any] = {
                "model": model,
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                payload["system"] = system_prompt

            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.config.api_key or "",
                "anthropic-version": "2023-06-01",
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers=headers, method="POST")

            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result.get("content", [])
                if content and isinstance(content, list):
                    return content[0].get("text", "")
                return ""
        except Exception as exc:
            logger.warning("Anthropic provider request failed: %s", exc)
            raise


class OpenRouterProvider(AIProvider):
    """OpenRouter API provider (supporting Qwen3-Coder 480B A35B and open-weight models)."""
    provider_id = "openrouter"

    def complete(self, prompt: str, system_prompt: str | None = None) -> str:
        from sdat.ai.adapters.openrouter import OpenRouterAdapter

        adapter = OpenRouterAdapter(
            model=self.config.model,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            timeout_seconds=self.config.timeout_seconds,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
        return adapter.complete(prompt, system_prompt=system_prompt)


class AIGateway:
    """Unified AI Gateway for SDAT — routing requests across plug-and-play providers.

    Features fail-open resilience: if an AI request fails, times out, or encounters
    an unavailable key, telemetry records the failure and a safe fallback string
    is returned, ensuring core deterministic audits continue uninterrupted.
    """

    def __init__(self, config: AIConfig | None = None, telemetry: AuditTelemetry | None = None) -> None:
        self.config = config or AIConfig.from_env()
        self.telemetry = telemetry
        self._provider = self._init_provider()

    def _init_provider(self) -> AIProvider:
        if not self.config.is_available:
            return NoneProvider(self.config)

        prov = self.config.provider
        if prov == "openrouter":
            return OpenRouterProvider(self.config)
        elif prov in ("gemini", "gemma", "google_genai", "google-genai"):
            return GoogleGenAIProvider(self.config)
        elif prov == "ollama":
            return OllamaProvider(self.config)
        elif prov in ("openai", "groq", "mistral", "cohere", "openai-compatible"):
            return OpenAICompatibleProvider(self.config)
        elif prov == "anthropic":
            return AnthropicProvider(self.config)
        else:
            return NoneProvider(self.config)

    def complete(self, prompt: str, system_prompt: str | None = None, fallback: str = "") -> str:
        """Execute a text completion through the gateway with fail-open safety.

        Returns *fallback* if the provider is disabled, unconfigured, or encounters
        any error. Records timing and failure metrics in AuditTelemetry.
        """
        if not self.config.is_available or isinstance(self._provider, NoneProvider):
            return fallback

        for attempt in range(1, self.config.max_retries + 2):
            try:
                if self.telemetry:
                    with self.telemetry.time_operation("ai_request"):
                        res = self._provider.complete(prompt, system_prompt=system_prompt)
                else:
                    res = self._provider.complete(prompt, system_prompt=system_prompt)
                return res if res else fallback
            except Exception as exc:
                logger.debug("AI Gateway attempt %d failed: %s", attempt, exc)
                if attempt > self.config.max_retries:
                    if self.telemetry:
                        self.telemetry.record_ai_failure()
                    logger.info("AI Gateway request failed after %d retries; falling back.", attempt)
                    return fallback

        return fallback
