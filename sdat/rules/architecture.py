"""Architectural rules — the mapping between signal IDs and concepts.

Each entry in this list maps one signal ID to a concept ID and a kind.
The scanner emits signals, the rule engine uses this table to aggregate them
into per-concept ``Decision`` objects.

Format: ``(signal_id, concept_id, kind)`` where:
- ``kind`` is one of: ``presence``, ``absence``, ``misconfiguration``, ``anti_pattern``.
- A ``presence`` signal ID means: "I found evidence that this concept IS implemented."
- An ``absence`` signal ID means: "I found evidence this concept is NOT implemented."
- A ``misconfiguration`` signal ID means: "I found evidence the concept exists but is wrong."
- An ``anti_pattern`` signal ID means: "I found evidence of an anti-pattern."

These entries are loaded by the rule engine from ``config/rules/architecture/rules.yaml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

# ─────────────────────────────────────────────────────────────────────────────
# Architecture rule — maps signal IDs to concept IDs and kinds
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ArchitectureRule:
    """Maps a signal ID to a concept and a kind."""
    signal_id: str
    concept_id: str
    kind: str  # "presence" | "absence" | "misconfiguration" | "anti_pattern"


# ─────────────────────────────────────────────────────────────────────────────
# Foundation
# ─────────────────────────────────────────────────────────────────────────────

FOUNDATION_CONFIG_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.config.presence.dotenv", "foundation.config", "presence"),
    ArchitectureRule("foundation.config.presence.environ", "foundation.config", "presence"),
    ArchitectureRule("foundation.config.presence.os-getenv", "foundation.config", "presence"),
    ArchitectureRule("foundation.config.absence", "foundation.config", "absence"),
    ArchitectureRule("foundation.config.misconfig.hardcoded-secret", "foundation.config", "misconfiguration"),
]

FOUNDATION_LOGGING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.logging.presence.logging-module", "foundation.logging", "presence"),
    ArchitectureRule("foundation.logging.presence.loguru", "foundation.logging", "presence"),
    ArchitectureRule("foundation.logging.presence.structlog", "foundation.logging", "presence"),
    ArchitectureRule("foundation.logging.presence.custom-logger", "foundation.logging", "presence"),
    ArchitectureRule("foundation.logging.absence", "foundation.logging", "absence"),
    ArchitectureRule("foundation.logging.misconfig.no-logging", "foundation.logging", "misconfiguration"),
]

FOUNDATION_CACHING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.caching.presence.redis", "foundation.caching", "presence"),
    ArchitectureRule("foundation.caching.presence.memcache", "foundation.caching", "presence"),
    ArchitectureRule("foundation.caching.presence.lru-cache", "foundation.caching", "presence"),
    ArchitectureRule("foundation.caching.absence", "foundation.caching", "absence"),
]

FOUNDATION_ERROR_HANDLING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.error-handling.presence.errorhandler", "foundation.error-handling", "presence"),
    ArchitectureRule("foundation.error-handling.presence.try-except", "foundation.error-handling", "presence"),
    ArchitectureRule("foundation.error-handling.presence.middleware", "foundation.error-handling", "presence"),
    ArchitectureRule("foundation.error-handling.presence.custom-error", "foundation.error-handling", "presence"),
    ArchitectureRule("foundation.error-handling.absence", "foundation.error-handling", "absence"),
    ArchitectureRule("foundation.error-handling.misconfig.bare-except", "foundation.error-handling", "misconfiguration"),
    ArchitectureRule("foundation.error-handling.misconfig.print-exception", "foundation.error-handling", "misconfiguration"),
    ArchitectureRule("foundation.error-handling.anti.no-error-handling", "foundation.error-handling", "anti_pattern"),
]

FOUNDATION_VALIDATION_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.validation.presence.pydantic", "foundation.validation", "presence"),
    ArchitectureRule("foundation.validation.presence.zod", "foundation.validation", "presence"),
    ArchitectureRule("foundation.validation.presence.joi", "foundation.validation", "presence"),
    ArchitectureRule("foundation.validation.presence.validator", "foundation.validation", "presence"),
    ArchitectureRule("foundation.validation.presence.class-validator", "foundation.validation", "presence"),
    ArchitectureRule("foundation.validation.presence.manual-check", "foundation.validation", "presence"),
    ArchitectureRule("foundation.validation.absence", "foundation.validation", "absence"),
    ArchitectureRule("foundation.validation.misconfig.no-sanitize", "foundation.validation", "misconfiguration"),
]

FOUNDATION_AUTH_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.auth.presence.jwt", "foundation.auth", "presence"),
    ArchitectureRule("foundation.auth.presence.oauth", "foundation.auth", "presence"),
    ArchitectureRule("foundation.auth.presence.passport", "foundation.auth", "presence"),
    ArchitectureRule("foundation.auth.presence.session", "foundation.auth", "presence"),
    ArchitectureRule("foundation.auth.presence.bcrypt", "foundation.auth", "presence"),
    ArchitectureRule("foundation.auth.presence.argon2", "foundation.auth", "presence"),
    ArchitectureRule("foundation.auth.absence", "foundation.auth", "absence"),
    ArchitectureRule("foundation.auth.misconfig.plaintext-password", "foundation.auth", "misconfiguration"),
]

FOUNDATION_AUTHORIZATION_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.authorization.presence.rbac", "foundation.authorization", "presence"),
    ArchitectureRule("foundation.authorization.presence.casbin", "foundation.authorization", "presence"),
    ArchitectureRule("foundation.authorization.presence.policy", "foundation.authorization", "presence"),
    ArchitectureRule("foundation.authorization.presence.role-check", "foundation.authorization", "presence"),
    ArchitectureRule("foundation.authorization.presence.permission-decorator", "foundation.authorization", "presence"),
    ArchitectureRule("foundation.authorization.absence", "foundation.authorization", "absence"),
]

FOUNDATION_RATE_LIMITING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("foundation.rate-limiting.presence.express-rate-limit", "foundation.rate-limiting", "presence"),
    ArchitectureRule("foundation.rate-limiting.presence.slowapi", "foundation.rate-limiting", "presence"),
    ArchitectureRule("foundation.rate-limiting.presence.ratelimit", "foundation.rate-limiting", "presence"),
    ArchitectureRule("foundation.rate-limiting.presence.throttle", "foundation.rate-limiting", "presence"),
    ArchitectureRule("foundation.rate-limiting.absence", "foundation.rate-limiting", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────────────────────────────────────

SECURITY_SECRETS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("security.secrets-management.presence.vault", "security.secrets-management", "presence"),
    ArchitectureRule("security.secrets-management.presence.aws-secrets-manager", "security.secrets-management", "presence"),
    ArchitectureRule("security.secrets-management.presence.azure-keyvault", "security.secrets-management", "presence"),
    ArchitectureRule("security.secrets-management.presence.doppler", "security.secrets-management", "presence"),
    ArchitectureRule("security.secrets-management.presence.sops", "security.secrets-management", "presence"),
    ArchitectureRule("security.secrets-management.absence", "security.secrets-management", "absence"),
    ArchitectureRule("security.secrets-management.misconfig.hardcoded-secret", "security.secrets-management", "misconfiguration"),
    ArchitectureRule("security.secrets-management.anti.secret-in-code", "security.secrets-management", "anti_pattern"),
]

SECURITY_HTTPS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("security.https.presence.force-ssl", "security.https", "presence"),
    ArchitectureRule("security.https.presence.https-redirect", "security.https", "presence"),
    ArchitectureRule("security.https.presence.certbot", "security.https", "presence"),
    ArchitectureRule("security.https.presence.tls-config", "security.https", "presence"),
    ArchitectureRule("security.https.absence", "security.https", "absence"),
]

SECURITY_CORS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("security.cors.presence.cors", "security.cors", "presence"),
    ArchitectureRule("security.cors.presence.fastapi-cors", "security.cors", "presence"),
    ArchitectureRule("security.cors.presence.express-cors", "security.cors", "presence"),
    ArchitectureRule("security.cors.absence", "security.cors", "absence"),
    ArchitectureRule("security.cors.misconfig.wildcard-origin", "security.cors", "misconfiguration"),
    ArchitectureRule("security.cors.anti.wildcard-cors", "security.cors", "anti_pattern"),
]

SECURITY_HEADERS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("security.headers.presence.helmet", "security.headers", "presence"),
    ArchitectureRule("security.headers.presence.hsts", "security.headers", "presence"),
    ArchitectureRule("security.headers.presence.csp", "security.headers", "presence"),
    ArchitectureRule("security.headers.presence.x-frame-options", "security.headers", "presence"),
    ArchitectureRule("security.headers.absence", "security.headers", "absence"),
]

SECURITY_SANITIZATION_RULES: List[ArchitectureRule] = [
    ArchitectureRule("security.sanitization.presence.sanitize", "security.sanitization", "presence"),
    ArchitectureRule("security.sanitization.presence.escape", "security.sanitization", "presence"),
    ArchitectureRule("security.sanitization.presence.parameterized-query", "security.sanitization", "presence"),
    ArchitectureRule("security.sanitization.presence.prepared-statement", "security.sanitization", "presence"),
    ArchitectureRule("security.sanitization.presence.orm-default", "security.sanitization", "presence"),
    ArchitectureRule("security.sanitization.absence", "security.sanitization", "absence"),
    ArchitectureRule("security.sanitization.misconfig.sql-format", "security.sanitization", "misconfiguration"),
    ArchitectureRule("security.sanitization.misconfig.f-string-sql", "security.sanitization", "misconfiguration"),
    ArchitectureRule("security.sanitization.anti.raw-sql-concat", "security.sanitization", "anti_pattern"),
]

SECURITY_DEPENDENCY_SCAN_RULES: List[ArchitectureRule] = [
    ArchitectureRule("security.dependency-scan.presence.snyk", "security.dependency-scan", "presence"),
    ArchitectureRule("security.dependency-scan.presence.dependabot", "security.dependency-scan", "presence"),
    ArchitectureRule("security.dependency-scan.presence.pip-audit", "security.dependency-scan", "presence"),
    ArchitectureRule("security.dependency-scan.presence.trivy", "security.dependency-scan", "presence"),
    ArchitectureRule("security.dependency-scan.presence.npm-audit", "security.dependency-scan", "presence"),
    ArchitectureRule("security.dependency-scan.presence.safety", "security.dependency-scan", "presence"),
    ArchitectureRule("security.dependency-scan.absence", "security.dependency-scan", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────

DATA_ORM_RULES: List[ArchitectureRule] = [
    ArchitectureRule("data.orm.presence.sqlalchemy", "data.orm", "presence"),
    ArchitectureRule("data.orm.presence.prisma", "data.orm", "presence"),
    ArchitectureRule("data.orm.presence.typeorm", "data.orm", "presence"),
    ArchitectureRule("data.orm.presence.sequelize", "data.orm", "presence"),
    ArchitectureRule("data.orm.presence.eloquent", "data.orm", "presence"),
    ArchitectureRule("data.orm.presence.gorm", "data.orm", "presence"),
    ArchitectureRule("data.orm.presence.django-orm", "data.orm", "presence"),
    ArchitectureRule("data.orm.absence", "data.orm", "absence"),
    ArchitectureRule("data.orm.misconfig.raw-sql-concat", "data.orm", "misconfiguration"),
    ArchitectureRule("data.orm.anti.raw-sql-only", "data.orm", "anti_pattern"),
]

DATA_MIGRATIONS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("data.migrations.presence.alembic", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.presence.flyway", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.presence.liquibase", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.presence.knex-migrate", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.presence.prisma-migrate", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.presence.django-migrate", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.presence.migration-dir", "data.migrations", "presence"),
    ArchitectureRule("data.migrations.absence", "data.migrations", "absence"),
]

DATA_INDEXING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("data.indexing.presence.index", "data.indexing", "presence"),
    ArchitectureRule("data.indexing.presence.create-index", "data.indexing", "presence"),
    ArchitectureRule("data.indexing.presence.unique-index", "data.indexing", "presence"),
    ArchitectureRule("data.indexing.presence.index-model", "data.indexing", "presence"),
    ArchitectureRule("data.indexing.absence", "data.indexing", "absence"),
]

DATA_BACKUP_RULES: List[ArchitectureRule] = [
    ArchitectureRule("data.backup.presence.backup-script", "data.backup", "presence"),
    ArchitectureRule("data.backup.presence.pg-dump", "data.backup", "presence"),
    ArchitectureRule("data.backup.presence.snapshot", "data.backup", "presence"),
    ArchitectureRule("data.backup.presence.restore", "data.backup", "presence"),
    ArchitectureRule("data.backup.presence.replication", "data.backup", "presence"),
    ArchitectureRule("data.backup.absence", "data.backup", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Observability
# ─────────────────────────────────────────────────────────────────────────────

OBS_METRICS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("observability.metrics.presence.prometheus", "observability.metrics", "presence"),
    ArchitectureRule("observability.metrics.presence.datadog", "observability.metrics", "presence"),
    ArchitectureRule("observability.metrics.presence.newrelic", "observability.metrics", "presence"),
    ArchitectureRule("observability.metrics.presence.statsd", "observability.metrics", "presence"),
    ArchitectureRule("observability.metrics.presence.opentelemetry", "observability.metrics", "presence"),
    ArchitectureRule("observability.metrics.presence.custom-metrics", "observability.metrics", "presence"),
    ArchitectureRule("observability.metrics.absence", "observability.metrics", "absence"),
]

OBS_TRACING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("observability.tracing.presence.opentelemetry", "observability.tracing", "presence"),
    ArchitectureRule("observability.tracing.presence.jaeger", "observability.tracing", "presence"),
    ArchitectureRule("observability.tracing.presence.zipkin", "observability.tracing", "presence"),
    ArchitectureRule("observability.tracing.presence.tracer", "observability.tracing", "presence"),
    ArchitectureRule("observability.tracing.presence.span", "observability.tracing", "presence"),
    ArchitectureRule("observability.tracing.absence", "observability.tracing", "absence"),
]

OBS_ALERTING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("observability.alerting.presence.alertmanager", "observability.alerting", "presence"),
    ArchitectureRule("observability.alerting.presence.pagerduty", "observability.alerting", "presence"),
    ArchitectureRule("observability.alerting.presence.opsgenie", "observability.alerting", "presence"),
    ArchitectureRule("observability.alerting.presence.alert", "observability.alerting", "presence"),
    ArchitectureRule("observability.alerting.presence.slo", "observability.alerting", "presence"),
    ArchitectureRule("observability.alerting.absence", "observability.alerting", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Resilience
# ─────────────────────────────────────────────────────────────────────────────

RES_CIRCUIT_BREAKER_RULES: List[ArchitectureRule] = [
    ArchitectureRule("resilience.circuit-breaker.presence.pybreaker", "resilience.circuit-breaker", "presence"),
    ArchitectureRule("resilience.circuit-breaker.presence.opossum", "resilience.circuit-breaker", "presence"),
    ArchitectureRule("resilience.circuit-breaker.presence.hystrix", "resilience.circuit-breaker", "presence"),
    ArchitectureRule("resilience.circuit-breaker.presence.resilience4j", "resilience.circuit-breaker", "presence"),
    ArchitectureRule("resilience.circuit-breaker.presence.breaker-decorator", "resilience.circuit-breaker", "presence"),
    ArchitectureRule("resilience.circuit-breaker.absence", "resilience.circuit-breaker", "absence"),
]

RES_RETRIES_RULES: List[ArchitectureRule] = [
    ArchitectureRule("resilience.retries.presence.tenacity", "resilience.retries", "presence"),
    ArchitectureRule("resilience.retries.presence.backoff", "resilience.retries", "presence"),
    ArchitectureRule("resilience.retries.presence.retry-decorator", "resilience.retries", "presence"),
    ArchitectureRule("resilience.retries.presence.exponential-backoff", "resilience.retries", "presence"),
    ArchitectureRule("resilience.retries.absence", "resilience.retries", "absence"),
    ArchitectureRule("resilience.retries.misconfig.fixed-retry", "resilience.retries", "misconfiguration"),
]

RES_TIMEOUTS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("resilience.timeouts.presence.timeout", "resilience.timeouts", "presence"),
    ArchitectureRule("resilience.timeouts.presence.read-timeout", "resilience.timeouts", "presence"),
    ArchitectureRule("resilience.timeouts.presence.connect-timeout", "resilience.timeouts", "presence"),
    ArchitectureRule("resilience.timeouts.absence", "resilience.timeouts", "absence"),
    ArchitectureRule("resilience.timeouts.misconfig.no-timeout", "resilience.timeouts", "misconfiguration"),
]

RES_DEAD_LETTER_RULES: List[ArchitectureRule] = [
    ArchitectureRule("resilience.dead-letter.presence.dlq", "resilience.dead-letter", "presence"),
    ArchitectureRule("resilience.dead-letter.presence.dead-letter-queue", "resilience.dead-letter", "presence"),
    ArchitectureRule("resilience.dead-letter.presence.dead_letter", "resilience.dead-letter", "presence"),
    ArchitectureRule("resilience.dead-letter.presence.requeue", "resilience.dead-letter", "presence"),
    ArchitectureRule("resilience.dead-letter.absence", "resilience.dead-letter", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Deployment
# ─────────────────────────────────────────────────────────────────────────────

DEPLOY_CONTAINERS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("deployment.containers.presence.dockerfile", "deployment.containers", "presence"),
    ArchitectureRule("deployment.containers.presence.docker-compose", "deployment.containers", "presence"),
    ArchitectureRule("deployment.containers.presence.dockerignore", "deployment.containers", "presence"),
    ArchitectureRule("deployment.containers.absence", "deployment.containers", "absence"),
]

DEPLOY_ORCHESTRATION_RULES: List[ArchitectureRule] = [
    ArchitectureRule("deployment.orchestration.presence.kubernetes", "deployment.orchestration", "presence"),
    ArchitectureRule("deployment.orchestration.presence.helm", "deployment.orchestration", "presence"),
    ArchitectureRule("deployment.orchestration.presence.argo", "deployment.orchestration", "presence"),
    ArchitectureRule("deployment.orchestration.presence.ecs", "deployment.orchestration", "presence"),
    ArchitectureRule("deployment.orchestration.absence", "deployment.orchestration", "absence"),
]

DEPLOY_CI_CD_RULES: List[ArchitectureRule] = [
    ArchitectureRule("deployment.ci-cd.presence.github-actions", "deployment.ci-cd", "presence"),
    ArchitectureRule("deployment.ci-cd.presence.gitlab-ci", "deployment.ci-cd", "presence"),
    ArchitectureRule("deployment.ci-cd.presence.jenkins", "deployment.ci-cd", "presence"),
    ArchitectureRule("deployment.ci-cd.presence.circleci", "deployment.ci-cd", "presence"),
    ArchitectureRule("deployment.ci-cd.presence.azure-pipelines", "deployment.ci-cd", "presence"),
    ArchitectureRule("deployment.ci-cd.presence.docker-compose", "deployment.ci-cd", "presence"),
    ArchitectureRule("deployment.ci-cd.absence", "deployment.ci-cd", "absence"),
]

DEPLOY_IAAC_RULES: List[ArchitectureRule] = [
    ArchitectureRule("deployment.iaac.presence.terraform", "deployment.iaac", "presence"),
    ArchitectureRule("deployment.iaac.presence.cloudformation", "deployment.iaac", "presence"),
    ArchitectureRule("deployment.iaac.presence.pulumi", "deployment.iaac", "presence"),
    ArchitectureRule("deployment.iaac.presence.arm-template", "deployment.iaac", "presence"),
    ArchitectureRule("deployment.iaac.presence.bicep", "deployment.iaac", "presence"),
    ArchitectureRule("deployment.iaac.absence", "deployment.iaac", "absence"),
]

DEPLOY_HEALTHCHECKS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("deployment.healthchecks.presence.health-endpoint", "deployment.healthchecks", "presence"),
    ArchitectureRule("deployment.healthchecks.presence.readiness-endpoint", "deployment.healthchecks", "presence"),
    ArchitectureRule("deployment.healthchecks.presence.liveness-endpoint", "deployment.healthchecks", "presence"),
    ArchitectureRule("deployment.healthchecks.absence", "deployment.healthchecks", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Performance
# ─────────────────────────────────────────────────────────────────────────────

PERF_CONNECTION_POOL_RULES: List[ArchitectureRule] = [
    ArchitectureRule("performance.connection-pool.presence.pool", "performance.connection-pool", "presence"),
    ArchitectureRule("performance.connection-pool.presence.pool-size", "performance.connection-pool", "presence"),
    ArchitectureRule("performance.connection-pool.presence.pgbouncer", "performance.connection-pool", "presence"),
    ArchitectureRule("performance.connection-pool.presence.connection-pool", "performance.connection-pool", "presence"),
    ArchitectureRule("performance.connection-pool.absence", "performance.connection-pool", "absence"),
]

PERF_ASYNC_RULES: List[ArchitectureRule] = [
    ArchitectureRule("performance.async.presence.async-def", "performance.async", "presence"),
    ArchitectureRule("performance.async.presence.await", "performance.async", "presence"),
    ArchitectureRule("performance.async.presence.asyncio", "performance.async", "presence"),
    ArchitectureRule("performance.async.presence.promise", "performance.async", "presence"),
    ArchitectureRule("performance.async.presence.event-loop", "performance.async", "presence"),
    ArchitectureRule("performance.async.absence", "performance.async", "absence"),
]

PERF_PAGINATION_RULES: List[ArchitectureRule] = [
    ArchitectureRule("performance.pagination.presence.limit", "performance.pagination", "presence"),
    ArchitectureRule("performance.pagination.presence.offset", "performance.pagination", "presence"),
    ArchitectureRule("performance.pagination.presence.cursor", "performance.pagination", "presence"),
    ArchitectureRule("performance.pagination.presence.page", "performance.pagination", "presence"),
    ArchitectureRule("performance.pagination.absence", "performance.pagination", "absence"),
]

PERF_CDN_RULES: List[ArchitectureRule] = [
    ArchitectureRule("performance.cdn.presence.cloudfront", "performance.cdn", "presence"),
    ArchitectureRule("performance.cdn.presence.cloudflare", "performance.cdn", "presence"),
    ArchitectureRule("performance.cdn.presence.fastly", "performance.cdn", "presence"),
    ArchitectureRule("performance.cdn.presence.akamai", "performance.cdn", "presence"),
    ArchitectureRule("performance.cdn.absence", "performance.cdn", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Streaming
# ─────────────────────────────────────────────────────────────────────────────

STREAM_MSG_BROKER_RULES: List[ArchitectureRule] = [
    ArchitectureRule("streaming.message-broker.presence.kafka", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.presence.rabbitmq", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.presence.nats", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.presence.pulsar", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.presence.redis-pubsub", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.presence.aws-sqs", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.presence.azure-servicebus", "streaming.message-broker", "presence"),
    ArchitectureRule("streaming.message-broker.absence", "streaming.message-broker", "absence"),
]

STREAM_WEBSOCKETS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("streaming.websockets.presence.websockets", "streaming.websockets", "presence"),
    ArchitectureRule("streaming.websockets.presence.socket-io", "streaming.websockets", "presence"),
    ArchitectureRule("streaming.websockets.presence.fastapi-websocket", "streaming.websockets", "presence"),
    ArchitectureRule("streaming.websockets.presence.ws-lib", "streaming.websockets", "presence"),
    ArchitectureRule("streaming.websockets.absence", "streaming.websockets", "absence"),
]

STREAM_EVENT_STREAMING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("streaming.event-streaming.presence.kafka", "streaming.event-streaming", "presence"),
    ArchitectureRule("streaming.event-streaming.presence.pulsar", "streaming.event-streaming", "presence"),
    ArchitectureRule("streaming.event-streaming.presence.kinesis", "streaming.event-streaming", "presence"),
    ArchitectureRule("streaming.event-streaming.presence.consumer-group", "streaming.event-streaming", "presence"),
    ArchitectureRule("streaming.event-streaming.absence", "streaming.event-streaming", "absence"),
]

STREAM_WEBRTC_RULES: List[ArchitectureRule] = [
    ArchitectureRule("streaming.webrtc.presence.webrtc", "streaming.webrtc", "presence"),
    ArchitectureRule("streaming.webrtc.presence.mediasoup", "streaming.webrtc", "presence"),
    ArchitectureRule("streaming.webrtc.presence.livekit", "streaming.webrtc", "presence"),
    ArchitectureRule("streaming.webrtc.presence.janus", "streaming.webrtc", "presence"),
    ArchitectureRule("streaming.webrtc.absence", "streaming.webrtc", "absence"),
]

STREAM_LIVE_STREAMING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("streaming.live-streaming.presence.rtmp", "streaming.live-streaming", "presence"),
    ArchitectureRule("streaming.live-streaming.presence.hls", "streaming.live-streaming", "presence"),
    ArchitectureRule("streaming.live-streaming.presence.dash", "streaming.live-streaming", "presence"),
    ArchitectureRule("streaming.live-streaming.presence.transcode", "streaming.live-streaming", "presence"),
    ArchitectureRule("streaming.live-streaming.presence.ffmpeg", "streaming.live-streaming", "presence"),
    ArchitectureRule("streaming.live-streaming.absence", "streaming.live-streaming", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# ML & AI
# ─────────────────────────────────────────────────────────────────────────────

ML_MODEL_SERVING_RULES: List[ArchitectureRule] = [
    ArchitectureRule("ml.model-serving.presence.torchserve", "ml.model-serving", "presence"),
    ArchitectureRule("ml.model-serving.presence.triton", "ml.model-serving", "presence"),
    ArchitectureRule("ml.model-serving.presence.mlflow", "ml.model-serving", "presence"),
    ArchitectureRule("ml.model-serving.presence.bentoml", "ml.model-serving", "presence"),
    ArchitectureRule("ml.model-serving.presence.inference", "ml.model-serving", "presence"),
    ArchitectureRule("ml.model-serving.presence.predict", "ml.model-serving", "presence"),
    ArchitectureRule("ml.model-serving.absence", "ml.model-serving", "absence"),
]

ML_NLP_RULES: List[ArchitectureRule] = [
    ArchitectureRule("ml.nlp.presence.transformers", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.spacy", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.nltk", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.llm", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.gpt", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.bert", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.embedding", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.langchain", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.presence.llamaindex", "ml.nlp", "presence"),
    ArchitectureRule("ml.nlp.absence", "ml.nlp", "absence"),
]

ML_TRANSFORMERS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("ml.transformers.presence.transformer", "ml.transformers", "presence"),
    ArchitectureRule("ml.transformers.presence.attention", "ml.transformers", "presence"),
    ArchitectureRule("ml.transformers.presence.self-attention", "ml.transformers", "presence"),
    ArchitectureRule("ml.transformers.presence.multi-head", "ml.transformers", "presence"),
    ArchitectureRule("ml.transformers.presence.encoder", "ml.transformers", "presence"),
    ArchitectureRule("ml.transformers.presence.decoder", "ml.transformers", "presence"),
    ArchitectureRule("ml.transformers.absence", "ml.transformers", "absence"),
]

ML_MLOPS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("ml.mlops.presence.mlops", "ml.mlops", "presence"),
    ArchitectureRule("ml.mlops.presence.training", "ml.mlops", "presence"),
    ArchitectureRule("ml.mlops.presence.evaluation", "ml.mlops", "presence"),
    ArchitectureRule("ml.mlops.presence.model-registry", "ml.mlops", "presence"),
    ArchitectureRule("ml.mlops.presence.drift", "ml.mlops", "presence"),
    ArchitectureRule("ml.mlops.presence.kubeflow", "ml.mlops", "presence"),
    ArchitectureRule("ml.mlops.absence", "ml.mlops", "absence"),
]

ML_FEATURE_STORE_RULES: List[ArchitectureRule] = [
    ArchitectureRule("ml.feature-store.presence.feast", "ml.feature-store", "presence"),
    ArchitectureRule("ml.feature-store.presence.tecton", "ml.feature-store", "presence"),
    ArchitectureRule("ml.feature-store.presence.feature-store", "ml.feature-store", "presence"),
    ArchitectureRule("ml.feature-store.absence", "ml.feature-store", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Networking
# ─────────────────────────────────────────────────────────────────────────────

NET_PROXY_RULES: List[ArchitectureRule] = [
    ArchitectureRule("networking.proxy.presence.nginx", "networking.proxy", "presence"),
    ArchitectureRule("networking.proxy.presence.traefik", "networking.proxy", "presence"),
    ArchitectureRule("networking.proxy.presence.kong", "networking.proxy", "presence"),
    ArchitectureRule("networking.proxy.presence.envoy", "networking.proxy", "presence"),
    ArchitectureRule("networking.proxy.presence.api-gateway", "networking.proxy", "presence"),
    ArchitectureRule("networking.proxy.presence.upstream", "networking.proxy", "presence"),
    ArchitectureRule("networking.proxy.absence", "networking.proxy", "absence"),
]

NET_LOAD_BALANCER_RULES: List[ArchitectureRule] = [
    ArchitectureRule("networking.load-balancer.presence.load-balancer", "networking.load-balancer", "presence"),
    ArchitectureRule("networking.load-balancer.presence.lb", "networking.load-balancer", "presence"),
    ArchitectureRule("networking.load-balancer.presence.alb", "networking.load-balancer", "presence"),
    ArchitectureRule("networking.load-balancer.presence.elb", "networking.load-balancer", "presence"),
    ArchitectureRule("networking.load-balancer.presence.nginx-upstream", "networking.load-balancer", "presence"),
    ArchitectureRule("networking.load-balancer.absence", "networking.load-balancer", "absence"),
]

NET_SERVICE_MESH_RULES: List[ArchitectureRule] = [
    ArchitectureRule("networking.service-mesh.presence.istio", "networking.service-mesh", "presence"),
    ArchitectureRule("networking.service-mesh.presence.linkerd", "networking.service-mesh", "presence"),
    ArchitectureRule("networking.service-mesh.presence.service-mesh", "networking.service-mesh", "presence"),
    ArchitectureRule("networking.service-mesh.presence.sidecar", "networking.service-mesh", "presence"),
    ArchitectureRule("networking.service-mesh.absence", "networking.service-mesh", "absence"),
]

NET_DNS_RULES: List[ArchitectureRule] = [
    ArchitectureRule("networking.dns.presence.dns", "networking.dns", "presence"),
    ArchitectureRule("networking.dns.presence.consul", "networking.dns", "presence"),
    ArchitectureRule("networking.dns.presence.core-dns", "networking.dns", "presence"),
    ArchitectureRule("networking.dns.presence.service-discovery", "networking.dns", "presence"),
    ArchitectureRule("networking.dns.absence", "networking.dns", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Compliance
# ─────────────────────────────────────────────────────────────────────────────

COMPLIANCE_PII_RULES: List[ArchitectureRule] = [
    ArchitectureRule("compliance.pii.presence.pii", "compliance.pii", "presence"),
    ArchitectureRule("compliance.pii.presence.anonymize", "compliance.pii", "presence"),
    ArchitectureRule("compliance.pii.presence.redact", "compliance.pii", "presence"),
    ArchitectureRule("compliance.pii.absence", "compliance.pii", "absence"),
    ArchitectureRule("compliance.pii.misconfig.unencrypted-pii", "compliance.pii", "misconfiguration"),
]

COMPLIANCE_AUDIT_LOG_RULES: List[ArchitectureRule] = [
    ArchitectureRule("compliance.audit-log.presence.audit", "compliance.audit-log", "presence"),
    ArchitectureRule("compliance.audit-log.presence.audit-log", "compliance.audit-log", "presence"),
    ArchitectureRule("compliance.audit-log.presence.soc2", "compliance.audit-log", "presence"),
    ArchitectureRule("compliance.audit-log.presence.hipaa", "compliance.audit-log", "presence"),
    ArchitectureRule("compliance.audit-log.absence", "compliance.audit-log", "absence"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Complete list
# ─────────────────────────────────────────────────────────────────────────────

ALL_ARCHITECTURE_RULES: List[ArchitectureRule] = [
    # Foundation
    *FOUNDATION_CONFIG_RULES,
    *FOUNDATION_LOGGING_RULES,
    *FOUNDATION_CACHING_RULES,
    *FOUNDATION_ERROR_HANDLING_RULES,
    *FOUNDATION_VALIDATION_RULES,
    *FOUNDATION_AUTH_RULES,
    *FOUNDATION_AUTHORIZATION_RULES,
    *FOUNDATION_RATE_LIMITING_RULES,
    # Security
    *SECURITY_SECRETS_RULES,
    *SECURITY_HTTPS_RULES,
    *SECURITY_CORS_RULES,
    *SECURITY_HEADERS_RULES,
    *SECURITY_SANITIZATION_RULES,
    *SECURITY_DEPENDENCY_SCAN_RULES,
    # Data
    *DATA_ORM_RULES,
    *DATA_MIGRATIONS_RULES,
    *DATA_INDEXING_RULES,
    *DATA_BACKUP_RULES,
    # Observability
    *OBS_METRICS_RULES,
    *OBS_TRACING_RULES,
    *OBS_ALERTING_RULES,
    # Resilience
    *RES_CIRCUIT_BREAKER_RULES,
    *RES_RETRIES_RULES,
    *RES_TIMEOUTS_RULES,
    *RES_DEAD_LETTER_RULES,
    # Deployment
    *DEPLOY_CONTAINERS_RULES,
    *DEPLOY_ORCHESTRATION_RULES,
    *DEPLOY_CI_CD_RULES,
    *DEPLOY_IAAC_RULES,
    *DEPLOY_HEALTHCHECKS_RULES,
    # Performance
    *PERF_CONNECTION_POOL_RULES,
    *PERF_ASYNC_RULES,
    *PERF_PAGINATION_RULES,
    *PERF_CDN_RULES,
    # Streaming
    *STREAM_MSG_BROKER_RULES,
    *STREAM_WEBSOCKETS_RULES,
    *STREAM_EVENT_STREAMING_RULES,
    *STREAM_WEBRTC_RULES,
    *STREAM_LIVE_STREAMING_RULES,
    # ML & AI
    *ML_MODEL_SERVING_RULES,
    *ML_NLP_RULES,
    *ML_TRANSFORMERS_RULES,
    *ML_MLOPS_RULES,
    *ML_FEATURE_STORE_RULES,
    # Networking
    *NET_PROXY_RULES,
    *NET_LOAD_BALANCER_RULES,
    *NET_SERVICE_MESH_RULES,
    *NET_DNS_RULES,
    # Compliance
    *COMPLIANCE_PII_RULES,
    *COMPLIANCE_AUDIT_LOG_RULES,
]

# Lookup: signal_id -> concept_id
SIGNAL_ID_TO_CONCEPT: dict[str, str] = {r.signal_id: r.concept_id for r in ALL_ARCHITECTURE_RULES}

# Lookup: signal_id -> kind
SIGNAL_ID_TO_KIND: dict[str, str] = {r.signal_id: r.kind for r in ALL_ARCHITECTURE_RULES}
