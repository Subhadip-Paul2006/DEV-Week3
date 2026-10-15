"""Backend KnowledgePack — Rule definitions and deterministic evaluation engine.

Implements the 25 system-design rule categories for backend architecture,
evaluating structural EvidenceFacts, BackendAnalysisSummary, and code patterns.
"""

from __future__ import annotations

from sdat.backend.models import (
    BackendAnalysisSummary,
    BackendRule,
    BackendRuleEvaluationResult,
)
from sdat.models import Decision, DecisionStatus, Evidence, EvidenceFact, EvidenceKind, Priority


class BackendKnowledgePack:
    """Authoritative knowledge pack for backend system-design auditing."""

    id: str = "kp.backend"
    domain: str = "backend"
    version: str = "1.0.0"
    dependencies: list[str] = ["core"]
    scoring_dimensions: list[str] = [
        "api_architecture",
        "request_lifecycle",
        "data_interaction",
        "reliability_resilience",
        "security",
        "async_concurrency",
        "observability",
    ]

    RULES: list[BackendRule] = [
        # A. API Architecture
        BackendRule(
            id="BE-API-01",
            dimension="api_architecture",
            name="API Route Structuring & Handler Separation",
            description="Exposes structured API endpoints (REST, RPC, GraphQL) with defined routes and handler separation.",
            priority=Priority.HIGH,
            concept_id="backend.api-architecture",
            remediation_guidance="Organize API endpoints into explicit route controllers and separate routing from business logic.",
        ),
        # B. Request Lifecycle
        BackendRule(
            id="BE-LIFE-01",
            dimension="request_lifecycle",
            name="Request Lifecycle & Layer Boundary Separation",
            description="Maintains clear separation between transport middleware, service domain logic, and data access.",
            priority=Priority.HIGH,
            concept_id="backend.request-lifecycle",
            remediation_guidance="Introduce distinct service and repository layers rather than invoking database queries directly inside route handlers.",
        ),
        # C. Service Architecture
        BackendRule(
            id="BE-SRV-01",
            dimension="request_lifecycle",
            name="Service Modularity & Dependency Direction",
            description="Defines modular service boundaries with clean dependency direction between domain modules.",
            priority=Priority.MEDIUM,
            concept_id="backend.service-boundaries",
            remediation_guidance="Decouple tightly-coupled services by injecting repository interfaces or domain adapters.",
        ),
        # D. Authentication
        BackendRule(
            id="BE-AUTH-01",
            dimension="security",
            name="Authentication Middleware Enforcement",
            description="Enforces authentication validation (JWT, sessions, API keys) at entrypoint middleware boundaries.",
            priority=Priority.CRITICAL,
            concept_id="backend.authentication",
            remediation_guidance="Apply authentication guards/middleware globally or at route group boundaries to prevent unauthenticated access.",
        ),
        # E. Authorization
        BackendRule(
            id="BE-AUTH-02",
            dimension="security",
            name="Authorization & Privilege Enforcement",
            description="Enforces role-based or permission-based access control checks at sensitive operational endpoints.",
            priority=Priority.HIGH,
            concept_id="backend.authorization",
            remediation_guidance="Add explicit role/permission checks on mutation endpoints rather than relying solely on authentication identity.",
        ),
        # F. Input Validation
        BackendRule(
            id="BE-VAL-01",
            dimension="security",
            name="Schema-Based Input Validation",
            description="Validates incoming request payloads and query parameters using declarative schemas (Pydantic, Zod, @Valid) at ingress.",
            priority=Priority.HIGH,
            concept_id="backend.input-validation",
            remediation_guidance="Bind typed schema validators to all controller request bodies to reject malformed or malicious payloads.",
        ),
        # G. Error Handling
        BackendRule(
            id="BE-ERR-01",
            dimension="reliability_resilience",
            name="Structured Error Handling & Exception Envelopes",
            description="Provides centralized exception handling and uniform structured error response envelopes.",
            priority=Priority.MEDIUM,
            concept_id="backend.error-handling",
            remediation_guidance="Register a global exception handler to catch unhandled errors and return sanitized RFC 7807 problem details.",
        ),
        # H. Timeout Management
        BackendRule(
            id="BE-TIME-01",
            dimension="reliability_resilience",
            name="Bounded Client & External Call Timeouts",
            description="Configures explicit, bounded execution timeouts for HTTP, RPC, and database client calls.",
            priority=Priority.HIGH,
            concept_id="backend.timeout-management",
            remediation_guidance="Set explicit read/connect timeouts on HTTP clients and database connections to avoid thread exhaustion.",
        ),
        # I. Retry Architecture
        BackendRule(
            id="BE-RETRY-01",
            dimension="reliability_resilience",
            name="Retry Architecture with Exponential Backoff & Jitter",
            description="Configures retry policies with maximum attempt limits, exponential backoff, and full jitter.",
            priority=Priority.HIGH,
            concept_id="backend.retry-architecture",
            remediation_guidance="Replace fixed retry delays with exponential backoff and jitter, and cap attempts to 3-5 to prevent retry storms.",
        ),
        # J. Idempotency
        BackendRule(
            id="BE-IDEM-01",
            dimension="reliability_resilience",
            name="Idempotency for Mutating Operations",
            description="Implements idempotency keys or deduplication mechanisms for state-mutating requests (POST, payment, charge).",
            priority=Priority.HIGH,
            concept_id="backend.idempotency",
            remediation_guidance="Require an Idempotency-Key header on critical mutation endpoints and cache completed responses.",
        ),
        # K. Rate Limiting
        BackendRule(
            id="BE-RATE-01",
            dimension="security",
            name="API Rate Limiting & Abuse Prevention",
            description="Applies token bucket or sliding window rate limiting at API ingress boundaries.",
            priority=Priority.MEDIUM,
            concept_id="backend.rate-limiting",
            remediation_guidance="Deploy rate limiting middleware (e.g. Redis sliding window or token bucket) to protect public routes.",
        ),
        # L. Caching
        BackendRule(
            id="BE-CACHE-01",
            dimension="data_interaction",
            name="Backend Caching with Explicit TTL",
            description="Implements caching layers with explicit TTL expiration and deterministic invalidation on updates.",
            priority=Priority.MEDIUM,
            concept_id="backend.caching",
            remediation_guidance="Ensure all cache writes specify an explicit TTL and that mutation endpoints invalidate related cached keys.",
        ),
        # M. Async Processing
        BackendRule(
            id="BE-ASYNC-01",
            dimension="async_concurrency",
            name="Asynchronous Non-Blocking Processing",
            description="Uses asynchronous coroutines or non-blocking event loops for I/O operations.",
            priority=Priority.MEDIUM,
            concept_id="backend.async-processing",
            remediation_guidance="Offload blocking I/O calls to thread pools or use native async/await drivers.",
        ),
        # N. Background Jobs
        BackendRule(
            id="BE-QUEUE-01",
            dimension="async_concurrency",
            name="Distributed Background Task Queues",
            description="Decouples heavy or asynchronous processing into message queues (Celery, Kafka, RabbitMQ, BullMQ).",
            priority=Priority.MEDIUM,
            concept_id="backend.background-jobs",
            remediation_guidance="Move long-running tasks out of the HTTP request cycle into dedicated background workers.",
        ),
        # O. Database Interaction
        BackendRule(
            id="BE-DB-01",
            dimension="data_interaction",
            name="Parameterized Database Queries & Injection Prevention",
            description="Uses parameterized queries or ORM abstractions to prevent SQL injection vulnerabilities.",
            priority=Priority.CRITICAL,
            concept_id="backend.database-interaction",
            remediation_guidance="Never concatenate untrusted input into raw SQL queries; use prepared statements or ORM binding.",
        ),
        # P. Connection Pooling
        BackendRule(
            id="BE-POOL-01",
            dimension="data_interaction",
            name="Database Connection Pooling",
            description="Manages database connections via a bounded connection pool with configured min/max pool sizes.",
            priority=Priority.HIGH,
            concept_id="backend.connection-pooling",
            remediation_guidance="Configure an explicit connection pool (e.g. HikariCP, SQLAlchemy pool, pgxpool) with max capacity limits.",
        ),
        # Q. External Services
        BackendRule(
            id="BE-EXT-01",
            dimension="reliability_resilience",
            name="External Service Client Isolation",
            description="Encapsulates external HTTP/third-party API integrations into dedicated client adapters.",
            priority=Priority.MEDIUM,
            concept_id="backend.external-service-integration",
            remediation_guidance="Wrap external third-party SDK calls in dedicated service adapters with fallback logic.",
        ),
        # R. Transaction Boundaries
        BackendRule(
            id="BE-TXN-01",
            dimension="data_interaction",
            name="Isolated Transaction Boundaries",
            description="Keeps database transaction blocks focused and atomic, avoiding external network calls inside open transactions.",
            priority=Priority.HIGH,
            concept_id="backend.transaction-boundaries",
            remediation_guidance="Move external network/HTTP calls outside database transaction scopes to avoid holding DB locks during external latency.",
        ),
        # S. Concurrency
        BackendRule(
            id="BE-CONC-01",
            dimension="async_concurrency",
            name="Safe Concurrency & Thread Synchronization",
            description="Protects shared mutable state with thread-safe synchronization primitives, mutexes, or channels.",
            priority=Priority.HIGH,
            concept_id="backend.concurrency",
            remediation_guidance="Guard shared in-memory state with mutexes or migrate to thread-safe lock-free data structures.",
        ),
        # T. Resource Lifecycle
        BackendRule(
            id="BE-RES-01",
            dimension="data_interaction",
            name="Resource Disposal & Graceful Shutdown",
            description="Properly disposes open database connections, network streams, and handles process termination signals.",
            priority=Priority.MEDIUM,
            concept_id="backend.resource-lifecycle",
            remediation_guidance="Register graceful shutdown handlers to flush pending writes and close active database pools on SIGTERM.",
        ),
        # U. Observability
        BackendRule(
            id="BE-OBS-01",
            dimension="observability",
            name="Structured Logging & Correlation IDs",
            description="Emits structured JSON logs and propagates correlation/request IDs across backend execution paths.",
            priority=Priority.MEDIUM,
            concept_id="backend.observability",
            remediation_guidance="Configure structured logging (e.g. structlog, zap, winston) and attach request IDs to all log entries.",
        ),
        # V. Security
        BackendRule(
            id="BE-SEC-01",
            dimension="security",
            name="Backend Secret Hygiene & Transport Security",
            description="Resolves secrets via environment variables or secret vaults without hardcoded credentials in source code.",
            priority=Priority.CRITICAL,
            concept_id="backend.security",
            remediation_guidance="Externalize all database passwords and API tokens to environment variables or secret management services.",
        ),
        # W. Performance
        BackendRule(
            id="BE-PERF-01",
            dimension="api_architecture",
            name="Non-Blocking Execution & Serialization Efficiency",
            description="Avoids synchronous CPU-intensive operations on the main request event loop.",
            priority=Priority.MEDIUM,
            concept_id="backend.performance",
            remediation_guidance="Profile serialization bottlenecks and offload heavy computation away from request threads.",
        ),
        # X. Scalability
        BackendRule(
            id="BE-SCAL-01",
            dimension="api_architecture",
            name="Stateless Design for Horizontal Scaling",
            description="Keeps backend application instances stateless by externalizing session state to Redis or databases.",
            priority=Priority.HIGH,
            concept_id="backend.scalability",
            remediation_guidance="Store session and temporary data in external stores (e.g. Redis) rather than in-process global memory.",
        ),
        # Y. Resilience
        BackendRule(
            id="BE-RESL-01",
            dimension="reliability_resilience",
            name="Graceful Degradation & Circuit Breaking",
            description="Wraps external and volatile downstream dependencies in circuit breakers with fallback defaults.",
            priority=Priority.HIGH,
            concept_id="backend.resilience",
            remediation_guidance="Introduce circuit breakers with fallback values around external service calls to prevent cascading failures.",
        ),
    ]

    def evaluate(self, facts: list[EvidenceFact], summary: BackendAnalysisSummary) -> list[BackendRuleEvaluationResult]:
        """Evaluate all 25 rules against EvidenceFacts and the BackendAnalysisSummary."""
        results: list[BackendRuleEvaluationResult] = []

        is_backend = bool(
            summary.endpoints
            or summary.middlewares
            or summary.detected_frameworks
            or summary.detected_databases
            or summary.detected_queues
            or any(f.framework for f in facts)
            or any("route" in str(f.file_path).lower() or "controller" in str(f.file_path).lower() for f in facts)
        )

        for rule in self.RULES:
            res = self._evaluate_rule(rule, facts, summary, is_backend)
            results.append(res)

        return results

    def _evaluate_rule(
        self,
        rule: BackendRule,
        facts: list[EvidenceFact],
        summary: BackendAnalysisSummary,
        is_backend: bool,
    ) -> BackendRuleEvaluationResult:
        """Deterministic evaluation for an individual backend rule."""
        if not is_backend:
            return BackendRuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.UNKNOWN,
                confidence=0.5,
                gaps=["No backend architecture detected in target repository."],
            )

        if rule.id == "BE-API-01":
            # API Route Structuring
            if summary.endpoints:
                ev_list = [
                    Evidence(
                        file=str(ep.file_path),
                        line=ep.line,
                        snippet=f"{ep.method} {ep.path}",
                        note=f"Discovered backend endpoint: {ep.method} {ep.path}",
                    )
                    for ep in summary.endpoints[:5]
                ]
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.IMPLEMENTED,
                    confidence=0.95,
                    evidence=ev_list,
                )
            # Check EvidenceFacts for endpoint routes
            route_facts = [f for f in facts if f.kind in (EvidenceKind.DECORATOR, EvidenceKind.CALL) and any(r in f.subject.lower() for r in ("route", "get", "post", "handler"))]
            if route_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Route declaration detected")
                    for f in route_facts[:5]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            return BackendRuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISSING,
                confidence=0.85,
                gaps=["No structured API endpoints or routing handlers detected."],
                recommendation=rule.remediation_guidance,
            )

        if rule.id == "BE-LIFE-01":
            # Request Lifecycle & Layer Separation
            layers = {b.layer for b in summary.boundaries}
            has_separation = ("controller" in layers or "handler" in layers) and ("service" in layers or "repository" in layers)
            if has_separation:
                ev_list = [
                    Evidence(file=str(b.file_path), line=1, snippet=f"Layer: {b.layer}", note=f"Separated architectural layer: {b.name} ({b.layer})")
                    for b in summary.boundaries[:4]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            # Check if controllers have direct DB access (layer leakage)
            leaked_controllers = [b for b in summary.boundaries if b.layer == "controller" and b.has_direct_db_access]
            if leaked_controllers:
                ev_list = [
                    Evidence(file=str(b.file_path), line=1, snippet="Direct DB operation in controller", note="Controller interacts directly with database")
                    for b in leaked_controllers[:3]
                ]
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.MISCONFIGURED,
                    confidence=0.85,
                    evidence=ev_list,
                    misconfiguration="Direct database interaction discovered within transport/controller layer.",
                    gaps=["Missing dedicated service/repository layer abstraction."],
                    recommendation=rule.remediation_guidance,
                )
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.6, gaps=["Insufficient layer boundaries observed."])

        if rule.id == "BE-AUTH-01":
            # Authentication
            auth_mw = [mw for mw in summary.middlewares if mw.purpose == "auth"]
            auth_facts = [f for f in facts if any(a in f.subject.lower() for a in ("jwt", "auth", "session", "oauth", "passport", "security"))]
            if auth_mw:
                ev_list = [
                    Evidence(file=str(mw.file_path), line=mw.line, snippet=f"Middleware: {mw.name}", note="Authentication middleware enforced")
                    for mw in auth_mw
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.95, evidence=ev_list)
            if auth_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Authentication library/call detected")
                    for f in auth_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.85, evidence=ev_list)
            return BackendRuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISSING,
                confidence=0.85,
                gaps=["No authentication middleware or token verification detected on backend API."],
                recommendation=rule.remediation_guidance,
            )

        if rule.id == "BE-VAL-01":
            # Input Validation
            val_facts = [f for f in facts if any(v in f.subject.lower() for v in ("pydantic", "zod", "joi", "validator", "schema", "valid"))]
            if summary.has_input_validation or val_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Input validation schema configured")
                    for f in val_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            return BackendRuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISSING,
                confidence=0.80,
                gaps=["No input validation schemas observed at endpoint ingress boundaries."],
                recommendation=rule.remediation_guidance,
            )

        if rule.id == "BE-TIME-01":
            # Timeout Management
            timeout_facts = [f for f in facts if f.timeout_observed or "timeout" in (f.snippet.lower() if f.snippet else "")]
            if summary.has_timeouts or timeout_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Timeout configuration observed")
                    for f in timeout_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            # If external calls exist but no timeout
            ext_calls = [f for f in facts if f.kind == EvidenceKind.CALL and any(c in f.subject.lower() for c in ("requests", "http.get", "http.post", "axios", "fetch"))]
            if ext_calls:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="External call without timeout")
                    for f in ext_calls[:3]
                ]
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.MISCONFIGURED,
                    confidence=0.88,
                    evidence=ev_list,
                    misconfiguration="External HTTP calls invoked without explicit timeout configuration.",
                    gaps=["No timeout specified on external network calls; vulnerable to thread exhaustion."],
                    recommendation=rule.remediation_guidance,
                )
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No external network calls or timeouts observed."])

        if rule.id == "BE-RETRY-01":
            # Retry Architecture
            retry_facts = [f for f in facts if f.retry_count_observed is not None or any(r in f.subject.lower() for r in ("retry", "backoff", "tenacity"))]
            if summary.has_retries or retry_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Retry logic observed")
                    for f in retry_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No explicit retry mechanisms observed."])

        if rule.id == "BE-IDEM-01":
            # Idempotency
            idem_facts = [f for f in facts if any(i in (f.snippet.lower() if f.snippet else "") for i in ("idempotency", "x-idempotency", "dedup"))]
            if summary.has_idempotency or idem_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Idempotency key enforcement observed")
                    for f in idem_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.92, evidence=ev_list)
            return BackendRuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISSING,
                confidence=0.75,
                gaps=["No idempotency keys or request deduplication logic observed on mutating operations."],
                recommendation=rule.remediation_guidance,
            )

        if rule.id == "BE-CACHE-01":
            # Caching
            cache_facts = [f for f in facts if f.ttl_observed is not None or any(c in f.subject.lower() for c in ("cache", "redis", "memcached"))]
            ttl_facts = [f for f in cache_facts if f.ttl_observed is True or "ttl" in (f.snippet.lower() if f.snippet else "")]
            if ttl_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Cache set with explicit TTL")
                    for f in ttl_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.95, evidence=ev_list)
            if cache_facts and not ttl_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Cache write without TTL observed")
                    for f in cache_facts[:3]
                ]
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.MISCONFIGURED,
                    confidence=0.88,
                    evidence=ev_list,
                    misconfiguration="Cache operations detected but without explicit TTL expiration.",
                    gaps=["No TTL expiration observed on cache entries; risk of stale data leaks."],
                    recommendation=rule.remediation_guidance,
                )
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No caching infrastructure detected."])

        if rule.id == "BE-DB-01":
            # Database Parameterization & SQL Injection Prevention
            db_facts = [f for f in facts if f.kind == EvidenceKind.DB_QUERY or any(d in f.subject.lower() for d in ("sqlalchemy", "sql", "query", "orm", "gorm", "hibernate"))]
            raw_concat = [f for f in db_facts if f.snippet and ("+" in f.snippet or "%" in f.snippet) and any(q in f.snippet.upper() for q in ("SELECT", "INSERT", "UPDATE", "WHERE"))]
            if raw_concat:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Potential SQL query string concatenation")
                    for f in raw_concat[:3]
                ]
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.MISCONFIGURED,
                    confidence=0.92,
                    evidence=ev_list,
                    misconfiguration="Direct string concatenation or formatting detected in SQL query statement.",
                    gaps=["Missing query parameterization; critical vulnerability to SQL injection."],
                    recommendation=rule.remediation_guidance,
                )
            if db_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Parameterized query or ORM access")
                    for f in db_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No database operations detected."])

        if rule.id == "BE-POOL-01":
            # Connection Pooling
            pool_facts = [f for f in facts if any(p in f.subject.lower() or p in (f.snippet.lower() if f.snippet else "") for p in ("pool", "max_connections", "pool_size", "hikaricp", "pgxpool"))]
            if summary.has_connection_pooling or pool_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Database connection pool configuration")
                    for f in pool_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.92, evidence=ev_list)
            if summary.detected_databases:
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.MISSING,
                    confidence=0.82,
                    gaps=["Database detected but no connection pooling configuration observed."],
                    recommendation=rule.remediation_guidance,
                )
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No database usage detected."])

        if rule.id == "BE-TXN-01":
            # Transaction Scope Isolation
            if summary.has_transaction_boundaries:
                return BackendRuleEvaluationResult(
                    rule=rule,
                    status=DecisionStatus.IMPLEMENTED,
                    confidence=0.88,
                    evidence=[Evidence(file=str(summary.target_root), line=1, snippet="transaction block", note="Database transaction boundaries configured")],
                )
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No explicit transaction blocks observed."])

        if rule.id == "BE-OBS-01":
            # Structured Logging & Telemetry
            obs_facts = [f for f in facts if any(o in f.subject.lower() for o in ("structlog", "zap", "winston", "prometheus", "opentelemetry", "logging", "logger"))]
            if summary.has_structured_logging or obs_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Structured logging / telemetry detected")
                    for f in obs_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.90, evidence=ev_list)
            return BackendRuleEvaluationResult(
                rule=rule,
                status=DecisionStatus.MISSING,
                confidence=0.80,
                gaps=["No structured logging or telemetry instrumentation detected."],
                recommendation=rule.remediation_guidance,
            )

        if rule.id == "BE-SEC-01":
            # Secret Hygiene
            secret_facts = [f for f in facts if f.kind == EvidenceKind.ENV_VAR or any(s in f.subject.lower() for s in ("getenv", "os.environ", "dotenv", "vault"))]
            if secret_facts:
                ev_list = [
                    Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note="Environment variable / vault secret resolution")
                    for f in secret_facts[:3]
                ]
                return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.92, evidence=ev_list)
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.UNKNOWN, confidence=0.5, gaps=["No explicit secret management patterns detected."])

        # Default fallback evaluation for remaining rules
        relevant_facts = [f for f in facts if rule.concept_id.split(".")[1] in f.subject.lower() or (f.snippet and rule.concept_id.split(".")[1] in f.snippet.lower())]
        if relevant_facts:
            ev_list = [
                Evidence(file=str(f.file_path), line=f.line_range[0] if f.line_range else 1, snippet=f.snippet, note=f"Structural evidence for {rule.name}")
                for f in relevant_facts[:3]
            ]
            return BackendRuleEvaluationResult(rule=rule, status=DecisionStatus.IMPLEMENTED, confidence=0.85, evidence=ev_list)

        return BackendRuleEvaluationResult(
            rule=rule,
            status=DecisionStatus.UNKNOWN,
            confidence=0.5,
            gaps=[f"No concrete evidence observed for {rule.concept_id}."],
        )

    def to_decisions(self, results: list[BackendRuleEvaluationResult]) -> list[Decision]:
        """Convert BackendRuleEvaluationResults into canonical Decision objects."""
        decisions: list[Decision] = []
        for res in results:
            decisions.append(
                Decision(
                    concept_id=res.rule.concept_id,
                    concept_name=res.rule.name,
                    status=res.status,
                    confidence=res.confidence,
                    evidence=list(res.evidence),
                    misconfiguration=res.misconfiguration,
                    gaps=tuple(res.gaps),
                    recommendation=res.recommendation,
                    priority=res.rule.priority,
                )
            )
        return decisions
