#!/usr/bin/env python3
"""Phase 1 bootstrap — creates all missing concept files, project-classifications,
agent scopes, and rebuilds INDEX.yaml.

Run: python scripts/phase1_bootstrap.py
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_DIR = REPO_ROOT / "concepts"
AGENTS_DIR = REPO_ROOT / "config" / "agents"

# Agent ID → owning agent mapping
AGENT_MAP = {
    # Foundation
    "foundation.caching": "F-01",
    "foundation.config": "F-02",
    "foundation.logging": "F-03",
    "foundation.error-handling": "F-04",
    "foundation.validation": "F-05",
    "foundation.auth": "F-06",
    "foundation.authorization": "F-07",
    "foundation.rate-limiting": "F-08",
    # Security
    "security.https": "F-09",
    "security.cors": "F-09",
    "security.headers": "F-09",
    "security.secrets-management": "F-09",
    "security.sanitization": "F-09",
    "security.dependency-scan": "F-09",
    # Data
    "data.orm": "D-10",
    "data.migrations": "D-11",
    "data.indexing": "D-12",
    "data.backup": "D-13",
    # Observability
    "observability.metrics": "O-14",
    "observability.tracing": "O-15",
    "observability.alerting": "O-16",
    # Resilience
    "resilience.circuit-breaker": "R-17",
    "resilience.retries": "R-18",
    "resilience.timeouts": "R-19",
    "resilience.dead-letter": "R-20",
    # Deployment
    "deployment.containers": "D-21",
    "deployment.orchestration": "D-22",
    "deployment.ci-cd": "D-23",
    "deployment.iaac": "D-24",
    "deployment.healthchecks": "D-25",
    # Performance
    "performance.connection-pool": "P-26",
    "performance.async": "P-27",
    "performance.pagination": "P-28",
    "performance.cdn": "P-29",
    # Streaming
    "streaming.message-broker": "S-30",
    "streaming.websockets": "S-31",
    "streaming.event-streaming": "S-32",
    "streaming.webrtc": "S-33",
    "streaming.live-streaming": "S-34",
    # ML & AI
    "ml.nlp": "M-35",
    "ml.transformers": "M-35",
    "ml.mlops": "M-36",
    "ml.model-serving": "M-37",
    "ml.feature-store": "M-38",
    # Networking
    "networking.proxy": "N-39",
    "networking.load-balancer": "N-40",
    "networking.service-mesh": "N-41",
    "networking.dns": "N-42",
    # Compliance
    "compliance.pii": "C-43",
    "compliance.audit-log": "C-44",
    # Foundation extras
    "foundation.hld": "F-01",
    "foundation.lld": "F-01",
    "foundation.client-server": "F-01",
    "foundation.protocols": "F-01",
    "foundation.proxies": "F-01",
    "foundation.load-balancers": "F-01",
    "foundation.message-queues": "F-01",
    "foundation.db-scaling": "F-01",
    "foundation.connection-pooling": "F-01",
    "foundation.consistent-hashing": "F-01",
    "foundation.cap-consistency": "F-01",
    "foundation.latency-bandwidth": "F-01",
    "foundation.idempotency": "F-01",
    "foundation.fault-tolerance": "F-01",
}

# ─────────────────────────────────────────────────────────────────────────────
# Concept definitions for new files
# ─────────────────────────────────────────────────────────────────────────────

NEW_CONCEPTS: list[dict[str, Any]] = [
    # ── Security ─────────────────────────────────────────────────────────────
    {
        "id": "security.https",
        "category": "security",
        "name": "HTTPS / TLS",
        "owning_agent": "F-09",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["tls", "ssl", "encryption", "certificates"],
        "related": ["security.cors", "security.headers"],
        "file": "security/https.md",
    },
    {
        "id": "security.headers",
        "category": "security",
        "name": "Security Headers",
        "owning_agent": "F-09",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["helmet", "csp", "hsts", "x-frame-options"],
        "related": ["security.https", "security.cors"],
        "file": "security/headers.md",
    },
    {
        "id": "security.sanitization",
        "category": "security",
        "name": "Input Sanitization",
        "owning_agent": "F-09",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["xss", "sql-injection", "sanitize", "escape"],
        "related": ["security.dependency-scan", "foundation.validation"],
        "file": "security/sanitization.md",
    },
    {
        "id": "security.secrets-management",
        "category": "security",
        "name": "Secrets Management",
        "owning_agent": "F-09",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["vault", "secrets", "credentials", "rotation"],
        "related": ["foundation.config", "security.https"],
        "file": "security/secrets-management.md",
    },
    {
        "id": "security.dependency-scan",
        "category": "security",
        "name": "Dependency Scanning",
        "owning_agent": "F-09",
        "maturity": "emerging",
        "languages": ["any"],
        "tags": ["snyk", "dependabot", "pip-audit", "trivy"],
        "related": ["deployment.ci-cd", "security.sanitization"],
        "file": "security/dependency-scan.md",
    },
    # ── Data ──────────────────────────────────────────────────────────────────
    {
        "id": "data.orm",
        "category": "data",
        "name": "ORM / Data Mapper",
        "owning_agent": "D-10",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java", "kotlin", "php", "ruby"],
        "tags": ["sqlalchemy", "prisma", "typeorm", "eloquent", "gorm"],
        "related": ["data.migrations", "data.indexing"],
        "file": "data/orm.md",
    },
    {
        "id": "data.migrations",
        "category": "data",
        "name": "Database Migrations",
        "owning_agent": "D-11",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java", "php"],
        "tags": ["alembic", "flyway", "liquibase", "prisma-migrate"],
        "related": ["data.orm", "data.backup"],
        "file": "data/migrations.md",
    },
    {
        "id": "data.indexing",
        "category": "data",
        "name": "Database Indexing",
        "owning_agent": "D-12",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["b-tree", "composite-index", "covering-index", "query-optimization"],
        "related": ["data.orm", "performance.pagination"],
        "file": "data/indexing.md",
    },
    {
        "id": "data.backup",
        "category": "data",
        "name": "Backup & Recovery",
        "owning_agent": "D-13",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["snapshot", "replication", "pitr", "point-in-time"],
        "related": ["data.migrations", "compliance.audit-log"],
        "file": "data/backup.md",
    },
    # ── Observability ────────────────────────────────────────────────────────
    {
        "id": "observability.metrics",
        "category": "observability",
        "name": "Metrics & Monitoring",
        "owning_agent": "O-14",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["prometheus", "datadog", "statsd", "histogram", "counter"],
        "related": ["observability.tracing", "observability.alerting"],
        "file": "observability/metrics.md",
    },
    {
        "id": "observability.tracing",
        "category": "observability",
        "name": "Distributed Tracing",
        "owning_agent": "O-15",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["opentelemetry", "jaeger", "zipkin", "trace-id", "span"],
        "related": ["observability.metrics", "streaming.event-streaming"],
        "file": "observability/tracing.md",
    },
    {
        "id": "observability.alerting",
        "category": "observability",
        "name": "Alerting & Paging",
        "owning_agent": "O-16",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["alertmanager", "pagerduty", "opsgenie", "slo", "error-budget"],
        "related": ["observability.metrics", "resilience.timeouts"],
        "file": "observability/alerting.md",
    },
    # ── Resilience ───────────────────────────────────────────────────────────
    {
        "id": "resilience.circuit-breaker",
        "category": "resilience",
        "name": "Circuit Breaker",
        "owning_agent": "R-17",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["pybreaker", "resilience4j", "hystrix", "opossum"],
        "related": ["resilience.retries", "resilience.timeouts"],
        "file": "resilience/circuit-breaker.md",
    },
    {
        "id": "resilience.retries",
        "category": "resilience",
        "name": "Retry Strategy",
        "owning_agent": "R-18",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["tenacity", "backoff", "exponential", "jitter"],
        "related": ["resilience.circuit-breaker", "foundation.idempotency"],
        "file": "resilience/retries.md",
    },
    {
        "id": "resilience.timeouts",
        "category": "resilience",
        "name": "Timeouts & Deadlines",
        "owning_agent": "R-19",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["connect-timeout", "read-timeout", "deadline", "context-timeout"],
        "related": ["resilience.circuit-breaker", "resilience.retries"],
        "file": "resilience/timeouts.md",
    },
    {
        "id": "resilience.dead-letter",
        "category": "resilience",
        "name": "Dead Letter Queues",
        "owning_agent": "R-20",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["dlq", "poison-message", "requeue", "sqs-dead-letter"],
        "related": ["streaming.message-broker", "resilience.retries"],
        "file": "resilience/dead-letter.md",
    },
    # ── Deployment ───────────────────────────────────────────────────────────
    {
        "id": "deployment.containers",
        "category": "deployment",
        "name": "Containerisation",
        "owning_agent": "D-21",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["docker", "dockerfile", "docker-compose", "image"],
        "related": ["deployment.orchestration", "deployment.ci-cd"],
        "file": "deployment/containers.md",
    },
    {
        "id": "deployment.orchestration",
        "category": "deployment",
        "name": "Container Orchestration",
        "owning_agent": "D-22",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["kubernetes", "k8s", "helm", "argo-cd", "ecs"],
        "related": ["deployment.containers", "networking.service-mesh"],
        "file": "deployment/orchestration.md",
    },
    {
        "id": "deployment.ci-cd",
        "category": "deployment",
        "name": "CI/CD Pipelines",
        "owning_agent": "D-23",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["github-actions", "gitlab-ci", "jenkins", "pipeline"],
        "related": ["deployment.iaac", "security.dependency-scan"],
        "file": "deployment/ci-cd.md",
    },
    {
        "id": "deployment.iaac",
        "category": "deployment",
        "name": "Infrastructure as Code",
        "owning_agent": "D-24",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["terraform", "cloudformation", "pulumi", "bicep"],
        "related": ["deployment.orchestration", "cloud.cost-optimization"],
        "file": "deployment/iaac.md",
    },
    {
        "id": "deployment.healthchecks",
        "category": "deployment",
        "name": "Health Checks",
        "owning_agent": "D-25",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["liveness", "readiness", "health-endpoint", "startup-probe"],
        "related": ["deployment.orchestration", "observability.metrics"],
        "file": "deployment/healthchecks.md",
    },
    # ── Performance ──────────────────────────────────────────────────────────
    {
        "id": "performance.connection-pool",
        "category": "performance",
        "name": "Connection Pooling",
        "owning_agent": "P-26",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["pgbouncer", "pool-size", "max-connections", "pooling"],
        "related": ["data.orm", "foundation.connection-pooling"],
        "file": "performance/connection-pool.md",
    },
    {
        "id": "performance.async",
        "category": "performance",
        "name": "Async Processing",
        "owning_agent": "P-27",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["async-await", "asyncio", "event-loop", "non-blocking"],
        "related": ["streaming.message-broker", "performance.connection-pool"],
        "file": "performance/async.md",
    },
    {
        "id": "performance.pagination",
        "category": "performance",
        "name": "Pagination Strategy",
        "owning_agent": "P-28",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["cursor-pagination", "offset", "keyset", "limit"],
        "related": ["data.indexing", "performance.connection-pool"],
        "file": "performance/pagination.md",
    },
    {
        "id": "performance.cdn",
        "category": "performance",
        "name": "CDN & Edge Caching",
        "owning_agent": "P-29",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["cloudflare", "cloudfront", "fastly", "edge"],
        "related": ["performance.async", "foundation.caching"],
        "file": "performance/cdn.md",
    },
    # ── Streaming ────────────────────────────────────────────────────────────
    {
        "id": "streaming.message-broker",
        "category": "streaming",
        "name": "Message Broker",
        "owning_agent": "S-30",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["kafka", "rabbitmq", "nats", "pulsar", "sqs"],
        "related": ["streaming.event-streaming", "resilience.dead-letter"],
        "file": "streaming/message-broker.md",
    },
    {
        "id": "streaming.websockets",
        "category": "streaming",
        "name": "WebSocket Connections",
        "owning_agent": "S-31",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["websocket", "socket-io", "real-time", "pub-sub"],
        "related": ["streaming.message-broker", "streaming.webrtc"],
        "file": "streaming/websockets.md",
    },
    {
        "id": "streaming.event-streaming",
        "category": "streaming",
        "name": "Event Streaming",
        "owning_agent": "S-32",
        "maturity": "emerging",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["kafka-streams", "kinesis", "event-driven", "consumer-group"],
        "related": ["streaming.message-broker", "observability.tracing"],
        "file": "streaming/event-streaming.md",
    },
    {
        "id": "streaming.webrtc",
        "category": "streaming",
        "name": "WebRTC",
        "owning_agent": "S-33",
        "maturity": "emerging",
        "languages": ["python", "typescript", "go"],
        "tags": ["webrtc", "mediasoup", "livekit", "p2p", "sfu"],
        "related": ["streaming.websockets", "streaming.live-streaming"],
        "file": "streaming/webrtc.md",
    },
    {
        "id": "streaming.live-streaming",
        "category": "streaming",
        "name": "Live Streaming",
        "owning_agent": "S-34",
        "maturity": "emerging",
        "languages": ["python", "typescript", "go"],
        "tags": ["rtmp", "hls", "dash", "ffmpeg", "transcode"],
        "related": ["streaming.webrtc", "cdn.cdn"],
        "file": "streaming/live-streaming.md",
    },
    # ── ML & AI ──────────────────────────────────────────────────────────────
    {
        "id": "ml.nlp",
        "category": "ml-ai",
        "name": "NLP Pipelines",
        "owning_agent": "M-35",
        "maturity": "stable",
        "languages": ["python", "typescript"],
        "tags": ["transformers", "spacy", "nltk", "llm", "openai", "embedding"],
        "related": ["ml.transformers", "ml.model-serving"],
        "file": "ml-ai/nlp.md",
    },
    {
        "id": "ml.transformers",
        "category": "ml-ai",
        "name": "Transformer Architectures",
        "owning_agent": "M-35",
        "maturity": "stable",
        "languages": ["python"],
        "tags": ["attention", "encoder", "decoder", "bert", "gpt"],
        "related": ["ml.nlp", "ml.mlops"],
        "file": "ml-ai/transformers.md",
    },
    {
        "id": "ml.mlops",
        "category": "ml-ai",
        "name": "MLOps Pipeline",
        "owning_agent": "M-36",
        "maturity": "emerging",
        "languages": ["python"],
        "tags": ["mlflow", "kubeflow", "drift", "model-registry", "training"],
        "related": ["ml.nlp", "deployment.orchestration"],
        "file": "ml-ai/mlops.md",
    },
    {
        "id": "ml.model-serving",
        "category": "ml-ai",
        "name": "Model Serving",
        "owning_agent": "M-37",
        "maturity": "emerging",
        "languages": ["python"],
        "tags": ["torchserve", "triton", "bentoml", "inference", "predict"],
        "related": ["ml.mlops", "deployment.containers"],
        "file": "ml-ai/model-serving.md",
    },
    {
        "id": "ml.feature-store",
        "category": "ml-ai",
        "name": "Feature Store",
        "owning_agent": "M-38",
        "maturity": "emerging",
        "languages": ["python"],
        "tags": ["feast", "tecton", "feature-view", "online-store"],
        "related": ["ml.mlops", "data.orm"],
        "file": "ml-ai/feature-store.md",
    },
    # ── Networking ───────────────────────────────────────────────────────────
    {
        "id": "networking.proxy",
        "category": "networking",
        "name": "Reverse Proxy",
        "owning_agent": "N-39",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["nginx", "traefik", "kong", "envoy"],
        "related": ["networking.load-balancer", "foundation.proxies"],
        "file": "networking/proxy.md",
    },
    {
        "id": "networking.load-balancer",
        "category": "networking",
        "name": "Load Balancer",
        "owning_agent": "N-40",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["alb", "elb", "lb", "round-robin", "least-connections"],
        "related": ["networking.proxy", "foundation.load-balancers"],
        "file": "networking/load-balancer.md",
    },
    {
        "id": "networking.service-mesh",
        "category": "networking",
        "name": "Service Mesh",
        "owning_agent": "N-41",
        "maturity": "emerging",
        "languages": ["any"],
        "tags": ["istio", "linkerd", "sidecar", "mtls", "envoy"],
        "related": ["networking.proxy", "deployment.orchestration"],
        "file": "networking/service-mesh.md",
    },
    {
        "id": "networking.dns",
        "category": "networking",
        "name": "DNS & Service Discovery",
        "owning_agent": "N-42",
        "maturity": "stable",
        "languages": ["any"],
        "tags": ["dns", "consul", "core-dns", "service-discovery"],
        "related": ["networking.proxy", "deployment.orchestration"],
        "file": "networking/dns.md",
    },
    # ── Compliance ───────────────────────────────────────────────────────────
    {
        "id": "compliance.pii",
        "category": "compliance",
        "name": "PII Protection",
        "owning_agent": "C-43",
        "maturity": "stable",
        "languages": ["python", "typescript", "java"],
        "tags": ["pii", "gdpr", "anonymize", "redact", "mask"],
        "related": ["security.sanitization", "compliance.audit-log"],
        "file": "compliance/pii.md",
    },
    {
        "id": "compliance.audit-log",
        "category": "compliance",
        "name": "Audit Logging",
        "owning_agent": "C-44",
        "maturity": "stable",
        "languages": ["python", "typescript", "go", "java"],
        "tags": ["audit", "soc2", "hipaa", "immutable-log", "tamper-proof"],
        "related": ["compliance.pii", "observability.tracing"],
        "file": "compliance/audit-log.md",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# 24 project categories
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_CLASSIFICATIONS = [
    {"id": "backend", "name": "Backend API Service", "agents": ["F-01", "F-02", "F-03", "F-04", "F-05", "F-06", "F-07", "F-08", "F-09", "D-10", "D-11", "D-12", "D-13", "O-14", "O-15", "O-16", "R-17", "R-18", "R-19", "R-20", "D-21", "D-22", "D-23", "D-24", "D-25", "P-26", "P-27", "P-28", "P-29", "N-39", "N-40", "C-43", "C-44"]},
    {"id": "frontend", "name": "Frontend Web Application", "agents": ["F-01", "F-03", "F-04", "F-05", "F-07", "F-08", "F-09", "D-21", "D-22", "D-23", "O-14", "N-39", "C-43", "C-44"]},
    {"id": "mobile", "name": "Mobile Application", "agents": ["F-01", "F-03", "F-04", "F-05", "F-06", "F-07", "F-09", "D-21", "D-23", "O-14", "C-43"]},
    {"id": "fullstack", "name": "Full-Stack Application", "agents": ["F-01", "F-02", "F-03", "F-04", "F-05", "F-06", "F-07", "F-08", "F-09", "D-10", "D-11", "D-21", "D-22", "D-23", "O-14", "O-15", "R-17", "R-18", "R-19", "P-26", "N-39", "C-43", "C-44"]},
    {"id": "ml-pipeline", "name": "ML Training Pipeline", "agents": ["M-35", "M-36", "M-37", "M-38", "D-10", "D-13", "O-14", "D-22", "R-17", "R-18", "R-19"]},
    {"id": "ml-serving", "name": "ML Model Serving", "agents": ["M-37", "M-36", "D-10", "D-21", "D-22", "O-14", "R-17", "R-18", "R-19", "P-26"]},
    {"id": "data-engineering", "name": "Data Engineering", "agents": ["D-10", "D-11", "D-12", "D-13", "S-30", "S-32", "O-14", "O-15", "R-17", "R-18", "R-19", "D-22", "D-23"]},
    {"id": "streaming", "name": "Real-Time Streaming", "agents": ["S-30", "S-31", "S-32", "S-33", "S-34", "R-17", "R-18", "R-19", "R-20", "O-14", "O-15", "D-22"]},
    {"id": "iot", "name": "IoT / Edge", "agents": ["F-01", "F-02", "F-03", "F-04", "F-09", "N-39", "N-40", "N-42", "D-21", "O-14", "R-17", "R-18"]},
    {"id": "blockchain", "name": "Blockchain / Web3", "agents": ["F-01", "F-06", "F-09", "D-10", "D-13", "N-39", "N-40", "C-43", "C-44", "R-17"]},
    {"id": "gaming", "name": "Gaming / Real-Time", "agents": ["S-30", "S-31", "S-33", "P-26", "P-27", "R-17", "R-18", "R-19", "N-40", "N-42"]},
    {"id": "devops-platform", "name": "DevOps Platform", "agents": ["D-21", "D-22", "D-23", "D-24", "D-25", "N-39", "N-40", "N-42", "O-14", "O-15", "O-16"]},
    {"id": "cybersecurity", "name": "Cybersecurity Tooling", "agents": ["F-09", "C-43", "C-44", "N-39", "N-40", "N-42", "O-14", "O-15", "O-16", "R-17", "R-18", "R-19"]},
    {"id": "voice-ai", "name": "Voice AI Application", "agents": ["M-35", "M-37", "S-30", "S-31", "R-17", "R-18", "O-14", "F-06", "F-09"]},
    {"id": "video-platform", "name": "Video Platform", "agents": ["S-34", "S-33", "S-31", "P-26", "P-27", "N-40", "O-14", "D-22", "R-17", "R-18", "R-19"]},
    {"id": "saas", "name": "SaaS Platform", "agents": ["F-01", "F-02", "F-03", "F-04", "F-05", "F-06", "F-07", "F-08", "F-09", "D-10", "D-11", "D-21", "D-22", "D-23", "O-14", "O-15", "R-17", "R-18", "P-26", "N-39", "C-43", "C-44"]},
    {"id": "ecommerce", "name": "E-Commerce", "agents": ["F-01", "F-02", "F-03", "F-04", "F-06", "F-07", "F-08", "F-09", "D-10", "D-11", "D-21", "D-22", "O-14", "R-17", "R-18", "P-26", "N-39", "C-43"]},
    {"id": "fintech", "name": "Fintech", "agents": ["F-01", "F-02", "F-04", "F-06", "F-07", "F-09", "D-10", "D-11", "D-13", "C-43", "C-44", "N-39", "R-17", "R-18", "R-19", "O-14", "O-15", "O-16"]},
    {"id": "healthtech", "name": "HealthTech", "agents": ["F-01", "F-02", "F-03", "F-04", "F-06", "F-09", "D-10", "D-11", "D-13", "C-43", "C-44", "O-14", "O-15", "O-16", "R-17", "R-18"]},
    {"id": "edtech", "name": "EdTech", "agents": ["F-01", "F-03", "F-04", "F-06", "F-09", "D-10", "O-14", "S-30", "M-35", "R-17", "N-39"]},
    {"id": "api-gateway", "name": "API Gateway", "agents": ["F-01", "F-02", "F-03", "F-04", "F-07", "F-08", "F-09", "N-39", "N-40", "N-42", "O-14", "R-17", "R-18", "R-19", "C-43", "C-44"]},
    {"id": "chatbot", "name": "Chatbot / Conversational AI", "agents": ["M-35", "M-37", "F-06", "F-07", "S-30", "S-31", "R-17", "R-18", "O-14"]},
    {"id": "search-engine", "name": "Search Engine", "agents": ["D-10", "D-12", "P-26", "P-27", "S-30", "S-32", "O-14", "R-17", "R-18", "D-22"]},
    {"id": "analytics-platform", "name": "Analytics Platform", "agents": ["D-10", "D-11", "D-12", "S-30", "S-32", "O-14", "O-15", "O-16", "P-26", "P-27", "R-17", "R-18", "D-22"]},
    {"id": "low-code", "name": "Low-Code Platform", "agents": ["F-01", "F-03", "F-04", "F-05", "D-21", "D-22", "D-23", "O-14", "N-39", "C-43"]},
    {"id": "cli-tool", "name": "CLI / Developer Tool", "agents": ["F-01", "F-02", "F-03", "F-04", "F-05", "R-17", "R-18", "R-19"]},
    {"id": "library-sdk", "name": "Library / SDK", "agents": ["F-01", "F-03", "F-04", "F-05", "R-17", "R-18"]},
]

# ─────────────────────────────────────────────────────────────────────────────
# Agent definitions for scope.yaml files
# ─────────────────────────────────────────────────────────────────────────────

AGENT_DEFS = [
    {"id": "F-01", "name": "Foundation Architect", "category": "foundation", "concepts": [
        "foundation.caching", "foundation.hld", "foundation.lld", "foundation.client-server",
        "foundation.protocols", "foundation.proxies", "foundation.load-balancers",
        "foundation.message-queues", "foundation.db-scaling", "foundation.connection-pooling",
        "foundation.consistent-hashing", "foundation.cap-consistency", "foundation.latency-bandwidth",
        "foundation.idempotency", "foundation.fault-tolerance",
    ]},
    {"id": "F-02", "name": "Configuration Auditor", "category": "foundation", "concepts": [
        "foundation.config", "foundation.hld",
    ]},
    {"id": "F-03", "name": "Logging Architect", "category": "foundation", "concepts": [
        "foundation.logging",
    ]},
    {"id": "F-04", "name": "Error Handling Specialist", "category": "foundation", "concepts": [
        "foundation.error-handling",
    ]},
    {"id": "F-05", "name": "Validation Specialist", "category": "foundation", "concepts": [
        "foundation.validation",
    ]},
    {"id": "F-06", "name": "Authentication Specialist", "category": "foundation", "concepts": [
        "foundation.auth",
    ]},
    {"id": "F-07", "name": "Authorization Specialist", "category": "foundation", "concepts": [
        "foundation.authorization",
    ]},
    {"id": "F-08", "name": "Rate Limiting Specialist", "category": "foundation", "concepts": [
        "foundation.rate-limiting",
    ]},
    {"id": "F-09", "name": "Security Auditor", "category": "security", "concepts": [
        "security.https", "security.headers", "security.sanitization",
        "security.secrets-management", "security.dependency-scan",
        "security.cors",
    ]},
    {"id": "D-10", "name": "Data Architect", "category": "data", "concepts": [
        "data.orm",
    ]},
    {"id": "D-11", "name": "Migration Specialist", "category": "data", "concepts": [
        "data.migrations",
    ]},
    {"id": "D-12", "name": "Query Performance Specialist", "category": "data", "concepts": [
        "data.indexing",
    ]},
    {"id": "D-13", "name": "Backup & Recovery Specialist", "category": "data", "concepts": [
        "data.backup",
    ]},
    {"id": "O-14", "name": "Metrics Specialist", "category": "observability", "concepts": [
        "observability.metrics",
    ]},
    {"id": "O-15", "name": "Tracing Specialist", "category": "observability", "concepts": [
        "observability.tracing",
    ]},
    {"id": "O-16", "name": "Alerting Specialist", "category": "observability", "concepts": [
        "observability.alerting",
    ]},
    {"id": "R-17", "name": "Circuit Breaker Specialist", "category": "resilience", "concepts": [
        "resilience.circuit-breaker",
    ]},
    {"id": "R-18", "name": "Retry Strategy Specialist", "category": "resilience", "concepts": [
        "resilience.retries",
    ]},
    {"id": "R-19", "name": "Timeout Specialist", "category": "resilience", "concepts": [
        "resilience.timeouts",
    ]},
    {"id": "R-20", "name": "DLQ Specialist", "category": "resilience", "concepts": [
        "resilience.dead-letter",
    ]},
    {"id": "D-21", "name": "Containerisation Specialist", "category": "deployment", "concepts": [
        "deployment.containers",
    ]},
    {"id": "D-22", "name": "Orchestration Specialist", "category": "deployment", "concepts": [
        "deployment.orchestration",
    ]},
    {"id": "D-23", "name": "CI/CD Specialist", "category": "deployment", "concepts": [
        "deployment.ci-cd",
    ]},
    {"id": "D-24", "name": "IaC Specialist", "category": "deployment", "concepts": [
        "deployment.iaac",
    ]},
    {"id": "D-25", "name": "Health Check Specialist", "category": "deployment", "concepts": [
        "deployment.healthchecks",
    ]},
    {"id": "P-26", "name": "Connection Pool Specialist", "category": "performance", "concepts": [
        "performance.connection-pool",
    ]},
    {"id": "P-27", "name": "Async Performance Specialist", "category": "performance", "concepts": [
        "performance.async",
    ]},
    {"id": "P-28", "name": "Pagination Specialist", "category": "performance", "concepts": [
        "performance.pagination",
    ]},
    {"id": "P-29", "name": "CDN & Edge Specialist", "category": "performance", "concepts": [
        "performance.cdn",
    ]},
    {"id": "S-30", "name": "Message Broker Specialist", "category": "streaming", "concepts": [
        "streaming.message-broker",
    ]},
    {"id": "S-31", "name": "WebSocket Specialist", "category": "streaming", "concepts": [
        "streaming.websockets",
    ]},
    {"id": "S-32", "name": "Event Streaming Specialist", "category": "streaming", "concepts": [
        "streaming.event-streaming",
    ]},
    {"id": "S-33", "name": "WebRTC Specialist", "category": "streaming", "concepts": [
        "streaming.webrtc",
    ]},
    {"id": "S-34", "name": "Live Streaming Specialist", "category": "streaming", "concepts": [
        "streaming.live-streaming",
    ]},
    {"id": "M-35", "name": "NLP Specialist", "category": "ml-ai", "concepts": [
        "ml.nlp", "ml.transformers",
    ]},
    {"id": "M-36", "name": "MLOps Specialist", "category": "ml-ai", "concepts": [
        "ml.mlops",
    ]},
    {"id": "M-37", "name": "Model Serving Specialist", "category": "ml-ai", "concepts": [
        "ml.model-serving",
    ]},
    {"id": "M-38", "name": "Feature Store Specialist", "category": "ml-ai", "concepts": [
        "ml.feature-store",
    ]},
    {"id": "N-39", "name": "Proxy Specialist", "category": "networking", "concepts": [
        "networking.proxy",
    ]},
    {"id": "N-40", "name": "Load Balancer Specialist", "category": "networking", "concepts": [
        "networking.load-balancer",
    ]},
    {"id": "N-41", "name": "Service Mesh Specialist", "category": "networking", "concepts": [
        "networking.service-mesh",
    ]},
    {"id": "N-42", "name": "DNS Specialist", "category": "networking", "concepts": [
        "networking.dns",
    ]},
    {"id": "C-43", "name": "PII Specialist", "category": "compliance", "concepts": [
        "compliance.pii",
    ]},
    {"id": "C-44", "name": "Audit Log Specialist", "category": "compliance", "concepts": [
        "compliance.audit-log",
    ]},
]


# ─────────────────────────────────────────────────────────────────────────────
# Concept file template
# ─────────────────────────────────────────────────────────────────────────────

CONCEPT_TEMPLATE = textwrap.dedent("""\
    ---
    id: {id}
    category: {category}
    name: {name}
    owning_agent: {owning_agent}
    maturity: {maturity}
    languages: [{languages}]
    tags: [{tags}]
    related: [{related}]
    ---

    # {name}

    ## 1. Overview

    {overview}

    ## 2. Core Principles

    {principles}

    ## 3. Sub-Concepts

    {subconcepts}

    ## 4. Implementation Patterns

    {patterns}

    ## 5. Anti-Patterns

    {antipatterns}

    ## 6. Real-World Examples

    {examples}

    ## 7. Detection Signals

    {signals}
