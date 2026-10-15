"""Data models for SDAT Frontend System-Design Auditing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from sdat.models import Decision


class PageType(str, Enum):
    """Categorization of individual frontend routes or entrypoints."""
    SPA = "spa"
    MPA = "mpa"
    STATIC = "static"
    SSR = "ssr"
    DYNAMIC = "dynamic"
    VISUAL_3D = "visual_3d"


class RenderingModel(str, Enum):
    """Architectural rendering model used for a page or component."""
    SSR = "ssr"
    SSG = "ssg"
    CSR = "csr"
    STREAMING = "streaming"
    HYDRATION = "hydration"
    STATIC_HTML = "static_html"
    UNKNOWN = "unknown"


class LoadingStrategy(str, Enum):
    """Loading and delivery strategy for bundles, components, and assets."""
    EAGER = "eager"
    LAZY = "lazy"
    DYNAMIC_IMPORT = "dynamic_import"
    ROUTE_SPLIT = "route_split"
    PROGRESSIVE = "progressive"


class DataFetchingPattern(str, Enum):
    """Pattern used for client/server data communication."""
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    SSE = "sse"
    SERVER_FETCH = "server_fetch"
    CLIENT_QUERY = "client_query"
    NONE = "none"


@dataclass(frozen=True)
class RuntimeMetrics:
    """Runtime performance metrics gathered from optional browser instrumentation.

    When runtime testing is unavailable (e.g. offline static audit),
    measured must remain False with explicit unmeasured reasoning.
    SDAT NEVER fabricates runtime scores.
    """
    measured: bool = False
    fcp_ms: float | None = None
    lcp_ms: float | None = None
    cls: float | None = None
    ttfb_ms: float | None = None
    inp_ms: float | None = None
    dom_nodes: int | None = None
    request_count: int | None = None
    transferred_bytes: int | None = None
    notes: str = "Runtime browser metrics unavailable; static structural evaluation only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "measured": self.measured,
            "fcp_ms": self.fcp_ms,
            "lcp_ms": self.lcp_ms,
            "cls": self.cls,
            "ttfb_ms": self.ttfb_ms,
            "inp_ms": self.inp_ms,
            "dom_nodes": self.dom_nodes,
            "request_count": self.request_count,
            "transferred_bytes": self.transferred_bytes,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class PageAnalysis:
    """Page-specific architectural assessment for a discrete route or entrypoint."""
    file_path: Path
    route: str
    page_type: PageType
    rendering_model: RenderingModel
    loading_strategy: LoadingStrategy
    data_fetching_pattern: DataFetchingPattern
    approximate_complexity: dict[str, Any] = field(default_factory=dict)
    has_responsive_evidence: bool = False
    asset_behavior: tuple[str, ...] = field(default_factory=tuple)
    findings: tuple[str, ...] = field(default_factory=tuple)
    dimension_results: dict[str, Any] = field(default_factory=dict)
    runtime_measurements: RuntimeMetrics = field(default_factory=RuntimeMetrics)

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": str(self.file_path),
            "route": self.route,
            "page_type": self.page_type.value,
            "rendering_model": self.rendering_model.value,
            "loading_strategy": self.loading_strategy.value,
            "data_fetching_pattern": self.data_fetching_pattern.value,
            "approximate_complexity": dict(self.approximate_complexity),
            "has_responsive_evidence": self.has_responsive_evidence,
            "asset_behavior": list(self.asset_behavior),
            "findings": list(self.findings),
            "dimension_results": dict(self.dimension_results),
            "runtime_measurements": self.runtime_measurements.to_dict(),
        }


@dataclass(frozen=True)
class FrontendDimensionScore:
    """Structured, explainable score for a discrete frontend architectural dimension."""
    dimension: str
    name: str
    score: float | None                # 0.0 - 100.0 or None if insufficient evidence
    status: str                        # "evaluated" | "insufficient_evidence"
    confidence: float
    rules_evaluated: int
    rules_passed: int
    findings: tuple[str, ...] = field(default_factory=tuple)
    recommendations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "name": self.name,
            "score": self.score,
            "status": self.status,
            "confidence": self.confidence,
            "rules_evaluated": self.rules_evaluated,
            "rules_passed": self.rules_passed,
            "findings": list(self.findings),
            "recommendations": list(self.recommendations),
        }


@dataclass(frozen=True)
class FrontendAuditResult:
    """Consolidated application-level frontend audit output with page-level breakdown."""
    target_root: Path
    detected_frameworks: tuple[str, ...]
    is_frontend: bool
    pages: tuple[PageAnalysis, ...]
    dimension_scores: dict[str, FrontendDimensionScore]
    overall_score: float | None
    overall_status: str
    summary: str
    decisions: tuple[Decision, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_root": str(self.target_root),
            "detected_frameworks": list(self.detected_frameworks),
            "is_frontend": self.is_frontend,
            "pages": [p.to_dict() for p in self.pages],
            "dimension_scores": {k: v.to_dict() for k, v in self.dimension_scores.items()},
            "overall_score": self.overall_score,
            "overall_status": self.overall_status,
            "summary": self.summary,
            "decisions": [
                {
                    "concept_id": d.concept_id,
                    "concept_name": d.concept_name,
                    "status": d.status.value,
                    "confidence": d.confidence,
                    "priority": d.priority.value,
                    "recommendation": d.recommendation,
                }
                for d in self.decisions
            ],
        }
