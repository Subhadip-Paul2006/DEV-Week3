"""Foundation Rule Engine Agent.

Audits foundation concepts (caching, circuit-breakers, retries, auth, logging, config, etc.)
from project signals and structural evidence facts according to AGENTS.md.
"""

from __future__ import annotations

from typing import Any, List, Optional

from sdat.models import EvidenceKind, FileSignals, Signal, SignalKind
from sdat.rules.engine import build_decisions


class FoundationAgent:
    """Agent evaluating foundational system-design rules."""

    agent_id: str = "F-01"
    agent_name: str = "foundation_rules_agent"

    def __init__(self, agent_id: str = "F-01", agent_name: str = "foundation_agent", owned_concepts: Optional[List[str]] = None) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.owned_concepts = owned_concepts

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        """Execute rule evaluations against project context and return AGENTS.md schema."""
        target_root = project_context.get("target_root", "")
        run_id = project_context.get("run_id", "foundation_run")
        signals = project_context.get("signals", [])

        # Group signals into FileSignals
        file_map: dict[str, list[Signal]] = {}
        for s in signals:
            if isinstance(s, Signal):
                file_map.setdefault(str(s.file_path), []).append(s)

        absence_concepts = {
            "ttl": "foundation.caching",
            "retries": "resilience.retries",
            "timeout": "resilience.timeouts",
        }
        for bundle in project_context.get("bundles", []):
            for fact in getattr(bundle, "facts", ()):
                concept_id = absence_concepts.get(fact.subject)
                if fact.kind != EvidenceKind.ABSENT_PATTERN or not concept_id:
                    continue
                if bundle.concept_id != concept_id:
                    continue
                absence = Signal(
                    concept_id=concept_id,
                    kind=SignalKind.ABSENCE,
                    file_path=fact.file_path,
                    line_range=fact.line_range,
                    evidence=fact.snippet,
                    confidence=fact.extraction_confidence,
                )
                file_map.setdefault(str(fact.file_path), []).append(absence)

        file_signals = [FileSignals(file=f, signals=sigs) for f, sigs in file_map.items()]
        project_type = project_context.get("project_type", "backend")

        # Evaluate rules
        all_decisions = build_decisions(file_signals, project_type=project_type)

        # Filter by owned concepts if specified
        if self.owned_concepts:
            filtered_decisions = [d for d in all_decisions if d.concept_id in self.owned_concepts]
        else:
            filtered_decisions = all_decisions

        # Serialize decisions according to AGENTS.md contract
        decisions_json = []
        for d in filtered_decisions:
            decisions_json.append({
                "concept_id": d.concept_id,
                "concept_name": d.concept_name,
                "status": d.status.value,
                "confidence": d.confidence,
                "evidence": [
                    {
                        "file": ev.file,
                        "line": ev.line,
                        "snippet": ev.snippet,
                        "note": ev.note,
                    }
                    for ev in d.evidence
                ],
                "misconfiguration": d.misconfiguration,
                "gaps": d.gaps,
                "recommendation": d.recommendation,
                "priority": d.priority.value,
            })

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": run_id,
            "target_root": target_root,
            "concepts_evaluated": len(decisions_json),
            "decisions": decisions_json,
        }
