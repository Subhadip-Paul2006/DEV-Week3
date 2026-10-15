"""Research Agent — external context provider.

Implements AGENTS.md §6 (Research provides context, NOT target proof):
- Peer patterns and literature findings provide architectural context and
  expected-pattern expectations.
- A peer or reference project using a pattern is NEVER proof that the target
  project implements it. Target repository implementation truth comes strictly
  from scanner EvidenceFacts.
- Research is optional and fail-open: any failure degrades gracefully and the
  deterministic audit continues unaffected.
"""

from __future__ import annotations

import logging
from typing import Any, List

from sdat.ai.config import AIConfig
from sdat.ai.gateway import AIGateway
from sdat.models import Decision, DecisionStatus
from sdat.telemetry.tracker import AuditTelemetry

logger = logging.getLogger("sdat.ai.research")


class ResearchAgent:
    """Optional model-context helper; it does not perform live external research."""

    def __init__(
        self,
        config: AIConfig | None = None,
        telemetry: AuditTelemetry | None = None,
    ) -> None:
        self.gateway = AIGateway(config=config, telemetry=telemetry)

    def research(
        self,
        decisions: List[Decision],
        target_root: str = ".",
        max_concepts: int = 10,
    ) -> dict[str, Any]:
        """Generate bounded conceptual context without claiming external sources."""
        if not self.gateway.config.is_available:
            return {
                "enabled": False,
                "origin": "none",
                "sources": [],
                "context": {},
                "note": "Context provider unavailable; no external research was performed.",
            }

        # Prioritise MISSING and MISCONFIGURED findings by priority
        priority_rank = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }
        candidates = [
            d for d in decisions
            if d.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED)
        ]
        candidates.sort(key=lambda d: priority_rank.get(d.priority.value, 9))
        top = candidates[:max_concepts]

        candidates = [
            {
                "concept_id": d.concept_id,
                "concept_name": d.concept_name,
                "status": d.status.value,
                "gaps": list(d.gaps)[:5],
            }
            for d in top
        ]
        system_prompt = (
            "You provide general model-prior architectural context, not live research. Return JSON with "
            "a context object keyed by input concept_id, each value containing peer_patterns, "
            "literature_findings, and expected_implementation lists. Do not include sources or citations. "
            "This context is not evidence about the target repository."
        )
        prompt = (
            f"Findings for architectural context only: {candidates}"
        )
        try:
            import json
            raw = self.gateway.complete(prompt, system_prompt=system_prompt, fallback="")
            if not raw:
                return {"enabled": False, "origin": "none", "sources": [], "context": {}}
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(raw[start:end + 1])
                returned = parsed.get("context", {})
                allowed = {item["concept_id"] for item in candidates}
                context = {key: value for key, value in returned.items() if key in allowed and isinstance(value, dict)}
                return {
                    "enabled": True,
                    "origin": "model_prior_knowledge",
                    "sources": [],
                    "context": context,
                    "note": "Generated context only; no live external research or citations were used.",
                }
            return {"enabled": False, "origin": "none", "sources": [], "context": {}}
        except Exception as exc:
            logger.debug("Optional model context generation failed: %s", exc)
            return {"enabled": False, "origin": "none", "sources": [], "context": {}}
