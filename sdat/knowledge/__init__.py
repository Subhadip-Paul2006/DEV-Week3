"""SDAT Knowledge Subsystem.

Canonical architecture separating Language, Domain, Capability, Concept, Rule,
Evidence Requirements, and Specialist Agents.
"""

from __future__ import annotations

from sdat.knowledge.models import (
    AuditScoringSummary,
    Capability,
    Concept,
    ConceptRelationType,
    ConceptStatus,
    DimensionScore,
    Domain,
    DomainScore,
    DomainTier,
    EvidenceRequirement,
    EvidenceRequirementScope,
    KnowledgePack,
    Language,
    Rule,
    RuleApplicability,
)
from sdat.knowledge.registry import (
    KnowledgeRegistry,
    KnowledgeValidationError,
    build_canonical_registry,
)
from sdat.knowledge.scoring import UniversalScoringEngine

__all__ = [
    "AuditScoringSummary",
    "Capability",
    "Concept",
    "ConceptRelationType",
    "ConceptStatus",
    "DimensionScore",
    "Domain",
    "DomainScore",
    "DomainTier",
    "EvidenceRequirement",
    "EvidenceRequirementScope",
    "KnowledgePack",
    "KnowledgeRegistry",
    "KnowledgeValidationError",
    "Language",
    "Rule",
    "RuleApplicability",
    "UniversalScoringEngine",
    "build_canonical_registry",
]

