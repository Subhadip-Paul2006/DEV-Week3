"""Tests for FrontendScoringEngine explainable scoring."""

from __future__ import annotations

from sdat.frontend.knowledge_pack import FrontendRule, RuleEvaluationResult
from sdat.frontend.scoring import FrontendScoringEngine
from sdat.models import DecisionStatus, Priority


def test_scoring_clean_evaluation():
    engine = FrontendScoringEngine()
    rule1 = FrontendRule(
        id="FE-REND-01",
        dimension="rendering",
        name="Appropriate Rendering Strategy",
        description="desc",
        priority=Priority.HIGH,
        concept_id="frontend.rendering",
    )
    res1 = RuleEvaluationResult(rule=rule1, status=DecisionStatus.IMPLEMENTED, confidence=0.95)

    rule2 = FrontendRule(
        id="FE-REND-02",
        dimension="rendering",
        name="Boundary Isolation",
        description="desc",
        priority=Priority.HIGH,
        concept_id="frontend.rendering",
    )
    res2 = RuleEvaluationResult(rule=rule2, status=DecisionStatus.IMPLEMENTED, confidence=0.90)

    dim_scores, overall, status = engine.compute_scores([res1, res2])

    assert "rendering" in dim_scores
    rend = dim_scores["rendering"]
    assert rend.score == 100.0
    assert rend.status == "evaluated"
    assert rend.rules_passed == 2
    assert overall == 100.0
    assert status == "evaluated"


def test_scoring_critical_security_penalty():
    engine = FrontendScoringEngine()
    rule_sec = FrontendRule(
        id="FE-SEC-01",
        dimension="security",
        name="XSS Prevention",
        description="desc",
        priority=Priority.CRITICAL,
        concept_id="frontend.security",
    )
    res_sec = RuleEvaluationResult(
        rule=rule_sec,
        status=DecisionStatus.MISCONFIGURED,
        confidence=0.95,
        misconfiguration="Dangerous raw HTML injection",
    )

    dim_scores, overall, status = engine.compute_scores([res_sec])

    assert "security" in dim_scores
    sec = dim_scores["security"]
    assert sec.score == 0.0
    assert "Dangerous raw HTML injection" in sec.findings[0]


def test_scoring_insufficient_evidence():
    engine = FrontendScoringEngine()
    rule_perf = FrontendRule(
        id="FE-PERF-02",
        dimension="runtime_performance",
        name="Runtime Telemetry",
        description="desc",
        priority=Priority.MEDIUM,
        concept_id="frontend.runtime-performance",
    )
    res_perf = RuleEvaluationResult(
        rule=rule_perf,
        status=DecisionStatus.UNKNOWN,
        confidence=0.5,
        gaps=["Unmeasured"],
    )

    dim_scores, overall, status = engine.compute_scores([res_perf])

    assert "runtime_performance" in dim_scores
    perf = dim_scores["runtime_performance"]
    assert perf.score is None
    assert perf.status == "insufficient_evidence"
    assert overall is None
    assert status == "insufficient_evidence"
