"""Tests for Backend Scoring Engine."""

from __future__ import annotations

from sdat.backend.models import BackendRule, BackendRuleEvaluationResult
from sdat.backend.scoring import BackendScoringEngine
from sdat.models import DecisionStatus, Priority


def _make_result(dimension: str, status: DecisionStatus, priority: Priority = Priority.HIGH) -> BackendRuleEvaluationResult:
    rule = BackendRule(
        id=f"TEST-{dimension[:4].upper()}-01",
        dimension=dimension,
        name=f"Rule for {dimension}",
        description="Testing dimension scoring",
        priority=priority,
        concept_id=f"backend.{dimension}",
    )
    return BackendRuleEvaluationResult(
        rule=rule,
        status=status,
        confidence=0.9,
    )


def test_scoring_all_implemented_healthy() -> None:
    engine = BackendScoringEngine()
    results = [
        _make_result("api_architecture", DecisionStatus.IMPLEMENTED),
        _make_result("security", DecisionStatus.IMPLEMENTED),
        _make_result("reliability_resilience", DecisionStatus.IMPLEMENTED),
        _make_result("data_interaction", DecisionStatus.IMPLEMENTED),
    ]
    dim_scores, overall_score, overall_status = engine.compute_scores(results)
    assert len(dim_scores) == 4
    assert all(ds.score == 100.0 for ds in dim_scores)
    assert overall_score == 100.0
    assert overall_status == "healthy"


def test_scoring_critical_misconfiguration_penalty() -> None:
    engine = BackendScoringEngine()
    results = [
        _make_result("security", DecisionStatus.IMPLEMENTED),
        _make_result("security", DecisionStatus.MISCONFIGURED, priority=Priority.CRITICAL),
    ]
    dim_scores, overall_score, overall_status = engine.compute_scores(results)
    sec_score = next(ds for ds in dim_scores if ds.dimension == "security")
    # Base ratio 50% - 25% critical penalty = 25.0%
    assert sec_score.score == 25.0
    assert sec_score.critical_issues == 1
    assert sec_score.status == "critical"
    assert overall_status == "critical"


def test_scoring_unobserved_returns_unknown() -> None:
    engine = BackendScoringEngine()
    results = [
        _make_result("api_architecture", DecisionStatus.UNKNOWN),
        _make_result("security", DecisionStatus.UNKNOWN),
    ]
    dim_scores, overall_score, overall_status = engine.compute_scores(results)
    assert overall_score is None
    assert overall_status == "unknown"
