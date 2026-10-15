"""Context Grounding Subsystem for AI Interactions.

Implements AGENTS.md §11.3, §11.4:
- Context Grounding: Bounded context drawn strictly from deterministic SDAT
  findings, evidence facts, and verified concepts.
- Deterministic Evidence is Authoritative: AI never invents, modifies,
  suppresses, or overrides factual evidence.
- Token Budgeting: Enforces token/character budgets to avoid context blowout.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from sdat.models import Decision, DecisionStatus, Priority


@dataclass(frozen=True)
class GroundedFinding:
    """A single deterministic finding, bounded and formatted for AI consumption."""
    concept_id: str
    concept_name: str
    status: str
    priority: str
    confidence: float
    evidence_citations: tuple[str, ...] = field(default_factory=tuple)
    gaps: tuple[str, ...] = field(default_factory=tuple)
    misconfiguration: str | None = None
    recommendation: str | None = None

    @classmethod
    def from_decision(cls, decision: Decision) -> "GroundedFinding":
        citations: list[str] = []
        for ev in decision.evidence:
            note = f" ({ev.note})" if ev.note else ""
            citations.append(f"{ev.file}:{ev.line} -> `{ev.snippet}`{note}")
        return cls(
            concept_id=decision.concept_id,
            concept_name=decision.concept_name,
            status=decision.status.value,
            priority=decision.priority.value,
            confidence=round(decision.confidence, 2),
            evidence_citations=tuple(citations),
            gaps=tuple(decision.gaps),
            misconfiguration=decision.misconfiguration,
            recommendation=decision.recommendation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "status": self.status,
            "priority": self.priority,
            "confidence": self.confidence,
            "evidence": list(self.evidence_citations),
            "gaps": list(self.gaps),
            "misconfiguration": self.misconfiguration,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class GroundedContext:
    """Strictly bounded context bundle passed to AI providers."""
    target_root: str
    total_decisions: int
    implemented_count: int
    missing_count: int
    misconfigured_count: int
    findings: tuple[GroundedFinding, ...] = field(default_factory=tuple)
    project_profile: dict[str, Any] = field(default_factory=dict)
    character_budget: int = 16000

    @classmethod
    def build(
        cls,
        decisions: Sequence[Decision],
        target_root: str | Path,
        project_profile: dict[str, Any] | None = None,
        character_budget: int = 16000,
        focus_status: tuple[DecisionStatus, ...] | None = None,
    ) -> "GroundedContext":
        """Build grounded context from decisions, respecting budget and filters."""
        root_str = str(target_root)
        filtered_decisions = [
            d for d in decisions
            if focus_status is None or d.status in focus_status
        ]

        # Sort: MISCONFIGURED > MISSING > IMPLEMENTED, then priority (CRITICAL first)
        priority_rank = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
            Priority.INFO: 4,
            Priority.N_A: 5,
        }
        status_rank = {
            DecisionStatus.MISCONFIGURED: 0,
            DecisionStatus.MISSING: 1,
            DecisionStatus.IMPLEMENTED: 2,
            DecisionStatus.UNKNOWN: 3,
        }
        sorted_decisions = sorted(
            filtered_decisions,
            key=lambda d: (status_rank.get(d.status, 9), priority_rank.get(d.priority, 9), d.concept_id),
        )

        findings: list[GroundedFinding] = []
        current_len = 0

        for d in sorted_decisions:
            gf = GroundedFinding.from_decision(d)
            finding_repr = json.dumps(gf.to_dict())
            if current_len + len(finding_repr) > character_budget:
                # Bounded by budget
                break
            findings.append(gf)
            current_len += len(finding_repr)

        imp_count = sum(1 for d in decisions if d.status == DecisionStatus.IMPLEMENTED)
        mis_count = sum(1 for d in decisions if d.status == DecisionStatus.MISSING)
        msc_count = sum(1 for d in decisions if d.status == DecisionStatus.MISCONFIGURED)

        return cls(
            target_root=root_str,
            total_decisions=len(decisions),
            implemented_count=imp_count,
            missing_count=mis_count,
            misconfigured_count=msc_count,
            findings=tuple(findings),
            project_profile=project_profile or {},
            character_budget=character_budget,
        )

    def to_json(self) -> str:
        """Serialize grounded context to JSON for prompt injection."""
        data = {
            "target_root": self.target_root,
            "summary": {
                "total_evaluated": self.total_decisions,
                "implemented": self.implemented_count,
                "missing": self.missing_count,
                "misconfigured": self.misconfigured_count,
            },
            "project_profile": self.project_profile,
            "grounded_findings": [f.to_dict() for f in self.findings],
        }
        return json.dumps(data, indent=2)

    def format_for_prompt(self) -> str:
        """Format as clear markdown context block for LLM prompt."""
        lines = [
            f"Target System: {self.target_root}",
            f"Audit Summary: {self.total_decisions} concepts evaluated ({self.implemented_count} implemented, {self.missing_count} missing, {self.misconfigured_count} misconfigured)",
            "",
            "### Deterministic Verified Findings (Ground Truth — Do Not Alter):",
        ]

        for idx, f in enumerate(self.findings, 1):
            lines.append(
                f"{idx}. [{f.status.upper()}] **{f.concept_name}** (`{f.concept_id}`) — Priority: {f.priority}, Confidence: {f.confidence}"
            )
            if f.evidence_citations:
                lines.append(f"   - Evidence: {'; '.join(f.evidence_citations[:2])}")
            if f.misconfiguration:
                lines.append(f"   - Misconfiguration: {f.misconfiguration}")
            if f.gaps:
                lines.append(f"   - Gaps: {', '.join(f.gaps)}")
            if f.recommendation:
                lines.append(f"   - Recommended Rule: {f.recommendation}")
            lines.append("")

        return "\n".join(lines)
