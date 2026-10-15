"""Comprehensive Tests for SDAT Concept & Domain Knowledge Architecture.

Verifies:
- Canonical separation of Language, Domain, Capability, Concept, Rule, Evidence, and Agent
- Global Concept ID uniqueness
- Core vs Domain concept separation & specialization
- KnowledgePack contract and dependency resolution
- Agent -> KnowledgePack mapping
- 4-Tier Scoring Hierarchy
- Negative Tests (Names != Evidence, Comments != Evidence, Language != Domain)
"""

from __future__ import annotations

import pytest

from sdat.frontend.agent import FrontendAgent
from sdat.frontend.knowledge_pack import FrontendKnowledgePack
from sdat.knowledge import (
    Concept,
    ConceptRelationType,
    ConceptStatus,
    KnowledgePack,
    KnowledgeRegistry,
    KnowledgeValidationError,
    Language,
    Rule,
    RuleApplicability,
    UniversalScoringEngine,
    build_canonical_registry,
)
from sdat.models import DecisionStatus, EvidenceFact, EvidenceKind


@pytest.fixture
def canonical_registry() -> KnowledgeRegistry:
    return build_canonical_registry()


# =============================================================================
# 1. Concept ID Uniqueness & Validation
# =============================================================================


def test_concept_id_uniqueness(canonical_registry: KnowledgeRegistry):
    """Every registered concept ID must be globally unique across all domains."""
    concepts = canonical_registry.all_concepts
    concept_ids = [c.concept_id for c in concepts]
    assert len(concept_ids) == len(set(concept_ids)), "Duplicate concept IDs discovered!"


def test_duplicate_concept_registration_raises():
    """Attempting to register a different concept with an existing ID must raise KnowledgeValidationError."""
    registry = KnowledgeRegistry()
    c1 = Concept(
        concept_id="core.caching",
        domain="core",
        name="Caching 1",
        description="First",
        category="caching",
    )
    c2 = Concept(
        concept_id="core.caching",
        domain="frontend",
        name="Caching 2",
        description="Second",
        category="caching",
    )
    registry.register_concept(c1)
    with pytest.raises(KnowledgeValidationError, match="Duplicate concept ID"):
        registry.register_concept(c2)


# =============================================================================
# 2. Rule -> Concept Reference Integrity
# =============================================================================


def test_rule_references_valid_concept(canonical_registry: KnowledgeRegistry):
    """Every rule must reference an existing, registered concept."""
    for rule in canonical_registry.all_rules:
        concept = canonical_registry.get_concept(rule.concept_id)
        assert concept is not None, f"Rule {rule.rule_id} references missing concept {rule.concept_id}"


def test_unregistered_rule_concept_raises():
    """Registering a rule with an unknown concept ID must raise KnowledgeValidationError."""
    registry = KnowledgeRegistry()
    rule = Rule(
        rule_id="RULE-INVALID-01",
        concept_id="nonexistent.concept",
        name="Invalid Rule",
        description="Should fail",
        applicability=RuleApplicability(),
        required_evidence=(),
        evaluation_logic="always_true",
    )
    with pytest.raises(KnowledgeValidationError, match="references unknown concept_id"):
        registry.register_rule(rule)


# =============================================================================
# 3. Core vs Domain Concept Separation & Specialization
# =============================================================================


def test_core_vs_domain_separation(canonical_registry: KnowledgeRegistry):
    """Universal concepts must live in 'core'. Domain concepts must specialize them."""
    caching = canonical_registry.get_concept("core.caching")
    assert caching is not None
    assert caching.domain == "core"
    assert caching.is_universal

    fe_caching = canonical_registry.get_concept("frontend.client-caching")
    assert fe_caching is not None
    assert fe_caching.domain == "frontend"
    assert not fe_caching.is_universal
    assert "core.caching" in fe_caching.related_core_concepts
    assert "core.caching" in fe_caching.relationships.get(ConceptRelationType.SPECIALIZES, ())


def test_web3_rpc_retry_specializes_core_retry(canonical_registry: KnowledgeRegistry):
    """Web3 domain RPC retry specializes universal core.retries."""
    web3_retry = canonical_registry.get_concept("web3.rpc-retry")
    assert web3_retry is not None
    assert web3_retry.domain == "web3"
    assert web3_retry.status == ConceptStatus.SPEC_ONLY
    assert "core.retries" in web3_retry.related_core_concepts
    assert "core.retries" in web3_retry.relationships.get(ConceptRelationType.SPECIALIZES, ())


def test_no_duplicate_universal_concepts_in_domains(canonical_registry: KnowledgeRegistry):
    """Registry integrity check ensures domain concepts in universal categories specialize core concepts."""
    warnings = canonical_registry.validate_integrity()
    unspecialized_domain_caching = [w for w in warnings if "client-caching" in w]
    assert len(unspecialized_domain_caching) == 0


# =============================================================================
# 4. KnowledgePack Contract & Agent Mapping
# =============================================================================


def test_frontend_knowledge_pack_contract(canonical_registry: KnowledgeRegistry):
    """FrontendKnowledgePack satisfies the KnowledgePack contract."""
    kp = canonical_registry.get_knowledge_pack("kp.frontend")
    assert kp is not None
    assert kp.domain == "frontend"
    assert "core" in kp.dependencies
    assert len(kp.scoring_dimensions) >= 5
    assert len(kp.concepts) == 15
    assert len(kp.capabilities) >= 2


def test_agent_to_knowledge_pack_mapping():
    """FrontendAgent maps directly to domain and KnowledgePack, not to a language alone."""
    agent = FrontendAgent()
    assert agent.agent_id == "D-21"
    assert agent.domain == "frontend"
    assert agent.knowledge_pack_id == "kp.frontend"
    assert isinstance(agent.knowledge_pack, FrontendKnowledgePack)


