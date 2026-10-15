"""Frontend System-Design Auditor Agent (D-21).

Implements the SDAT Swarm Agent Contract (AGENTS.md) for the Frontend workload domain.
Consumes structured EvidenceFacts and repository context, evaluates frontend
system-design concepts, and outputs decisions and explainable dimension scores.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from sdat.frontend.knowledge_pack import FrontendKnowledgePack
from sdat.frontend.models import FrontendAuditResult
from sdat.frontend.page_analyzer import FrontendPageAnalyzer
from sdat.frontend.runtime import OfflineRuntimeCollector, ProvidedRuntimeCollector
from sdat.frontend.scoring import FrontendScoringEngine
from sdat.models import Decision, EvidenceFact


class FrontendAgent:
    """D-21 Frontend System-Design Auditor Agent."""

    agent_id: str = "D-21"
    agent_name: str = "frontend_agent"
    domain: str = "frontend"
    knowledge_pack_id: str = "kp.frontend"

    def __init__(self, agent_id: str = "D-21", agent_name: str = "frontend_agent") -> None:
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.domain = "frontend"
        self.knowledge_pack_id = "kp.frontend"
        self.knowledge_pack = FrontendKnowledgePack()
        self.scoring_engine = FrontendScoringEngine()

    def run(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the frontend agent audit (alias to audit for SwarmAgent protocol)."""
        return self.audit(project_context)

    def audit(self, project_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the frontend system-design audit against project_context.

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

        # Optional runtime telemetry ingestion
        runtime_data = project_context.get("runtime_metrics")
        if runtime_data:
            collector = ProvidedRuntimeCollector(runtime_data)
        else:
            collector = OfflineRuntimeCollector()
        runtime = collector.collect()

        # Page-level analysis
        page_analyzer = FrontendPageAnalyzer(target_root)
        pages = page_analyzer.analyze_all_pages(runtime=runtime)

        # Detect frontend frameworks from facts or pages
        frameworks: set[str] = set()
        for f in facts:
            if f.framework:
                frameworks.add(f.framework)
        for p in pages:
            if p.rendering_model.value in ("ssr", "ssg", "csr"):
                frameworks.add(p.rendering_model.value)

        # Evaluate rules across 15 dimensions
        eval_results = self.knowledge_pack.evaluate(facts, pages, runtime=runtime)
        decisions: list[Decision] = self.knowledge_pack.to_decisions(eval_results)

        # Compute multi-dimensional scores
        dimension_scores, overall_score, overall_status = self.scoring_engine.compute_scores(eval_results)

        # Create audit result summary
        is_frontend = bool(pages or any("frontend" in str(f.file_path).lower() for f in facts) or bool(frameworks))
        summary = (
            f"Evaluated {len(pages)} frontend pages across {len(dimension_scores)} architectural dimensions. "
            f"Overall score: {overall_score if overall_score is not None else 'N/A'} ({overall_status})."
        )

        audit_result = FrontendAuditResult(
            target_root=target_root,
            detected_frameworks=tuple(sorted(frameworks)),
            is_frontend=is_frontend,
            pages=tuple(pages),
            dimension_scores=dimension_scores,
            overall_score=overall_score,
            overall_status=overall_status,
            summary=summary,
            decisions=tuple(decisions),
        )

        # Output format matching AGENTS.md §3 contract
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
            "frontend_audit": audit_result.to_dict(),
        }
