"""Backend System-Design Domain Models.

Defines structural models for backend architecture analysis, including endpoints,
middleware, service boundaries, rules, evaluation results, and audit results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sdat.models import Decision, DecisionStatus, Evidence, Priority


@dataclass(frozen=True)
class EndpointDefinition:
    """Represents a discovered backend API route or handler."""
    path: str
    method: str
    handler_symbol: str
    file_path: Path
    line: int
    framework: str | None = None
    has_auth: bool = False
    has_validation: bool = False
    has_timeout: bool = False
    db_operations: tuple[str, ...] = field(default_factory=tuple)
    external_calls: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class MiddlewareDefinition:
    """Represents a middleware or interceptor in the request processing pipeline."""
    name: str
    file_path: Path
    line: int
    purpose: str  # "auth", "cors", "rate_limiting", "logging", "error_handling", "tracing", "custom"
    scope: str = "global"  # "global", "router", "endpoint"


@dataclass(frozen=True)
class ServiceBoundaryDefinition:
    """Represents an architectural service, repository, or controller boundary."""
    name: str
    file_path: Path
    layer: str  # "controller", "handler", "service", "repository", "client", "adapter"
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    has_direct_db_access: bool = False
    has_external_calls: bool = False


@dataclass
class BackendAnalysisSummary:
    """Aggregated structural analysis of a backend codebase."""
    target_root: Path
    endpoints: list[EndpointDefinition] = field(default_factory=list)
    middlewares: list[MiddlewareDefinition] = field(default_factory=list)
    boundaries: list[ServiceBoundaryDefinition] = field(default_factory=list)
    detected_frameworks: set[str] = field(default_factory=set)
    detected_databases: set[str] = field(default_factory=set)
    detected_queues: set[str] = field(default_factory=set)
    has_structured_logging: bool = False
    has_metrics: bool = False
    has_tracing: bool = False
    has_healthcheck: bool = False
    has_connection_pooling: bool = False
    has_rate_limiting: bool = False
    has_caching: bool = False
    has_retries: bool = False
    has_circuit_breaker: bool = False
    has_idempotency: bool = False
    has_input_validation: bool = False
    has_timeouts: bool = False
    has_transaction_boundaries: bool = False


@dataclass(frozen=True)
class BackendRule:
    """A deterministic system-design evaluation rule in the Backend KnowledgePack."""
    id: str
    dimension: str
    name: str
    description: str
    priority: Priority
    concept_id: str
    remediation_guidance: str = ""

    @property
    def rule_id(self) -> str:
        return self.id

    @property
    def severity(self) -> Priority:
        return self.priority


@dataclass
class BackendRuleEvaluationResult:
    """The result of evaluating a BackendRule against grounded structural evidence."""
    rule: BackendRule
    status: DecisionStatus
    confidence: float
    evidence: list[Evidence] = field(default_factory=list)
    misconfiguration: str | None = None
    gaps: list[str] = field(default_factory=list)
    recommendation: str | None = None


@dataclass(frozen=True)
class BackendDimensionScore:
    """Score for a specific backend architectural dimension."""
    dimension: str
    score: float  # 0.0 to 100.0
    rules_evaluated: int
    rules_passed: int
    rules_failed: int
    critical_issues: int
    status: str  # "healthy", "warning", "critical"


@dataclass(frozen=True)
class BackendAuditResult:
    """Consolidated findings, dimension scores, and decisions for the Backend domain."""
    target_root: Path
    detected_frameworks: tuple[str, ...]
    detected_databases: tuple[str, ...]
    detected_queues: tuple[str, ...]
    is_backend: bool
    endpoints_count: int
    middlewares_count: int
    boundaries_count: int
    dimension_scores: tuple[BackendDimensionScore, ...]
    overall_score: float | None
    overall_status: str
    summary: str
    decisions: tuple[Decision, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_root": str(self.target_root),
            "detected_frameworks": list(self.detected_frameworks),
            "detected_databases": list(self.detected_databases),
            "detected_queues": list(self.detected_queues),
            "is_backend": self.is_backend,
            "endpoints_count": self.endpoints_count,
            "middlewares_count": self.middlewares_count,
            "boundaries_count": self.boundaries_count,
            "dimension_scores": [
                {
                    "dimension": ds.dimension,
                    "score": ds.score,
                    "rules_evaluated": ds.rules_evaluated,
                    "rules_passed": ds.rules_passed,
                    "rules_failed": ds.rules_failed,
                    "critical_issues": ds.critical_issues,
                    "status": ds.status,
                }
                for ds in self.dimension_scores
            ],
            "overall_score": self.overall_score,
            "overall_status": self.overall_status,
            "summary": self.summary,
            "decisions_count": len(self.decisions),
        }
