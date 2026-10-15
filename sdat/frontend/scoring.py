"""Frontend Scoring Engine — Multi-dimensional, transparent, explainable scoring."""

from __future__ import annotations

from typing import Dict, List

from sdat.frontend.knowledge_pack import RuleEvaluationResult
from sdat.frontend.models import FrontendDimensionScore
from sdat.models import DecisionStatus, Priority

DIMENSION_NAMES: Dict[str, str] = {
    "rendering": "Rendering Architecture",
    "navigation_routing": "Page & Route Architecture",
    "loading_strategy": "Loading Strategy & Code Splitting",
    "runtime_performance": "Runtime Performance",
    "dom_component_architecture": "DOM & Component Architecture",
    "responsive_design": "Responsive Design Architecture",
    "assets": "Asset Architecture & Optimization",
    "state_management": "State Management Architecture",
    "data_fetching": "Data Fetching Architecture",
    "caching_storage": "Frontend Caching & Storage",
    "error_handling_ux": "Error & Loading UX",
    "accessibility": "Accessibility Architecture",
    "security": "Frontend Security Architecture",
    "network_api": "Network & API Architecture",
    "perceived_latency": "Perceived Latency & Optimistic UX",
    "web3_frontend": "Web3 Frontend Architecture",
}

DIMENSION_WEIGHTS: Dict[str, float] = {
    "rendering": 1.2,
    "navigation_routing": 1.0,
    "loading_strategy": 1.1,
    "runtime_performance": 1.0,
    "dom_component_architecture": 1.0,
    "responsive_design": 1.1,
    "assets": 1.0,
    "state_management": 1.0,
    "data_fetching": 1.2,
    "caching_storage": 1.0,
    "error_handling_ux": 1.2,
    "accessibility": 1.0,
    "security": 1.5,
    "network_api": 1.0,
    "perceived_latency": 0.8,
    "web3_frontend": 1.2,
}


class FrontendScoringEngine:
    """Computes explainable dimensional and overall frontend architecture scores."""

    def compute_scores(
        self,
        results: List[RuleEvaluationResult],
    ) -> tuple[dict[str, FrontendDimensionScore], float | None, str]:
        """Group results by dimension and compute transparent scores.

        Returns:
            (dimension_scores_dict, overall_score, overall_status)
        """
        by_dimension: dict[str, list[RuleEvaluationResult]] = {}
        for r in results:
            by_dimension.setdefault(r.rule.dimension, []).append(r)

        dimension_scores: dict[str, FrontendDimensionScore] = {}
        weighted_sum = 0.0
        weight_total = 0.0

        for dim, dim_results in by_dimension.items():
            dim_name = DIMENSION_NAMES.get(dim, dim.replace("_", " ").title())
            score_obj = self._score_dimension(dim, dim_name, dim_results)
            dimension_scores[dim] = score_obj

            if score_obj.score is not None:
                w = DIMENSION_WEIGHTS.get(dim, 1.0)
                weighted_sum += score_obj.score * w
                weight_total += w

        if weight_total > 0:
            overall_score = round(weighted_sum / weight_total, 1)
            overall_status = "evaluated"
        else:
            overall_score = None
            overall_status = "insufficient_evidence"

        return dimension_scores, overall_score, overall_status

    def _score_dimension(
        self,
        dim: str,
        dim_name: str,
        results: list[RuleEvaluationResult],
    ) -> FrontendDimensionScore:
        evaluable_results = [r for r in results if r.status != DecisionStatus.UNKNOWN]

        findings: list[str] = []
        recommendations: list[str] = []

        for r in results:
            if r.misconfiguration:
                findings.append(f"[{r.rule.id}] {r.misconfiguration}")
            elif r.status == DecisionStatus.IMPLEMENTED:
                findings.append(f"[{r.rule.id}] {r.rule.name}: Implemented cleanly")
            elif r.status == DecisionStatus.MISSING:
                findings.append(f"[{r.rule.id}] {r.rule.name}: Missing")

            if r.recommendation:
                recommendations.append(f"[{r.rule.id}] {r.recommendation}")

        if not evaluable_results:
            return FrontendDimensionScore(
                dimension=dim,
                name=dim_name,
                score=None,
                status="insufficient_evidence",
                confidence=0.0,
                rules_evaluated=len(results),
                rules_passed=0,
                findings=tuple(findings or ["Insufficient evidence to evaluate dimension"]),
                recommendations=tuple(recommendations),
            )

        passed = sum(1 for r in evaluable_results if r.status == DecisionStatus.IMPLEMENTED)
        critical_violations = sum(
            1 for r in evaluable_results
            if r.status == DecisionStatus.MISCONFIGURED and r.rule.priority == Priority.CRITICAL
        )

        base_ratio = passed / len(evaluable_results)
        raw_score = base_ratio * 100.0

        # Critical security penalty
        if critical_violations > 0:
            raw_score = max(0.0, raw_score - (critical_violations * 40.0))

        confidence = sum(r.confidence for r in evaluable_results) / len(evaluable_results)

        return FrontendDimensionScore(
            dimension=dim,
            name=dim_name,
            score=round(raw_score, 1),
            status="evaluated",
            confidence=round(confidence, 2),
            rules_evaluated=len(evaluable_results),
            rules_passed=passed,
            findings=tuple(findings),
            recommendations=tuple(recommendations),
        )
