"""Tests for Backend domain models."""

from __future__ import annotations

from pathlib import Path

from sdat.backend.models import (
    BackendAuditResult,
    BackendDimensionScore,
    BackendRule,
    BackendRuleEvaluationResult,
    EndpointDefinition,
    MiddlewareDefinition,
    ServiceBoundaryDefinition,
)
from sdat.models import Decision, DecisionStatus, Evidence, Priority


def test_endpoint_and_middleware_definition() -> None:
    endpoint = EndpointDefinition(
        path="/api/v1/users",
        method="GET",
        handler_symbol="get_users",
        file_path=Path("app/api/users.py"),
        line=15,
        framework="FastAPI",
        has_auth=True,
        has_validation=True,
        has_timeout=True,
    )
    assert endpoint.path == "/api/v1/users"
    assert endpoint.method == "GET"
    assert endpoint.has_auth is True

    middleware = MiddlewareDefinition(
        name="AuthMiddleware",
        file_path=Path("app/middleware/auth.py"),
        line=10,
        purpose="auth",
        scope="global",
    )
    assert middleware.name == "AuthMiddleware"
    assert middleware.purpose == "auth"


def test_service_boundary_definition() -> None:
    boundary = ServiceBoundaryDefinition(
        name="UserService",
        file_path=Path("app/services/user_service.py"),
        layer="service",
        dependencies=("UserRepository", "AuthClient"),
        has_direct_db_access=False,
        has_external_calls=True,
    )
    assert boundary.layer == "service"
    assert "UserRepository" in boundary.dependencies
    assert boundary.has_direct_db_access is False


def test_backend_rule_and_evaluation_result() -> None:
    rule = BackendRule(
        id="BE-API-01",
        dimension="api_architecture",
        name="API Route Structuring",
        description="Endpoints use structured routes",
        priority=Priority.HIGH,
        concept_id="backend.api-architecture",
        remediation_guidance="Separate routes into controllers",
    )
    assert rule.rule_id == "BE-API-01"
    assert rule.severity == Priority.HIGH

    ev = Evidence(file="app/routes.py", line=12, snippet="@app.get('/users')", note="Endpoint route")
    res = BackendRuleEvaluationResult(
        rule=rule,
        status=DecisionStatus.IMPLEMENTED,
        confidence=0.95,
        evidence=[ev],
    )
    assert res.status == DecisionStatus.IMPLEMENTED
    assert res.confidence == 0.95
    assert len(res.evidence) == 1


def test_backend_audit_result_serialization() -> None:
    dim_score = BackendDimensionScore(
        dimension="api_architecture",
        score=92.5,
        rules_evaluated=3,
        rules_passed=3,
        rules_failed=0,
        critical_issues=0,
        status="healthy",
    )
    decision = Decision(
        concept_id="backend.api-architecture",
        concept_name="API Route Structuring",
        status=DecisionStatus.IMPLEMENTED,
        confidence=0.95,
        evidence=[Evidence(file="routes.py", line=5, snippet="@app.get('/')")],
        priority=Priority.HIGH,
    )
    audit_res = BackendAuditResult(
        target_root=Path("/workspace"),
        detected_frameworks=("FastAPI",),
        detected_databases=("PostgreSQL",),
        detected_queues=(),
        is_backend=True,
        endpoints_count=5,
        middlewares_count=2,
        boundaries_count=4,
        dimension_scores=(dim_score,),
        overall_score=92.5,
        overall_status="healthy",
        summary="Backend audit healthy",
        decisions=(decision,),
    )
    data = audit_res.to_dict()
    assert data["target_root"] == str(Path("/workspace"))
    assert data["is_backend"] is True
    assert data["endpoints_count"] == 5
    assert len(data["dimension_scores"]) == 1
    assert data["dimension_scores"][0]["score"] == 92.5
    assert data["overall_status"] == "healthy"
