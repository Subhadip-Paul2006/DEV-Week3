"""Tests for Backend KnowledgePack rules and deterministic evaluation."""

from __future__ import annotations

from pathlib import Path

from sdat.backend.knowledge_pack import BackendKnowledgePack
from sdat.backend.models import BackendAnalysisSummary, EndpointDefinition, MiddlewareDefinition
from sdat.models import DecisionStatus, EvidenceFact, EvidenceKind, Priority


def test_knowledge_pack_metadata() -> None:
    kp = BackendKnowledgePack()
    assert kp.id == "kp.backend"
    assert kp.domain == "backend"
    assert kp.version == "1.0.0"
    assert "core" in kp.dependencies
    assert len(kp.RULES) == 25
    assert len(kp.scoring_dimensions) == 7


def test_rules_concept_ids_and_priorities() -> None:
    kp = BackendKnowledgePack()
    concept_ids = {r.concept_id for r in kp.RULES}
    assert len(concept_ids) == 25
    assert all(cid.startswith("backend.") for cid in concept_ids)
    assert all(r.priority in Priority for r in kp.RULES)


def test_evaluate_non_backend_project() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(target_root=Path("/empty"))
    results = kp.evaluate([], summary)
    assert len(results) == 25
    assert all(r.status == DecisionStatus.UNKNOWN for r in results)


def test_evaluate_api_endpoints_detected() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(
        target_root=Path("/workspace"),
        endpoints=[
            EndpointDefinition(
                path="/api/items",
                method="GET",
                handler_symbol="list_items",
                file_path=Path("routes.py"),
                line=10,
            )
        ],
    )
    results = kp.evaluate([], summary)
    api_res = next(r for r in results if r.rule.id == "BE-API-01")
    assert api_res.status == DecisionStatus.IMPLEMENTED
    assert api_res.confidence >= 0.90
    assert len(api_res.evidence) == 1
    assert "GET /api/items" in api_res.evidence[0].snippet


def test_evaluate_missing_authentication() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(
        target_root=Path("/workspace"),
        endpoints=[
            EndpointDefinition(
                path="/api/checkout",
                method="POST",
                handler_symbol="checkout",
                file_path=Path("routes.py"),
                line=20,
            )
        ],
    )
    results = kp.evaluate([], summary)
    auth_res = next(r for r in results if r.rule.id == "BE-AUTH-01")
    assert auth_res.status == DecisionStatus.MISSING
    assert auth_res.confidence >= 0.80
    assert len(auth_res.gaps) > 0
    assert auth_res.recommendation is not None


def test_evaluate_authenticated_middleware() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(
        target_root=Path("/workspace"),
        endpoints=[
            EndpointDefinition(
                path="/api/profile",
                method="GET",
                handler_symbol="get_profile",
                file_path=Path("routes.py"),
                line=5,
            )
        ],
        middlewares=[
            MiddlewareDefinition(
                name="JWTAuthMiddleware",
                file_path=Path("middleware.py"),
                line=12,
                purpose="auth",
            )
        ],
    )
    results = kp.evaluate([], summary)
    auth_res = next(r for r in results if r.rule.id == "BE-AUTH-01")
    assert auth_res.status == DecisionStatus.IMPLEMENTED
    assert auth_res.confidence >= 0.90


def test_evaluate_cache_with_ttl_vs_misconfigured() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(
        target_root=Path("/workspace"),
        detected_frameworks={"FastAPI"},
    )
    # 1. Fact with TTL
    ttl_fact = EvidenceFact(
        kind=EvidenceKind.CALL,
        subject="redis.setex",
        language="python",
        file_path=Path("cache.py"),
        line_range=(10, 10),
        snippet="redis.setex('k', 300, 'v')",
        ttl_observed=True,
    )
    results = kp.evaluate([ttl_fact], summary)
    cache_res = next(r for r in results if r.rule.id == "BE-CACHE-01")
    assert cache_res.status == DecisionStatus.IMPLEMENTED

    # 2. Fact without TTL
    no_ttl_fact = EvidenceFact(
        kind=EvidenceKind.CALL,
        subject="redis.set",
        language="python",
        file_path=Path("cache.py"),
        line_range=(10, 10),
        snippet="redis.set('k', 'v')",
        ttl_observed=False,
    )
    results_no_ttl = kp.evaluate([no_ttl_fact], summary)
    cache_res_no_ttl = next(r for r in results_no_ttl if r.rule.id == "BE-CACHE-01")
    assert cache_res_no_ttl.status == DecisionStatus.MISCONFIGURED
    assert cache_res_no_ttl.misconfiguration is not None


def test_evaluate_unbounded_external_call_misconfiguration() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(
        target_root=Path("/workspace"),
        detected_frameworks={"Express"},
    )
    ext_call_no_timeout = EvidenceFact(
        kind=EvidenceKind.CALL,
        subject="axios.post",
        language="typescript",
        file_path=Path("client.ts"),
        line_range=(15, 15),
        snippet="axios.post(url, data)",
        timeout_observed=False,
    )
    results = kp.evaluate([ext_call_no_timeout], summary)
    time_res = next(r for r in results if r.rule.id == "BE-TIME-01")
    assert time_res.status == DecisionStatus.MISCONFIGURED
    assert "timeout" in time_res.misconfiguration.lower()


def test_to_decisions_conversion() -> None:
    kp = BackendKnowledgePack()
    summary = BackendAnalysisSummary(
        target_root=Path("/workspace"),
        endpoints=[
            EndpointDefinition(
                path="/health",
                method="GET",
                handler_symbol="health",
                file_path=Path("main.py"),
                line=1,
            )
        ],
    )
    results = kp.evaluate([], summary)
    decisions = kp.to_decisions(results)
    assert len(decisions) == 25
    assert all(d.concept_id.startswith("backend.") for d in decisions)
    assert any(d.concept_id == "backend.api-architecture" and d.status == DecisionStatus.IMPLEMENTED for d in decisions)
