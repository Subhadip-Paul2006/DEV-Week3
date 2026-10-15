"""Data models for SDAT signals, decisions, and audit artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SignalKind(str, Enum):
    PRESENCE = "presence"
    ABSENCE = "absence"
    WEAKNESS = "weakness"
    CONFIG = "config"


class DecisionStatus(str, Enum):
    IMPLEMENTED = "implemented"
    MISSING = "missing"
    MISCONFIGURED = "misconfigured"
    UNKNOWN = "unknown"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    N_A = "n/a"


@dataclass(frozen=True)
class Signal:
    """A detected pattern in source code linking to a concept."""
    concept_id: str
    kind: SignalKind
    file_path: Path
    line_range: tuple[int, int] | None
    evidence: str
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Evidence:
    """Citation for a decision: file, line, snippet, and note."""
    file: str
    line: int
    snippet: str
    note: str = ""


@dataclass(frozen=True)
class Decision:
    """An evaluated verdict on a concept."""
    concept_id: str
    concept_name: str
    status: DecisionStatus
    confidence: float
    priority: Priority = Priority.INFO
    evidence: list["Evidence"] = field(default_factory=list)
    misconfiguration: str | None = None
    gaps: list[str] = field(default_factory=list)
    recommendation: str | None = None


@dataclass(frozen=True)
class FileSignals:
    """All signals produced from a single file during a scan run."""
    file: str
    signals: list[Signal] = field(default_factory=list)


@dataclass(frozen=True)
class AuditManifest:
    """Metadata for a single audit run."""
    run_id: str
    sdat_version: str
    kb_version: str
    auditor_provider: str
    scanners_invoked: list[str]
    target_root: str
    git_head: str | None = None
    duration_seconds: float = 0.0
    signals_count: int = 0
    decisions_count: int = 0


# =============================================================================
# Phase 2.5 — Common Evidence Model (Language-Agnostic, Typed Evidence)
# =============================================================================


class EvidenceKind(str, Enum):
    """Canonical typed evidence kinds for source code observations."""
    # Structural
    IMPORT = "import"                     # Module/package imported
    CALL = "call"                         # Function or method invocation
    DECORATOR = "decorator"               # Decorator applied to function/class/method
    INHERITANCE = "inheritance"           # Class inheritance hierarchy
    INSTANTIATION = "instantiation"       # Object or class instantiation
    ANNOTATION = "annotation"             # Type hint or structural annotation

    # Behavioral & Control Flow
    CONTROL_FLOW = "control_flow"         # Loop, try/except/retry, fallback branch
    ASYNC_PATTERN = "async_pattern"       # Async/await, coroutine, event loop interaction
    CONCURRENCY = "concurrency"           # Threads, multiprocessing, worker pool

    # Configuration & Environment
    CONFIG_KEY = "config_key"             # Key-value declaration in settings/config
    ENV_VAR = "env_var"                   # Environment variable access or definition

    # Data & Storage
    DB_QUERY = "db_query"                 # SQL statement, ORM query, transaction block
    SCHEMA_DEF = "schema_def"             # DB model, migration table, Pydantic/Zod schema
    MIGRATION = "migration"               # Schema migration step

    # Architecture & Manifest
    DEPENDENCY = "dependency"             # Manifest package dependency (package.json, pyproject.toml)
    FRAMEWORK_MARKER = "framework_marker" # Sentinel file or framework-specific boilerplate
    ARCHITECTURE_PATTERN = "architecture_pattern"  # High-level architectural pattern

    # Explicit Absence
    ABSENT_PATTERN = "absent_pattern"     # Explicitly verified absence of required safeguard

    # Backward Compatibility
    LEGACY_SIGNAL = "legacy_signal"       # Bridge representation for legacy Signal instances


@dataclass(frozen=True)
class EvidenceFact:
    """A typed, structural, concept-agnostic observation in source code.

    An EvidenceFact represents an objective, verifiable observation in the code
    (e.g., an import, instantiation, method call, or config setting).
    It deliberately carries NO concept_id and makes NO architectural judgments.
    """
    kind: EvidenceKind
    subject: str                         # Target symbol/module/key (e.g. 'redis', 'retry')
    language: str                        # 'python', 'typescript', etc.
    file_path: Path
    line_range: tuple[int, int] | None
    snippet: str                         # Verbatim source code snippet (<= 200 chars)
    scope: str | None = None             # Enclosing function or class name
    call_target: str | None = None       # Resolved/qualified call target
    call_args_schema: str | None = None  # Summary of arguments passed
    parent_symbol: str | None = None     # Base class or decorated symbol
    value_observed: str | None = None    # Config or constant value
    value_schema: str | None = None      # Type/format of observed value
    extraction_confidence: float = 1.0   # Scanner extraction certainty (not architectural verdict)
    identifier_hints: tuple[str, ...] = field(default_factory=tuple)  # Weak corroborating hints only
    framework: str | None = None         # 'fastapi', 'express', etc.
    library: str | None = None           # 'tenacity', 'redis-py', etc.
    ttl_observed: bool | None = None
    retry_count_observed: int | None = None
    timeout_observed: bool | None = None
    circuit_breaker_threshold: int | None = None

    def __post_init__(self) -> None:
        # Enforce frozen immutability with normalized types
        if not isinstance(self.kind, EvidenceKind):
            object.__setattr__(self, "kind", EvidenceKind(self.kind))
        if not isinstance(self.file_path, Path):
            object.__setattr__(self, "file_path", Path(self.file_path))
        if isinstance(self.line_range, list):
            object.__setattr__(self, "line_range", tuple(self.line_range))
        if not isinstance(self.identifier_hints, tuple):
            object.__setattr__(self, "identifier_hints", tuple(self.identifier_hints))
        # Ensure snippet is bounded (<= 200 chars)
        if len(self.snippet) > 200:
            object.__setattr__(self, "snippet", self.snippet[:200])
        # Validate extraction_confidence bounds
        if not (0.0 <= self.extraction_confidence <= 1.0):
            raise ValueError(f"extraction_confidence must be in [0.0, 1.0], got {self.extraction_confidence}")

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "kind": self.kind.value,
            "subject": self.subject,
            "language": self.language,
            "file_path": str(self.file_path),
            "line_range": list(self.line_range) if self.line_range else None,
            "snippet": self.snippet,
            "scope": self.scope,
            "call_target": self.call_target,
            "call_args_schema": self.call_args_schema,
            "parent_symbol": self.parent_symbol,
            "value_observed": self.value_observed,
            "value_schema": self.value_schema,
            "extraction_confidence": self.extraction_confidence,
            "identifier_hints": list(self.identifier_hints),
            "framework": self.framework,
            "library": self.library,
            "ttl_observed": self.ttl_observed,
            "retry_count_observed": self.retry_count_observed,
            "timeout_observed": self.timeout_observed,
            "circuit_breaker_threshold": self.circuit_breaker_threshold,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceFact":
        """Reconstruct an EvidenceFact from a dictionary."""
        line_range = data.get("line_range")
        if line_range is not None:
            line_range = (line_range[0], line_range[1])
        return cls(
            kind=EvidenceKind(data["kind"]),
            subject=data["subject"],
            language=data.get("language", "unknown"),
            file_path=Path(data["file_path"]),
            line_range=line_range,
            snippet=data.get("snippet", ""),
            scope=data.get("scope"),
            call_target=data.get("call_target"),
            call_args_schema=data.get("call_args_schema"),
            parent_symbol=data.get("parent_symbol"),
            value_observed=data.get("value_observed"),
            value_schema=data.get("value_schema"),
            extraction_confidence=float(data.get("extraction_confidence", 1.0)),
            identifier_hints=tuple(data.get("identifier_hints", ())),
            framework=data.get("framework"),
            library=data.get("library"),
            ttl_observed=data.get("ttl_observed"),
            retry_count_observed=data.get("retry_count_observed"),
            timeout_observed=data.get("timeout_observed"),
            circuit_breaker_threshold=data.get("circuit_breaker_threshold"),
        )


@dataclass(frozen=True)
class FileEvidence:
    """Collection of EvidenceFacts extracted from a single source file."""
    file: str
    facts: tuple[EvidenceFact, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.facts, tuple):
            object.__setattr__(self, "facts", tuple(self.facts))

    def to_dict(self) -> dict[str, Any]:
        return {
            "file": self.file,
            "facts": [f.to_dict() for f in self.facts],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileEvidence":
        return cls(
            file=data["file"],
            facts=tuple(EvidenceFact.from_dict(f) for f in data.get("facts", [])),
        )


@dataclass(frozen=True)
class EvidenceBundle:
    """Pre-correlated bundle of facts dispatched to an agent for concept evaluation."""
    concept_id: str
    facts: tuple[EvidenceFact, ...]
    peer_patterns: tuple[str, ...] = field(default_factory=tuple)
    literature_findings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.facts, tuple):
            object.__setattr__(self, "facts", tuple(self.facts))
        if not isinstance(self.peer_patterns, tuple):
            object.__setattr__(self, "peer_patterns", tuple(self.peer_patterns))
        if not isinstance(self.literature_findings, tuple):
            object.__setattr__(self, "literature_findings", tuple(self.literature_findings))

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "facts": [f.to_dict() for f in self.facts],
            "peer_patterns": list(self.peer_patterns),
            "literature_findings": list(self.literature_findings),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceBundle":
        return cls(
            concept_id=data["concept_id"],
            facts=tuple(EvidenceFact.from_dict(f) for f in data.get("facts", [])),
            peer_patterns=tuple(data.get("peer_patterns", ())),
            literature_findings=tuple(data.get("literature_findings", ())),
        )


class SignalBridge:
    """Bidirectional compatibility bridge between legacy Signal and EvidenceFact.

    Enables gradual migration without breaking legacy rules or consumers.
    Conversion is loss-aware: extra metadata is preserved when possible.
    """

    @staticmethod
    def to_evidence_fact(signal: Signal) -> EvidenceFact:
        """Convert a legacy Signal to an EvidenceFact.

        Infers the most appropriate EvidenceKind and preserves metadata.
        """
        # Determine kind
        meta_kind = signal.metadata.get("evidence_kind")
        if meta_kind:
            try:
                kind = EvidenceKind(meta_kind)
            except ValueError:
                kind = EvidenceKind.LEGACY_SIGNAL
        elif signal.kind == SignalKind.ABSENCE:
            kind = EvidenceKind.ABSENT_PATTERN
        elif signal.kind == SignalKind.CONFIG:
            kind = EvidenceKind.CONFIG_KEY
        else:
            kind = EvidenceKind.LEGACY_SIGNAL

        language = signal.metadata.get("language", "unknown")
        hints = signal.metadata.get("identifier_hints", signal.metadata.get("hints", []))
        if isinstance(hints, str):
            hints = [hints]

        return EvidenceFact(
            kind=kind,
            subject=signal.concept_id,
            language=language,
            file_path=signal.file_path,
            line_range=signal.line_range,
            snippet=signal.evidence[:200],
            extraction_confidence=signal.confidence,
            identifier_hints=tuple(hints),
            framework=signal.metadata.get("framework"),
            library=signal.metadata.get("library"),
            call_target=signal.metadata.get("call_target"),
            call_args_schema=signal.metadata.get("call_args_schema"),
            scope=signal.metadata.get("scope"),
            value_observed=signal.metadata.get("value_observed"),
            ttl_observed=signal.metadata.get("ttl_observed"),
            retry_count_observed=signal.metadata.get("retry_count_observed"),
            timeout_observed=signal.metadata.get("timeout_observed"),
            circuit_breaker_threshold=signal.metadata.get("circuit_breaker_threshold"),
        )

    @staticmethod
    def to_legacy_signal(fact: EvidenceFact, concept_id: str = "") -> Signal:
        """Convert an EvidenceFact to a legacy Signal view.

        If concept_id is empty, uses fact.subject or 'unknown'.
        """
        cid = concept_id or fact.subject or "unknown"

        # Determine legacy SignalKind
        if fact.kind == EvidenceKind.ABSENT_PATTERN:
            signal_kind = SignalKind.ABSENCE
        elif fact.kind in (EvidenceKind.CONFIG_KEY, EvidenceKind.ENV_VAR):
            signal_kind = SignalKind.CONFIG
        elif fact.kind == EvidenceKind.LEGACY_SIGNAL and fact.snippet.startswith("[WEAKNESS]"):
            signal_kind = SignalKind.WEAKNESS
        else:
            signal_kind = SignalKind.PRESENCE

        metadata: dict[str, Any] = {
            "evidence_kind": fact.kind.value,
            "language": fact.language,
        }
        if fact.identifier_hints:
            metadata["identifier_hints"] = list(fact.identifier_hints)
        if fact.framework:
            metadata["framework"] = fact.framework
        if fact.library:
            metadata["library"] = fact.library
        if fact.scope:
            metadata["scope"] = fact.scope
        if fact.call_target:
            metadata["call_target"] = fact.call_target
        if fact.call_args_schema:
            metadata["call_args_schema"] = fact.call_args_schema
        if fact.parent_symbol:
            metadata["parent_symbol"] = fact.parent_symbol
        if fact.value_observed:
            metadata["value_observed"] = fact.value_observed
        if fact.value_schema:
            metadata["value_schema"] = fact.value_schema
        if fact.ttl_observed is not None:
            metadata["ttl_observed"] = fact.ttl_observed
        if fact.retry_count_observed is not None:
            metadata["retry_count_observed"] = fact.retry_count_observed
        if fact.timeout_observed is not None:
            metadata["timeout_observed"] = fact.timeout_observed
        if fact.circuit_breaker_threshold is not None:
            metadata["circuit_breaker_threshold"] = fact.circuit_breaker_threshold

        return Signal(
            concept_id=cid,
            kind=signal_kind,
            file_path=fact.file_path,
            line_range=fact.line_range,
            evidence=fact.snippet,
            confidence=fact.extraction_confidence,
            metadata=metadata,
        )