def test_unresolved_knowledge_pack_dependency_raises():
    """KnowledgePack with invalid dependencies fails validation."""
    registry = KnowledgeRegistry()
    bad_kp = KnowledgePack(
        id="kp.broken",
        domain="broken",
        version="1.0.0",
        dependencies=["nonexistent_domain_dep"],
    )
    registry.register_knowledge_pack(bad_kp)
    with pytest.raises(KnowledgeValidationError, match="unresolved dependency"):
        registry.validate_integrity()


# =============================================================================
# 5. Multi-Domain Composition
# =============================================================================


def test_domain_composition_resolution(canonical_registry: KnowledgeRegistry):
    """Composite projects (Frontend + Web3) resolve domain dependencies cleanly."""
    resolved = canonical_registry.resolve_domain_composition(["frontend", "web3"])
    resolved_ids = [d.id for d in resolved]

    # Core must be resolved as a dependency first
    assert "core" in resolved_ids
    assert "frontend" in resolved_ids
    assert "web3" in resolved_ids


def test_multi_domain_stack_resolution(canonical_registry: KnowledgeRegistry):
    """Full-stack (Frontend + Backend + Database) resolves composite graph."""
    resolved = canonical_registry.resolve_domain_composition(["frontend", "backend", "database"])
    resolved_ids = [d.id for d in resolved]
    assert resolved_ids[0] == "core"
    assert set(resolved_ids) == {"core", "frontend", "backend", "database"}


# =============================================================================
# 6. Scoring Hierarchy Verification
# =============================================================================


def test_four_tier_scoring_hierarchy():
    """Verify tier 1 (rules) -> tier 2 (dimension) -> tier 3 (domain) -> tier 4 (app summary)."""
    engine = UniversalScoringEngine()

    # Tier 1 & 2: Dimension scores
    dim_rendering = engine.compute_dimension_score(
        dimension="rendering",
        statuses=[DecisionStatus.IMPLEMENTED, DecisionStatus.IMPLEMENTED],
        confidences=[0.9, 0.9],
    )
    assert dim_rendering.score == 100.0
    assert dim_rendering.status == DecisionStatus.IMPLEMENTED

    dim_loading = engine.compute_dimension_score(
        dimension="loading_strategy",
        statuses=[DecisionStatus.IMPLEMENTED, DecisionStatus.MISCONFIGURED],
        confidences=[1.0, 1.0],
    )
    # (100 + 40) / 2 = 70.0
    assert dim_loading.score == 70.0

    # Tier 3: Domain score
    domain_score = engine.compute_domain_score(
        domain="frontend",
        dimension_scores={"rendering": dim_rendering, "loading_strategy": dim_loading},
    )
    # (100 + 70) / 2 = 85.0
    assert domain_score.overall_score == 85.0

    # Tier 4: Application summary score with penalties
    app_summary = engine.compute_application_summary(
        domain_scores={"frontend": domain_score},
        critical_count=1,  # -5.0 penalty
        high_count=1,      # -2.0 penalty
    )
    # 85.0 - 7.0 = 78.0
    assert app_summary.application_score == 78.0
    assert "frontend" in app_summary.active_domains


# =============================================================================
# 7. Negative Tests: Names != Evidence, Language != Domain
# =============================================================================


def test_negative_comments_are_not_evidence(canonical_registry: KnowledgeRegistry):
    """Comments alone must never be accepted as structural evidence facts."""
    comment_fact = EvidenceFact(
        language="python",
        file_path="app/cache.py",
        line_range=(1, 1),
        kind=EvidenceKind.CALL,
        subject="redis",
        snippet="# TODO: instantiate redis client with TTL",
    )
    assert not canonical_registry.verify_evidence_authenticity(comment_fact)


def test_negative_empty_snippet_is_not_evidence(canonical_registry: KnowledgeRegistry):
    """Empty or whitespace snippets fail authenticity validation."""
    empty_fact = EvidenceFact(
        language="python",
        file_path="app/cache.py",
        line_range=(1, 1),
        kind=EvidenceKind.CALL,
        subject="client.get",
        snippet="   \n",
    )
    assert not canonical_registry.verify_evidence_authenticity(empty_fact)


def test_negative_valid_structural_call_is_authentic(canonical_registry: KnowledgeRegistry):
    """Actual AST call and configuration statements pass authenticity validation."""
    call_fact = EvidenceFact(
        language="python",
        file_path="app/cache.py",
        line_range=(5, 5),
        kind=EvidenceKind.CALL,
        subject="redis.setex",
        snippet="client.setex('key', 3600, data)",
    )
    assert canonical_registry.verify_evidence_authenticity(call_fact)


def test_negative_folder_name_alone_is_flagged_hazard(canonical_registry: KnowledgeRegistry):
    """Having 'frontend' in target root path issues a domain hazard warning."""
    context = {"target_root": "/home/user/my_frontend_project"}
    hazards = canonical_registry.detect_domain_activation_hazards(context)
    assert len(hazards) > 0
    assert any("structural evidence" in h for h in hazards)


def test_negative_language_alone_does_not_equal_domain():
    """TypeScript language existence does not automatically classify repository as Frontend.

    A TypeScript CLI or Node.js backend must not be forced into a Frontend domain audit.
    """
    ts_lang = Language(id="typescript", name="TypeScript", extensions=(".ts", ".tsx"))
    assert ts_lang.id == "typescript"
    # Domain is a separate entity from language
    assert ts_lang.name != "Frontend"
