"""Backend System-Design Domain Module for SDAT.

Provides domain models, structural analyzers, knowledge packs, scoring engine,
and the D-01 BackendAgent for comprehensive backend system-design audits.
"""

from sdat.backend.agent import BackendAgent
from sdat.backend.analyzer import BackendStructuralAnalyzer
from sdat.backend.knowledge_pack import BackendKnowledgePack
from sdat.backend.models import (
    BackendAnalysisSummary,
    BackendAuditResult,
    BackendDimensionScore,
    BackendRule,
    BackendRuleEvaluationResult,
    EndpointDefinition,
    MiddlewareDefinition,
    ServiceBoundaryDefinition,
)
from sdat.backend.scoring import BackendScoringEngine

__all__ = [
    "BackendAgent",
    "BackendAnalysisSummary",
    "BackendAuditResult",
    "BackendDimensionScore",
    "BackendKnowledgePack",
    "BackendRule",
    "BackendRuleEvaluationResult",
    "BackendScoringEngine",
    "BackendStructuralAnalyzer",
    "EndpointDefinition",
    "MiddlewareDefinition",
    "ServiceBoundaryDefinition",
]
