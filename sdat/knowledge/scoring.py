"""Canonical Multi-Tier Scoring Architecture for SDAT.

Implements the four-tier architectural scoring hierarchy:
1. Concept / Rule Evaluation Results
       ↓
2. Dimension Scores (domain-specific architectural dimensions)
       ↓
3. Domain Scores (composite score for a workload domain)
       ↓
4. Application-Level Summary (cross-domain weighted audit summary)

Separates scoring criteria across domains:
- Frontend: Rendering, Loading, Navigation, Runtime Performance, Accessibility
- Backend: API Design, Resilience, Concurrency, Security
- Database: Schema Design, Indexing, Migrations, Data Lifecycle
- ML/NLP (Spec Only): Pipeline, Representation, Evaluation, Lineage
"""

from __future__ import annotations

from sdat.knowledge.models import (
    AuditScoringSummary,
    DimensionScore,
    DomainScore,
)
from sdat.models import DecisionStatus


class UniversalScoringEngine:
    """Computes explainable, multi-tiered scores from evaluated rules across domains."""

    @staticmethod
    def compute_dimension_score(
        dimension: str,
        statuses: list[DecisionStatus],
        confidences: list[float] | None = None,
        notes: list[str] | None = None,
    ) -> DimensionScore:
        """Compute score for an architectural dimension from rule statuses.

        Scoring formula:
        - IMPLEMENTED: 100 points
        - MISCONFIGURED: 40 points
        - UNKNOWN: 20 points
        - MISSING: 0 points
        Weighted by confidence when provided.
        """
        if not statuses:
            return DimensionScore(
                dimension=dimension,
                score=100.0,
                status=DecisionStatus.UNKNOWN,
                rules_evaluated=0,
                rules_passed=0,
                notes=("No evaluated rules in dimension",),
            )

        status_weights = {
            DecisionStatus.IMPLEMENTED: 100.0,
            DecisionStatus.MISCONFIGURED: 40.0,
            DecisionStatus.UNKNOWN: 20.0,
            DecisionStatus.MISSING: 0.0,
        }

        confs = confidences if (confidences and len(confidences) == len(statuses)) else [1.0] * len(statuses)

        total_weight = sum(confs)
        if total_weight <= 0.0:
            total_weight = 1.0

        weighted_sum = sum(
            status_weights.get(s, 0.0) * conf
            for s, conf in zip(statuses, confs, strict=False)
        )
        score = round(weighted_sum / total_weight, 2)

        rules_passed = sum(1 for s in statuses if s == DecisionStatus.IMPLEMENTED)
        overall_status = DecisionStatus.IMPLEMENTED if score >= 80.0 else (
            DecisionStatus.MISCONFIGURED if score >= 40.0 else DecisionStatus.MISSING
        )

        return DimensionScore(
            dimension=dimension,
            score=score,
            status=overall_status,
            rules_evaluated=len(statuses),
            rules_passed=rules_passed,
            notes=tuple(notes or ()),
        )

    @staticmethod
    def compute_domain_score(
        domain: str,
        dimension_scores: dict[str, DimensionScore],
        dimension_weights: dict[str, float] | None = None,
    ) -> DomainScore:
        """Compute domain score from constituent dimension scores."""
        if not dimension_scores:
            return DomainScore(domain=domain, overall_score=100.0, dimension_scores={}, summary="No active dimensions")

        weights = dimension_weights or {d: 1.0 for d in dimension_scores}
        total_weight = sum(weights.get(d, 1.0) for d in dimension_scores)
        if total_weight <= 0.0:
            total_weight = 1.0

        weighted_score = sum(
            ds.score * weights.get(dim, 1.0)
            for dim, ds in dimension_scores.items()
        )
        overall = round(weighted_score / total_weight, 2)

        summary = f"Domain '{domain}' achieved score {overall:.1f}/100 across {len(dimension_scores)} dimensions."
        return DomainScore(
            domain=domain,
            overall_score=overall,
            dimension_scores=dimension_scores,
            summary=summary,
        )

    @staticmethod
    def compute_application_summary(
        domain_scores: dict[str, DomainScore],
        domain_weights: dict[str, float] | None = None,
        critical_count: int = 0,
        high_count: int = 0,
    ) -> AuditScoringSummary:
        """Compute composite application summary score across all active domains."""
        if not domain_scores:
            return AuditScoringSummary(
                application_score=100.0,
                domain_scores={},
                active_domains=(),
                critical_findings_count=critical_count,
                high_findings_count=high_count,
            )

        weights = domain_weights or {d: 1.0 for d in domain_scores}
        total_weight = sum(weights.get(d, 1.0) for d in domain_scores)
        if total_weight <= 0.0:
            total_weight = 1.0

        weighted_app_score = sum(
            ds.overall_score * weights.get(dom, 1.0)
            for dom, ds in domain_scores.items()
        )
        app_score = round(weighted_app_score / total_weight, 2)

        # Severity penalties for critical/high defects
        penalty = (critical_count * 5.0) + (high_count * 2.0)
        final_app_score = max(0.0, round(app_score - penalty, 2))

        return AuditScoringSummary(
            application_score=final_app_score,
            domain_scores=domain_scores,
            active_domains=tuple(sorted(domain_scores.keys())),
            critical_findings_count=critical_count,
            high_findings_count=high_count,
        )
