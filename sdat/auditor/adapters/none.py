"""None auditor adapter — returns unknown for every concept. No LLM required."""

from __future__ import annotations

from ..auditor.base import Auditor, TargetContext
from ..models import Decision, DecisionStatus, Priority, Signal


class NoneAuditor(Auditor):
    """Stub auditor: returns unknown decisions for every signal's concept."""

    provider_id = "none"

    def audit(self, signals: list[Signal], context: TargetContext) -> list[Decision]:
        seen: set[str] = set()
        decisions: list[Decision] = []

        for sig in signals:
            if sig.concept_id not in seen:
                seen.add(sig.concept_id)
                decisions.append(
                    Decision(
                        concept_id=sig.concept_id,
                        concept_name=sig.concept_id.split(".")[-1],
                        status=DecisionStatus.UNKNOWN,
                        confidence=0.0,
                        priority=Priority.N_A,
                    )
                )

        return decisions

