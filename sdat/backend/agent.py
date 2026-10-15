"""Backend System-Design Auditor Agent (D-01).

Implements the SDAT Swarm Agent Contract (AGENTS.md) for the Backend workload domain.
Consumes structured EvidenceFacts and repository context, evaluates backend
system-design concepts, and outputs decisions and explainable dimension scores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sdat.backend.analyzer import BackendStructuralAnalyzer
from sdat.backend.knowledge_pack import BackendKnowledgePack
from sdat.backend.models import BackendAuditResult
from sdat.backend.scoring import BackendScoringEngine
from sdat.models import Decision, EvidenceFact


class BackendAgent:
    """D-01 Backend System-Design Auditor Agent."""

    agent_id: str = "D-01"
    agent_name: str = "backend_agent"
    domain: str = "backend"
    knowledge_pack_id: str = "kp.backend"

    def __init__(self, agent_id: str = "D-01", agent_name: str = "backend_agent") -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.domain = "backend"
        self.knowledge_pack_id = "kp.backend"
        self.knowledge_pack = BackendKnowledgePack()
        self.scoring_engine = BackendScoringEngine()

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        """Execute the backend agent audit (alias for SwarmAgent protocol)."""
        return self.audit(project_context)

    def audit(self, project_context: dict[str, Any]) -> dict[str, Any]:
        """Execute the backend system-design audit against project_context.

        Conforms strictly to the AGENTS.md Agent Contract.
        """
        target_root_raw = project_context.get("target_root", ".")
        target_root = Path(target_root_raw)
        run_id = project_context.get("run_id", "run-local")

        # Ingest or parse EvidenceFacts
        raw_facts = project_context.get("evidence_facts", [])
        facts: list[EvidenceFact] = []
        for rf in raw_facts:
            if isinstance(rf, EvidenceFact):
                facts.append(rf)
            elif isinstance(rf, dict):
                try:
                    facts.append(EvidenceFact.from_dict(rf))
                except Exception:
                    pass

        # Perform structural discovery
        analyzer = BackendStructuralAnalyzer(target_root)
        summary = analyzer.analyze(facts)

        # Evaluate rules
        eval_results = self.knowledge_pack.evaluate(facts, summary)
        decisions: list[Decision] = self.knowledge_pack.to_decisions(eval_results)

        # Compute dimension scores
        dimension_scores, overall_score, overall_status = self.scoring_engine.compute_scores(eval_results)

        is_backend = bool(
            summary.endpoints
            or summary.middlewares
            or summary.detected_frameworks
            or summary.detected_databases
            or summary.detected_queues
            or any(f.framework for f in facts)
            or any("backend" in str(f.file_path).lower() or "api" in str(f.file_path).lower() for f in facts)
        )

        audit_summary = (
            f"Evaluated {len(summary.endpoints)} endpoints, {len(summary.middlewares)} middlewares across "
            f"{len(dimension_scores)} architectural dimensions. "
            f"Overall score: {overall_score if overall_score is not None else 'N/A'} ({overall_status})."
        )

        audit_result = BackendAuditResult(
            target_root=target_root,
            detected_frameworks=tuple(sorted(summary.detected_frameworks)),
            detected_databases=tuple(sorted(summary.detected_databases)),
            detected_queues=tuple(sorted(summary.detected_queues)),
            is_backend=is_backend,
            endpoints_count=len(summary.endpoints),
            middlewares_count=len(summary.middlewares),
            boundaries_count=len(summary.boundaries),
            dimension_scores=dimension_scores,
            overall_score=overall_score,
            overall_status=overall_status,
            summary=audit_summary,
            decisions=tuple(decisions),
        )

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": run_id,
            "target_root": str(target_root),
            "concepts_evaluated": len(decisions),
            "decisions": [
                {
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
                    "gaps": list(d.gaps),
                    "recommendation": d.recommendation,
                    "priority": d.priority.value,
                }
                for d in decisions
            ],
            "backend_audit": audit_result.to_dict(),
        }
