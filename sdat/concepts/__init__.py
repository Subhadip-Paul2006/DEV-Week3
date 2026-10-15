"""Concept taxonomy — the catalog of every system-design concept SDAT can evaluate.

Each concept has a stable ``id``, a human-readable ``name``, a ``category`` for grouping,
a ``priority`` rank (CRITICAL → NA), and a ``question`` the rule engine answers.

The taxonomy is the single source of truth; scanners, the rule engine, and reports
all reference concepts by their ``id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Priority(str, Enum):
    """Priority rank for a concept. Lower value = more important."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    N_A = "n/a"


class Category(str, Enum):
    """High-level category for grouping concepts in reports."""
    FOUNDATION = "Foundation"
    DEPLOYMENT = "Deployment & DevOps"
    SECURITY = "Security"
    DATA = "Data Management"
    OBSERVABILITY = "Observability"
    RESILIENCE = "Resilience"
    PERFORMANCE = "Performance"
    UX = "User Experience"
    INTEGRATION = "Integration"
    STREAMING = "Streaming & Messaging"
    ML_AI = "ML & AI"
    NETWORKING = "Networking"
    COMPLIANCE = "Compliance & Governance"
    FRONTEND = "Frontend Architecture"


@dataclass(frozen=True)
class Concept:
    """A single system-design concept SDAT can detect."""
    id: str
    name: str
    category: Category
    priority: Priority = Priority.MEDIUM
    question: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    domain: str = "core"
    status: str = "active"
    related_core_concepts: tuple[str, ...] = field(default_factory=tuple)
    applicable_capabilities: tuple[str, ...] = field(default_factory=tuple)
    required_evidence_kinds: tuple[str, ...] = field(default_factory=tuple)

    @property
    def concept_id(self) -> str:
        """Canonical concept_id alias for consistency with Knowledge Architecture."""
        return self.id

    @property
    def category_label(self) -> str:
        return self.category.value



# ─────────────────────────────────────────────────────────────────────────────
# Foundation concepts (always relevant to any backend project)
# ─────────────────────────────────────────────────────────────────────────────

FOUNDATION_CACHING = Concept(
    id="foundation.caching",
    name="Caching",
    category=Category.FOUNDATION,
    priority=Priority.HIGH,
    question="Does the project use a caching layer?",
    description="A caching layer (Redis, Memcached, in-memory LRU) reduces latency and offloads the primary datastore.",
    tags=["redis", "memcache", "lru", "cache", "ttl"],
)

FOUNDATION_CONFIG = Concept(
    id="foundation.config",
    name="Environment Configuration",
    category=Category.FOUNDATION,
    priority=Priority.CRITICAL,
    question="Does the project manage configuration via environment variables or a config service?",
    description="Hard-coded secrets and config values are a top source of breaches and incidents.",
    tags=["dotenv", "environment", "config", "settings", "env"],
)

FOUNDATION_LOGGING = Concept(
    id="foundation.logging",
    name="Structured Logging",
    category=Category.FOUNDATION,
    priority=Priority.HIGH,
    question="Does the project use structured (JSON) logging?",
    description="Structured logs are machine-parseable and essential for log aggregation platforms.",
    tags=["logging", "loguru", "structlog", "winston", "pino", "logger"],
)

FOUNDATION_ERROR_HANDLING = Concept(
    id="foundation.error-handling",
    name="Centralised Error Handling",
    category=Category.FOUNDATION,
    priority=Priority.HIGH,
    question="Is there a central error handler / middleware?",
    description="A single error-handling path ensures consistent HTTP responses and prevents stack leaks.",
    tags=["try", "except", "catch", "errorhandler", "middleware", "exception"],
)

FOUNDATION_VALIDATION = Concept(
    id="foundation.validation",
    name="Input Validation",
    category=Category.FOUNDATION,
    priority=Priority.CRITICAL,
    question="Does the project validate and sanitise incoming data?",
    description="Input validation is the first line of defence against injection attacks and corrupt data.",
    tags=["validator", "pydantic", "zod", "joi", "class-validator", "sanitize"],
)

FOUNDATION_AUTH = Concept(
    id="foundation.auth",
    name="Authentication",
    category=Category.FOUNDATION,
    priority=Priority.CRITICAL,
    question="Does the project implement user authentication?",
    description="Every service that serves user data must authenticate callers.",
    tags=["jwt", "oauth", "passport", "auth", "session", "token", "bcrypt", "argon2"],
)

