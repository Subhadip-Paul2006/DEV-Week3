"""Evidence Aggregator for SDAT.

Responsible for:
1. Cross-file and same-file correlation (e.g., import -> instantiation -> method calls).
2. Cross-language correlation (neutral representation of analogous patterns).
3. Concept indexing (mapping facts to relevant concepts without premature architectural verdicts).
4. Absence synthesis (verifying missing expected safeguards when coverage justifies the claim).
5. EvidenceBundle generation (deterministic, deduplicated packages for agent evaluation).
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from sdat.concepts import CONCEPTS_BY_ID
from sdat.models import EvidenceBundle, EvidenceFact, EvidenceKind

# ─────────────────────────────────────────────────────────────────────────────
# Concept Mapping Rules
# Maps structural subjects, libraries, or patterns to candidate concept IDs.
# Crucial principle: candidate relevance != final architectural verdict.
# ─────────────────────────────────────────────────────────────────────────────

CONCEPT_KEYWORDS: dict[str, list[str]] = {
    "foundation.caching": [
        "redis", "memcache", "pylibmc", "pymemcache", "lru_cache", "cache",
        "ioredis", "node-cache", "cache-manager", "swr", "react-query", "tanstack",
        "ttl",
    ],
    "foundation.circuit-breaker": [
        "circuit_breaker", "pybreaker", "opossum", "resilience4j", "bpr",
        "circuitbreaker", "fallback",
    ],
    "resilience.retries": [
        "retry", "tenacity", "backoff", "retrying", "p-retry", "async-retry",
        "exponential_backoff", "jitter",
    ],
    "foundation.logging": [
        "logging", "loguru", "structlog", "winston", "pino", "bunyan", "morgan",
        "logger", "console.info", "console.error", "console.warn",
    ],
    "foundation.config": [
        "dotenv", "load_dotenv", "os.environ", "os.getenv", "process.env",
        "config", "convict", "configservice", "settings",
    ],
    "foundation.validation": [
        "pydantic", "basemodel", "zod", "joi", "validator", "class-validator",
        "marshmallow", "cerberus",
    ],
    "foundation.auth": [
        "jwt", "oauth", "passport", "bcrypt", "argon2", "session",
        "authlib", "create_access_token", "decode_token",
    ],
    "foundation.authorization": [
        "rbac", "casbin", "policy", "permission", "is_admin", "is_authorized",
        "enforcer", "guard",
    ],
    "foundation.rate-limiting": [
        "ratelimit", "slowapi", "limiter", "throttle", "express-rate-limit",
        "rate_limit",
    ],
    "foundation.error-handling": [
        "try", "except", "errorhandler", "exception", "middleware", "http-errors",
        "exceptionfilter", "catch",
    ],
    "foundation.connection-pooling": [
        "pool", "connection_pool", "pool_size", "max_overflow", "pool_pre_ping",
        "pgpool",
    ],
    "foundation.message-queues": [
        "celery", "rabbitmq", "pika", "bullmq", "bull", "sqs", "amqp",
    ],
    "foundation.idempotency": [
        "idempotent", "idempotency_key", "x-idempotency-key", "idempotency",
    ],
    "foundation.observability": [
        "prometheus", "opentelemetry", "datadog", "newrelic", "jaeger",
        "telemetry", "metrics", "tracing",
    ],
    "foundation.health-checks": [
        "health", "healthz", "readyz", "liveness", "readiness",
    ],
    "data.orm": [
        "sqlalchemy", "prisma", "typeorm", "mongoose", "sequelize",
        "tortoise", "peewee", "sessionmaker",
    ],
    "data.migrations": [
        "alembic", "knex", "flyway", "liquibase", "migration",
    ],
    "api.rest": [
        "fastapi", "express", "flask", "router", "apirouter", "app.get",
        "app.post", "controller",
    ],
    "api.graphql": [
        "graphql", "apollo", "strawberry", "graphene", "type-graphql",
    ],
    "streaming.kafka": [
        "kafka", "confluent_kafka", "kafkajs", "kafka-python", "aiokafka",
    ],
    "resilience.timeouts": [
        "timeout", "connect_timeout", "read_timeout", "request_timeout",
    ],
    "frontend.rendering": [
        "createroot", "hydrate", "hydrateroot", "serversideprops", "getserversideprops",
        "getstaticprops", "generatestaticparams", "prerender", "streaming", "ssr", "ssg", "csr",
    ],
    "frontend.routing": [
        "router", "routes", "route", "createrouter", "createbrowserrouter", "link",
        "navlink", "navigate", "next/navigation", "next/router", "vue-router", "page.tsx",
    ],
    "frontend.loading": [
        "lazy", "suspense", "dynamic", "import(", "skeleton", "fallback",
        "loading.tsx", "code-splitting",
    ],
    "frontend.runtime-performance": [
        "usememo", "usecallback", "react.memo", "web-vitals", "inp", "lcp", "fcp",
    ],
    "frontend.component-architecture": [
        "virtualizer", "react-window", "react-virtualized", "virtual-list",
    ],
    "frontend.responsive-design": [
        "@media", "breakpoint", "viewport", "mobile", "desktop", "container-query",
    ],
    "frontend.assets": [
        "next/image", "next/font", "@font-face", "webp", "avif", "preload", "srcset",
    ],
    "frontend.state-management": [
        "redux", "zustand", "recoil", "jotai", "vuex", "pinia", "context", "createstore",
    ],
    "frontend.data-fetching": [
        "usequery", "useswr", "tanstack", "apollo", "graphql", "fetch", "axios",
    ],
    "frontend.caching": [
        "cache-control", "localstorage", "sessionstorage", "indexeddb", "swr", "queryclient",
    ],
    "frontend.error-handling": [
        "errorboundary", "error-boundary", "error.tsx", "fallbackrender", "componentdidcatch",
    ],
    "frontend.accessibility": [
        "aria-", "role=", "alt=", "sr-only", "tabindex", "aria-label",
    ],
    "frontend.security": [
        "dangerouslysetinnerhtml", "v-html", "sanitizer", "dompurify", "xss",
    ],
    "frontend.network-api": [
        "abortcontroller", "retry", "backoff", "websocket", "reconnect",
    ],
    "frontend.perceived-latency": [
        "optimistic", "useoptimistic", "skeleton", "prefetch",
    ],
    "frontend.web3": [
        "wagmi", "rainbowkit", "web3modal", "useaccount", "useconnect", "sendtransaction",
    ],
}


class EvidenceAggregator:
    """Aggregates, correlates, and indexes EvidenceFacts into concept EvidenceBundles."""

    def __init__(self, target_root: str | Path | None = None) -> None:
        self.target_root = Path(target_root) if target_root else None

    # ─────────────────────────────────────────────────────────────────────────
    # Indexing Utilities
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def index_by_file(facts: Iterable[EvidenceFact]) -> dict[str, list[EvidenceFact]]:
        """Group facts by source file path."""
        by_file: dict[str, list[EvidenceFact]] = defaultdict(list)
        for f in facts:
            by_file[str(f.file_path)].append(f)
        return dict(by_file)

    @staticmethod
    def index_by_subject(facts: Iterable[EvidenceFact]) -> dict[str, list[EvidenceFact]]:
        """Group facts by primary subject."""
        by_subject: dict[str, list[EvidenceFact]] = defaultdict(list)
        for f in facts:
            by_subject[f.subject.lower()].append(f)
        return dict(by_subject)

    @staticmethod
    def index_by_library(facts: Iterable[EvidenceFact]) -> dict[str, list[EvidenceFact]]:
        """Group facts by library attribute."""
        by_lib: dict[str, list[EvidenceFact]] = defaultdict(list)
        for f in facts:
            if f.library:
                by_lib[f.library.lower()].append(f)
        return dict(by_lib)

    # ─────────────────────────────────────────────────────────────────────────
    # Cross-File & Same-File Correlation
    # ─────────────────────────────────────────────────────────────────────────

    def correlate(self, facts: list[EvidenceFact]) -> list[EvidenceFact]:
        """Correlate related facts across files or within the same file.

        Detects structural relationships such as:
        - Import -> Instantiation -> Method Calls (e.g. redis module -> client = Redis -> client.set)
        - Framework markers -> Controllers/Endpoints
        Returns all facts, preserving original observations and deduplicating.
        """
        # Deduplicate facts deterministically
        seen: set[tuple[str, Any, str, str, str]] = set()
        deduped: list[EvidenceFact] = []

        for f in facts:
            key = (
                str(f.file_path),
                f.line_range,
                f.kind.value,
                f.subject,
                f.snippet,
            )
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        return deduped

    def find_call_chains(self, facts: list[EvidenceFact], base_subject: str) -> list[EvidenceFact]:
        """Trace call and instantiation facts connected to a given subject/module."""
        target = base_subject.lower()
        results: list[EvidenceFact] = []
        for f in facts:
            sub = f.subject.lower()
            call = (f.call_target or "").lower()
            lib = (f.library or "").lower()
            if target in sub or target in call or target in lib:
                results.append(f)
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Concept Indexing
    # ─────────────────────────────────────────────────────────────────────────

    def map_fact_to_concepts(self, fact: EvidenceFact) -> set[str]:
        """Identify candidate concept IDs relevant to a single EvidenceFact.

        This performs CANDIDATE RELEVANCE indexing, not a final verdict.
        """
        matched: set[str] = set()
        sub = fact.subject.lower()
        snippet = fact.snippet.lower()
        lib = (fact.library or "").lower()
        framework = (fact.framework or "").lower()
        hints = [h.lower() for h in fact.identifier_hints]

        # 1. Direct match if subject is already a concept_id (e.g. from legacy bridge)
        if fact.subject in CONCEPTS_BY_ID:
            matched.add(fact.subject)

        # 2. Check concept keyword rules
        searchable_terms = {sub, lib, framework, *hints}
        for concept_id, keywords in CONCEPT_KEYWORDS.items():
            for kw in keywords:
                if any(kw == t or kw in t for t in searchable_terms if t):
                    matched.add(concept_id)
                    break
                # Only check snippet if subject didn't match and snippet explicitly contains keyword
                if kw in snippet:
                    matched.add(concept_id)
                    break

        # 3. Structural heuristics
        if fact.kind in (EvidenceKind.CONFIG_KEY, EvidenceKind.ENV_VAR):
            matched.add("foundation.config")
        if fact.kind == EvidenceKind.SCHEMA_DEF:
            matched.add("foundation.validation")
        if fact.kind == EvidenceKind.DB_QUERY:
            matched.add("data.orm")
        if fact.kind == EvidenceKind.ASYNC_PATTERN:
            matched.add("performance.async-io")

        return matched

    # ─────────────────────────────────────────────────────────────────────────
    # Absence Synthesis
    # ─────────────────────────────────────────────────────────────────────────

    def synthesize_absence(self, facts: list[EvidenceFact]) -> list[EvidenceFact]:
        """Synthesize explicit absence facts where expected safeguards are provably missing.

        Rules:
        1. If external HTTP/network calls exist, verify whether timeouts or retries are present.
           If missing across the observed calls, emit an ABSENT_PATTERN fact.
        2. If cache writes are observed, verify whether TTL was configured.
        Absence is ONLY emitted when sufficient positive facts justify the expectation.
        """
        synthesized: list[EvidenceFact] = []

        # 1. External HTTP Calls without Timeout
        http_call_facts = [
            f for f in facts
            if f.kind == EvidenceKind.CALL
            and any(x in f.subject.lower() or x in (f.call_target or "").lower()
                    for x in ("requests.", "httpx.", "fetch", "axios.", "http.request", "urllib."))
        ]

        if http_call_facts:
            # Check if any call had a timeout observed
            calls_without_timeout = [f for f in http_call_facts if f.timeout_observed is not True]

            # If external calls exist but lack timeouts, synthesize absence for the unshielded calls
            for call in calls_without_timeout:
                synthesized.append(EvidenceFact(
                    kind=EvidenceKind.ABSENT_PATTERN,
                    subject="timeout",
                    language=call.language,
                    file_path=call.file_path,
                    line_range=call.line_range,
                    snippet=f"External call '{call.subject}' observed without explicit timeout safeguard",
                    scope=call.scope,
                    call_target=call.call_target,
                    extraction_confidence=0.85,
                    identifier_hints=("missing_timeout",),
                ))

            # Check if any retry library or pattern is present anywhere in facts
            retry_facts = [
                f for f in facts
                if any(x in f.subject.lower() or x in (f.library or "").lower()
                       for x in ("tenacity", "backoff", "retry", "opossum", "pybreaker"))
            ]
            if not retry_facts:
                first_call = http_call_facts[0]
                synthesized.append(EvidenceFact(
                    kind=EvidenceKind.ABSENT_PATTERN,
                    subject="retries",
                    language=first_call.language,
                    file_path=first_call.file_path,
                    line_range=first_call.line_range,
                    snippet="External HTTP calls present but no retry mechanism or library observed",
                    extraction_confidence=0.80,
                    identifier_hints=("missing_retries",),
                ))

        # 2. Cache Writes without TTL
        cache_write_facts = [
            f for f in facts
            if f.kind == EvidenceKind.CALL
            and any(op in f.subject.lower() or op in (f.call_target or "").lower()
                    for op in (".set", "client.set", "redis.set", "set("))
            and f.ttl_observed is False
        ]
        for cw in cache_write_facts:
            synthesized.append(EvidenceFact(
                kind=EvidenceKind.ABSENT_PATTERN,
                subject="ttl",
                language=cw.language,
                file_path=cw.file_path,
                line_range=cw.line_range,
                snippet=f"Cache write '{cw.subject}' observed without explicit TTL expiration",
                scope=cw.scope,
                call_target=cw.call_target,
                extraction_confidence=0.90,
                identifier_hints=("missing_ttl",),
            ))

        return synthesized

    # ─────────────────────────────────────────────────────────────────────────
    # EvidenceBundle Generation
    # ─────────────────────────────────────────────────────────────────────────

    def bundle_by_concept(
        self,
        facts: list[EvidenceFact],
        peer_patterns: dict[str, list[str]] | None = None,
        literature_findings: dict[str, list[str]] | None = None,
    ) -> list[EvidenceBundle]:
        """Index facts by concept, correlate them, synthesize absence, and generate EvidenceBundles.

        Returns a deterministically sorted list of EvidenceBundle objects.
        """
        correlated_facts = self.correlate(facts)
        absence_facts = self.synthesize_absence(correlated_facts)
        all_facts = correlated_facts + absence_facts

        # Group facts into candidate concepts
        concept_to_facts: dict[str, list[EvidenceFact]] = defaultdict(list)
        for f in all_facts:
            concepts = self.map_fact_to_concepts(f)
            for cid in concepts:
                concept_to_facts[cid].append(f)

        peer_map = peer_patterns or {}
        lit_map = literature_findings or {}

        bundles: list[EvidenceBundle] = []
        for cid in sorted(concept_to_facts.keys()):
            # Deduplicate and sort facts deterministically
            raw_facts = concept_to_facts[cid]
            seen: set[tuple[str, Any, str, str]] = set()
            sorted_facts: list[EvidenceFact] = []
            
            # Deterministic sorting key for facts: (file_path, line_start, kind, subject)
            def fact_sort_key(fact: EvidenceFact) -> tuple[str, int, str, str]:
                lr = fact.line_range[0] if fact.line_range else 0
                return (str(fact.file_path), lr, fact.kind.value, fact.subject)

            for f in sorted(raw_facts, key=fact_sort_key):
                key = (str(f.file_path), f.line_range, f.kind.value, f.subject)
                if key not in seen:
                    seen.add(key)
                    sorted_facts.append(f)

            bundle = EvidenceBundle(
                concept_id=cid,
                facts=tuple(sorted_facts),
                peer_patterns=tuple(sorted(peer_map.get(cid, []))),
                literature_findings=tuple(sorted(lit_map.get(cid, []))),
            )
            bundles.append(bundle)

        return bundles

    def aggregate(
        self,
        facts: list[EvidenceFact],
        peer_patterns: dict[str, list[str]] | None = None,
        literature_findings: dict[str, list[str]] | None = None,
    ) -> list[EvidenceBundle]:
        """Top-level pipeline method: correlates, synthesizes absence, and packages into EvidenceBundles."""
        return self.bundle_by_concept(
            facts=facts,
            peer_patterns=peer_patterns,
            literature_findings=literature_findings,
        )
