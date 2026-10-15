"""Canonical Knowledge Architecture Models for SDAT.

Establishes the clean separation between:
- Language: "How is the software written?"
- Domain: "What kind of software/system/component is being built?"
- Capability: "What observable capability exists?"
- Concept: "What architectural principle should be considered?"
- Rule: "How should that concept be evaluated?"
- Evidence: "What concrete repository/runtime observation supports the evaluation?"
- Agent: "Which specialist execution context evaluates the relevant concepts?"

Core Invariant:
"Names are clues. Behavior is evidence.
Language tells SDAT how the code is written.
Domain classification tells SDAT what the system is doing.
Evidence tells SDAT what the repository actually implements.
Concepts tell SDAT what should be considered.
Rules tell SDAT how those concepts are evaluated.
Agents execute the relevant domain audit."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from sdat.models import DecisionStatus, EvidenceKind, Priority


class DomainTier(int, Enum):
    """Tier for domain classification and agent scheduling."""
    FOUNDATION = 1      # Core foundation (always-on or fundamental baseline)
    WORKLOAD = 2        # Domain workload (frontend, backend, database, etc.)
    SPECIALIZED = 3     # Emerging or specialized domains (web3, ML, NLP, etc.)


class ConceptRelationType(str, Enum):
    """Typed architectural relationships between concepts."""
    DEPENDS_ON = "depends_on"         # Prerequisite concept required
    EXTENDS = "extends"               # Broadens or builds upon parent concept
    SPECIALIZES = "specializes"       # Domain specialization of a universal core concept
    RELATED_TO = "related_to"         # Architectural affinity
    REQUIRES = "requires"             # Mutual co-implementation requirement
    CONFLICTS_WITH = "conflicts_with" # Incompatible architectural anti-pattern
    CROSS_DOMAIN = "cross_domain"     # Cross-cutting concept spanning multiple domains


class ConceptStatus(str, Enum):
    """Maturity and implementation lifecycle status of a concept."""
    ACTIVE = "active"                 # Fully operational and evaluated by active rules
    DRAFT = "draft"                   # Concept drafted, rules under development
    DEPRECATED = "deprecated"         # Replaced or sunset
    SPEC_ONLY = "spec_only"           # Architectural contract defined, implementation reserved


class EvidenceRequirementScope(str, Enum):
    """Scope where evidence must be observed to satisfy evaluation requirements."""
    LOCAL_FILE = "local_file"
    CROSS_FILE = "cross_file"
    REPOSITORY_WIDE = "repository_wide"
    RUNTIME_OPTIONAL = "runtime_optional"


@dataclass(frozen=True)
class Language:
    """Represents a programming or markup language in target repositories.

    'Language tells SDAT how the code is written.'
    A language is never a substitute for domain classification.
    """
    id: str                           # e.g., "python", "typescript", "rust"
    name: str                         # e.g., "Python", "TypeScript", "Rust"
    extensions: tuple[str, ...]       # e.g., (".py",), (".ts", ".tsx")
    scanner_supported: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Domain:
    """Represents a software domain or workload classification.

    'Domain classification tells SDAT what the system is doing.'
    """
    id: str                           # e.g., "core", "frontend", "backend", "database"
    name: str                         # e.g., "Frontend Architecture", "Core System Design"
    description: str
    tier: DomainTier = DomainTier.WORKLOAD
    dependencies: tuple[str, ...] = field(default_factory=tuple)  # e.g. ["core"]
    scoring_dimensions: tuple[str, ...] = field(default_factory=tuple)
    status: ConceptStatus = ConceptStatus.ACTIVE


@dataclass(frozen=True)
class Capability:
    """Represents an observable behavioral capability in the repository.

    'Capability tells SDAT what observable software capability appears to exist.'
    Crucial: Capability != Finding. Capability alone does not prove correct architecture.
    """
    id: str                           # e.g., "cap.frontend.react_tree"
    name: str                         # e.g., "React Component Hierarchy"
    domain: str                       # e.g., "frontend"
    description: str
    detection_evidence_kinds: tuple[EvidenceKind, ...] = field(default_factory=tuple)
    activated_concepts: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EvidenceRequirement:
    """Specification of concrete repository or runtime evidence required to evaluate a concept or rule.

    'Evidence tells SDAT what the repository actually implements.'
    Evidence must remain grounded in typed EvidenceFacts, never raw symbol substrings or comments.
    """
    evidence_kind: EvidenceKind
    description: str
    subject_pattern: str | None = None
    min_occurrences: int = 1
    scope: EvidenceRequirementScope = EvidenceRequirementScope.REPOSITORY_WIDE
    allow_runtime: bool = False


@dataclass(frozen=True)
class RuleApplicability:
    """Defines the activation preconditions for an evaluation rule."""
    domains: tuple[str, ...] = field(default_factory=lambda: ("all",))
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    languages: tuple[str, ...] = field(default_factory=lambda: ("any",))
    frameworks: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Rule:
    """A deterministic evaluation rule operating over grounded evidence.

    'Rules tell SDAT how concepts are evaluated.'
    A Rule evaluates evidence, not language syntax, unless explicitly language-specific.
    """
    rule_id: str                      # e.g., "FE-REND-01", "CORE-CACHE-01"
    concept_id: str                   # e.g., "frontend.rendering", "core.caching"
    name: str
    description: str
    applicability: RuleApplicability
    required_evidence: tuple[EvidenceRequirement, ...]
    evaluation_logic: str             # Deterministic logic description
    severity: Priority = Priority.HIGH
    confidence_requirements: float = 0.8
    remediation_guidance: str = ""
    references: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Concept:
    """Canonical architectural principle considered during an audit.

    'Concepts tell SDAT what should be considered.'
    Universal concepts live in 'core'. Domain concepts specialize universal core concepts.
    """
    concept_id: str                   # Globally unique ID (e.g. "core.caching", "frontend.rendering")
    domain: str                       # e.g., "core", "frontend", "backend", "database"
    name: str                         # Human-readable concept name
    description: str
    category: str                     # e.g., "caching", "resilience", "rendering"
    related_core_concepts: tuple[str, ...] = field(default_factory=tuple)
    applicable_capabilities: tuple[str, ...] = field(default_factory=tuple)
    required_evidence_kinds: tuple[EvidenceKind, ...] = field(default_factory=tuple)
    status: ConceptStatus = ConceptStatus.ACTIVE
    relationships: dict[ConceptRelationType, tuple[str, ...]] = field(default_factory=dict)
    question: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def id(self) -> str:
        """Alias for backward compatibility with legacy Concept references."""
        return self.concept_id

    @property
    def is_universal(self) -> bool:
        """True if concept is part of universal core system design."""
        return self.domain == "core" or self.concept_id.startswith("core.")


@dataclass
class KnowledgePack:
    """Domain knowledge definition package.

    A KnowledgePack encapsulates domain knowledge reusable across languages.
    It is NOT a scanner, language parser, agent, or evidence store.
    """
    id: str                           # e.g., "kp.frontend", "kp.core"
    domain: str                       # e.g., "frontend", "core"
    version: str                      # Semver, e.g. "1.0.0"
    concepts: list[Concept] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    evidence_requirements: list[EvidenceRequirement] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # Domain dependencies, e.g. ["core"]
    scoring_dimensions: list[str] = field(default_factory=list)
    recommendations: dict[str, str] = field(default_factory=dict)

    @property
    def concepts_by_id(self) -> dict[str, Concept]:
        return {c.concept_id: c for c in self.concepts}

    @property
    def rules_by_id(self) -> dict[str, Rule]:
        return {r.rule_id: r for r in self.rules}


# =============================================================================
# Scoring Hierarchy Models
# =============================================================================


@dataclass(frozen=True)
class DimensionScore:
    """Score for a specific architectural dimension within a domain."""
    dimension: str                    # e.g., "rendering", "loading_strategy"
    score: float                      # 0.0 to 100.0
    status: DecisionStatus            # Evaluated dimension status
    rules_evaluated: int
    rules_passed: int
    notes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DomainScore:
    """Aggregate score for a domain workload across its dimensions."""
    domain: str                       # e.g., "frontend", "backend"
    overall_score: float              # 0.0 to 100.0
    dimension_scores: dict[str, DimensionScore] = field(default_factory=dict)
    summary: str = ""


@dataclass(frozen=True)
class AuditScoringSummary:
    """Application-level summary aggregating scores across all active domains."""
    application_score: float          # Weighted composite score (0.0 to 100.0)
    domain_scores: dict[str, DomainScore] = field(default_factory=dict)
    active_domains: tuple[str, ...] = field(default_factory=tuple)
    critical_findings_count: int = 0
    high_findings_count: int = 0
