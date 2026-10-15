"""SDAT AI Enhancement Layer — optional, plug-and-play, never mandatory.

Implements AGENTS.md §11 (AI Layer Integration & Developer Invariants):

1. **SDAT Core Independence** — the deterministic audit engine MUST remain fully
   functional with no AI model configured. This package is loaded lazily and
   every AI call is wrapped in fail-open semantics: a missing key, a network
   error, or an unavailable model never raises into the core audit path.
2. **Gateway Abstraction** — all AI interaction passes through ``AIGateway``.
   Agents and tools never bind directly to a single provider.
3. **Deterministic Evidence is Authoritative** — AI produces plain-language
   explanations, executive summaries, and conversational Q&A only. It MUST
   never silently modify, invent, suppress, or override factual evidence,
   detection status, or severity scores.
4. **Context Grounding** — AI operates on strictly bounded context drawn from
   SDAT findings, never raw source or unverified claims.
5. **Secret Hygiene** — no API keys or tokens are embedded in source, fixtures,
   or version-controlled configs. All credentials resolve via environment
   variables or secure storage.

Public surface is intentionally small: configuration, gateway, grounding,
explanation, and research.
"""

from __future__ import annotations

from sdat.ai.config import AIConfig
from sdat.ai.gateway import AIGateway
from sdat.ai.grounding import GroundedContext

__all__ = ["AIConfig", "AIGateway", "GroundedContext"]
__version__ = "0.1.0"