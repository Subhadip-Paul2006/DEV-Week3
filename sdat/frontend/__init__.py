"""SDAT Frontend System-Design Auditing Module."""

from __future__ import annotations

from .agent import FrontendAgent
from .knowledge_pack import FrontendKnowledgePack, FrontendRule, RuleEvaluationResult
from .models import (
    DataFetchingPattern,
    FrontendAuditResult,
    FrontendDimensionScore,
    LoadingStrategy,
    PageAnalysis,
    PageType,
    RenderingModel,
    RuntimeMetrics,
)
from .page_analyzer import FrontendPageAnalyzer
from .runtime import (
    BrowserRuntimeCollector,
    OfflineRuntimeCollector,
    ProvidedRuntimeCollector,
)
from .scoring import FrontendScoringEngine

__all__ = [
    "BrowserRuntimeCollector",
    "DataFetchingPattern",
    "FrontendAgent",
    "FrontendAuditResult",
    "FrontendDimensionScore",
    "FrontendKnowledgePack",
    "FrontendPageAnalyzer",
    "FrontendRule",
    "FrontendScoringEngine",
    "LoadingStrategy",
    "OfflineRuntimeCollector",
    "PageAnalysis",
    "PageType",
    "ProvidedRuntimeCollector",
    "RenderingModel",
    "RuleEvaluationResult",
    "RuntimeMetrics",
]