FOUNDATION_AUTHORIZATION = Concept(
    id="foundation.authorization",
    name="Authorization",
    category=Category.FOUNDATION,
    priority=Priority.CRITICAL,
    question="Does the project enforce role-based or attribute-based access control?",
    description="Authentication alone is insufficient — authorization enforces who can do what.",
    tags=["rbac", "abac", "casbin", "policy", "permission", "acl", "role"],
)

FOUNDATION_RATE_LIMITING = Concept(
    id="foundation.rate-limiting",
    name="Rate Limiting",
    category=Category.FOUNDATION,
    priority=Priority.HIGH,
    question="Does the project enforce rate limits?",
    description="Rate limiting prevents abuse, thwarts brute-force attacks, and protects downstream services.",
    tags=["ratelimit", "throttle", "express-rate-limit", "slowapi", "limiter"],
)

FOUNDATION_API_VERSIONING = Concept(
    id="foundation.api-versioning",
    name="API Versioning",
    category=Category.FOUNDATION,
    priority=Priority.MEDIUM,
    question="Is the API versioned (URL, header, or media-type)?",
    description="Versioned APIs let you ship breaking changes without breaking existing clients.",
    tags=["/v1/", "/v2/", "api-version", "versioning"],
)

FOUNDATION_IDEMPOTENCY = Concept(
    id="foundation.idempotency",
    name="Idempotency Keys",
    category=Category.FOUNDATION,
    priority=Priority.MEDIUM,
    question="Does the project use idempotency keys for mutating endpoints?",
    description="Idempotency keys prevent duplicate charges and double-writes on retry.",
    tags=["idempotency", "idempotent", "Idempotency-Key"],
)

