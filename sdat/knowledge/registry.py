"""Knowledge Architecture Registry & Validation Engine.

Manages the registration, dependency graph, cross-referencing, and integrity
validation for Domains, Capabilities, Concepts, Rules, and KnowledgePacks.
"""

from __future__ import annotations

from typing import Any

from sdat.knowledge.models import (
    Capability,
    Concept,
    ConceptRelationType,
    ConceptStatus,
    Domain,
    DomainTier,
    KnowledgePack,
    Language,
    Rule,
    RuleApplicability,
)
from sdat.models import EvidenceFact, EvidenceKind


class KnowledgeValidationError(Exception):
    """Raised when knowledge architecture integrity invariants are violated."""


class KnowledgeRegistry:
    """Canonical registry and validation engine for system-design knowledge."""

    def __init__(self) -> None:
        self._languages: dict[str, Language] = {}
        self._domains: dict[str, Domain] = {}
        self._capabilities: dict[str, Capability] = {}
        self._concepts: dict[str, Concept] = {}
        self._rules: dict[str, Rule] = {}
        self._knowledge_packs: dict[str, KnowledgePack] = {}

    # ─────────────────────────────────────────────────────────────────────────
    # Registration Methods
    # ─────────────────────────────────────────────────────────────────────────

    def register_language(self, language: Language) -> None:
        """Register a supported programming language."""
        self._languages[language.id] = language

    def register_domain(self, domain: Domain) -> None:
        """Register an architectural domain."""
        self._domains[domain.id] = domain

    def register_capability(self, capability: Capability) -> None:
        """Register an observable behavioral capability."""
        self._capabilities[capability.id] = capability

    def register_concept(self, concept: Concept) -> None:
        """Register an architectural concept. Enforces global ID uniqueness."""
        if concept.concept_id in self._concepts:
            existing = self._concepts[concept.concept_id]
            if existing != concept:
                raise KnowledgeValidationError(
                    f"Duplicate concept ID registered: '{concept.concept_id}' "
                    f"(existing: {existing.name} in {existing.domain}, new: {concept.name} in {concept.domain})"
                )
        self._concepts[concept.concept_id] = concept

    def register_rule(self, rule: Rule) -> None:
        """Register an evaluation rule. Validates concept reference."""
        if rule.concept_id not in self._concepts:
            raise KnowledgeValidationError(
                f"Rule '{rule.rule_id}' references unknown concept_id: '{rule.concept_id}'"
            )
        self._rules[rule.rule_id] = rule

    def register_knowledge_pack(self, kp: KnowledgePack) -> None:
        """Register a domain KnowledgePack and its constituent elements."""
        for concept in kp.concepts:
            self.register_concept(concept)
        for capability in kp.capabilities:
            self.register_capability(capability)
        for rule in kp.rules:
            self.register_rule(rule)
        self._knowledge_packs[kp.id] = kp

    # ─────────────────────────────────────────────────────────────────────────
    # Lookup Methods
    # ─────────────────────────────────────────────────────────────────────────

    def get_domain(self, domain_id: str) -> Domain | None:
        return self._domains.get(domain_id)

    def get_concept(self, concept_id: str) -> Concept | None:
        return self._concepts.get(concept_id)

    def get_rule(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def get_knowledge_pack(self, kp_id: str) -> KnowledgePack | None:
        return self._knowledge_packs.get(kp_id)

    @property
    def all_concepts(self) -> list[Concept]:
        return list(self._concepts.values())

    @property
    def all_rules(self) -> list[Rule]:
        return list(self._rules.values())

    @property
    def all_domains(self) -> list[Domain]:
        return list(self._domains.values())

    @property
    def all_knowledge_packs(self) -> list[KnowledgePack]:
        return list(self._knowledge_packs.values())

    # ─────────────────────────────────────────────────────────────────────────
    # Validation & Invariant Enforcement
    # ─────────────────────────────────────────────────────────────────────────

    def validate_integrity(self) -> list[str]:
        """Perform full invariant verification across all registered knowledge.

        Returns:
            List of warning messages (empty if completely clean).
        Raises:
            KnowledgeValidationError if a fatal invariant is breached.
        """
        warnings: list[str] = []

        # 1. Rule -> Concept references
        for rule_id, rule in self._rules.items():
            if rule.concept_id not in self._concepts:
                raise KnowledgeValidationError(
                    f"Rule '{rule_id}' references non-existent concept '{rule.concept_id}'"
                )

        # 2. KnowledgePack dependencies
        for kp_id, kp in self._knowledge_packs.items():
            for dep in kp.dependencies:
                if dep not in self._domains and dep not in self._knowledge_packs:
                    raise KnowledgeValidationError(
                        f"KnowledgePack '{kp_id}' has unresolved dependency: '{dep}'"
                    )

        # 3. Universal Concept Deduplication Invariant
        # Universal concepts (caching, retries, etc.) must NOT be duplicated in domain folders
        # without explicit specialization of a core concept.
        universal_categories = {"caching", "resilience", "observability", "security", "concurrency", "idempotency"}
        for concept in self._concepts.values():
            if concept.domain != "core" and concept.category in universal_categories:
                has_specialization = (
                    ConceptRelationType.SPECIALIZES in concept.relationships
                    or len(concept.related_core_concepts) > 0
                )
                if not has_specialization:
                    warnings.append(
                        f"Domain concept '{concept.concept_id}' in category '{concept.category}' "
                        f"should specialize a universal core concept rather than creating an independent duplicate."
                    )

        # 4. Concept Relationship Target Validation
        for concept in self._concepts.values():
            for rel_type, targets in concept.relationships.items():
                for target_id in targets:
                    if target_id not in self._concepts:
                        warnings.append(
                            f"Concept '{concept.concept_id}' relationship '{rel_type.value}' "
                            f"references unregistered target '{target_id}'"
                        )

        return warnings

    # ─────────────────────────────────────────────────────────────────────────
    # Domain Composition & Negative Verification Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def resolve_domain_composition(self, active_domain_ids: list[str]) -> list[Domain]:
        """Resolve a composite list of active domains including required dependencies.

        Supports multi-domain composition:
        e.g., [frontend, web3] -> [core, frontend, web3]
        e.g., [frontend, backend, database] -> [core, backend, database, frontend]
        """
        resolved_ids: list[str] = []
        visited: set[str] = set()

        def visit(d_id: str) -> None:
            if d_id in visited:
                return
            visited.add(d_id)
            domain = self._domains.get(d_id)
            if domain:
                for dep in domain.dependencies:
                    visit(dep)
                resolved_ids.append(d_id)

        for d_id in active_domain_ids:
            visit(d_id)

        return [self._domains[d_id] for d_id in resolved_ids if d_id in self._domains]

    @staticmethod
    def verify_evidence_authenticity(fact: EvidenceFact) -> bool:
        """Verify that an EvidenceFact represents concrete structural/behavioral execution.

        Negative Rule:
        - Symbol names, comments, and bare identifier tokens alone are WEAK HINTS,
          never conclusive architectural proof.
        - KnowledgePack existence is never proof of target implementation.
        - Outbound research notes are external context, never target implementation proof.
        """
        if not fact.snippet or not fact.snippet.strip():
            return False

        stripped = fact.snippet.strip()
        # Comments alone do not constitute evidence
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            return False

        # Bare variable name without call, import, or configuration
        if fact.kind not in (
            EvidenceKind.IMPORT,
            EvidenceKind.CALL,
            EvidenceKind.INSTANTIATION,
            EvidenceKind.CONFIG_KEY,
            EvidenceKind.INHERITANCE,
            EvidenceKind.DECORATOR,
            EvidenceKind.FRAMEWORK_MARKER,
            EvidenceKind.CONTROL_FLOW,
            EvidenceKind.ANNOTATION,
            EvidenceKind.SCHEMA_DEF,
        ):
            return False

        return True

    @staticmethod
    def detect_domain_activation_hazards(context: dict[str, Any]) -> list[str]:
        """Detect invalid domain activation patterns.

        Invariants:
        1. Function name alone must not activate a domain.
        2. Filename alone must not activate a domain.
        3. Language alone must not activate a domain (e.g. TypeScript != Frontend, Python != Backend).
        """
        hazards: list[str] = []
        target_root = str(context.get("target_root", "")).lower()

        # Filename heuristics check
        if any(h in target_root for h in ("backend", "frontend", "web3", "ml")):
            hazards.append(
                "Warning: target root directory name contains domain keyword; "
                "domain classification must be derived from structural evidence, not folder names."
            )
        return hazards


def build_canonical_registry() -> KnowledgeRegistry:
    """Instantiate and populate the canonical SDAT KnowledgeRegistry."""
    registry = KnowledgeRegistry()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Register Languages
    # ─────────────────────────────────────────────────────────────────────────
    languages = [
        Language(id="python", name="Python", extensions=(".py",)),
        Language(id="typescript", name="TypeScript", extensions=(".ts", ".tsx")),
        Language(id="javascript", name="JavaScript", extensions=(".js", ".jsx", ".mjs")),
        Language(id="go", name="Go", extensions=(".go",)),
        Language(id="rust", name="Rust", extensions=(".rs",)),
        Language(id="c_cpp", name="C/C++", extensions=(".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")),
        Language(id="php", name="PHP", extensions=(".php",)),
        Language(id="java", name="Java", extensions=(".java",)),
        Language(id="kotlin", name="Kotlin", extensions=(".kt", ".kts")),
    ]
    for lang in languages:
        registry.register_language(lang)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Register Domains
    # ─────────────────────────────────────────────────────────────────────────
    domains = [
        Domain(
            id="core",
            name="Core System Design",
            description="Universal system-design principles applicable to all distributed systems.",
            tier=DomainTier.FOUNDATION,
            dependencies=(),
            scoring_dimensions=("reliability", "scalability", "performance", "security", "observability"),
        ),
        Domain(
            id="frontend",
            name="Frontend Architecture",
            description="Client-side rendering, routing, loading, component trees, and browser performance.",
            tier=DomainTier.WORKLOAD,
            dependencies=("core",),
            scoring_dimensions=("rendering", "loading_strategy", "navigation_routing", "runtime_performance", "accessibility"),
        ),
        Domain(
            id="backend",
            name="Backend Architecture",
            description="API design, microservices, background queues, and request lifecycle.",
            tier=DomainTier.WORKLOAD,
            dependencies=("core",),
            scoring_dimensions=("api_design", "resilience", "concurrency", "security"),
        ),
        Domain(
            id="database",
            name="Database Architecture",
            description="Data persistence, indexing, migrations, query performance, and connection management.",
            tier=DomainTier.WORKLOAD,
            dependencies=("core",),
            scoring_dimensions=("schema_design", "indexing", "migrations", "data_lifecycle"),
        ),
        Domain(
            id="devops",
            name="Deployment & DevOps",
            description="CI/CD, containerization, orchestration, and infrastructure as code.",
            tier=DomainTier.WORKLOAD,
            dependencies=("core",),
            scoring_dimensions=("automation", "containerization", "infrastructure"),
        ),
        Domain(
            id="networking",
            name="Networking & Ingress",
            description="Reverse proxies, API gateways, load balancers, and transport protocols.",
            tier=DomainTier.WORKLOAD,
            dependencies=("core",),
            scoring_dimensions=("traffic_management", "protocol_efficiency"),
        ),
        Domain(
            id="web3",
            name="Web3 & Blockchain",
            description="Chain-neutral Web3 principles: transaction lifecycle, RPC resilience, key safety.",
            tier=DomainTier.SPECIALIZED,
            dependencies=("core",),
            scoring_dimensions=("transaction_lifecycle", "rpc_resilience", "key_management"),
            status=ConceptStatus.SPEC_ONLY,
        ),
        Domain(
            id="machine_learning",
            name="Machine Learning Systems (Legacy)",
            description="ML pipelines, model registries, feature stores, and inference serving.",
            tier=DomainTier.SPECIALIZED,
            dependencies=("core",),
            scoring_dimensions=("pipeline_reproducibility", "feature_engineering", "model_management"),
            status=ConceptStatus.SPEC_ONLY,
        ),
        Domain(
            id="ml",
            name="Machine Learning Systems",
            description="ML pipelines, numerical stability, optimization, and serialization safety.",
            tier=DomainTier.SPECIALIZED,
            dependencies=("core",),
            scoring_dimensions=("mathematical_numerical_stability", "training_optimization_hygiene", "reproducibility_and_safety"),
            status=ConceptStatus.ACTIVE,
        ),
        Domain(
            id="nlp",
            name="Natural Language Processing",
            description="Tokenization pipelines, tensor contracts, attention masking, and sequence length budgets.",
            tier=DomainTier.SPECIALIZED,
            dependencies=("core", "ml"),
            scoring_dimensions=("transformer_tensor_soundness", "tokenization_and_sequence_contract"),
            status=ConceptStatus.ACTIVE,
        ),
        Domain(
            id="cross_domain",
            name="Cross-Domain Integration",
            description="Cross-cutting concepts bridging multiple architectural domains.",
            tier=DomainTier.WORKLOAD,
            dependencies=("core",),
            scoring_dimensions=("integration_hygiene",),
        ),
    ]
    for d in domains:
        registry.register_domain(d)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Register Universal Core Concepts
    # ─────────────────────────────────────────────────────────────────────────
    core_concepts = [
        Concept(
            concept_id="core.caching",
            domain="core",
            name="Caching Strategy",
            description="Caching reduces latency and datastore load via high-speed in-memory or distributed key-value stores.",
            category="caching",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT, EvidenceKind.CONFIG_KEY),
            question="Does the system implement a caching layer with explicit invalidation and TTL?",
            tags=("cache", "redis", "memcached", "lru", "ttl"),
        ),
        Concept(
            concept_id="core.resilience",
            domain="core",
            name="Resilience & Fault Tolerance",
            description="System degrades gracefully under failure using isolation, circuit breakers, and fallbacks.",
            category="resilience",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            question="Are external dependencies wrapped in fault-tolerant isolation patterns?",
            tags=("resilience", "circuit-breaker", "fallback", "bulkhead"),
        ),
        Concept(
            concept_id="core.retries",
            domain="core",
            name="Retry with Backoff & Jitter",
            description="Transient failures are retried using exponential backoff and randomized jitter to prevent storms.",
            category="resilience",
            related_core_concepts=("core.resilience",),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            question="Do retry policies use exponential backoff and jitter?",
            tags=("retry", "backoff", "jitter", "tenacity"),
        ),
        Concept(
            concept_id="core.timeouts",
            domain="core",
            name="Request & Connection Timeouts",
            description="Explicit connect, read, and execution timeouts bound waiting duration on external I/O.",
            category="resilience",
            related_core_concepts=("core.resilience",),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            question="Are connect and read timeouts configured on all network and database operations?",
            tags=("timeout", "deadline", "read_timeout"),
        ),
        Concept(
            concept_id="core.idempotency",
            domain="core",
            name="Idempotency Guarantees",
            description="Mutating requests can be safely retried without duplicate side-effects.",
            category="idempotency",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            question="Are state-mutating requests protected by idempotency keys or idempotent state transitions?",
            tags=("idempotency", "deduplication", "idempotency-key"),
        ),
        Concept(
            concept_id="core.concurrency",
            domain="core",
            name="Bounded Concurrency & Workpools",
            description="Concurrency is strictly bounded by worker pools and backpressure mechanisms.",
            category="concurrency",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            question="Are concurrent operations executed within bounded worker pools to prevent resource exhaustion?",
            tags=("concurrency", "threadpool", "worker", "semaphore", "backpressure"),
        ),
        Concept(
            concept_id="core.observability",
            domain="core",
            name="Structured Observability",
            description="Telemetry capturing logs, metrics, traces, and operational diagnostics.",
            category="observability",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            question="Does the system emit structured logs, metrics, and traces?",
            tags=("logging", "metrics", "tracing", "opentelemetry"),
        ),
        Concept(
            concept_id="core.security",
            domain="core",
            name="Security Fundamentals",
            description="Defense-in-depth: authentication, authorization, secret hygiene, and input sanitization.",
            category="security",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY, EvidenceKind.IMPORT),
            question="Are security boundaries, input sanitization, and secret protection enforced?",
            tags=("auth", "security", "sanitization", "secrets"),
        ),
        Concept(
            concept_id="core.performance",
            domain="core",
            name="System Performance",
            description="Latency, throughput, resource efficiency, and asynchronous non-blocking processing.",
            category="performance",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            question="Is I/O asynchronous and non-blocking with efficient resource utilization?",
            tags=("performance", "async", "latency", "throughput"),
        ),
    ]
    for c in core_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Register Frontend Domain Concepts (Specializing Core where applicable)
    # ─────────────────────────────────────────────────────────────────────────
    frontend_concepts = [
        Concept(
            concept_id="frontend.rendering",
            domain="frontend",
            name="Rendering Architecture",
            description="Client/Server rendering strategies (SSR, SSG, CSR, Streaming) and boundary isolation.",
            category="rendering",
            applicable_capabilities=("cap.frontend.react_tree", "cap.frontend.ssr_engine"),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT, EvidenceKind.FRAMEWORK_MARKER),
            tags=("ssr", "ssg", "csr", "hydration", "react", "nextjs"),
        ),
        Concept(
            concept_id="frontend.routing",
            domain="frontend",
            name="Routing Architecture",
            description="Route boundaries, code-split entrypoints, and fallback 404 handlers.",
            category="navigation_routing",
            applicable_capabilities=("cap.frontend.client_router",),
            required_evidence_kinds=(EvidenceKind.FRAMEWORK_MARKER, EvidenceKind.CALL),
            tags=("router", "route", "not_found", "boundary"),
        ),
        Concept(
            concept_id="frontend.loading",
            domain="frontend",
            name="Loading Strategy & Code Splitting",
            description="Dynamic imports, code-splitting, lazy loading, and progressive Suspense fallbacks.",
            category="loading_strategy",
            applicable_capabilities=("cap.frontend.dynamic_import",),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("dynamic_import", "lazy", "suspense", "code_splitting"),
        ),
        Concept(
            concept_id="frontend.navigation",
            domain="frontend",
            name="Navigation Experience",
            description="Client-side prefetching, layout preservation, and smooth route transitions.",
            category="navigation_routing",
            applicable_capabilities=("cap.frontend.client_router",),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("prefetch", "link", "transition"),
        ),
        Concept(
            concept_id="frontend.runtime-performance",
            domain="frontend",
            name="Frontend Runtime Performance",
            description="DOM mutation efficiency, scroll performance, frame stability, and Core Web Vitals.",
            category="runtime_performance",
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("vitals", "lcp", "cls", "inp", "frame_rate"),
        ),
        Concept(
            concept_id="frontend.component-architecture",
            domain="frontend",
            name="Component Architecture & Tree Depth",
            description="Component encapsulation, hierarchy depth, and prop drilling mitigation.",
            category="rendering",
            applicable_capabilities=("cap.frontend.react_tree",),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("components", "atomic", "props", "hierarchy"),
        ),
        Concept(
            concept_id="frontend.dom-architecture",
            domain="frontend",
            name="DOM Architecture & Virtualization",
            description="Virtualization for unbounded lists, shallow DOM trees, and memory retention prevention.",
            category="rendering",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("virtualization", "dom", "table", "infinite_scroll"),
        ),
        Concept(
            concept_id="frontend.responsive-design",
            domain="frontend",
            name="Responsive Design & Viewports",
            description="Viewport meta configurations, fluid media breakpoints, and adaptive layouts.",
            category="rendering",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("viewport", "responsive", "media_query", "mobile"),
        ),
        Concept(
            concept_id="frontend.state-management",
            domain="frontend",
            name="State Management Architecture",
            description="Separation between server cache and client state; atomicity and selector memoization.",
            category="loading_strategy",
            applicable_capabilities=("cap.frontend.state_store",),
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("redux", "zustand", "context", "state", "recoil"),
        ),
        Concept(
            concept_id="frontend.data-fetching",
            domain="frontend",
            name="Client Data Fetching",
            description="Data synchronization libraries, deduped network queries, and waterfall prevention.",
            category="loading_strategy",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("swr", "react-query", "tanstack", "fetch"),
        ),
        Concept(
            concept_id="frontend.client-caching",
            domain="frontend",
            name="Client-Side Caching & Stale-While-Revalidate",
            description="Browser HTTP caching, service worker offline storage, and stale-while-revalidate data layers.",
            category="caching",
            related_core_concepts=("core.caching",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.caching",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("swr", "cache-control", "service-worker", "localstorage"),
        ),
        Concept(
            concept_id="frontend.asset-architecture",
            domain="frontend",
            name="Asset Architecture & Optimization",
            description="Modern image formats (WebP/AVIF), font display swap, and media compression.",
            category="loading_strategy",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("images", "webp", "avif", "fonts", "assets"),
        ),
        Concept(
            concept_id="frontend.accessibility",
            domain="frontend",
            name="Accessibility & Assistive Tech",
            description="Semantic HTML, ARIA compliance, keyboard navigability, and color contrast.",
            category="accessibility",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("a11y", "aria", "semantic", "keyboard"),
        ),
        Concept(
            concept_id="frontend.security",
            domain="frontend",
            name="Frontend Security & Content Policy",
            description="CSP headers, XSS prevention, sanitized markup injection, and secret leak defense.",
            category="security",
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("csp", "xss", "dangerouslysetinnerhtml", "sanitize"),
        ),
        Concept(
            concept_id="frontend.browser-runtime",
            domain="frontend",
            name="Browser Runtime Observability",
            description="Client-side error boundary reporting, unhandled rejection capture, and RUM metrics.",
            category="runtime_performance",
            related_core_concepts=("core.observability",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.observability",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("error-boundary", "sentry", "rum", "telemetry"),
        ),
    ]
    for c in frontend_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. Register Database Domain Concepts
    # ─────────────────────────────────────────────────────────────────────────
    database_concepts = [
        Concept(
            concept_id="data.backup",
            domain="database",
            name="Backup & Recovery Strategy",
            description="Automated snapshots, point-in-time recovery (PITR), and disaster recovery plans.",
            category="database",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("backup", "snapshot", "pitr", "pg_dump"),
        ),
        Concept(
            concept_id="data.indexing",
            domain="database",
            name="Database Indexing Strategy",
            description="B-tree, composite, and covering indexes on high-cardinality queried columns.",
            category="database",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("index", "unique_index", "b-tree", "composite"),
        ),
        Concept(
            concept_id="data.migrations",
            domain="database",
            name="Database Migrations",
            description="Deterministic, versioned schema migrations (Alembic, Flyway, Prisma Migrate).",
            category="database",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("migrations", "alembic", "flyway", "liquibase"),
        ),
        Concept(
            concept_id="data.orm",
            domain="database",
            name="ORM / Data Mapper",
            description="Query builders and ORMs preventing raw SQL injection and managing schema mappings.",
            category="database",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("orm", "sqlalchemy", "prisma", "typeorm", "hibernate"),
        ),
    ]
    for c in database_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Register DevOps Domain Concepts
    # ─────────────────────────────────────────────────────────────────────────
    devops_concepts = [
        Concept(
            concept_id="deployment.ci-cd",
            domain="devops",
            name="CI/CD Automation Pipeline",
            description="Automated continuous integration and deployment pipelines with testing gates.",
            category="devops",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY,),
            tags=("ci-cd", "github-actions", "gitlab-ci", "jenkins"),
        ),
        Concept(
            concept_id="deployment.containers",
            domain="devops",
            name="Containerization Parity",
            description="Docker container definitions ensuring build reproducibility and environment parity.",
            category="devops",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY,),
            tags=("docker", "container", "dockerfile"),
        ),
        Concept(
            concept_id="deployment.healthchecks",
            domain="devops",
            name="Liveness & Readiness Healthchecks",
            description="Dedicated /healthz and /readyz probes for container and orchestrator lifecycles.",
            category="devops",
            required_evidence_kinds=(EvidenceKind.FRAMEWORK_MARKER, EvidenceKind.CALL),
            tags=("health", "liveness", "readiness", "probe"),
        ),
        Concept(
            concept_id="deployment.iaac",
            domain="devops",
            name="Infrastructure as Code",
            description="Declarative infrastructure definitions via Terraform, CloudFormation, or Pulumi.",
            category="devops",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY,),
            tags=("terraform", "cloudformation", "pulumi", "iac"),
        ),
        Concept(
            concept_id="deployment.orchestration",
            domain="devops",
            name="Container Orchestration",
            description="Kubernetes, ECS, or Nomad manifests for auto-scaling and declarative reconciliation.",
            category="devops",
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY,),
            tags=("kubernetes", "helm", "k8s", "ecs"),
        ),
    ]
    for c in devops_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Register Web3 / Blockchain Concepts (Spec Only, Chain-Neutral)
    # ─────────────────────────────────────────────────────────────────────────
    web3_concepts = [
        Concept(
            concept_id="web3.transaction-lifecycle",
            domain="web3",
            name="Web3 Transaction Lifecycle Management",
            description="Deterministic gas estimation, nonce tracking, receipt polling, and reorg protection.",
            category="web3",
            status=ConceptStatus.SPEC_ONLY,
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("web3", "transaction", "nonce", "receipt", "gas"),
        ),
        Concept(
            concept_id="web3.rpc-retry",
            domain="web3",
            name="RPC Provider Failover & Retry",
            description="Multi-endpoint JSON-RPC fallback with exponential backoff and rate limit handling.",
            category="web3",
            status=ConceptStatus.SPEC_ONLY,
            related_core_concepts=("core.retries", "core.resilience"),
            relationships={ConceptRelationType.SPECIALIZES: ("core.retries",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("rpc", "failover", "provider", "infura", "alchemy"),
        ),
        Concept(
            concept_id="web3.key-management",
            domain="web3",
            name="Non-Custodial Key Hygiene",
            description="Zero-knowledge private key isolation; avoidance of hardcoded mnemonics or raw seeds.",
            category="web3",
            status=ConceptStatus.SPEC_ONLY,
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("private_key", "mnemonic", "signer", "kms", "vault"),
        ),
    ]
    for c in web3_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Register Machine Learning & NLP Concepts (Stage-1 Active)
    # ─────────────────────────────────────────────────────────────────────────
    ml_concepts = [
        Concept(
            concept_id="ml.pipeline",
            domain="machine_learning",
            name="Machine Learning Training & Pipeline Lifecycle",
            description="Deterministic, versioned ML training pipelines with reproducible artifact lineage.",
            category="machine_learning",
            status=ConceptStatus.SPEC_ONLY,
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("ml", "pipeline", "lineage", "training"),
        ),
        Concept(
            concept_id="ml.model-registry",
            domain="machine_learning",
            name="Model Registry & Artifact Lineage",
            description="Model tracking, metric logging, and versioned weight artifact registries.",
            category="machine_learning",
            status=ConceptStatus.SPEC_ONLY,
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("model-registry", "mlflow", "wandb", "weights"),
        ),
        Concept(
            concept_id="ml.mathematical-correctness",
            domain="ml",
            name="Mathematical & Numerical Correctness in ML",
            description="Logit vs probability compatibility and numerically stable log-sum-exp formulations.",
            category="ml-ai",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.INSTANTIATION),
            tags=("math", "numerical-stability", "loss", "logits"),
        ),
        Concept(
            concept_id="ml.optimization-hygiene",
            domain="ml",
            name="Training Loop & Optimization Hygiene",
            description="Orderly synchronization between learning rate schedulers and optimizer updates.",
            category="ml-ai",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONTROL_FLOW),
            tags=("optimization", "scheduler", "optimizer", "training"),
        ),
        Concept(
            concept_id="ml.serialization-safety",
            domain="ml",
            name="Model Artifact Serialization & Deserialization Safety",
            description="Safetensors and weights_only security verification against RCE attacks.",
            category="security",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("security", "pickle", "safetensors", "torch.load"),
        ),
        Concept(
            concept_id="nlp.tensor-contracts",
            domain="nlp",
            name="Transformer Tensor Contracts & Dimensional Integrity",
            description="Attention head dimension divisibility (d_model % n_heads == 0) and projection contracts.",
            category="nlp",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.INHERITANCE, EvidenceKind.CALL),
            tags=("transformer", "tensor", "attention", "dimension"),
        ),
        Concept(
            concept_id="nlp.attention-masking",
            domain="nlp",
            name="Attention Masking & Numerical Probability Soundness",
            description="Negative masking constants before softmax to eliminate non-zero attention mass.",
            category="nlp",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONTROL_FLOW),
            tags=("attention", "mask", "softmax", "probability"),
        ),
        Concept(
            concept_id="nlp.tokenization-pipeline",
            domain="nlp",
            name="NLP Tokenization & Input Normalization",
            description="Deterministic vocabulary mapping, truncation, padding, and embedding matrix synchronization.",
            category="nlp",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.DEPENDS_ON: ("ml.mathematical-correctness",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("nlp", "tokenization", "huggingface", "tiktoken"),
        ),
        Concept(
            concept_id="nlp.sequence-budget",
            domain="nlp",
            name="Sequence Length Budget & Context Boundaries",
            description="Bounding sequence length and enforcing truncation to prevent memory exhaustion.",
            category="nlp",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("sequence", "truncation", "max_length", "context"),
        ),
    ]
    for c in ml_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Register Cross-Domain Concepts
    # ─────────────────────────────────────────────────────────────────────────
    cross_concepts = [
        Concept(
            concept_id="streaming.message-broker",
            domain="cross_domain",
            name="Message Broker Decoupling",
            description="Asynchronous publish/subscribe message broker (Kafka, RabbitMQ, Redis Streams).",
            category="cross_domain",
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("kafka", "rabbitmq", "pubsub", "broker"),
        ),
        Concept(
            concept_id="compliance.audit-log",
            domain="cross_domain",
            name="Immutable Audit Logging",
            description="Tamper-evident, structured audit trails for sensitive state mutations.",
            category="cross_domain",
            related_core_concepts=("core.observability", "core.security"),
            relationships={ConceptRelationType.SPECIALIZES: ("core.observability",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("audit", "soc2", "compliance", "immutable"),
        ),
    ]
    for c in cross_concepts:
        registry.register_concept(c)

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Register Frontend KnowledgePack
    # ─────────────────────────────────────────────────────────────────────────
    frontend_kp = KnowledgePack(
        id="kp.frontend",
        domain="frontend",
        version="1.0.0",
        concepts=frontend_concepts,
        capabilities=[
            Capability(
                id="cap.frontend.react_tree",
                name="React Component Hierarchy",
                domain="frontend",
                description="Observable React component trees and JSX elements.",
                detection_evidence_kinds=(EvidenceKind.IMPORT, EvidenceKind.CALL),
                activated_concepts=("frontend.rendering", "frontend.component-architecture"),
            ),
            Capability(
                id="cap.frontend.client_router",
                name="Client-Side Routing",
                domain="frontend",
                description="Observable client-side router or file-system route hierarchy.",
                detection_evidence_kinds=(EvidenceKind.FRAMEWORK_MARKER, EvidenceKind.CALL),
                activated_concepts=("frontend.routing", "frontend.navigation"),
            ),
        ],
        dependencies=["core"],
        scoring_dimensions=[
            "rendering",
            "loading_strategy",
            "navigation_routing",
            "runtime_performance",
            "accessibility",
        ],
        recommendations={
            "frontend.rendering": "Adopt SSR/SSG for content-heavy or public routes to optimize initial paint and SEO.",
            "frontend.loading": "Employ dynamic imports and Suspense boundaries for heavy visual and 3D components.",
            "frontend.client-caching": "Utilize SWR or TanStack Query to deduplicate network requests with stale-while-revalidate.",
        },
    )
    registry.register_knowledge_pack(frontend_kp)

    # ─────────────────────────────────────────────────────────────────────────
    # 11. Register Backend Concepts & KnowledgePack
    # ─────────────────────────────────────────────────────────────────────────
    from sdat.backend.knowledge_pack import BackendKnowledgePack

    backend_concepts = [
        Concept(
            concept_id="backend.api-architecture",
            domain="backend",
            name="Backend API Architecture",
            description="REST, RPC, and GraphQL routing, controllers, and response envelopes.",
            category="api",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.DECORATOR, EvidenceKind.CALL),
            tags=("rest", "rpc", "routing", "controller"),
        ),
        Concept(
            concept_id="backend.request-lifecycle",
            domain="backend",
            name="Request Lifecycle & Layer Separation",
            description="Separation between transport handlers, service domain logic, and repositories.",
            category="request_lifecycle",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.ARCHITECTURE_PATTERN),
            tags=("middleware", "lifecycle", "layers", "controller", "service"),
        ),
        Concept(
            concept_id="backend.service-boundaries",
            domain="backend",
            name="Service Boundaries & Modularity",
            description="Service coupling, domain modularity, and dependency boundaries.",
            category="architecture",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.ARCHITECTURE_PATTERN, EvidenceKind.IMPORT),
            tags=("modularity", "boundaries", "coupling", "microservices"),
        ),
        Concept(
            concept_id="backend.authentication",
            domain="backend",
            name="Backend Authentication Flow",
            description="Authentication middleware, JWT/session verification, and credential handling.",
            category="security",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("auth", "jwt", "session", "middleware"),
        ),
        Concept(
            concept_id="backend.authorization",
            domain="backend",
            name="Backend Authorization & Access Control",
            description="Role and permission enforcement at sensitive route endpoints.",
            category="security",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.DECORATOR),
            tags=("rbac", "abac", "permissions", "roles"),
        ),
        Concept(
            concept_id="backend.input-validation",
            domain="backend",
            name="Input Validation & Schema Boundaries",
            description="Schema validation and sanitization of incoming payloads at API ingress.",
            category="security",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.SCHEMA_DEF, EvidenceKind.CALL),
            tags=("validation", "pydantic", "zod", "schema"),
        ),
        Concept(
            concept_id="backend.error-handling",
            domain="backend",
            name="Structured Error Handling & Exception Containment",
            description="Centralized exception filters and uniform error response envelopes.",
            category="reliability",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.CONTROL_FLOW, EvidenceKind.CALL),
            tags=("exceptions", "rfc7807", "error_handling"),
        ),
        Concept(
            concept_id="backend.timeout-management",
            domain="backend",
            name="Timeout Management & Bounded Execution",
            description="Explicit bounded timeouts on HTTP clients, DB connections, and RPC calls.",
            category="resilience",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.timeouts",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.timeouts",)},
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("timeout", "deadlines", "cancellation"),
        ),
        Concept(
            concept_id="backend.retry-architecture",
            domain="backend",
            name="Retry Architecture & Backoff Safety",
            description="Exponential backoff with full jitter and capped retry attempts.",
            category="resilience",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.retries",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.retries",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.DECORATOR),
            tags=("retries", "backoff", "jitter", "storm"),
        ),
        Concept(
            concept_id="backend.idempotency",
            domain="backend",
            name="Idempotency & Deduplication",
            description="Idempotency keys and duplicate request suppression on state mutations.",
            category="reliability",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.idempotency",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.idempotency",)},
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("idempotency", "deduplication", "mutation"),
        ),
        Concept(
            concept_id="backend.rate-limiting",
            domain="backend",
            name="Rate Limiting & Abuse Prevention",
            description="Ingress rate limiting and quota enforcement via token or leaky buckets.",
            category="scalability",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.resilience",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.resilience",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("rate_limiting", "token_bucket", "quota"),
        ),
        Concept(
            concept_id="backend.caching",
            domain="backend",
            name="Backend Caching & TTL Invalidation",
            description="In-memory or distributed cache usage with explicit TTL and invalidation.",
            category="caching",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.caching",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.caching",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("cache", "redis", "ttl", "invalidation"),
        ),
        Concept(
            concept_id="backend.async-processing",
            domain="backend",
            name="Asynchronous Task Processing",
            description="Non-blocking event loop execution and coroutine concurrency.",
            category="concurrency",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.concurrency",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.concurrency",)},
            required_evidence_kinds=(EvidenceKind.ASYNC_PATTERN, EvidenceKind.CALL),
            tags=("async", "await", "event_loop", "coroutines"),
        ),
        Concept(
            concept_id="backend.background-jobs",
            domain="backend",
            name="Background Jobs & Worker Queues",
            description="Message broker job queuing, distributed workers, and consumer concurrency.",
            category="concurrency",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.concurrency",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.concurrency",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("celery", "kafka", "rabbitmq", "bullmq", "workers"),
        ),
        Concept(
            concept_id="backend.database-interaction",
            domain="backend",
            name="Database Interaction & Parameterized Access",
            description="Parameterized queries and ORM mappings to prevent injection vulnerabilities.",
            category="performance",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.DB_QUERY, EvidenceKind.CALL),
            tags=("sql", "orm", "parameterized", "injection"),
        ),
        Concept(
            concept_id="backend.connection-pooling",
            domain="backend",
            name="Database Connection Pooling",
            description="Bounded database connection pool sizing and lifecycle management.",
            category="performance",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.CONFIG_KEY, EvidenceKind.CALL),
            tags=("pool", "connection_pool", "pool_size"),
        ),
        Concept(
            concept_id="backend.external-service-integration",
            domain="backend",
            name="External Service Client Isolation",
            description="Dedicated client adapters and isolation for third-party API dependencies.",
            category="resilience",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.resilience",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.resilience",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.IMPORT),
            tags=("http_client", "third_party", "adapter"),
        ),
        Concept(
            concept_id="backend.transaction-boundaries",
            domain="backend",
            name="Transaction Boundaries & Scope Containment",
            description="Atomic database transaction blocks without external network latency inside.",
            category="performance",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.DB_QUERY, EvidenceKind.CONTROL_FLOW),
            tags=("transaction", "atomic", "commit", "rollback"),
        ),
        Concept(
            concept_id="backend.concurrency",
            domain="backend",
            name="Concurrency & Non-Blocking Execution",
            description="Thread safety, goroutines, mutex synchronization, and race avoidance.",
            category="concurrency",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.concurrency",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.concurrency",)},
            required_evidence_kinds=(EvidenceKind.CONCURRENCY, EvidenceKind.CALL),
            tags=("threads", "mutex", "goroutines", "race_condition"),
        ),
        Concept(
            concept_id="backend.resource-lifecycle",
            domain="backend",
            name="Resource Lifecycle & Disposal",
            description="Disposal of open streams, sockets, and graceful shutdown signal handling.",
            category="performance",
            status=ConceptStatus.ACTIVE,
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONTROL_FLOW),
            tags=("lifecycle", "shutdown", "cleanup", "disposal"),
        ),
        Concept(
            concept_id="backend.observability",
            domain="backend",
            name="Backend Observability & Telemetry",
            description="Structured JSON logging, metrics collection, and request correlation IDs.",
            category="observability",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.observability",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.observability",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONFIG_KEY),
            tags=("logging", "metrics", "tracing", "correlation_id"),
        ),
        Concept(
            concept_id="backend.security",
            domain="backend",
            name="Backend Security & Secret Hygiene",
            description="Vault/env secret resolution, HTTPS/TLS enforcement, and CORS protections.",
            category="security",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.security",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.security",)},
            required_evidence_kinds=(EvidenceKind.ENV_VAR, EvidenceKind.CONFIG_KEY),
            tags=("secrets", "vault", "env", "tls"),
        ),
        Concept(
            concept_id="backend.performance",
            domain="backend",
            name="Backend Execution Performance & Non-Blocking I/O",
            description="Efficient request serialization, non-blocking I/O, and waterfall elimination.",
            category="performance",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.ASYNC_PATTERN, EvidenceKind.CALL),
            tags=("performance", "non_blocking", "serialization"),
        ),
        Concept(
            concept_id="backend.scalability",
            domain="backend",
            name="Statelessness & Horizontal Scalability",
            description="Shared-nothing stateless server design for seamless horizontal scaling.",
            category="scalability",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.performance",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.performance",)},
            required_evidence_kinds=(EvidenceKind.ARCHITECTURE_PATTERN, EvidenceKind.CONFIG_KEY),
            tags=("stateless", "horizontal_scaling", "shared_nothing"),
        ),
        Concept(
            concept_id="backend.resilience",
            domain="backend",
            name="Backend Resilience & Graceful Degradation",
            description="Circuit breaking, bulkheads, health probes, and graceful degradation.",
            category="resilience",
            status=ConceptStatus.ACTIVE,
            related_core_concepts=("core.resilience",),
            relationships={ConceptRelationType.SPECIALIZES: ("core.resilience",)},
            required_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.CONTROL_FLOW),
            tags=("circuit_breaker", "bulkhead", "degradation", "resilience"),
        ),
    ]

    for c in backend_concepts:
        registry.register_concept(c)

    for rule in BackendKnowledgePack.RULES:
        registry.register_rule(
            Rule(
                rule_id=rule.id,
                concept_id=rule.concept_id,
                name=rule.name,
                description=rule.description,
                applicability=RuleApplicability(domains=("backend",)),
                required_evidence=(),
                evaluation_logic=f"Deterministic evaluation for {rule.id}",
                severity=rule.priority,
                remediation_guidance=rule.remediation_guidance,
            )
        )

    backend_kp = KnowledgePack(
        id="kp.backend",
        domain="backend",
        version="1.0.0",
        concepts=backend_concepts,
        capabilities=[
            Capability(
                id="cap.backend.api_router",
                name="Backend API Routing & Handlers",
                domain="backend",
                description="Observable backend endpoints, route decorators, and HTTP/RPC handlers.",
                detection_evidence_kinds=(EvidenceKind.DECORATOR, EvidenceKind.CALL),
                activated_concepts=("backend.api-architecture", "backend.request-lifecycle"),
            ),
            Capability(
                id="cap.backend.db_access",
                name="Database Interaction & ORM",
                domain="backend",
                description="Observable database queries, models, or connection pools.",
                detection_evidence_kinds=(EvidenceKind.DB_QUERY, EvidenceKind.CALL),
                activated_concepts=("backend.database-interaction", "backend.connection-pooling"),
            ),
        ],
        dependencies=["core"],
        scoring_dimensions=[
            "api_architecture",
            "request_lifecycle",
            "data_interaction",
            "reliability_resilience",
            "security",
            "async_concurrency",
            "observability",
        ],
        recommendations={
            "backend.api-architecture": "Structure API endpoints with explicit routing controllers and versioning.",
            "backend.timeout-management": "Configure explicit timeouts on all HTTP and database clients.",
            "backend.retry-architecture": "Use exponential backoff with jitter and max attempt limits.",
            "backend.caching": "Specify explicit TTL expiration and deterministic invalidation keys.",
        },
    )
    registry.register_knowledge_pack(backend_kp)

    # ─────────────────────────────────────────────────────────────────────────
    # 12. Register Machine Learning KnowledgePack & Rules
    # ─────────────────────────────────────────────────────────────────────────
    from sdat.ml.knowledge_pack import MLKnowledgePack

    for rule in MLKnowledgePack.RULES:
        registry.register_rule(
            Rule(
                rule_id=rule.id,
                concept_id=rule.concept_id,
                name=rule.name,
                description=rule.description,
                applicability=RuleApplicability(domains=("ml",)),
                required_evidence=(),
                evaluation_logic=f"Deterministic evaluation for {rule.id}",
                severity=rule.priority,
                remediation_guidance=rule.remediation_guidance,
            )
        )

    ml_kp = KnowledgePack(
        id="kp.machine-learning",
        domain="ml",
        version="1.0.0",
        concepts=[c for c in ml_concepts if c.domain == "ml"],
        capabilities=[
            Capability(
                id="cap.ml.math_stability",
                name="ML Mathematical & Loss Stability",
                domain="ml",
                description="Observable loss functions, logit calculations, and numerical stability.",
                detection_evidence_kinds=(EvidenceKind.CALL, EvidenceKind.INSTANTIATION),
                activated_concepts=("ml.mathematical-correctness",),
            ),
        ],
        dependencies=["core"],
        scoring_dimensions=[
            "mathematical_numerical_stability",
            "training_optimization_hygiene",
            "reproducibility_and_safety",
        ],
        recommendations={
            "ml.mathematical-correctness": "Pass unconstrained logits to cross_entropy; use logsumexp for numerical stability.",
            "ml.optimization-hygiene": "Call scheduler.step() strictly after optimizer.step() in training loops.",
            "ml.serialization-safety": "Use safetensors or weights_only=True when loading model checkpoints.",
        },
    )
    registry.register_knowledge_pack(ml_kp)

    # ─────────────────────────────────────────────────────────────────────────
    # 13. Register Natural Language Processing KnowledgePack & Rules
    # ─────────────────────────────────────────────────────────────────────────
    from sdat.nlp.knowledge_pack import NLPKnowledgePack

    for rule in NLPKnowledgePack.RULES:
        registry.register_rule(
            Rule(
                rule_id=rule.id,
                concept_id=rule.concept_id,
                name=rule.name,
                description=rule.description,
                applicability=RuleApplicability(domains=("nlp",)),
                required_evidence=(),
                evaluation_logic=f"Deterministic evaluation for {rule.id}",
                severity=rule.priority,
                remediation_guidance=rule.remediation_guidance,
            )
        )

    nlp_kp = KnowledgePack(
        id="kp.natural-language-processing",
        domain="nlp",
        version="1.0.0",
        concepts=[c for c in ml_concepts if c.domain == "nlp"],
        capabilities=[
            Capability(
                id="cap.nlp.attention_contracts",
                name="Transformer Attention Contracts",
                domain="nlp",
                description="Observable multi-head attention and masking tensor contracts.",
                detection_evidence_kinds=(EvidenceKind.INHERITANCE, EvidenceKind.CALL),
                activated_concepts=("nlp.tensor-contracts", "nlp.attention-masking"),
            ),
        ],
        dependencies=["core", "ml"],
        scoring_dimensions=[
            "transformer_tensor_soundness",
            "tokenization_and_sequence_contract",
        ],
        recommendations={
            "nlp.tensor-contracts": "Ensure hidden dimension d_model is evenly divisible by number of attention heads n_heads.",
            "nlp.attention-masking": "Use -inf (or -1e4/-1e9) when adding attention masks to logit matrices before softmax.",
            "nlp.tokenization-pipeline": "Call model.resize_token_embeddings(len(tokenizer)) after adding tokens to tokenizer.",
            "nlp.sequence-budget": "Enforce explicit truncation=True and max_length bounds on tokenized inputs.",
        },
    )
    registry.register_knowledge_pack(nlp_kp)

    return registry

