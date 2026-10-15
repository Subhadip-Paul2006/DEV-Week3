"""Swarm adapter for deterministic KnowledgePacks without dedicated agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sdat.models import Decision


class KnowledgePackAgent:
    """Expose an existing deterministic pack through the swarm agent contract."""

    def __init__(self, agent_id: str, agent_name: str, knowledge_pack: Any) -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.knowledge_pack = knowledge_pack

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        target_root = Path(project_context.get("target_root", "."))
        facts = project_context.get("evidence_facts", [])
        if not isinstance(facts, list):
            facts = []
        results = self.knowledge_pack.evaluate(facts, target_root=target_root)
        decisions: list[Decision] = self.knowledge_pack.to_decisions(results)
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": project_context.get("run_id", "run-local"),
            "target_root": str(target_root),
            "concepts_evaluated": len(decisions),
            "decisions": [
                {
                    "concept_id": decision.concept_id,
                    "concept_name": decision.concept_name,
                    "status": decision.status.value,
                    "confidence": decision.confidence,
                    "evidence": [
                        {"file": item.file, "line": item.line, "snippet": item.snippet, "note": item.note}
                        for item in decision.evidence
                    ],
                    "misconfiguration": decision.misconfiguration,
                    "gaps": list(decision.gaps),
                    "recommendation": decision.recommendation,
                    "priority": decision.priority.value,
                }
                for decision in decisions
            ],
        }