FOUNDATION_OPENAPI = Concept(
    id="foundation.openapi",
    name="API Documentation (OpenAPI)",
    category=Category.FOUNDATION,
    priority=Priority.LOW,
    question="Does the project expose an OpenAPI / Swagger spec?",
    description="Machine-readable API docs accelerate frontend integration and contract testing.",
    tags=["openapi", "swagger", "fastapi.openapi", "express-openapi"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Security
# ─────────────────────────────────────────────────────────────────────────────

SECURITY_SECRETS = Concept(
    id="security.secrets-management",
    name="Secrets Management",
    category=Category.SECURITY,
    priority=Priority.CRITICAL,
    question="Are secrets stored in a vault or secrets manager, not in code or .env files?",
    description="Hard-coded secrets are the #1 cause of supply-chain breaches.",
    tags=["vault", "aws secretsmanager", "azure keyvault", "doppler", "sops", "secret"],
)

SECURITY_HTTPS = Concept(
    id="security.https",
    name="HTTPS / TLS Enforcement",
    category=Category.SECURITY,
    priority=Priority.CRITICAL,
    question="Does the project enforce HTTPS/TLS for all traffic?",
    description="TLS protects data in transit and is mandatory for any production service.",
    tags=["https", "tls", "ssl", "certbot", "certificate", "force-ssl"],
)

SECURITY_CORS = Concept(
    id="security.cors",
    name="CORS Policy",
    category=Category.SECURITY,
    priority=Priority.HIGH,
    question="Is CORS configured with an explicit allowlist?",
    description="A wildcard CORS policy (`*`) exposes the API to cross-origin attacks.",
    tags=["cors", "Access-Control-Allow-Origin", "helmet"],
)

SECURITY_HEADERS = Concept(
    id="security.headers",
    name="Security Headers",
    category=Category.SECURITY,
    priority=Priority.HIGH,
    question="Are security headers (HSTS, CSP, X-Frame-Options) set?",
    description="Security headers provide defence-in-depth against clickjacking, XSS, and downgrade attacks.",
    tags=["helmet", "hsts", "csp", "X-Frame-Options", "X-Content-Type-Options"],
)

SECURITY_SANITIZATION = Concept(
    id="security.sanitization",
    name="Input Sanitisation",
    category=Category.SECURITY,
    priority=Priority.CRITICAL,
    question="Does the project sanitise user input to prevent injection attacks?",
    description="SQL injection, XSS, and command injection are the top OWASP risks.",
    tags=["sanitize", "escape", "sqlalchemy.text", "parameterized", "prepared"],
)

SECURITY_DEPENDENCY_SCAN = Concept(
    id="security.dependency-scan",
    name="Dependency Vulnerability Scanning",
    category=Category.SECURITY,
    priority=Priority.HIGH,
    question="Does the CI pipeline scan dependencies for known vulnerabilities?",
    description="Known CVEs in dependencies are exploited in the wild within hours of disclosure.",
    tags=["snyk", "dependabot", "pip-audit", "trivy", "npm audit", "cve"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Data Management
# ─────────────────────────────────────────────────────────────────────────────

DATA_ORM = Concept(
    id="data.orm",
    name="ORM / Query Builder",
    category=Category.DATA,
    priority=Priority.HIGH,
    question="Does the project use an ORM or query builder instead of raw SQL?",
    description="ORMs prevent SQL injection by default and provide schema migration tooling.",
    tags=["sqlalchemy", "prisma", "typeorm", "sequelize", "eloquent", "gorm", "django-orm"],
)

DATA_MIGRATIONS = Concept(
    id="data.migrations",
    name="Database Migrations",
    category=Category.DATA,
    priority=Priority.HIGH,
    question="Does the project use versioned database migrations?",
    description="Migrations are the only safe way to evolve production schemas without data loss.",
    tags=["alembic", "flyway", "liquibase", "knex", "migrate", "prisma migrate", "django migrate"],
)

DATA_INDEXING = Concept(
    id="data.indexing",
    name="Database Indexing Strategy",
    category=Category.DATA,
    priority=Priority.MEDIUM,
    question="Are indexes defined on high-cardinality query columns?",
    description="Missing indexes cause full-table scans and quadratic growth in latency.",
    tags=["index", "CREATE INDEX", "@index", "unique_index"],
)

DATA_BACKUP = Concept(
    id="data.backup",
    name="Backup & Recovery",
    category=Category.DATA,
    priority=Priority.HIGH,
    question="Is there a documented backup and recovery strategy?",
    description="Without backups, a single DROP TABLE or disk failure is irreversible.",
    tags=["backup", "pg_dump", "mongodump", "snapshot", "restore", "replication"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Observability
# ─────────────────────────────────────────────────────────────────────────────

OBS_METRICS = Concept(
    id="observability.metrics",
    name="Metrics & Monitoring",
    category=Category.OBSERVABILITY,
    priority=Priority.HIGH,
    question="Does the project emit application metrics (RED / USE)?",
    description="Metrics let you detect latency spikes, error rate increases, and saturation before users do.",
    tags=["prometheus", "statsd", "datadog", "newrelic", "opentelemetry", "metrics", "histogram"],
)

OBS_TRACING = Concept(
    id="observability.tracing",
    name="Distributed Tracing",
    category=Category.OBSERVABILITY,
    priority=Priority.MEDIUM,
    question="Does the project emit distributed traces (OpenTelemetry, Jaeger, Zipkin)?",
    description="Traces connect spans across services and are essential for debugging microservice chains.",
    tags=["opentelemetry", "jaeger", "zipkin", "tracer", "span", "trace"],
)

OBS_ALERTING = Concept(
    id="observability.alerting",
    name="Alerting & Paging",
    category=Category.OBSERVABILITY,
    priority=Priority.HIGH,
    question="Are there defined alerting rules and escalation paths?",
    description="Alerts that page on-call engineers reduce mean-time-to-detect (MTTD).",
    tags=["alertmanager", "pagerduty", "opsgenie", "alert", "slo", "sli"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Resilience
# ─────────────────────────────────────────────────────────────────────────────

RES_CIRCUIT_BREAKER = Concept(
    id="resilience.circuit-breaker",
    name="Circuit Breaker",
    category=Category.RESILIENCE,
    priority=Priority.HIGH,
    question="Does the project use a circuit breaker for external calls?",
    description="Circuit breakers prevent cascading failures when a downstream service degrades.",
    tags=["pybreaker", "opossum", "hystrix", "resilience4j", "circuit", "breaker"],
)

RES_RETRIES = Concept(
    id="resilience.retries",
    name="Retry with Backoff",
    category=Category.RESILIENCE,
    priority=Priority.HIGH,
    question="Does the project implement retries with exponential backoff and jitter?",
    description="Fixed-interval retries amplify thundering-herd problems; exponential backoff with jitter mitigates them.",
    tags=["retry", "backoff", "tenacity", "exponential", "jitter"],
)

RES_TIMEOUTS = Concept(
    id="resilience.timeouts",
    name="Request Timeouts",
    category=Category.RESILIENCE,
    priority=Priority.HIGH,
    question="Does the project set explicit connect, read, and write timeouts?",
    description="Unbounded timeouts exhaust connection pools and thread pools under partial failure.",
    tags=["timeout", "connectTimeout", "readTimeout", "socket-timeout"],
)

RES_DEAD_LETTER = Concept(
    id="resilience.dead-letter",
    name="Dead-Letter Queue",
    category=Category.RESILIENCE,
    priority=Priority.MEDIUM,
    question="Is there a dead-letter queue (DLQ) for failed messages?",
    description="A DLQ captures poison messages without blocking the main processing pipeline.",
    tags=["dlq", "dead-letter", "dead_letter", "requeue"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Deployment & DevOps
# ─────────────────────────────────────────────────────────────────────────────

DEPLOY_CONTAINERS = Concept(
    id="deployment.containers",
    name="Containerisation",
    category=Category.DEPLOYMENT,
    priority=Priority.HIGH,
    question="Is the project containerised with Docker?",
    description="Containers provide reproducible builds and environment parity across dev/staging/prod.",
    tags=["Dockerfile", "docker-compose", "docker", "container"],
)

DEPLOY_ORCHESTRATION = Concept(
    id="deployment.orchestration",
    name="Container Orchestration",
    category=Category.DEPLOYMENT,
    priority=Priority.MEDIUM,
    question="Does the project deploy via Kubernetes or a managed orchestrator?",
    description="Orchestrators automate rollouts, self-heal failed containers, and manage secrets.",
    tags=["kubernetes", "k8s", "helm", "deployment.yaml", "argo", "service"],
)

DEPLOY_CI_CD = Concept(
    id="deployment.ci-cd",
    name="CI/CD Pipeline",
    category=Category.DEPLOYMENT,
    priority=Priority.HIGH,
    question="Is there a CI/CD pipeline (GitHub Actions, GitLab CI, Jenkins)?",
    description="Automated pipelines catch bugs early and ship changes to production safely.",
    tags=["github/workflows", ".gitlab-ci.yml", "Jenkinsfile", "ci/cd", "pipeline"],
)

DEPLOY_IAAC = Concept(
    id="deployment.iaac",
    name="Infrastructure as Code",
    category=Category.DEPLOYMENT,
    priority=Priority.MEDIUM,
    question="Is infrastructure defined as code (Terraform, CloudFormation, Pulumi)?",
    description="IaC makes infrastructure reproducible, version-controlled, and peer-reviewable.",
    tags=["terraform", "cloudformation", "pulumi", ".tf", "main.tf"],
)

DEPLOY_HEALTHCHECKS = Concept(
    id="deployment.healthchecks",
    name="Health Checks",
    category=Category.DEPLOYMENT,
    priority=Priority.HIGH,
    question="Does the service expose liveness and readiness endpoints?",
    description="Health checks allow orchestrators and load balancers to manage traffic safely.",
    tags=["/health", "/ready", "liveness", "readiness", "health"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Performance
# ─────────────────────────────────────────────────────────────────────────────

PERF_CONNECTION_POOL = Concept(
    id="performance.connection-pool",
    name="Database Connection Pooling",
    category=Category.PERFORMANCE,
    priority=Priority.HIGH,
    question="Does the project use a connection pool for database connections?",
    description="Connection pools amortise TCP handshake cost and prevent connection exhaustion.",
    tags=["pool", "pool_size", "max_connections", "connection pool", "pgbouncer"],
)

PERF_ASYNC = Concept(
    id="performance.async",
    name="Async / Non-blocking I/O",
    category=Category.PERFORMANCE,
    priority=Priority.MEDIUM,
    question="Does the project use async I/O (asyncio, event loop, promises)?",
    description="Non-blocking I/O lets a single thread handle many concurrent connections.",
    tags=["async def", "await", "asyncio", "Promise", "async/await", "event-loop"],
)

PERF_PAGINATION = Concept(
    id="performance.pagination",
    name="Cursor / Offset Pagination",
    category=Category.PERFORMANCE,
    priority=Priority.MEDIUM,
    question="Does the API paginate list endpoints?",
    description="Returning unbounded lists causes memory blow-ups and slow responses.",
    tags=["limit", "offset", "cursor", "page", "pagination"],
)

PERF_CDN = Concept(
    id="performance.cdn",
    name="CDN / Edge Caching",
    category=Category.PERFORMANCE,
    priority=Priority.LOW,
    question="Are static assets served via a CDN or edge cache?",
    description="CDNs reduce origin load and cut latency for globally distributed users.",
    tags=["cdn", "cloudfront", "cloudflare", "cdnjs", "max-age", "cache-control"],
)

# ─────────────────────────────────────────────────────────────────────────────
# User Experience
# ─────────────────────────────────────────────────────────────────────────────

UX_I18N = Concept(
    id="ux.i18n",
    name="Internationalisation (i18n)",
    category=Category.UX,
    priority=Priority.LOW,
    question="Does the project support multiple locales or languages?",
    description="i18n is essential for global products and is cheaper to build from the start.",
    tags=["i18n", "locale", "translations", "gettext", "i18next"],
)

UX_ACCESSIBILITY = Concept(
    id="ux.accessibility",
    name="Accessibility (a11y)",
    category=Category.UX,
    priority=Priority.LOW,
    question="Does the frontend include accessibility labels and ARIA attributes?",
    description="Accessible interfaces are usable by people with disabilities and required by law in many jurisdictions.",
    tags=["aria-", "role=", "alt=", "a11y", "accessibility"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Integration
# ─────────────────────────────────────────────────────────────────────────────

INTEG_WEBHOOKS = Concept(
    id="integration.webhooks",
    name="Webhooks",
    category=Category.INTEGRATION,
    priority=Priority.MEDIUM,
    question="Does the project expose or consume webhooks?",
    description="Webhooks enable event-driven integrations without polling.",
    tags=["webhook", "callback", "incoming-webhook"],
)

INTEG_GRAPHQL = Concept(
    id="integration.graphql",
    name="GraphQL API",
    category=Category.INTEGRATION,
    priority=Priority.LOW,
    question="Does the project expose a GraphQL endpoint?",
    description="GraphQL lets clients request exactly the data they need, reducing over-fetching.",
    tags=["graphql", "gql", "apollo", "strawberry", "graphene"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Streaming & Messaging
# ─────────────────────────────────────────────────────────────────────────────

STREAM_MSG_BROKER = Concept(
    id="streaming.message-broker",
    name="Message Broker",
    category=Category.STREAMING,
    priority=Priority.MEDIUM,
    question="Does the project use a message broker (Kafka, RabbitMQ, NATS)?",
    description="Message brokers decouple producers from consumers and buffer traffic spikes.",
    tags=["kafka", "rabbitmq", "nats", "pulsar", "redis pub/sub", "broker"],
)

STREAM_EVENT_STREAMING = Concept(
    id="streaming.event-streaming",
    name="Event Streaming (Kafka / Pulsar)",
    category=Category.STREAMING,
    priority=Priority.MEDIUM,
    question="Does the project use event streaming for real-time data pipelines?",
    description="Event streaming enables real-time analytics, log aggregation, and CQRS patterns.",
    tags=["kafka", "pulsar", "kinesis", "event-stream", "consumer-group", "producer"],
)

STREAM_WEBRTC = Concept(
    id="streaming.webrtc",
    name="WebRTC / Real-Time Communication",
    category=Category.STREAMING,
    priority=Priority.LOW,
    question="Does the project use WebRTC for real-time audio/video?",
    description="WebRTC enables peer-to-peer video calls and screen sharing without plugins.",
    tags=["webrtc", "rtc", "peer-connection", "mediasoup", "livekit", "janus"],
)

STREAM_LIVE_STREAMING = Concept(
    id="streaming.live-streaming",
    name="Live Streaming Pipeline",
    category=Category.STREAMING,
    priority=Priority.LOW,
    question="Does the project support live video or audio streaming (RTMP, HLS, DASH)?",
    description="Live streaming pipelines ingest, transcode, and distribute real-time media at scale.",
    tags=["rtmp", "hls", "dash", "mpegts", "transcode", "ffmpeg", "live", "stream"],
)

STREAM_WEBSOCKETS = Concept(
    id="streaming.websockets",
    name="WebSocket Support",
    category=Category.STREAMING,
    priority=Priority.MEDIUM,
    question="Does the project use WebSockets for real-time bidirectional communication?",
    description="WebSockets are essential for chat, live dashboards, and collaborative editing.",
    tags=["websocket", "socket.io", "ws:", "wss:", "sse", "server-sent-events"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ML & AI
# ─────────────────────────────────────────────────────────────────────────────

ML_MODEL_SERVING = Concept(
    id="ml.model-serving",
    name="ML Model Serving",
    category=Category.ML_AI,
    priority=Priority.LOW,
    question="Does the project serve ML models (TorchServe, Triton, FastAPI + model)?",
    description="Model serving infrastructure makes trained models accessible via API.",
    tags=["torchserve", "triton", "mlflow", "bentoml", "model", "inference", "predict"],
)

ML_FEATURE_STORE = Concept(
    id="ml.feature-store",
    name="Feature Store",
    category=Category.ML_AI,
    priority=Priority.LOW,
    question="Does the project use a feature store (Feast, Tecton)?",
    description="Feature stores eliminate training-serving skew and enable feature reuse across models.",
    tags=["feast", "tecton", "feature-store", "feature engineering"],
)

ML_NLP = Concept(
    id="ml.nlp",
    name="NLP / Text Processing Pipeline",
    category=Category.ML_AI,
    priority=Priority.LOW,
    question="Does the project include NLP processing (tokenisation, embeddings, LLM calls)?",
    description="NLP pipelines power chatbots, search, summarisation, and content moderation.",
    tags=["transformers", "spacy", "nltk", "llm", "gpt", "bert", "embedding", "tokenizer", "langchain", "llamaindex"],
)

ML_TRANSFORMERS = Concept(
    id="ml.transformers",
    name="Transformer Architecture Implementation",
    category=Category.ML_AI,
    priority=Priority.LOW,
    question="Does the project implement or fine-tune transformer models?",
    description="Custom transformer implementations demonstrate deep understanding of attention mechanisms and model architecture.",
    tags=["transformer", "attention", "self-attention", "multi-head", "encoder", "decoder", "fine-tune"],
)

ML_MLOPS = Concept(
    id="ml.mlops",
    name="MLOps Pipeline",
    category=Category.ML_AI,
    priority=Priority.LOW,
    question="Does the project have an MLOps pipeline (training, evaluation, deployment, monitoring)?",
    description="MLOps automates the model lifecycle from data ingestion to production monitoring.",
    tags=["mlops", "pipeline", "training", "evaluation", "model-registry", "drift", "kubeflow"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Networking
# ─────────────────────────────────────────────────────────────────────────────

NET_PROXY = Concept(
    id="networking.proxy",
    name="Reverse Proxy / API Gateway",
    category=Category.NETWORKING,
    priority=Priority.MEDIUM,
    question="Does the project use a reverse proxy or API gateway?",
    description="Proxies and gateways centralise auth, rate limiting, and routing.",
    tags=["nginx", "traefik", "kong", "envoy", "api-gateway", "apigee"],
)

NET_SERVICE_MESH = Concept(
    id="networking.service-mesh",
    name="Service Mesh",
    category=Category.NETWORKING,
    priority=Priority.LOW,
    question="Does the project use a service mesh (Istio, Linkerd, Consul Connect)?",
    description="Service meshes provide mutual TLS, traffic shaping, and observability without application changes.",
    tags=["istio", "linkerd", "service-mesh", "sidecar", "consul"],
)

NET_DNS = Concept(
    id="networking.dns",
    name="DNS & Service Discovery",
    category=Category.NETWORKING,
    priority=Priority.MEDIUM,
    question="Does the project configure DNS or service discovery?",
    description="Proper DNS configuration is fundamental for service-to-service communication.",
    tags=["dns", "consul", "etcd", "core-dns", "service-discovery"],
)

NET_LOAD_BALANCER = Concept(
    id="networking.load-balancer",
    name="Load Balancer",
    category=Category.NETWORKING,
    priority=Priority.HIGH,
    question="Does the project use a load balancer for traffic distribution?",
    description="Load balancers distribute traffic across instances and provide failover.",
    tags=["load-balancer", "lb", "alb", "elb", "nginx upstream", "upstream"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Compliance & Governance
# ─────────────────────────────────────────────────────────────────────────────

COMPLIANCE_PII = Concept(
    id="compliance.pii",
    name="PII Handling & Data Privacy",
    category=Category.COMPLIANCE,
    priority=Priority.HIGH,
    question="Does the project identify and protect personally identifiable information (PII)?",
    description="PII exposure is a compliance violation under GDPR, CCPA, and other regulations.",
    tags=["pii", "gdpr", "ccpa", "personal-data", "anonymize", "redact"],
)

COMPLIANCE_AUDIT_LOG = Concept(
    id="compliance.audit-log",
    name="Audit Logging",
    category=Category.COMPLIANCE,
    priority=Priority.MEDIUM,
    question="Does the project log security-relevant events for audit purposes?",
    description="Audit logs are required for SOC 2, HIPAA, and many regulatory frameworks.",
    tags=["audit", "audit-log", "soc2", "hipaa", "compliance"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Frontend Architecture
# ─────────────────────────────────────────────────────────────────────────────

FRONTEND_RENDERING = Concept(
    id="frontend.rendering",
    name="Rendering Architecture",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Does the frontend employ an appropriate rendering strategy (SSR, SSG, CSR, Streaming, Hydration)?",
    description="Balances initial load latency, SEO, server resource utilization, and client responsiveness.",
    tags=["ssr", "ssg", "csr", "hydration", "streaming", "render", "prerender"],
)

FRONTEND_ROUTING = Concept(
    id="frontend.routing",
    name="Page & Route Architecture",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Does the frontend structure routes with proper code boundaries and navigation fallbacks?",
    description="Proper page and route architecture prevents monolithic bundle delivery and optimizes navigation.",
    tags=["routing", "router", "spa", "mpa", "route-splitting", "dynamic-routes"],
)

FRONTEND_LOADING = Concept(
    id="frontend.loading",
    name="Loading Strategy & Code Splitting",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Are non-critical components, heavy dependencies, and media assets lazily loaded?",
    description="Dynamic imports and progressive loading protect Time-to-Interactive and bandwidth.",
    tags=["lazy", "dynamic-import", "code-splitting", "suspense", "defer", "skeleton"],
)

FRONTEND_RUNTIME_PERFORMANCE = Concept(
    id="frontend.runtime-performance",
    name="Runtime Performance & Execution Latency",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Does the frontend minimize main-thread blocking, expensive re-renders, and execution bottlenecks?",
    description="Runtime performance governs user interaction responsiveness and frame stability.",
    tags=["performance", "re-render", "memo", "web-vitals", "inp", "main-thread"],
)

FRONTEND_COMPONENT_ARCHITECTURE = Concept(
    id="frontend.component-architecture",
    name="DOM & Component Architecture",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Are component boundaries clean, DOM nesting contained, and large lists virtualized?",
    description="Prevents DOM bloat and keeps rendering updates predictable and fast.",
    tags=["components", "dom-depth", "virtualization", "virtual-list", "windowing"],
)

FRONTEND_RESPONSIVE_DESIGN = Concept(
    id="frontend.responsive-design",
    name="Responsive Design Architecture",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Does the interface gracefully adapt across mobile, tablet, desktop, and large viewports?",
    description="Fluid grids, responsive breakpoints, and viewport adaptation ensure universal usability.",
    tags=["responsive", "media-queries", "breakpoints", "viewport", "mobile-first"],
)

FRONTEND_ASSETS = Concept(
    id="frontend.assets",
    name="Asset Architecture & Optimization",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Are images, fonts, scripts, and media optimized, modern-formatted, and prioritized?",
    description="Asset architecture controls payload sizes, critical rendering paths, and network usage.",
    tags=["assets", "images", "fonts", "webp", "avif", "preload", "next/image"],
)

FRONTEND_STATE_MANAGEMENT = Concept(
    id="frontend.state-management",
    name="State Architecture",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Is state appropriately partitioned between local, shared, global, and server state?",
    description="Clear state boundaries eliminate prop-drilling, desynchronization, and unnecessary re-renders.",
    tags=["state", "redux", "zustand", "context", "server-state", "signals"],
)

FRONTEND_DATA_FETCHING = Concept(
    id="frontend.data-fetching",
    name="Data Fetching Architecture",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Does the frontend manage data fetching with deduplication, caching, and waterfall prevention?",
    description="Strategic data fetching eliminates waterfall request chains and stale data UI.",
    tags=["fetch", "swr", "react-query", "graphql", "waterfall", "dedup"],
)

FRONTEND_CACHING = Concept(
    id="frontend.caching",
    name="Frontend Caching & Storage",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Does the frontend leverage client caching, storage, and revalidation strategies?",
    description="Client-side memory, HTTP cache headers, and local storage reduce roundtrips.",
    tags=["caching", "cache-control", "localstorage", "indexeddb", "swr", "query-cache"],
)

FRONTEND_ERROR_HANDLING = Concept(
    id="frontend.error-handling",
    name="Error & Loading UX",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Are error boundaries, loading skeletons, and recovery mechanisms implemented?",
    description="Resilient frontends gracefully handle network drops, API failures, and rendering exceptions.",
    tags=["error-boundary", "fallback-ui", "skeleton", "empty-state", "retry-ui"],
)

FRONTEND_ACCESSIBILITY = Concept(
    id="frontend.accessibility",
    name="Accessibility Architecture",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Does the frontend support keyboard navigation, ARIA semantics, and screen readers?",
    description="Universal access is a fundamental system-design requirement.",
    tags=["a11y", "aria", "semantic-html", "keyboard-nav", "focus-management"],
)

FRONTEND_SECURITY = Concept(
    id="frontend.security",
    name="Frontend Security Architecture",
    category=Category.FRONTEND,
    priority=Priority.HIGH,
    question="Does the frontend avoid client secret leakage, unsanitized HTML injection, and insecure storage?",
    description="Client applications must maintain strict trust boundaries and prevent XSS/injection.",
    tags=["security", "xss", "dangerouslysetinnerhtml", "client-secrets", "token-storage"],
)

FRONTEND_NETWORK_API = Concept(
    id="frontend.network-api",
    name="Network & API Architecture",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Are API timeouts, retries, cancellation, and WebSocket lifecycles managed safely?",
    description="Network resiliency prevents hung UI states and runaway connection leaks.",
    tags=["network", "timeout", "abortcontroller", "retry", "websocket-lifecycle"],
)

FRONTEND_PERCEIVED_LATENCY = Concept(
    id="frontend.perceived-latency",
    name="Perceived Latency & Optimistic UX",
    category=Category.FRONTEND,
    priority=Priority.LOW,
    question="Are optimistic updates, instant transitions, and skeleton placeholders used to minimize perceived delay?",
    description="Optimistic patterns make asynchronous web applications feel instantaneous to users.",
    tags=["optimistic-ui", "perceived-latency", "skeleton", "prefetch", "instant-transition"],
)

FRONTEND_WEB3 = Concept(
    id="frontend.web3",
    name="Web3 Frontend Architecture",
    category=Category.FRONTEND,
    priority=Priority.MEDIUM,
    question="Does the UI manage wallet connection lifecycles, network switching, and transaction progress cleanly?",
    description="Web3 user interfaces require explicit wallet state management and RPC failure UX.",
    tags=["wallet-connect", "wagmi", "rainbowkit", "tx-status", "network-switch", "rpc-fallback"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Complete taxonomy list — used by the rule engine
# ─────────────────────────────────────────────────────────────────────────────

ALL_CONCEPTS: List[Concept] = [
    # Foundation
    FOUNDATION_CACHING,
    FOUNDATION_CONFIG,
    FOUNDATION_LOGGING,
    FOUNDATION_ERROR_HANDLING,
    FOUNDATION_VALIDATION,
    FOUNDATION_AUTH,
    FOUNDATION_AUTHORIZATION,
    FOUNDATION_RATE_LIMITING,
    FOUNDATION_API_VERSIONING,
    FOUNDATION_IDEMPOTENCY,
    FOUNDATION_OPENAPI,
    # Security
    SECURITY_SECRETS,
    SECURITY_HTTPS,
    SECURITY_CORS,
    SECURITY_HEADERS,
    SECURITY_SANITIZATION,
    SECURITY_DEPENDENCY_SCAN,
    # Data
    DATA_ORM,
    DATA_MIGRATIONS,
    DATA_INDEXING,
    DATA_BACKUP,
    # Observability
    OBS_METRICS,
    OBS_TRACING,
    OBS_ALERTING,
    # Resilience
    RES_CIRCUIT_BREAKER,
    RES_RETRIES,
    RES_TIMEOUTS,
    RES_DEAD_LETTER,
    # Deployment
    DEPLOY_CONTAINERS,
    DEPLOY_ORCHESTRATION,
    DEPLOY_CI_CD,
    DEPLOY_IAAC,
    DEPLOY_HEALTHCHECKS,
    # Performance
    PERF_CONNECTION_POOL,
    PERF_ASYNC,
    PERF_PAGINATION,
    PERF_CDN,
    # UX
    UX_I18N,
    UX_ACCESSIBILITY,
    # Integration
    INTEG_WEBHOOKS,
    INTEG_GRAPHQL,
    # Streaming
    STREAM_MSG_BROKER,
    STREAM_EVENT_STREAMING,
    STREAM_WEBRTC,
    STREAM_LIVE_STREAMING,
    STREAM_WEBSOCKETS,
    # ML & AI
    ML_MODEL_SERVING,
    ML_FEATURE_STORE,
    ML_NLP,
    ML_TRANSFORMERS,
    ML_MLOPS,
    # Networking
    NET_PROXY,
    NET_SERVICE_MESH,
    NET_DNS,
    NET_LOAD_BALANCER,
    # Compliance
    COMPLIANCE_PII,
    COMPLIANCE_AUDIT_LOG,
    # Frontend Architecture
    FRONTEND_RENDERING,
    FRONTEND_ROUTING,
    FRONTEND_LOADING,
    FRONTEND_RUNTIME_PERFORMANCE,
    FRONTEND_COMPONENT_ARCHITECTURE,
    FRONTEND_RESPONSIVE_DESIGN,
    FRONTEND_ASSETS,
    FRONTEND_STATE_MANAGEMENT,
    FRONTEND_DATA_FETCHING,
    FRONTEND_CACHING,
    FRONTEND_ERROR_HANDLING,
    FRONTEND_ACCESSIBILITY,
    FRONTEND_SECURITY,
    FRONTEND_NETWORK_API,
    FRONTEND_PERCEIVED_LATENCY,
    FRONTEND_WEB3,
]

CONCEPTS_BY_ID: dict[str, Concept] = {c.id: c for c in ALL_CONCEPTS}