""")


def _languages_str(langs: list[str]) -> str:
    return ", ".join(langs)


def _tags_str(tags: list[str]) -> str:
    return ", ".join(tags)


def _related_str(related: list[str]) -> str:
    return ", ".join(related)


def generate_overview(concept: dict) -> str:
    cid = concept["id"]
    name = concept["name"]
    overviews = {
        "security.https": f"{name} encrypts HTTP traffic using TLS, preventing eavesdropping and man-in-the-middle attacks. Every production service must terminate TLS at the edge and enforce HTTPS-only access. Certificate management (rotation, renewal, stapling) is part of this concept's operational burden.",
        "security.headers": f"{name} are HTTP response headers that instruct browsers to enforce security policies. They mitigate XSS, clickjacking, MIME sniffing, and data exfiltration without changing application code.",
        "security.sanitization": f"{name} ensures user-supplied input cannot alter application logic or corrupt stored data. It covers output encoding, SQL parameterization, XSS prevention, and template auto-escaping.",
        "security.secrets-management": f"{name} covers how API keys, database passwords, and certificates are stored, distributed, and rotated. Hardcoded secrets in repositories are the leading cause of credential-related breaches.",
        "security.dependency-scan": f"{name} detects known vulnerabilities in third-party libraries before they reach production. Automated scanning in CI/CD is the primary defense against supply-chain attacks.",
        "data.orm": f"{name} abstracts SQL database access through an object-oriented interface, eliminating hand-written SQL for most operations while providing query builders, migrations, and connection management.",
        "data.migrations": f"{name} provides versioned, repeatable schema changes that can be applied and rolled back across environments without manual SQL execution.",
        "data.indexing": f"{name} uses B-tree, hash, and composite indexes to accelerate query performance. Index design directly affects read throughput and write latency.",
        "data.backup": f"{name} ensures data durability through periodic snapshots, replication, and point-in-time recovery. Backup strategy defines RPO (Recovery Point Objective) and RTO (Recovery Time Objective).",
        "observability.metrics": f"{name} captures numerical measurements (counters, gauges, histograms) over time. Metrics enable alerting, SLO tracking, and capacity planning without storing raw events.",
        "observability.tracing": f"{name} tracks a request across service boundaries using trace IDs and spans. Distributed tracing reveals latency hotspots in microservice architectures.",
        "observability.alerting": f"{name} converts metric thresholds and log patterns into human-actionable notifications. Alerting design must balance signal-to-noise ratio against detection latency.",
        "resilience.circuit-breaker": f"{name} stops calling a failing downstream service after a threshold of failures, giving it time to recover. Without circuit breakers, cascading failures take down entire dependency chains.",
        "resilience.retries": f"{name} re-attempts transient failures using strategies like exponential backoff with jitter. Retries must be idempotent-safe to prevent duplicate side effects.",
        "resilience.timeouts": f"{name} bounds the wall-clock time of every external call. A missing timeout can hold a thread or connection indefinitely during a downstream outage.",
        "resilience.dead-letter": f"{name} captures messages that cannot be processed after all retry attempts. DLQs preserve failed messages for later analysis and replay, preventing silent data loss.",
        "deployment.containers": f"{name} packages applications with their dependencies into portable, immutable images. Containers eliminate environment drift and enable reproducible deployments.",
        "deployment.orchestration": f"{name} automates container scheduling, networking, scaling, and self-healing across a cluster of machines. Kubernetes is the de facto standard.",
        "deployment.ci-cd": f"{name} automates building, testing, and deploying code on every commit. CI/CD pipelines enforce quality gates (lint, test, scan) before production promotion.",
        "deployment.iaac": f"{name} declaratively defines infrastructure in version-controlled files. IaC enables peer-reviewed infrastructure changes, drift detection, and reproducible environments.",
        "deployment.healthchecks": f"{name} exposes HTTP endpoints that indicate service readiness and liveness. Orchestrators use health checks to route traffic away from unhealthy instances.",
        "performance.connection-pool": f"{name} reuses TCP and database connections across requests, avoiding the overhead of creating a new connection per request. Pool sizing is critical: too small creates contention, too large exhausts backend capacity.",
        "performance.async": f"{name} uses non-blocking I/O to handle concurrent operations without dedicating a thread per operation. Async patterns are essential for I/O-bound workloads.",
        "performance.pagination": f"{name} splits large result sets into manageable pages. Offset pagination is simple but slow at depth; cursor-based pagination scales better for infinite feeds.",
        "performance.cdn": f"{name} caches static and dynamic content at geographically distributed edge locations. CDNs reduce latency for global users and absorb traffic spikes.",
        "streaming.message-broker": f"{name} decouples producers from consumers using durable message queues. Brokers provide at-least-once delivery, consumer group scaling, and replay capability.",
        "streaming.websockets": f"{name} maintains persistent, bidirectional TCP connections between server and client. WebSockets enable real-time updates, chat, and collaborative features without polling.",
        "streaming.event-streaming": f"{name} captures a continuous, ordered log of events that multiple consumers can read independently. Unlike simple message queues, event streams support replay, partitioning, and long-term retention.",
        "streaming.webrtc": f"{name} enables peer-to-peer audio, video, and data transfer with sub-second latency. WebRTC is the foundation for video conferencing, live streaming, and real-time collaboration.",
        "streaming.live-streaming": f"{name} captures, encodes, and delivers live video to viewers with adaptive bitrate. HLS and DASH are the dominant protocols, with RTMP remaining common for ingest.",
        "ml.nlp": f"{name} applies machine learning to text data: classification, generation, summarization, and embedding. Modern NLP is dominated by transformer-based models accessed via APIs or self-hosted inference.",
        "ml.transformers": f"{name} is the neural architecture behind modern NLP and multimodal AI. The self-attention mechanism enables parallel processing of sequences and context-aware representations.",
        "ml.mlops": f"{name} applies DevOps practices to ML: versioned training pipelines, model registries, drift detection, and reproducible experiments. MLOps bridges the gap between model development and production serving.",
        "ml.model-serving": f"{name} exposes trained models as low-latency, scalable inference APIs. Model serving must handle batching, model versioning, A/B testing, and resource isolation.",
        "ml.feature-store": f"{name} provides a centralised, versioned repository of features used across training and inference. Feature stores eliminate training-serving skew by ensuring consistent feature computation.",
        "networking.proxy": f"{name} sits between clients and servers, forwarding requests while applying routing rules, authentication, rate limiting, and caching. Proxies are the control plane of microservice communication.",
        "networking.load-balancer": f"{name} distributes incoming traffic across multiple backend instances. Load balancers operate at L4 (TCP/UDP) or L7 (HTTP/HTTPS) and provide health-checked routing.",
        "networking.service-mesh": f"{name} injects a sidecar proxy alongside each service to handle interservice communication. Service meshes provide mutual TLS, retries, circuit breaking, and observability without application code changes.",
        "networking.dns": f"{name} translates human-readable domain names to IP addresses. In modern infrastructure, DNS also enables service discovery, load balancing, and failover.",
        "compliance.pii": f"{name} identifies, classifies, and protects personally identifiable information throughout its lifecycle. PII handling is governed by GDPR, CCPA, HIPAA, and other regulations.",
        "compliance.audit-log": f"{name} creates tamper-evident, time-ordered records of security-relevant events. Audit logs are required for SOC 2, HIPAA, PCI-DSS, and internal incident investigation.",
    }
    return overviews.get(cid, f"{name} is a system-design concept that impacts architecture decisions, implementation patterns, and operational readiness.")


def generate_principles(concept: dict) -> str:
    return "\n".join([
        f"- {concept['name']} must be implemented with clear ownership and documented operational procedures.",
        f"- The implementation must be testable, observable, and recoverable in failure scenarios.",
        f"- Configuration must be externalised and never hardcoded in source control.",
        f"- Failure modes must be explicitly handled with appropriate fallbacks and timeouts.",
        f"- The concept's effectiveness must be measurable through metrics, logs, or traces.",
    ])


def generate_subconcepts(concept: dict) -> str:
    cid = concept["id"]
    subconcepts = {
        "security.https": (
            "\n### 3.1 TLS Termination\n\n"
            "**Definition:** The point at which encrypted HTTPS traffic is decrypted and passed as HTTP to backend services. Typically occurs at a load balancer, CDN, or reverse proxy.\n\n"
            "**Why it matters:** TLS termination at the edge centralises certificate management and offloads CPU-intensive encryption from application servers.\n\n"
            "**Implementation patterns:**\n"
            "- Cloud provider ALB/NLB with ACM certificate\n"
            "- Nginx with Let's Encrypt (certbot)\n"
            "- Envoy with SDS (Secret Discovery Service)\n"
        ),
        "streaming.live-streaming": (
            "\n### 3.1 Ingest (RTMP / SRT)\n\n"
            "**Definition:** The protocol used to send a live stream from broadcaster to the media server. RTMP is the legacy standard; SRT offers lower latency and better packet-loss recovery.\n\n"
            "### 3.2 Transcoding & Packaging\n\n"
            "**Definition:** Converting the incoming stream to multiple resolutions and bitrates (ABR ladder) and packaging into HLS (.m3u8 + .ts) or DASH (.mpd) segments.\n\n"
            "**Implementation:** FFmpeg or GStreamer for transcoding; MediaServer (nginx-rtmp), Mux, or AWS MediaLive for managed pipelines.\n\n"
            "### 3.3 Playback & Delivery\n\n"
            "**Definition:** Serving segmented video to end users via CDN. HLS is supported natively on iOS; DASH is preferred on Android and web.\n\n"
            "### 3.4 Latency Considerations\n\n"
            "**Definition:** Live streaming latency depends on segment duration and CDN cache TTL. LL-HLS and LL-DASH reduce latency to 2–5 seconds."
        ),
    }
    return subconcepts.get(cid, "\n### 3.1 Core Components\n\nEach concept can be decomposed into its primary components, each with distinct responsibilities, failure modes, and scaling characteristics.\n")


def generate_patterns(concept: dict) -> str:
    cid = concept["id"]
    patterns = {
        "security.https": (
            "```python\n# Python — Enforce HTTPS with FastAPI\n"
            "from fastapi import FastAPI, Request\n"
            "from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware\n\n"
            "app = FastAPI()\n"
            "app.add_middleware(HTTPSRedirectMiddleware)\n```\n\n"
            "```yaml\n# Nginx — TLS termination\n"
            "server {\n"
            "    listen 443 ssl http2;\n"
            "    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;\n"
            "    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;\n"
            "    ssl_protocols TLSv1.2 TLSv1.3;\n"
            "    ssl_ciphers HIGH:!aNULL:!MD5;\n"
            "}\n```"
        ),
        "streaming.live-streaming": (
            "```bash\n# FFmpeg — RTMP ingest → HLS output\n"
            "ffmpeg -i rtmp://localhost/live/stream \\\n"
            "  -c:v libx264 -preset veryfast -crf 22 \\\n"
            "  -c:a aac -b:a 128k \\\n"
            "  -f hls -hls_time 4 -hls_list_size 6 \\\n"
            "  /var/www/hls/stream.m3u8\n```\n\n"
            "```html\n<!-- HLS.js player -->\n"
            "<video id='player' controls autoplay></video>\n"
            "<script src='https://cdn.jsdelivr.net/npm/hls.js@latest'></script>\n"
            "<script>\n"
            "  const video = document.getElementById('player');\n"
            "  const hls = new Hls();\n"
            "  hls.loadSource('/hls/stream.m3u8');\n"
            "  hls.attachMedia(video);\n"
            "</script>\n```"
        ),
        "ml.nlp": (
            "```python\n# NLP — Hugging Face Transformers\n"
            "from transformers import AutoTokenizer, AutoModelForSequenceClassification\n"
            "import torch\n\n"
            "tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')\n"
            "model = AutoModelForSequenceClassification.from_pretrained('distilbert-base-uncased-finetuned-sst-2-english')\n\n"
            "inputs = tokenizer('I love this product!', return_tensors='pt', truncation=True, max_length=512)\n"
            "outputs = model(**inputs)\n"
            "prediction = torch.softmax(outputs.logits, dim=-1)\n"
            "print(f'Positive: {prediction[0][1].item():.2%}')\n```\n\n"
            "```python\n# Embeddings — sentence-transformers\n"
            "from sentence_transformers import SentenceTransformer\n\n"
            "model = SentenceTransformer('all-MiniLM-L6-v2')\n"
            "embeddings = model.encode(['Hello world', 'SDAT is awesome'])\n"
            "print(embeddings.shape)  # (2, 384)\n```"
        ),
        "ml.transformers": (
            "```python\n# PyTorch — Transformer Encoder Layer\n"
            "import torch\n"
            "import torch.nn as nn\n\n"
            "class TransformerEncoderLayer(nn.Module):\n"
            "    def __init__(self, d_model=512, nhead=8, dim_feedforward=2048):\n"
            "        super().__init__()\n"
            "        self.self_attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)\n"
            "        self.ffn = nn.Sequential(\n"
            "            nn.Linear(d_model, dim_feedforward),\n"
            "            nn.ReLU(),\n"
            "            nn.Linear(dim_feedforward, d_model),\n"
            "        )\n"
            "        self.norm1 = nn.LayerNorm(d_model)\n"
            "        self.norm2 = nn.LayerNorm(d_model)\n\n"
            "    def forward(self, x):\n"
            "        attn_out, _ = self.self_attn(x, x, x)\n"
            "        x = self.norm1(x + attn_out)\n"
            "        x = self.norm2(x + self.ffn(x))\n"
            "        return x\n```"
        ),
    }
    return patterns.get(cid, "```python\n# Implementation pattern\n# Refer to the scanner rules in config/rules/signals/ for detection patterns.\n```")


def generate_antipatterns(concept: dict) -> str:
    cid = concept["id"]
    antipatterns = {
        "security.https": (
            "\n**Hardcoded certificates** — Embedding certificate content in source code or environment variables without rotation.\n"
            "\n**Mixed content** — Serving HTTPS pages that load HTTP resources (scripts, images, APIs), which browsers block and which man-in-the-middle attacks exploit.\n"
        ),
        "security.headers": (
            "\n**Helmet-only illusion** — Adding Helmet.js with default settings without reviewing and tightening individual headers (CSP, HSTS max-age).\n"
        ),
        "security.sanitization": (
            "\n**Client-side only sanitization** — Trusting JavaScript input validation as the sole defense, ignoring that client-side checks can be bypassed.\n"
            "\n**String concatenation for SQL** — Building queries by concatenating user input, which is the #1 cause of SQL injection vulnerabilities.\n"
        ),
        "security.secrets-management": (
            "\n**Secrets in .env committed to git** — Even with .gitignore, a single committed .env file exposes secrets permanently in git history.\n"
            "\n**Secrets in plaintext configmaps** — Storing secrets in Kubernetes ConfigMaps instead of Secrets, making them visible to anyone with cluster read access.\n"
        ),
        "security.dependency-scan": (
            "\n**Scanning only in development** — Running dependency scans manually instead of in CI/CD, allowing vulnerable dependencies to reach production.\n"
        ),
        "data.indexing": (
            "\n**Over-indexing** — Adding indexes to every column without considering write overhead. Each index slows INSERT/UPDATE/DELETE operations.\n"
            "\n**Missing composite indexes** — Using separate single-column indexes instead of composite indexes for multi-column WHERE clauses.\n"
        ),
        "resilience.retries": (
            "\n**Retries without backoff** — Immediate retries amplify load on a failing service, turning a brief blip into an extended outage.\n"
            "\n**Retrying non-idempotent operations** — Retrying a POST that creates resources can produce duplicates.\n"
        ),
        "streaming.live-streaming": (
            "\n**Fixed bitrate without ABR** — Streaming a single bitrate forces viewers with slow connections to buffer or drop out.\n"
            "\n**Long segment durations** — HLS segments longer than 6 seconds increase channel change delay and live latency.\n"
        ),
        "ml.model-serving": (
            "\n**Loading model on every request** — Deserialising the model inside the prediction handler adds seconds of latency per request.\n"
        ),
    }
    return antipatterns.get(cid, "\n**Skipping this concept** — The most common anti-pattern is simply not implementing the concept at all, trading short-term velocity for long-term technical debt.\n")


def generate_examples(concept: dict) -> str:
    examples = {
        "security.https": (
            "\n- **GitHub** — Enforces HTTPS for all traffic, uses HSTS with max-age of 1 year.\n"
            "\n- **Stripe** — TLS 1.3 only, with certificate pinning for their dashboard.\n"
        ),
        "streaming.live-streaming": (
            "\n- **Twitch** — Uses RTMP ingest, FFmpeg transcoding, and HLS delivery with <3s latency.\n"
            "\n- **YouTube Live** — DASH-based ABR with hardware-accelerated encoding.\n"
            "\n- **Mux** — Managed live streaming API handling ingest, transcoding, and playback.\n"
        ),
        "ml.nlp": (
            "\n- **OpenAI** — GPT-4 via API for conversational AI.\n"
            "\n- **Hugging Face** — Hosted inference for 500,000+ models.\n"
            "\n- **LangChain** — Framework for building LLM-powered applications.\n"
        ),
        "deployment.orchestration": (
            "\n- **Spotify** — Allegedly runs the world's largest Kubernetes cluster (10,000+ nodes).\n"
            "\n- **Lyft** — Migrated from Mesos to Kubernetes, reducing deploy time from hours to minutes.\n"
        ),
    }
    return examples.get(concept["id"], f"\n- **Industry standard** — {concept['name']} is widely adopted across production systems at scale.\n")


def generate_signals(concept: dict) -> str:
    cid = concept["id"]
    signals = {
        "security.https": (
            "\n**Presence signals:**\n"
            "- `security.https.presence.force-ssl` — HTTPS redirect middleware or forced-SSL configuration.\n"
            "- `security.https.presence.tls-config` — TLS version/cipher configuration files.\n\n"
            "**Absence signal:**\n"
            "- `security.https.absence` — No TLS configuration, no HTTPS redirect, plain HTTP only.\n"
        ),
        "security.secrets-management": (
            "\n**Presence signals:**\n"
            "- `security.secrets-management.presence.vault` — HashiCorp Vault integration.\n"
            "- `security.secrets-management.presence.aws-secrets-manager` — AWS Secrets Manager client.\n"
            "- `security.secrets-management.presence.sops` — SOPS encrypted files.\n\n"
            "**Misconfiguration signals:**\n"
            "- `security.secrets-management.misconfig.hardcoded-secret` — Secrets embedded in source code.\n\n"
            "**Anti-pattern:**\n"
            "- `security.secrets-management.anti.secret-in-code` — API keys, passwords, or tokens in plaintext.\n"
        ),
    }
    return signals.get(cid, f"\n**Presence:** Detects library imports, configuration files, and code patterns specific to {concept['name']}.\n\n**Absence:** No evidence of this concept's implementation in the codebase.\n")


def build_concept_content(concept: dict) -> str:
    overview = generate_overview(concept)
    principles = generate_principles(concept)
    subconcepts = generate_subconcepts(concept)
    patterns = generate_patterns(concept)
    antipatterns = generate_antipatterns(concept)
    examples = generate_examples(concept)
    signals = generate_signals(concept)

    return CONCEPT_TEMPLATE.format(
        id=concept["id"],
        category=concept["category"],
        name=concept["name"],
        owning_agent=concept["owning_agent"],
        maturity=concept["maturity"],
        languages=_languages_str(concept.get("languages", ["any"])),
        tags=_tags_str(concept.get("tags", [])),
        related=_related_str(concept.get("related", [])),
        overview=overview,
        principles=principles,
        subconcepts=subconcepts,
        patterns=patterns,
        antipatterns=antipatterns,
        examples=examples,
        signals=signals,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Agent scope.yaml template
# ─────────────────────────────────────────────────────────────────────────────

AGENT_SCOPE_TEMPLATE = """\
agent_id: {id}
name: {name}
category: {category}
version: 0.1.0
description: >
  {description}

