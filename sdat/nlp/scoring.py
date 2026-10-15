"""Natural Language Processing Domain Scoring Engine.

Computes explainable, multi-dimensional scores for the NLP domain
tracing from Rule results to Dimension scores and overall Domain Score.
"""

from __future__ import annotations

from sdat.models import DecisionStatus, Priority
from sdat.nlp.models import NLPDimensionScore, NLPRuleEvaluationResult

DIMENSION_WEIGHTS = {
    "transformer_tensor_soundness": 1.5,
    "tokenization_and_sequence_contract": 1.4,
}


class NLPScoringEngine:
    """Calculates dimensional and domain scores for natural language processing architecture."""

    def compute_scores(
        self, results: list[NLPRuleEvaluationResult]
    ) -> tuple[tuple[NLPDimensionScore, ...], float | None, str]:
        """Compute dimension scores and overall domain score from evaluation results."""
        by_dimension: dict[str, list[NLPRuleEvaluationResult]] = {}
        for r in results:
            by_dimension.setdefault(r.rule.dimension, []).append(r)

        dimension_scores: list[NLPDimensionScore] = []

        total_weighted_score = 0.0
        total_weight = 0.0
        known_dimensions_count = 0

        for dim, dim_results in sorted(by_dimension.items()):
            evaluated_count = len(dim_results)
            passed = sum(1 for r in dim_results if r.status in (DecisionStatus.IMPLEMENTED, "PASS"))
            failed = sum(1 for r in dim_results if r.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED, "MISCONFIGURED"))
            critical = sum(
                1
                for r in dim_results
                if r.status in (DecisionStatus.MISCONFIGURED, "MISCONFIGURED")
                and r.rule.priority in (Priority.CRITICAL, Priority.HIGH)
            )

            # Active rules (excluding UNKNOWN and NOT_APPLICABLE for pure baseline calculation)
            active_results = [r for r in dim_results if r.status not in (DecisionStatus.UNKNOWN, "UNKNOWN", "NOT_APPLICABLE")]

            if not active_results:
                dim_score = 100.0  # Neutral baseline if unobserved
                dim_status = "healthy"
            else:
                base_ratio = passed / len(active_results)
                penalty = critical * 25.0
                dim_score = max(0.0, min(100.0, (base_ratio * 100.0) - penalty))
                if dim_score >= 80.0:
                    dim_status = "healthy"
                elif dim_score >= 50.0:
                    dim_status = "warning"
                else:
                    dim_status = "critical"
                known_dimensions_count += 1

            dimension_scores.append(
                NLPDimensionScore(
                    dimension=dim,
                    score=round(dim_score, 1),
                    rules_evaluated=evaluated_count,
                    rules_passed=passed,
                    rules_failed=failed,
                    critical_issues=critical,
                    status=dim_status,
                )
            )

            weight = DIMENSION_WEIGHTS.get(dim, 1.0)
            if active_results:
                total_weighted_score += dim_score * weight
                total_weight += weight

        if known_dimensions_count == 0 or total_weight == 0.0:
            return tuple(dimension_scores), None, "unknown"

        overall_score = round(total_weighted_score / total_weight, 1)
        if overall_score >= 80.0:
            overall_status = "healthy"
        elif overall_score >= 50.0:
            overall_status = "warning"
        else:
            overall_status = "critical"

        return tuple(dimension_scores), overall_score, overall_status
