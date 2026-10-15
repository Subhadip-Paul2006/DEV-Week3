"""Tests for Frontend Audit Data Models."""

from __future__ import annotations

from pathlib import Path

from sdat.frontend.models import (
    DataFetchingPattern,
    FrontendAuditResult,
    FrontendDimensionScore,
    LoadingStrategy,
    PageAnalysis,
    PageType,
    RenderingModel,
    RuntimeMetrics,
)


def test_runtime_metrics_default_is_unmeasured():
    rm = RuntimeMetrics()
    assert rm.measured is False
    assert rm.fcp_ms is None
    assert "unavailable" in rm.notes.lower() or "unmeasured" in rm.notes.lower()
    d = rm.to_dict()
    assert d["measured"] is False


def test_runtime_metrics_with_telemetry():
    rm = RuntimeMetrics(
        measured=True,
        fcp_ms=1200.5,
        lcp_ms=2100.0,
        cls=0.04,
        ttfb_ms=350.0,
        inp_ms=85.0,
        dom_nodes=820,
        request_count=24,
        transferred_bytes=450000,
        notes="Measured via browser subagent",
    )
    assert rm.measured is True
    assert rm.fcp_ms == 1200.5
    d = rm.to_dict()
    assert d["dom_nodes"] == 820


def test_page_analysis_serialization():
    pa = PageAnalysis(
        file_path=Path("app/dashboard/page.tsx"),
        route="/dashboard",
        page_type=PageType.DYNAMIC,
        rendering_model=RenderingModel.SSR,
        loading_strategy=LoadingStrategy.DYNAMIC_IMPORT,
        data_fetching_pattern=DataFetchingPattern.CLIENT_QUERY,
        approximate_complexity={"elements": 45, "interactive_elements": 8},
        has_responsive_evidence=True,
        asset_behavior=("next/image optimized component",),
        findings=("Page leverages SSR with client query hydration",),
        dimension_results={"rendering": "ssr"},
    )
    d = pa.to_dict()
    assert d["route"] == "/dashboard"
    assert d["rendering_model"] == "ssr"
    assert d["has_responsive_evidence"] is True
    assert len(d["asset_behavior"]) == 1


def test_frontend_dimension_score_serialization():
    score = FrontendDimensionScore(
        dimension="rendering",
        name="Rendering Architecture",
        score=92.5,
        status="evaluated",
        confidence=0.9,
        rules_evaluated=2,
        rules_passed=2,
        findings=("Clean SSR boundary",),
        recommendations=(),
    )
    d = score.to_dict()
    assert d["dimension"] == "rendering"
    assert d["score"] == 92.5
    assert d["status"] == "evaluated"


def test_frontend_audit_result_serialization():
    result = FrontendAuditResult(
        target_root=Path("/repo"),
        detected_frameworks=("react", "nextjs"),
        is_frontend=True,
        pages=(),
        dimension_scores={},
        overall_score=88.0,
        overall_status="evaluated",
        summary="Audit completed cleanly",
        decisions=(),
    )
    d = result.to_dict()
    assert d["is_frontend"] is True
    assert d["overall_score"] == 88.0
    assert "react" in d["detected_frameworks"]
