"""Natural Language Processing System-Design Domain Models.

Defines structural models for NLP architecture analysis, including rules,
evaluation results, dimension scores, and consolidated audit results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from sdat.models import Decision, DecisionStatus, Evidence, Priority


class RuleStatus(str, Enum):
    """The four deterministic verdict states for an SDAT rule evaluation."""
    PASS = "PASS"
    MISCONFIGURED = "MISCONFIGURED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, DecisionStatus):
            if self.value == "PASS" and other == DecisionStatus.IMPLEMENTED:
                return True
            if self.value == "MISCONFIGURED" and other == DecisionStatus.MISCONFIGURED:
                return True
            if self.value == "UNKNOWN" and other == DecisionStatus.UNKNOWN:
                return True
            return False
        if isinstance(other, str):
            return self.value.upper() == other.upper()
        return super().__eq__(other)

    def to_decision_status(self) -> DecisionStatus:
        if self == RuleStatus.PASS:
            return DecisionStatus.IMPLEMENTED
        elif self == RuleStatus.MISCONFIGURED:
            return DecisionStatus.MISCONFIGURED
        return DecisionStatus.UNKNOWN


@dataclass(frozen=True)
class NLPRule:
    """A deterministic system-design evaluation rule in the NLP KnowledgePack."""
    id: str
    dimension: str
    name: str
    description: str
    priority: Priority
    concept_id: str
    remediation_guidance: str = ""

    @property
    def rule_id(self) -> str:
        return self.id

    @property
    def severity(self) -> Priority:
        return self.priority


@dataclass
class NLPRuleEvaluationResult:
    """The result of evaluating an NLPRule against grounded structural evidence."""
    rule: NLPRule
    status: RuleStatus | DecisionStatus
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)
    misconfiguration: str | None = None
    gaps: list[str] = field(default_factory=list)
    recommendation: str | None = None
    applicability_context: str | None = None

    @property
    def rule_status(self) -> RuleStatus:
        if isinstance(self.status, RuleStatus):
            return self.status
        if self.status == DecisionStatus.IMPLEMENTED:
            return RuleStatus.PASS
        if self.status == DecisionStatus.MISCONFIGURED:
            return RuleStatus.MISCONFIGURED
        return RuleStatus.UNKNOWN


@dataclass(frozen=True)
class NLPDimensionScore:
    """Score for a specific NLP architectural dimension."""
    dimension: str
    score: float  # 0.0 to 100.0
    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    critical_issues: int
    status: str  # "healthy", "warning", "critical"


@dataclass(frozen=True)
class NLPAuditResult:
    """Consolidated findings, dimension scores, and decisions for the NLP domain."""
    target_root: Path
    detected_frameworks: tuple[str, ...]
    is_nlp: bool
    dimension_scores: tuple[NLPDimensionScore, ...]
    overall_score: float | None
    overall_status: str
    summary: str
    decisions: tuple[Decision, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_root": str(self.target_root),
            "detected_frameworks": list(self.detected_frameworks),
            "is_nlp": self.is_nlp,
            "dimension_scores": [
                {
                    "dimension": ds.dimension,
                    "score": ds.score,
                    "rules_evaluated": ds.rules_evaluated,
                    "rules_passed": ds.rules_passed,
                    "rules_failed": ds.rules_failed,
                    "critical_issues": ds.critical_issues,
                    "status": ds.status,
                }
                for ds in self.dimension_scores
            ],
            "overall_score": self.overall_score,
            "overall_status": self.overall_status,
            "summary": self.summary,
            "decisions": [d.to_dict() for d in self.decisions],
        }
