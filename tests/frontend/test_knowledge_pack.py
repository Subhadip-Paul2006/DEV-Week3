"""Tests for FrontendKnowledgePack rules and deterministic evaluation."""

from __future__ import annotations

from pathlib import Path

from sdat.frontend.knowledge_pack import FrontendKnowledgePack
from sdat.frontend.models import (
    DataFetchingPattern,
    LoadingStrategy,
    PageAnalysis,
    PageType,
    RenderingModel,
    RuntimeMetrics,
)
from sdat.models import DecisionStatus, EvidenceFact, EvidenceKind, Priority


def test_evaluate_clean_ssr_rendering_architecture():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("app/page.tsx"),
        route="/",
        page_type=PageType.SSR,
        rendering_model=RenderingModel.SSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.SERVER_FETCH,
    )
    results = kp.evaluate(facts=[], pages=[page])

    rend_results = [r for r in results if r.rule.id == "FE-REND-01"]
    assert len(rend_results) == 1
    assert rend_results[0].status == DecisionStatus.IMPLEMENTED
    assert rend_results[0].confidence >= 0.9


def test_evaluate_missing_404_routing_fallback():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("app/page.tsx"),
        route="/",
        page_type=PageType.SPA,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
    )
    results = kp.evaluate(facts=[], pages=[page])

    rout_results = [r for r in results if r.rule.id == "FE-ROUT-02"]
    assert len(rout_results) == 1
    assert rout_results[0].status == DecisionStatus.MISCONFIGURED
    assert "404" in rout_results[0].misconfiguration


def test_evaluate_eager_heavy_visual_hazard():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("src/Scene.tsx"),
        route="/scene",
        page_type=PageType.VISUAL_3D,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
        approximate_complexity={"visual_canvas": True},
    )
    results = kp.evaluate(facts=[], pages=[page])

    load_results = [r for r in results if r.rule.id == "FE-LOAD-01"]
    assert len(load_results) == 1
    assert load_results[0].status == DecisionStatus.MISCONFIGURED
    assert "dynamic import" in load_results[0].recommendation.lower()


def test_evaluate_unmeasured_runtime_metrics():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("src/App.tsx"),
        route="/",
        page_type=PageType.SPA,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
    )
    # Offline / unmeasured runtime
    results = kp.evaluate(facts=[], pages=[page], runtime=RuntimeMetrics(measured=False))

    perf_results = [r for r in results if r.rule.id == "FE-PERF-02"]
    assert len(perf_results) == 1
    assert perf_results[0].status == DecisionStatus.UNKNOWN
    assert "unmeasured" in perf_results[0].gaps[0].lower()


def test_evaluate_measured_runtime_metrics():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("src/App.tsx"),
        route="/",
        page_type=PageType.SPA,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
    )
    live_runtime = RuntimeMetrics(measured=True, fcp_ms=900, lcp_ms=1800, cls=0.02)
    results = kp.evaluate(facts=[], pages=[page], runtime=live_runtime)

    perf_results = [r for r in results if r.rule.id == "FE-PERF-02"]
    assert len(perf_results) == 1
    assert perf_results[0].status == DecisionStatus.IMPLEMENTED
    assert "FCP=900" in perf_results[0].evidence[0].snippet


def test_evaluate_xss_security_violation():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("src/BadView.tsx"),
        route="/bad",
        page_type=PageType.DYNAMIC,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
        findings=("Unsanitized raw HTML injection detected; XSS risk",),
    )
    results = kp.evaluate(facts=[], pages=[page])

    sec_results = [r for r in results if r.rule.id == "FE-SEC-01"]
    assert len(sec_results) == 1
    assert sec_results[0].status == DecisionStatus.MISCONFIGURED
    assert sec_results[0].rule.priority == Priority.CRITICAL


def test_evaluate_secret_exposure_violation():
    kp = FrontendKnowledgePack()
    fact = EvidenceFact(
        kind=EvidenceKind.CONFIG_KEY,
        subject="hardcoded_credential",
        language="typescript",
        file_path=Path("src/config.ts"),
        line_range=(5, 5),
        snippet="const SECRET = 'sk_live_123456789012';",
    )
    page = PageAnalysis(
        file_path=Path("src/App.tsx"),
        route="/",
        page_type=PageType.SPA,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
    )
    results = kp.evaluate(facts=[fact], pages=[page])

    sec_results = [r for r in results if r.rule.id == "FE-SEC-02"]
    assert len(sec_results) == 1
    assert sec_results[0].status == DecisionStatus.MISCONFIGURED


def test_evaluate_web3_frontend_when_present():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("src/Wallet.tsx"),
        route="/wallet",
        page_type=PageType.DYNAMIC,
        rendering_model=RenderingModel.CSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.NONE,
        dimension_results={"is_web3": True},
    )
    results = kp.evaluate(facts=[], pages=[page])

    w3_results = [r for r in results if r.rule.id == "FE-W3-01"]
    assert len(w3_results) == 1
    assert w3_results[0].status == DecisionStatus.IMPLEMENTED


def test_evaluate_to_decisions_conversion():
    kp = FrontendKnowledgePack()
    page = PageAnalysis(
        file_path=Path("app/page.tsx"),
        route="/",
        page_type=PageType.SSR,
        rendering_model=RenderingModel.SSR,
        loading_strategy=LoadingStrategy.EAGER,
        data_fetching_pattern=DataFetchingPattern.SERVER_FETCH,
        has_responsive_evidence=True,
    )
    results = kp.evaluate(facts=[], pages=[page])
    decisions = kp.to_decisions(results)

    assert len(decisions) >= 14
    concept_ids = {d.concept_id for d in decisions}
    assert "frontend.rendering" in concept_ids
    assert "frontend.responsive-design" in concept_ids
    assert "frontend.security" in concept_ids