scanner_signals:
{scanner_signals}

evaluation:
  primary_file_patterns: []
  secondary_file_patterns: []
  confidence_floor: 0.3
  presets:
    - absence_when_no_signals
    - misconfiguration_on_anti_pattern

output:
  concepts_owned: {concepts_owned}
  report_section: "{name} findings"
  priority_default: medium
"""


AGENT_DESCRIPTIONS = {
    "F-01": "Evaluates fundamental architecture patterns, design principles, and system boundaries that apply to every project regardless of technology stack.",
    "F-02": "Audits environment configuration management, ensuring secrets and settings are externalised and never hardcoded.",
    "F-03": "Evaluates logging architecture, log levels, structured output, and log aggregation readiness.",
    "F-04": "Evaluates error handling strategy, middleware configuration, and exception safety.",
    "F-05": "Evaluates input validation, schema enforcement, and sanitization patterns.",
    "F-06": "Evaluates authentication mechanisms, session management, and credential handling.",
    "F-07": "Evaluates authorization models, RBAC, and access control enforcement.",
    "F-08": "Evaluates rate limiting, throttling, and API abuse prevention.",
    "F-09": "Evaluates OWASP Top 10 coverage, TLS, security headers, and dependency vulnerability scanning.",
    "D-10": "Evaluates data modelling, ORM usage, query patterns, and schema design.",
    "D-11": "Evaluates database migration strategy, versioning, and rollback capability.",
    "D-12": "Evaluates query performance, index coverage, and N+1 detection.",
    "D-13": "Evaluates backup strategy, replication, and disaster recovery readiness.",
    "O-14": "Evaluates metrics instrumentation, dashboards, and SLO tracking.",
    "O-15": "Evaluates distributed tracing, correlation IDs, and span instrumentation.",
    "O-16": "Evaluates alerting configuration, escalation policies, and on-call readiness.",
    "R-17": "Evaluates circuit breaker usage, fallback paths, and failure isolation.",
    "R-18": "Evaluates retry configuration, backoff strategies, and idempotency guarantees.",
    "R-19": "Evaluates timeout configuration, deadline enforcement, and graceful degradation.",
    "R-20": "Evaluates dead letter queue configuration, replay capability, and poison message handling.",
    "D-21": "Evaluates containerisation quality, image optimisation, and Docker best practices.",
    "D-22": "Evaluates Kubernetes deployment quality, HPA, pod disruption budgets, and resource limits.",
    "D-23": "Evaluates CI/CD pipeline completeness, quality gates, and deployment automation.",
    "D-24": "Evaluates IaC usage, drift detection, and infrastructure version control.",
    "D-25": "Evaluates health check endpoint design and readiness/liveness probe configuration.",
    "P-26": "Evaluates connection pool sizing, configuration, and monitoring.",
    "P-27": "Evaluates async architecture, event loop usage, and non-blocking patterns.",
    "P-28": "Evaluates pagination strategy, cursor usage, and large dataset handling.",
    "P-29": "Evaluates CDN configuration, cache policies, and edge optimisation.",
    "S-30": "Evaluates message broker selection, topic design, and consumer group configuration.",
    "S-31": "Evaluates WebSocket implementation, scaling, and reconnection handling.",
    "S-32": "Evaluates event streaming architecture, partition strategy, and consumer lag.",
    "S-33": "Evaluates WebRTC usage, SFU/MCU selection, and peer connection management.",
    "S-34": "Evaluates live streaming pipeline, ABR ladder, and latency optimisation.",
    "M-35": "Evaluates NLP/transformer model selection, tokenisation, and inference patterns.",
    "M-36": "Evaluates ML pipeline maturity, experiment tracking, and drift detection.",
    "M-37": "Evaluates model serving architecture, batching, and model versioning.",
    "M-38": "Evaluates feature store usage, feature consistency, and online/offline parity.",
    "N-39": "Evaluates reverse proxy configuration, routing rules, and middleware chains.",
    "N-40": "Evaluates load balancer configuration, health checks, and session affinity.",
    "N-41": "Evaluates service mesh adoption, sidecar injection, and traffic management.",
    "N-42": "Evaluates DNS configuration, service discovery, and failover policies.",
    "C-43": "Evaluates PII detection, data classification, and privacy controls.",
    "C-44": "Evaluates audit log completeness, tamper resistance, and retention policies.",
}


def build_agent_scope(agent: dict) -> str:
    scanner_signals = "\n".join(
        f"    - {concept_id}" for concept_id in agent["concepts"]
    )
    return AGENT_SCOPE_TEMPLATE.format(
        id=agent["id"],
        name=agent["name"],
        category=agent["category"],
        description=AGENT_DESCRIPTIONS.get(agent["id"], f"Specialised agent for {agent['name']}."),
        scanner_signals=scanner_signals,
        concepts_owned=", ".join(agent["concepts"]),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("Phase 1 Bootstrap — KB Foundation")
    print("=" * 60)

    # 1. Create concept directories and files
    print("\n[1/5] Creating concept directories and files...")
    created_categories: set[str] = set()
    created_concepts = 0

    for concept in NEW_CONCEPTS:
        category = concept["category"]
        cat_dir = CONCEPTS_DIR / category
        if category not in created_categories:
            cat_dir.mkdir(parents=True, exist_ok=True)
            created_categories.add(category)

        filepath = REPO_ROOT / "concepts" / concept["file"]
        if not filepath.exists():
            content = build_concept_content(concept)
            filepath.write_text(content, encoding="utf-8")
            created_concepts += 1
            print(f"  Created: {concept['file']}")

    print(f"  Total concepts created: {created_concepts}")

    # 2. Create agent scopes
    print("\n[2/5] Creating agent scope.yaml files...")
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    created_agents = 0

    for agent in AGENT_DEFS:
        agent_dir = AGENTS_DIR / agent["id"]
        agent_dir.mkdir(parents=True, exist_ok=True)
        scope_path = agent_dir / "scope.yaml"
        if not scope_path.exists():
            scope_path.write_text(build_agent_scope(agent), encoding="utf-8")
            created_agents += 1

    print(f"  Created {created_agents} agent scope files in config/agents/")

    # 3. Create project-classifications.yaml
    print("\n[3/5] Creating project-classifications.yaml...")
    classifications_path = CONCEPTS_DIR / "project-classifications.yaml"
    if not classifications_path.exists():
        classifications = {
            "version": "0.1.0",
            "description": "24 project categories with agent dispatch mappings",
            "categories": PROJECT_CLASSIFICATIONS,
        }
        import yaml
        classifications_path.write_text(
            yaml.dump(classifications, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print(f"  Created: project-classifications.yaml")

    # 4. Ensure CONTRIBUTING.md exists
    print("\n[4/5] Checking CONTRIBUTING.md...")
    contributing_path = CONCEPTS_DIR / "CONTRIBUTING.md"
    if not contributing_path.exists():
        contributing_path.write_text(
            textwrap.dedent("""\
                # Contributing to the SDAT Knowledge Base

                ## Concept File Schema

                Each concept file is a Markdown file with YAML frontmatter:

                ```yaml
                ---
                id: unique.concept.id
                category: category-name
                name: Human Readable Name
                owning_agent: A-01
                maturity: stable | emerging | deprecated
                languages: [python, typescript, go]
                tags: [tag1, tag2, tag3]
                related: [related.concept.id]
                ---
                ```

                ## Agent Ownership

                Each concept must have an `owning_agent` field mapping to an agent in `config/agents/`.

                ## Review Criteria

                1. Frontmatter is valid YAML with all required fields
                2. Content covers all 7 sections
                3. Code examples are language-appropriate
                4. Detection signals are defined
            """).lstrip(),
            encoding="utf-8",
        )
        print("  Created: CONTRIBUTING.md")

    # 5. Rebuild INDEX.yaml
    print("\n[5/5] Rebuilding INDEX.yaml...")
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    from sdat.kb import rebuild_index

    rebuild_index()

    # Summary
    print("\n" + "=" * 60)
    print("Phase 1 Complete!")
    print("=" * 60)
    total_concepts = len(list(CONCEPTS_DIR.rglob("*.md")))
    categories = sorted(
        set(p.parent.name for p in CONCEPTS_DIR.rglob("*.md") if p.parent != CONCEPTS_DIR)
    )
    print(f"Total concept files: {total_concepts}")
    print(f"Categories: {len(categories)}")
    for cat in categories:
        count = len(list((CONCEPTS_DIR / cat).glob("*.md")))
        print(f"  {cat}: {count} concepts")
    print(f"\nAgent scopes: {len(AGENT_DEFS)}")
    print(f"Project classifications: {len(PROJECT_CLASSIFICATIONS)}")


if __name__ == "__main__":
    main()
