"""AI layer configuration — resolved from environment, never hard-coded.

All provider credentials resolve through environment variables. No secrets are
embedded in this file or in any checked-in config. See AGENTS.md §11.5.

Configuration is loaded lazily and cached: ``AIConfig.from_env()`` returns the
same instance across the process, so a single ``os.environ`` refresh is enough
to change providers without a restart.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# Environment-variable names for each provider. BYOK providers are read from
# these keys; free/local providers need no key at all.
_PROVIDER_ENV_VARS = {
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "gemma": "GEMINI_API_KEY",
    "google_genai": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "cohere": "COHERE_API_KEY",
    "ollama": None,          # local, no key required
    "none": None,
}


@dataclass(frozen=True)
class AIConfig:
    """Immutable configuration for the AI enhancement layer.

    ``enabled=False`` is the safe default: the audit engine runs identically
    with or without this config. ``enabled=True`` only activates when a
    provider with a resolvable backend is selected.
    """

    enabled: bool = False
    provider: str = "none"
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: float = 30.0
    max_tokens: int = 2048
    temperature: float = 0.2
    # Hard ceiling on how much evidence text may be sent to a provider per
    # request, to bound token cost and context size.
    context_budget_tokens: int = 4000
    # Number of attempts before an AI call is abandoned and treated as a
    # graceful no-op (core audit continues unaffected).
    max_retries: int = 1
    # When True, malformed or partial AI output is logged and discarded rather
    # than surfaced as a finding.
    retry_on_malformed: bool = True

    # ── Factory ──────────────────────────────────────────────────────────

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "AIConfig":
        """Build an AIConfig from the environment.

        Reads ``SDAT_AI_PROVIDER`` (default ``openrouter`` if OPENROUTER_API_KEY is present)
        and provider credential env vars. Returns an always-disabled config when no provider
        is selected or no backend is resolvable.
        """
        env = env if env is not None else os.environ

        provider = (env.get("SDAT_AI_PROVIDER") or "").strip().lower()
        if not provider or provider == "none":
            if env.get("OPENROUTER_API_KEY"):
                provider = "openrouter"
            elif env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or env.get("GEMMA_MODEL"):
                provider = "gemini"
            elif env.get("OPENAI_API_KEY"):
                provider = "openai"
            elif env.get("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            elif env.get("AI_MODEL") or env.get("SDAT_AI_MODEL"):
                # Infer provider from model if specified
                model_hint = (env.get("AI_MODEL") or env.get("SDAT_AI_MODEL") or "").lower()
                if "qwen" in model_hint or "/" in model_hint:
                    provider = "openrouter"
                else:
                    return cls(enabled=False, provider="none")
            else:
                return cls(enabled=False, provider="none")

        key_env = _PROVIDER_ENV_VARS.get(provider)
        api_key: str | None = None
        if key_env is not None:
            raw = env.get(key_env) or (env.get("GOOGLE_API_KEY") if provider in ("gemini", "gemma", "google_genai") else None)
            if raw and raw.strip():
                api_key = raw.strip()

        # Local providers (ollama) and free hosted APIs may not need a key, but OpenRouter needs one if configured
        if key_env is not None and api_key is None and provider not in ("ollama",):
            return cls(enabled=False, provider=provider)

        model = (
            env.get("AI_MODEL")
            or env.get("SDAT_AI_MODEL")
            or env.get("OPENROUTER_MODEL")
            or env.get("GEMMA_MODEL")
            or env.get("GEMINI_MODEL")
            or _DEFAULT_MODELS.get(provider, "qwen/qwen3-coder:free")
        )
        base_url = env.get("SDAT_AI_BASE_URL")
        if not base_url and provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"

        timeout = _float_env(env, "SDAT_AI_TIMEOUT_SECONDS", 30.0)
        max_tokens = _int_env(env, "SDAT_AI_MAX_TOKENS", 2048)
        temperature = _float_env(env, "SDAT_AI_TEMPERATURE", 0.2)
        budget = _int_env(env, "SDAT_AI_CONTEXT_BUDGET_TOKENS", 4000)
        retries = _int_env(env, "SDAT_AI_MAX_RETRIES", 1)
        malformed = _bool_env(env, "SDAT_AI_RETRY_ON_MALFORMED", True)

        return cls(
            enabled=True,
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            timeout_seconds=timeout,
            max_tokens=max_tokens,
            temperature=temperature,
            context_budget_tokens=budget,
            max_retries=retries,
            retry_on_malformed=malformed,
        )

    @property
    def is_available(self) -> bool:
        """True when a usable backend is configured for this provider."""
        return self.enabled and self.provider != "none"

    def redacted(self) -> dict[str, Any]:
        """Return a serialisable, credential-free summary for logging/telemetry."""
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "max_tokens": self.max_tokens,
            "context_budget_tokens": self.context_budget_tokens,
            "api_key_set": bool(self.api_key),
        }


_DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "qwen/qwen3-coder:free",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-sonnet-latest",
    "gemini": "gemini-2.5-flash",
    "gemma": "gemma-2-9b-it",
    "google_genai": "gemini-2.5-flash",
    "groq": "llama-3.1-8b-instant",
    "mistral": "mistral-small-latest",
    "cohere": "command-r-plus",
    "ollama": "qwen2.5-coder",
}


def _float_env(env: dict[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _int_env(env: dict[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(env: dict[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}