"""Python file scanner — emits signals from Python source files.

The scanner reads Python files and produces ``FileSignals`` objects
containing pattern-matched signals for system-design concepts.

Signal IDs follow the pattern: ``{concept_id}.{kind}.{pattern-name}``
but the emitted Signal uses the existing sdat.models.Signal format with
concept_id, kind (SignalKind), file_path, line_range, evidence, confidence.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List, Set

from sdat.models import (
    EvidenceFact,
    EvidenceKind,
    FileEvidence,
    FileSignals,
    Signal,
    SignalBridge,
    SignalKind,
)

# ─────────────────────────────────────────────────────────────────────────────
# Pattern definitions — each (concept_id, signal_kind, regex, language_tag)
# ─────────────────────────────────────────────────────────────────────────────

# Foundation: Environment Configuration
FOUNDATION_CONFIG_PATTERNS: List[tuple] = [
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"from\s+dotenv|import\s+dotenv|load_dotenv"), "python"),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"os\.environ|os\.getenv|getenv"), "python"),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"from\s+os\s+import\s+environ"), "python"),
]

FOUNDATION_CONFIG_ABSENCE = "foundation.config"
HARDCODED_SECRET_RE = re.compile(
    r"(?:api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]",
    re.IGNORECASE,
)

# Foundation: Logging
FOUNDATION_LOGGING_PATTERNS: List[tuple] = [
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"import\s+logging|from\s+logging"), "python"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"from\s+loguru|import\s+loguru"), "python"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"from\s+structlog|import\s+structlog"), "python"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"class\s+\w*Logger\w*"), "python"),
]

# Foundation: Caching
FOUNDATION_CACHING_PATTERNS: List[tuple] = [
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"from\s+redis|import\s+redis|redis\.Redis|redis\.StrictRedis|redis\.from_url"), "python"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"from\s+memcache|import\s+memcache|pylibmc|pymemcache"), "python"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"lru_cache|functools\.lru_cache|@cache|@lru_cache"), "python"),
]

# Foundation: Error Handling
FOUNDATION_ERROR_HANDLING_PATTERNS: List[tuple] = [
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"@.*errorhandler|register_error_handler"), "python"),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"try\s*:"), "python"),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"middleware|Middleware"), "python"),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"class\s+\w*Error\w*|class\s+\w*Exception\w*"), "python"),
]
BARE_EXCEPT_RE = re.compile(r"except\s*:")
PRINT_EXCEPTION_RE = re.compile(r"print\(.*[Ee]xception|print\(.*[Ee]rror")

# Foundation: Validation
FOUNDATION_VALIDATION_PATTERNS: List[tuple] = [
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+pydantic|import\s+pydantic|BaseModel"), "python"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+zod|import\s+.*zod|z\.object|z\.string"), "python"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+joi|import\s+joi|Joi\."), "python"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+validator|import\s+validator"), "python"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+class-validator|import\s+class_validator|@IsString"), "python"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"if\s+not\s+\w+\s*:|if\s+\w+\s+is\s+None"), "python"),
]

# Foundation: Auth
FOUNDATION_AUTH_PATTERNS: List[tuple] = [
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"jwt|JWT|pyjwt|create_access_token|decode_token"), "python"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"oauth|OAuth|authlib|requests_oauthlib"), "python"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"passport|passport-|Passport"), "python"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"session\[|Session\(|from\s+flask.*session"), "python"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"bcrypt|generate_password_hash|check_password_hash"), "python"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"argon2|phc.wrapper|argon2cffi"), "python"),
]
PLAINTEXT_PW_RE = re.compile(r"password\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE)

# Foundation: Authorization
FOUNDATION_AUTHORIZATION_PATTERNS: List[tuple] = [
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"rbac|RBAC|role.based"), "python"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"casbin|Casbin|Enforcer"), "python"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"@policy|require.*policy|zanzibar"), "python"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"role\s*==|has_role|is_admin|is_authorized"), "python"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"@permission|@requires|@guard"), "python"),
]

# Foundation: Rate Limiting
FOUNDATION_RATE_LIMITING_PATTERNS: List[tuple] = [
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"express-rate-limit|express_rate_limit|RateLimit"), "python"),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"slowapi|Limiter|@limiter\.limit"), "python"),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"ratelimit|DjangoRatelimit|@ratelimit"), "python"),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"throttle|Throttle|SimpleRateThrottle"), "python"),
]

# Data: ORM
DATA_ORM_PATTERNS: List[tuple] = [
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+sqlalchemy|import\s+sqlalchemy|SQLAlchemy|declarative_base"), "python"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+prisma|import\s+prisma|@prisma\.client|PrismaClient"), "python"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+typeorm|import\s+typeorm|TypeORM|createConnection"), "python"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+sequelize|import\s+sequelize|new\s+Sequelize"), "python"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+illuminate|import\s+illuminate|Eloquent|Schema::"), "python"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+gorm|import\s+gorm|gorm\.Open"), "python"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+django\.db|models\.Model|class\s+\w+\(models\.Model\)"), "python"),
]
RAW_SQL_CONCAT_RE = re.compile(r"execute\([^)]*\+|raw\([^)]*\+|f['\"]SELECT|f['\"]INSERT|f['\"]UPDATE|f['\"]DELETE", re.IGNORECASE)

# Data: Migrations
DATA_MIGRATIONS_PATTERNS: List[tuple] = [
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"alembic|from\s+alembic"), "python"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"flyway|Flyway"), "python"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"liquibase|Liquibase"), "python"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"knex|knex migrate|\.migrate\("), "python"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"prisma migrate|prisma\s+migrate"), "python"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"manage\.py\s+migrate|migrate\("), "python"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"migrations/|/migrations/"), "python"),
]

# Data: Indexing
DATA_INDEXING_PATTERNS: List[tuple] = [
    ("data.indexing", SignalKind.PRESENCE, re.compile(r"index\s*=\s*True|Index\(|unique_index|add_index"), "python"),
    ("data.indexing", SignalKind.PRESENCE, re.compile(r"CREATE\s+INDEX|createIndex|add_index"), "python"),
    ("data.indexing", SignalKind.PRESENCE, re.compile(r"unique\s*=\s*True|unique_index|UNIQUE"), "python"),
    ("data.indexing", SignalKind.PRESENCE, re.compile(r"__table_args__|@index|Index\("), "python"),
]

# Security: CORS
SECURITY_CORS_PATTERNS: List[tuple] = [
    ("security.cors", SignalKind.PRESENCE, re.compile(r"CORSMiddleware|cors\(|CORS|Access-Control-Allow-Origin"), "python"),
    ("security.cors", SignalKind.PRESENCE, re.compile(r"from\s+fastapi\.middleware|CORSMiddleware"), "python"),
    ("security.cors", SignalKind.PRESENCE, re.compile(r"cors\(\)|require\(.*cors|Access-Control-Allow-Origin"), "python"),
]
WILDCARD_CORS_RE = re.compile(r"\*\s*,\s*origin|Access-Control-Allow-Origin.*\*", re.IGNORECASE)

# Security: Headers
SECURITY_HEADERS_PATTERNS: List[tuple] = [
    ("security.headers", SignalKind.PRESENCE, re.compile(r"helmet|Helmet"), "python"),
    ("security.headers", SignalKind.PRESENCE, re.compile(r"Strict-Transport-Security|HSTS|forceSSL"), "python"),
    ("security.headers", SignalKind.PRESENCE, re.compile(r"Content-Security-Policy|CSP|helmet\.contentSecurityPolicy"), "python"),
    ("security.headers", SignalKind.PRESENCE, re.compile(r"X-Frame-Options|frame-ancestors"), "python"),
]

# Security: Dependency scan
SECURITY_DEPENDENCY_SCAN_PATTERNS: List[tuple] = [
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"snyk|\.snyk"), "python"),
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"dependabot|Dependabot"), "python"),
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"pip-audit|pip_audit"), "python"),
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"trivy|Trivy"), "python"),
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"npm\s+audit"), "python"),
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"safety\s+check"), "python"),
]

# Observability: Metrics
OBS_METRICS_PATTERNS: List[tuple] = [
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"prometheus|Prometheus|prometheus_client|from\s+prometheus"), "python"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"datadog|ddtrace|from\s+datadog"), "python"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"newrelic|newrelic\.agent"), "python"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"statsd|datadog\.statsd|from\s+statsd"), "python"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"opentelemetry|OTEL|from\s+opentelemetry"), "python"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"metrics\s*=|Counter\(|Histogram\(|Gauge\("), "python"),
]

# Observability: Tracing
OBS_TRACING_PATTERNS: List[tuple] = [
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"opentelemetry|trace\.get_tracer|TracerProvider"), "python"),
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"jaeger|Jaeger|from\s+jaeger"), "python"),
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"zipkin|Zipkin|from\s+zipkin"), "python"),
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"tracer|Tracer|start_span|trace_id"), "python"),
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"start_span|Span\(|current_span"), "python"),
]

# Observability: Alerting
OBS_ALERTING_PATTERNS: List[tuple] = [
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"alertmanager|Alertmanager"), "python"),
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"pagerduty|PagerDuty|pypagerduty"), "python"),
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"opsgenie|OpsGenie"), "python"),
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"alert\(|send_alert|raise.*alert"), "python"),
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"slo|SLI|error_budget"), "python"),
]

# Resilience: Circuit Breaker
RES_CIRCUIT_BREAKER_PATTERNS: List[tuple] = [
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"pybreaker|CircuitBreaker|breaker\("), "python"),
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"opossum|Opossum|Monkey"), "python"),
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"hystrix|Hystrix"), "python"),
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"resilience4j|CircuitBreaker"), "python"),
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"@breaker|@circuit_breaker"), "python"),
]

# Resilience: Retries
RES_RETRIES_PATTERNS: List[tuple] = [
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"from\s+tenacity|import\s+tenacity|@retry|stop_after_attempt"), "python"),
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"backoff|@backoff|backoff\.on_exception"), "python"),
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"@retry|retrying\.retry|retry\("), "python"),
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"exponential|backoff\.expo|exp\.jitter"), "python"),
]
FIXED_RETRY_RE = re.compile(r"time\.sleep\(\d+\)", re.IGNORECASE)

# Resilience: Timeouts
RES_TIMEOUTS_PATTERNS: List[tuple] = [
    ("resilience.timeouts", SignalKind.PRESENCE, re.compile(r"timeout\s*=|Timeout\(|timeout="), "python"),
    ("resilience.timeouts", SignalKind.PRESENCE, re.compile(r"read_timeout|readTimeout"), "python"),
    ("resilience.timeouts", SignalKind.PRESENCE, re.compile(r"connect_timeout|connectTimeout"), "python"),
]

# Resilience: Dead Letter Queue
RES_DEAD_LETTER_PATTERNS: List[tuple] = [
    ("resilience.dead-letter", SignalKind.PRESENCE, re.compile(r"dlq|DLQ|dead.letter|dead_letter_queue"), "python"),
    ("resilience.dead-letter", SignalKind.PRESENCE, re.compile(r"dead.letter.queue|dead_letter"), "python"),
    ("resilience.dead-letter", SignalKind.PRESENCE, re.compile(r"dead_letter|DeadLetter"), "python"),
    ("resilience.dead-letter", SignalKind.PRESENCE, re.compile(r"requeue|re-queue|nack.*requeue"), "python"),
]

# Deployment: Containers
DEPLOY_CONTAINERS_PATTERNS: List[tuple] = [
    ("deployment.containers", SignalKind.PRESENCE, re.compile(r"\b(?:Dockerfile|docker\.from_env|testcontainers)\b"), "python"),
    ("deployment.containers", SignalKind.PRESENCE, re.compile(r"\bdocker-compose\b"), "python"),
    ("deployment.containers", SignalKind.PRESENCE, re.compile(r"\.dockerignore\b"), "python"),
]

# Deployment: Orchestration
DEPLOY_ORCHESTRATION_PATTERNS: List[tuple] = [
    ("deployment.orchestration", SignalKind.PRESENCE, re.compile(r"\b(?:kubectl|kubernetes|CoreV1Api)\b"), "python"),
    ("deployment.orchestration", SignalKind.PRESENCE, re.compile(r"\b(?:Chart\.yaml|helm)\b"), "python"),
    ("deployment.orchestration", SignalKind.PRESENCE, re.compile(r"\b(?:argo-workflows|argoproj)\b"), "python"),
    ("deployment.orchestration", SignalKind.PRESENCE, re.compile(r"\b(?:ecs_client|taskDefinition)\b"), "python"),
]

# Deployment: CI/CD
DEPLOY_CI_CD_PATTERNS: List[tuple] = [
    ("deployment.ci-cd", SignalKind.PRESENCE, re.compile(r"\bgithub/actions\b"), "python"),
    ("deployment.ci-cd", SignalKind.PRESENCE, re.compile(r"\bgitlab-ci\.yml\b"), "python"),
    ("deployment.ci-cd", SignalKind.PRESENCE, re.compile(r"\bJenkinsfile\b"), "python"),
    ("deployment.ci-cd", SignalKind.PRESENCE, re.compile(r"\bcircleci\b"), "python"),
    ("deployment.ci-cd", SignalKind.PRESENCE, re.compile(r"\bazure-pipelines\b"), "python"),
]

# Deployment: IaC
DEPLOY_IAAC_PATTERNS: List[tuple] = [
    ("deployment.iaac", SignalKind.PRESENCE, re.compile(r"\b(?:terraform|pulumi|terrascript)\b"), "python"),
    ("deployment.iaac", SignalKind.PRESENCE, re.compile(r"\bAWSTemplateFormatVersion\b"), "python"),
    ("deployment.iaac", SignalKind.PRESENCE, re.compile(r"\b(?:bicep|troposphere)\b"), "python"),
]

# Deployment: Health Checks
DEPLOY_HEALTHCHECKS_PATTERNS: List[tuple] = [
    ("deployment.healthchecks", SignalKind.PRESENCE, re.compile(r"/health|health\(\)|def\s+health"), "python"),
    ("deployment.healthchecks", SignalKind.PRESENCE, re.compile(r"/ready|readiness\(\)|def\s+ready"), "python"),
    ("deployment.healthchecks", SignalKind.PRESENCE, re.compile(r"/live|liveness\(\)|def\s+live"), "python"),
]

# Performance: Connection Pool
PERF_CONNECTION_POOL_PATTERNS: List[tuple] = [
    ("performance.connection-pool", SignalKind.PRESENCE, re.compile(r"pool|pool_size|pooling|pool_connections|pool_maxsize"), "python"),
    ("performance.connection-pool", SignalKind.PRESENCE, re.compile(r"pool_size|poolsize|maxsize|max_overflow"), "python"),
    ("performance.connection-pool", SignalKind.PRESENCE, re.compile(r"pgbouncer|PGBouncer|pool_mode"), "python"),
    ("performance.connection-pool", SignalKind.PRESENCE, re.compile(r"connection_pool|ConnectionPool|create_engine"), "python"),
]

# Performance: Async
PERF_ASYNC_PATTERNS: List[tuple] = [
    ("performance.async", SignalKind.PRESENCE, re.compile(r"async\s+def"), "python"),
    ("performance.async", SignalKind.PRESENCE, re.compile(r"\bawait\b"), "python"),
    ("performance.async", SignalKind.PRESENCE, re.compile(r"asyncio|from\s+asyncio|import\s+asyncio"), "python"),
    ("performance.async", SignalKind.PRESENCE, re.compile(r"Promise|new\s+Promise|async\s+function"), "python"),
    ("performance.async", SignalKind.PRESENCE, re.compile(r"event.?loop|EventLoop|uvloop|trio"), "python"),
]

# Performance: Pagination
PERF_PAGINATION_PATTERNS: List[tuple] = [
    ("performance.pagination", SignalKind.PRESENCE, re.compile(r"limit\s*=|LIMIT\s+\d|\.limit\("), "python"),
    ("performance.pagination", SignalKind.PRESENCE, re.compile(r"offset\s*=|OFFSET\s+\d|\.offset\("), "python"),
    ("performance.pagination", SignalKind.PRESENCE, re.compile(r"cursor|Cursor|next_cursor|page_token"), "python"),
    ("performance.pagination", SignalKind.PRESENCE, re.compile(r"page\s*=|page_size|per_page"), "python"),
]

# Performance: CDN
PERF_CDN_PATTERNS: List[tuple] = [
    ("performance.cdn", SignalKind.PRESENCE, re.compile(r"cloudfront|CloudFront"), "python"),
    ("performance.cdn", SignalKind.PRESENCE, re.compile(r"cloudflare|Cloudflare|cf-cache-status"), "python"),
    ("performance.cdn", SignalKind.PRESENCE, re.compile(r"fastly|Fastly|fastly\.com"), "python"),
    ("performance.cdn", SignalKind.PRESENCE, re.compile(r"akamai|Akamai|akamaihd"), "python"),
]

# Streaming: Message Broker
STREAM_MSG_BROKER_PATTERNS: List[tuple] = [
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"kafka|Kafka|KafkaProducer|KafkaConsumer|confluent"), "python"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"rabbitmq|RabbitMQ|pika|amqp\.lib|BlockingConnection"), "python"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"nats|NATS|nats\.py|asyncio_nats"), "python"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"pulsar|Pulsar|pulsar-client"), "python"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"pubsub|PubSub|redis\.pubsub|xadd"), "python"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"boto3.*sqs|SQS|sqs\."), "python"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"azure\.servicebus|ServiceBusClient"), "python"),
]

# Streaming: WebSockets
STREAM_WEBSOCKETS_PATTERNS: List[tuple] = [
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"from\s+websockets|import\s+websockets|serve\("), "python"),
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"socket\.io|socketio|Socket\.IO"), "python"),
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"WebSocket|websocket|fastapi.*websocket"), "python"),
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"new\s+WebSocket|WebSocket\(|import\s+\{\s*WebSocket"), "python"),
]

# Streaming: Event Streaming
STREAM_EVENT_STREAMING_PATTERNS: List[tuple] = [
    ("streaming.event-streaming", SignalKind.PRESENCE, re.compile(r"kafka|Kafka|consumer_group|consumer-group"), "python"),
    ("streaming.event-streaming", SignalKind.PRESENCE, re.compile(r"pulsar|Pulsar"), "python"),
    ("streaming.event-streaming", SignalKind.PRESENCE, re.compile(r"kinesis|Kinesis"), "python"),
    ("streaming.event-streaming", SignalKind.PRESENCE, re.compile(r"consumer.group|consumer_group|ConsumerGroup"), "python"),
]

# Streaming: WebRTC
STREAM_WEBRTC_PATTERNS: List[tuple] = [
    ("streaming.webrtc", SignalKind.PRESENCE, re.compile(r"RTCPeerConnection|webrtc|getUserMedia"), "python"),
    ("streaming.webrtc", SignalKind.PRESENCE, re.compile(r"mediasoup|Mediasoup|createWebRtcTransport"), "python"),
    ("streaming.webrtc", SignalKind.PRESENCE, re.compile(r"livekit|LiveKit"), "python"),
    ("streaming.webrtc", SignalKind.PRESENCE, re.compile(r"janus|Janus|janus-gateway"), "python"),
]

# Streaming: Live Streaming
STREAM_LIVE_STREAMING_PATTERNS: List[tuple] = [
    ("streaming.live-streaming", SignalKind.PRESENCE, re.compile(r"rtmp|RTMP|rtmp://"), "python"),
    ("streaming.live-streaming", SignalKind.PRESENCE, re.compile(r"\.m3u8|HLS|master\.m3u8"), "python"),
    ("streaming.live-streaming", SignalKind.PRESENCE, re.compile(r"dash|DASH|mpd"), "python"),
    ("streaming.live-streaming", SignalKind.PRESENCE, re.compile(r"ffmpeg|transcode|encode|H\.264|H\.265|hevc"), "python"),
    ("streaming.live-streaming", SignalKind.PRESENCE, re.compile(r"ffmpeg|ffprobe"), "python"),
]

# ML: NLP
ML_NLP_PATTERNS: List[tuple] = [
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"transformers|AutoModel|AutoTokenizer|from_pretrained"), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"spacy|spacy\.load|nlp\s*="), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"nltk|from\s+nltk"), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"openai|anthropic|gpt|claude|gemini|llm"), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"bert|BERT|Roberta|DistilBert"), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"embedding|Embedding|sentence.?transformer"), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"langchain|LangChain|from\s+langchain"), "python"),
    ("ml.nlp", SignalKind.PRESENCE, re.compile(r"llama.?index|LlamaIndex|from\s+llama_index"), "python"),
]

# ML: Transformers Architecture
ML_TRANSFORMERS_PATTERNS: List[tuple] = [
    ("ml.transformers", SignalKind.PRESENCE, re.compile(r"class\s+Transformer|Transformer\(|nn\.Transformer"), "python"),
    ("ml.transformers", SignalKind.PRESENCE, re.compile(r"attention|Attention|scaled_dot_product|multi.head"), "python"),
    ("ml.transformers", SignalKind.PRESENCE, re.compile(r"self\.attention|self_attn|self-attention"), "python"),
    ("ml.transformers", SignalKind.PRESENCE, re.compile(r"multi.head|MultiHead|num_heads|n_head"), "python"),
    ("ml.transformers", SignalKind.PRESENCE, re.compile(r"class\s+Encoder|EncoderLayer|nn\.TransformerEncoder"), "python"),
    ("ml.transformers", SignalKind.PRESENCE, re.compile(r"class\s+Decoder|DecoderLayer|nn\.TransformerDecoder"), "python"),
]

# ML: MLOps
ML_MLOPS_PATTERNS: List[tuple] = [
    ("ml.mlops", SignalKind.PRESENCE, re.compile(r"mlops|MLOps|mlflow|kubeflow"), "python"),
    ("ml.mlops", SignalKind.PRESENCE, re.compile(r"train\(|\.fit\(|train_step|training_step"), "python"),
    ("ml.mlops", SignalKind.PRESENCE, re.compile(r"evaluate|\.eval\(|eval_step|metrics\.compute"), "python"),
    ("ml.mlops", SignalKind.PRESENCE, re.compile(r"model.registry|model_registry|register_model"), "python"),
    ("ml.mlops", SignalKind.PRESENCE, re.compile(r"drift|concept.drift|data.drift|evidently"), "python"),
    ("ml.mlops", SignalKind.PRESENCE, re.compile(r"kubeflow|Kubeflow"), "python"),
]

# ML: Model Serving
ML_MODEL_SERVING_PATTERNS: List[tuple] = [
    ("ml.model-serving", SignalKind.PRESENCE, re.compile(r"torchserve|TorchServe"), "python"),
    ("ml.model-serving", SignalKind.PRESENCE, re.compile(r"triton|Triton|tritonserver"), "python"),
    ("ml.model-serving", SignalKind.PRESENCE, re.compile(r"mlflow|MLflow"), "python"),
    ("ml.model-serving", SignalKind.PRESENCE, re.compile(r"bentoml|BentoML"), "python"),
    ("ml.model-serving", SignalKind.PRESENCE, re.compile(r"def\s+predict|\.predict\("), "python"),
]

# ML: Feature Store
ML_FEATURE_STORE_PATTERNS: List[tuple] = [
    ("ml.feature-store", SignalKind.PRESENCE, re.compile(r"feast|Feast|feature_store|FeatureStore"), "python"),
    ("ml.feature-store", SignalKind.PRESENCE, re.compile(r"tecton|Tecton"), "python"),
    ("ml.feature-store", SignalKind.PRESENCE, re.compile(r"feature.store|FeatureView"), "python"),
]

# Networking: Proxy
NET_PROXY_PATTERNS: List[tuple] = [
    ("networking.proxy", SignalKind.PRESENCE, re.compile(r"nginx|Nginx|upstream|proxy_pass"), "python"),
    ("networking.proxy", SignalKind.PRESENCE, re.compile(r"traefik|Traefik"), "python"),
    ("networking.proxy", SignalKind.PRESENCE, re.compile(r"kong|Kong"), "python"),
    ("networking.proxy", SignalKind.PRESENCE, re.compile(r"envoy|Envoy|static_resources"), "python"),
    ("networking.proxy", SignalKind.PRESENCE, re.compile(r"api.gateway|api_gateway|APIGateway"), "python"),
]

# Networking: Load Balancer
NET_LOAD_BALANCER_PATTERNS: List[tuple] = [
    ("networking.load-balancer", SignalKind.PRESENCE, re.compile(r"load.balancer|load_balancer|loadBalancer"), "python"),
    ("networking.load-balancer", SignalKind.PRESENCE, re.compile(r"\blb\b|target_group|targetGroup"), "python"),
    ("networking.load-balancer", SignalKind.PRESENCE, re.compile(r"ALB|elb\.amazonaws"), "python"),
    ("networking.load-balancer", SignalKind.PRESENCE, re.compile(r"ELB|elasticloadbalancing"), "python"),
    ("networking.load-balancer", SignalKind.PRESENCE, re.compile(r"upstream\s+\w+\s*\{|proxy_pass"), "python"),
]

# Networking: Service Mesh
NET_SERVICE_MESH_PATTERNS: List[tuple] = [
    ("networking.service-mesh", SignalKind.PRESENCE, re.compile(r"istio|Istio|VirtualService|DestinationRule"), "python"),
    ("networking.service-mesh", SignalKind.PRESENCE, re.compile(r"linkerd|Linkerd|linkerd2"), "python"),
    ("networking.service-mesh", SignalKind.PRESENCE, re.compile(r"service.mesh|service_mesh|sidecar"), "python"),
]

# Networking: DNS
NET_DNS_PATTERNS: List[tuple] = [
    ("networking.dns", SignalKind.PRESENCE, re.compile(r"dns|DNS|cname"), "python"),
    ("networking.dns", SignalKind.PRESENCE, re.compile(r"consul|Consul"), "python"),
    ("networking.dns", SignalKind.PRESENCE, re.compile(r"core-dns|coredns"), "python"),
    ("networking.dns", SignalKind.PRESENCE, re.compile(r"service.discovery"), "python"),
]

# Compliance: PII
COMPLIANCE_PII_PATTERNS: List[tuple] = [
    ("compliance.pii", SignalKind.PRESENCE, re.compile(r"pii|PII|personally.identifiable"), "python"),
    ("compliance.pii", SignalKind.PRESENCE, re.compile(r"anonymize|anonymise|pseudonymize|mask\("), "python"),
    ("compliance.pii", SignalKind.PRESENCE, re.compile(r"redact|redaction"), "python"),
]

# Security: Secrets Management
SECURITY_SECRETS_MANAGEMENT_PATTERNS: List[tuple] = [
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"vault|hvac|hvac\.Client|HVAC"), "python"),
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"secretsmanager|get_secret_value|aws_secretsmanager"), "python"),
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"azure\.keyvault|SecretClient|SecretStr"), "python"),
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"doppler|sops"), "python"),
]

# Security: HTTPS
SECURITY_HTTPS_PATTERNS: List[tuple] = [
    ("security.https", SignalKind.PRESENCE, re.compile(r"ssl\.create_default_context|SSLContext|HTTPSConnection|https://"), "python"),
    ("security.https", SignalKind.PRESENCE, re.compile(r"ssl_certfile|ssl_keyfile|certfile|keyfile"), "python"),
    ("security.https", SignalKind.PRESENCE, re.compile(r"HTTPSRedirectMiddleware|force_https"), "python"),
]

# Security: Sanitization
SECURITY_SANITIZATION_PATTERNS: List[tuple] = [
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"bleach|bleach\.clean"), "python"),
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"html\.escape|markupsafe|Markup|escape\("), "python"),
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"sanitize|clean_html"), "python"),
]

# Data: Backup
DATA_BACKUP_PATTERNS: List[tuple] = [
    ("data.backup", SignalKind.PRESENCE, re.compile(r"pg_dump|mysqldump|sqlite3.*backup|database_backup"), "python"),
    ("data.backup", SignalKind.PRESENCE, re.compile(r"snapshot|boto3.*create_db_snapshot|BackupManager"), "python"),
]

# Foundation: OpenAPI
FOUNDATION_OPENAPI_PATTERNS: List[tuple] = [
    ("foundation.openapi", SignalKind.PRESENCE, re.compile(r"FastAPI\(|APIRouter\(|openapi_url|swagger_ui"), "python"),
    ("foundation.openapi", SignalKind.PRESENCE, re.compile(r"redoc|swagger|get_openapi"), "python"),
]

# Foundation: Client-Server / HTTP Client & Server
FOUNDATION_CLIENT_SERVER_PATTERNS: List[tuple] = [
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"FastAPI\(|Flask\(|Starlette\(|Django"), "python"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"requests\.(get|post|put|delete|patch)|httpx\.(get|post|put|delete|patch|AsyncClient|Client)|aiohttp\.ClientSession"), "python"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Concept groups for absence checking
# ─────────────────────────────────────────────────────────────────────────────

CONCEPT_GROUPS: list[tuple] = [
    ("foundation.config", FOUNDATION_CONFIG_PATTERNS),
    ("foundation.logging", FOUNDATION_LOGGING_PATTERNS),
    ("foundation.caching", FOUNDATION_CACHING_PATTERNS),
    ("foundation.error-handling", FOUNDATION_ERROR_HANDLING_PATTERNS),
    ("foundation.validation", FOUNDATION_VALIDATION_PATTERNS),
    ("foundation.auth", FOUNDATION_AUTH_PATTERNS),
    ("foundation.authorization", FOUNDATION_AUTHORIZATION_PATTERNS),
    ("foundation.rate-limiting", FOUNDATION_RATE_LIMITING_PATTERNS),
    ("foundation.openapi", FOUNDATION_OPENAPI_PATTERNS),
    ("foundation.client-server", FOUNDATION_CLIENT_SERVER_PATTERNS),
    ("data.orm", DATA_ORM_PATTERNS),
    ("data.migrations", DATA_MIGRATIONS_PATTERNS),
    ("data.indexing", DATA_INDEXING_PATTERNS),
    ("data.backup", DATA_BACKUP_PATTERNS),
    ("security.cors", SECURITY_CORS_PATTERNS),
    ("security.headers", SECURITY_HEADERS_PATTERNS),
    ("security.dependency-scan", SECURITY_DEPENDENCY_SCAN_PATTERNS),
    ("security.secrets-management", SECURITY_SECRETS_MANAGEMENT_PATTERNS),
    ("security.https", SECURITY_HTTPS_PATTERNS),
    ("security.sanitization", SECURITY_SANITIZATION_PATTERNS),
    ("observability.metrics", OBS_METRICS_PATTERNS),
    ("observability.tracing", OBS_TRACING_PATTERNS),
    ("observability.alerting", OBS_ALERTING_PATTERNS),
    ("resilience.circuit-breaker", RES_CIRCUIT_BREAKER_PATTERNS),
    ("resilience.retries", RES_RETRIES_PATTERNS),
    ("resilience.timeouts", RES_TIMEOUTS_PATTERNS),
    ("resilience.dead-letter", RES_DEAD_LETTER_PATTERNS),
    ("deployment.containers", DEPLOY_CONTAINERS_PATTERNS),
    ("deployment.orchestration", DEPLOY_ORCHESTRATION_PATTERNS),
    ("deployment.ci-cd", DEPLOY_CI_CD_PATTERNS),
    ("deployment.iaac", DEPLOY_IAAC_PATTERNS),
    ("deployment.healthchecks", DEPLOY_HEALTHCHECKS_PATTERNS),
    ("performance.connection-pool", PERF_CONNECTION_POOL_PATTERNS),
    ("performance.async", PERF_ASYNC_PATTERNS),
    ("performance.pagination", PERF_PAGINATION_PATTERNS),
    ("performance.cdn", PERF_CDN_PATTERNS),
    ("streaming.message-broker", STREAM_MSG_BROKER_PATTERNS),
    ("streaming.websockets", STREAM_WEBSOCKETS_PATTERNS),
    ("streaming.event-streaming", STREAM_EVENT_STREAMING_PATTERNS),
    ("streaming.webrtc", STREAM_WEBRTC_PATTERNS),
    ("streaming.live-streaming", STREAM_LIVE_STREAMING_PATTERNS),
    ("ml.nlp", ML_NLP_PATTERNS),
    ("ml.transformers", ML_TRANSFORMERS_PATTERNS),
    ("ml.mlops", ML_MLOPS_PATTERNS),
    ("ml.model-serving", ML_MODEL_SERVING_PATTERNS),
    ("ml.feature-store", ML_FEATURE_STORE_PATTERNS),
    ("networking.proxy", NET_PROXY_PATTERNS),
    ("networking.load-balancer", NET_LOAD_BALANCER_PATTERNS),
    ("networking.service-mesh", NET_SERVICE_MESH_PATTERNS),
    ("networking.dns", NET_DNS_PATTERNS),
    ("compliance.pii", COMPLIANCE_PII_PATTERNS),
]

# Misconfiguration patterns (global scan)
MISCONFIG_PATTERNS: List[tuple] = [
    ("foundation.error-handling", SignalKind.WEAKNESS, BARE_EXCEPT_RE, "python"),
    ("foundation.error-handling", SignalKind.WEAKNESS, PRINT_EXCEPTION_RE, "python"),
    ("data.orm", SignalKind.WEAKNESS, RAW_SQL_CONCAT_RE, "python"),
    ("security.cors", SignalKind.WEAKNESS, WILDCARD_CORS_RE, "python"),
    ("security.secrets-management", SignalKind.WEAKNESS, HARDCODED_SECRET_RE, "python"),
    ("resilience.retries", SignalKind.WEAKNESS, FIXED_RETRY_RE, "python"),
    ("foundation.auth", SignalKind.WEAKNESS, PLAINTEXT_PW_RE, "python"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Python file scanner
# ─────────────────────────────────────────────────────────────────────────────

def _scan_python_file(file_path: Path | str) -> List[Signal]:
    """Scan a single Python file and return all signals found."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return []

    signals: List[Signal] = []
    seen_evidence: Set[str] = set()

    # Phase 1: Presence patterns
    for concept_id, patterns in CONCEPT_GROUPS:
        found_any = False
        for cid, kind, regex, lang in patterns:
            for m in regex.finditer(content):
                found_any = True
                evid = f"{cid}:{m.group(0)[:40]}"
                if evid not in seen_evidence:
                    seen_evidence.add(evid)
                    line_start = content[: m.start()].count("\n") + 1
                    line_end = content[: m.end()].count("\n") + 1
                    signals.append(Signal(
                        concept_id=cid,
                        kind=SignalKind.PRESENCE,
                        file_path=path,
                        line_range=(line_start, line_end),
                        evidence=m.group(0)[:300],
                        confidence=0.7,
                        metadata={"language": lang},
                    ))

        # Emit absence signal if no presence found
        if not found_any:
            signals.append(Signal(
                concept_id=concept_id,
                kind=SignalKind.ABSENCE,
                file_path=path,
                line_range=(1, 1),
                evidence="(not found in this file)",
                confidence=0.3,
                metadata={"language": "python"},
            ))

    # Phase 2: Misconfiguration patterns
    for concept_id, kind, regex, lang in MISCONFIG_PATTERNS:
        for m in regex.finditer(content):
            line_start = content[: m.start()].count("\n") + 1
            line_end = content[: m.end()].count("\n") + 1
            signals.append(Signal(
                concept_id=concept_id,
                kind=SignalKind.WEAKNESS,
                file_path=path,
                line_range=(line_start, line_end),
                evidence=f"[WEAKNESS] {m.group(0)[:250]}",
                confidence=0.6,
                metadata={"language": lang, "type": "misconfiguration"},
            ))

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# File discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_python_files(target_root: str | Path, exclude_dirs: Set[str] | None = None) -> List[Path]:
    """Find all Python files under target_root."""
    if exclude_dirs is None:
        exclude_dirs = {"venv", ".venv", "__pycache__", "node_modules", ".git", "dist", "build"}
    root = Path(target_root)
    if not root.exists() or not root.is_dir():
        return []
    return sorted([
        f
        for f in root.rglob("*.py")
        if not any(part in exclude_dirs for part in f.parts)
    ])


def scan_python_project(target_root: str | Path, exclude_dirs: Set[str] | None = None) -> List[FileSignals]:
    """Scan a Python project and return FileSignals for all files."""
    py_files = discover_python_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in py_files:
        sigs = _scan_python_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2.5: AST-based EvidenceFact extraction
# ─────────────────────────────────────────────────────────────────────────────

class PythonASTVisitor(ast.NodeVisitor):
    """Walks Python AST to extract structural, concept-agnostic EvidenceFacts."""

    def __init__(self, file_path: Path, source_lines: List[str]) -> None:
        self.file_path = file_path
        self.source_lines = source_lines
        self.facts: List[EvidenceFact] = []
        self.scope_stack: List[str] = []

    @property
    def current_scope(self) -> str | None:
        return self.scope_stack[-1] if self.scope_stack else None

    def _get_snippet(self, start_line: int, end_line: int) -> str:
        if not self.source_lines:
            return ""
        start_idx = max(0, start_line - 1)
        end_idx = min(len(self.source_lines), end_line)
        lines = self.source_lines[start_idx:end_idx]
        snippet = " ".join(line.strip() for line in lines)
        return snippet[:200]

    def visit_Import(self, node: ast.Import) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        snippet = self._get_snippet(node.lineno, end_lineno)
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            self.facts.append(
                EvidenceFact(
                    kind=EvidenceKind.IMPORT,
                    subject=alias.name,
                    language="python",
                    file_path=self.file_path,
                    line_range=(node.lineno, end_lineno),
                    snippet=snippet,
                    scope=self.current_scope,
                    library=base_mod,
                    extraction_confidence=1.0,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        snippet = self._get_snippet(node.lineno, end_lineno)
        mod = node.module or ""
        base_mod = mod.split(".")[0] if mod else ""
        for alias in node.names:
            full_sub = f"{mod}.{alias.name}" if mod else alias.name
            self.facts.append(
                EvidenceFact(
                    kind=EvidenceKind.IMPORT,
                    subject=full_sub,
                    language="python",
                    file_path=self.file_path,
                    line_range=(node.lineno, end_lineno),
                    snippet=snippet,
                    scope=self.current_scope,
                    library=base_mod,
                    extraction_confidence=1.0,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        snippet = self._get_snippet(node.lineno, min(end_lineno, node.lineno + 1))
        for base in node.bases:
            base_name = ""
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = f"{getattr(base.value, 'id', '')}.{base.attr}"
            if base_name:
                is_schema = any(x in base_name.lower() for x in ("basemodel", "schema", "entity", "model"))
                self.facts.append(
                    EvidenceFact(
                        kind=EvidenceKind.SCHEMA_DEF if is_schema else EvidenceKind.INHERITANCE,
                        subject=node.name,
                        language="python",
                        file_path=self.file_path,
                        line_range=(node.lineno, end_lineno),
                        snippet=snippet,
                        parent_symbol=base_name,
                        scope=self.current_scope,
                        extraction_confidence=1.0,
                    )
                )
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_func(node, is_async=True)

    def _handle_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        snippet = self._get_snippet(node.lineno, min(end_lineno, node.lineno + 1))
        if is_async:
            self.facts.append(
                EvidenceFact(
                    kind=EvidenceKind.ASYNC_PATTERN,
                    subject=node.name,
                    language="python",
                    file_path=self.file_path,
                    line_range=(node.lineno, end_lineno),
                    snippet=snippet,
                    scope=self.current_scope,
                    extraction_confidence=1.0,
                )
            )
        # Decorators
        for dec in node.decorator_list:
            dec_name = ""
            if isinstance(dec, ast.Name):
                dec_name = dec.id
            elif isinstance(dec, ast.Attribute):
                dec_name = f"{getattr(dec.value, 'id', '')}.{dec.attr}"
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    dec_name = dec.func.id
                elif isinstance(dec.func, ast.Attribute):
                    dec_name = f"{getattr(dec.func.value, 'id', '')}.{dec.func.attr}"
            if dec_name:
                self.facts.append(
                    EvidenceFact(
                        kind=EvidenceKind.DECORATOR,
                        subject=dec_name,
                        language="python",
                        file_path=self.file_path,
                        line_range=(dec.lineno, getattr(dec, "end_lineno", dec.lineno)),
                        snippet=self._get_snippet(dec.lineno, getattr(dec, "end_lineno", dec.lineno)),
                        parent_symbol=node.name,
                        scope=self.current_scope,
                        extraction_confidence=1.0,
                    )
                )
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        snippet = self._get_snippet(node.lineno, end_lineno)
        call_target = ""
        sub = ""
        if isinstance(node.func, ast.Name):
            sub = node.func.id
            call_target = node.func.id
        elif isinstance(node.func, ast.Attribute):
            sub = node.func.attr
            val_name = ""
            if isinstance(node.func.value, ast.Name):
                val_name = node.func.value.id
            elif isinstance(node.func.value, ast.Attribute):
                val_name = f"{getattr(node.func.value.value, 'id', '')}.{node.func.value.attr}"
            call_target = f"{val_name}.{sub}" if val_name else sub

        if sub:
            ttl_observed = None
            timeout_observed = None
            retry_count = None
            cb_threshold = None

            for kw in node.keywords:
                if kw.arg in ("ex", "px", "ttl"):
                    ttl_observed = True
                elif kw.arg == "timeout":
                    timeout_observed = True
                elif kw.arg in ("max_retries", "attempts"):
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                        retry_count = kw.value.value
                    else:
                        retry_count = 1
                elif kw.arg in ("failure_threshold", "fail_max"):
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, int):
                        cb_threshold = kw.value.value

            if call_target in ("client.set", "redis.set", "r.set", "cache.set") or (sub == "set" and "client" in call_target):
                if ttl_observed is None:
                    ttl_observed = False

            is_instantiation = sub[0].isupper() if sub else False
            kind = EvidenceKind.INSTANTIATION if is_instantiation else EvidenceKind.CALL

            if sub in ("execute", "select", "filter", "commit", "rollback") or "query" in call_target.lower():
                kind = EvidenceKind.DB_QUERY

            self.facts.append(
                EvidenceFact(
                    kind=kind,
                    subject=sub,
                    language="python",
                    file_path=self.file_path,
                    line_range=(node.lineno, end_lineno),
                    snippet=snippet,
                    call_target=call_target,
                    scope=self.current_scope,
                    ttl_observed=ttl_observed,
                    timeout_observed=timeout_observed,
                    retry_count_observed=retry_count,
                    circuit_breaker_threshold=cb_threshold,
                    extraction_confidence=0.95,
                )
            )
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        end_lineno = getattr(node, "end_lineno", node.lineno)
        snippet = self._get_snippet(node.lineno, min(end_lineno, node.lineno + 2))
        bare_except = any(h.type is None for h in node.handlers)
        hints = ("bare_except",) if bare_except else ()
        self.facts.append(
            EvidenceFact(
                kind=EvidenceKind.CONTROL_FLOW,
                subject="try_except",
                language="python",
                file_path=self.file_path,
                line_range=(node.lineno, end_lineno),
                snippet=snippet,
                scope=self.current_scope,
                identifier_hints=hints,
                extraction_confidence=1.0,
            )
        )
        self.generic_visit(node)


def _scan_python_evidence(path: Path) -> List[EvidenceFact]:
    """Scan a Python file and return native EvidenceFacts."""
    path = Path(path)
    if not path.exists() or not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    source_lines = content.splitlines()
    facts: List[EvidenceFact] = []

    # 1. Structural AST parsing
    try:
        tree = ast.parse(content, filename=str(path))
        visitor = PythonASTVisitor(path, source_lines)
        visitor.visit(tree)
        facts.extend(visitor.facts)
    except SyntaxError:
        pass

    # 2. Bridge positive and weakness pattern signals into facts
    legacy_sigs = _scan_python_file(path)
    for sig in legacy_sigs:
        if sig.kind != SignalKind.ABSENCE:
            fact = SignalBridge.to_evidence_fact(sig)
            # Avoid duplicate if an identical fact exists
            if not any(
                f.file_path == fact.file_path
                and f.line_range == fact.line_range
                and f.subject == fact.subject
                for f in facts
            ):
                facts.append(fact)

    return facts


def scan_python_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan a Python project and return FileEvidence per file."""
    py_files = discover_python_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in py_files:
        facts = _scan_python_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Official PythonScanner conforming to LanguageScanner protocol
# ─────────────────────────────────────────────────────────────────────────────

class PythonScanner:
    """Authoritative Python source code scanner for SDAT.

    Scans Python codebases for system design patterns, presence/absence signals,
    and architectural smells across 40+ concept categories.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "python"
    file_extensions: tuple[str, ...] = (".py",)

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        """Walk root and return discovered Python source files."""
        return discover_python_files(root, exclude_dirs=exclude_dirs)

    # Phase 2.5 Common Evidence Model
    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        """Scan a single Python file and return native EvidenceFacts."""
        return _scan_python_evidence(Path(file_path))

    def extract_evidence(self, files: List[Path]) -> List[EvidenceFact]:
        """Extract concept-agnostic EvidenceFacts from a list of Python files."""
        all_facts: List[EvidenceFact] = []
        for f in files:
            all_facts.extend(self.scan_file_evidence(f))
        return all_facts

    def scan_project_evidence(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileEvidence]:
        """Scan an entire Python project directory and return FileEvidence per file."""
        return scan_python_project_evidence(root, exclude_dirs=exclude_dirs)

    # Legacy Signal Protocol (backward compatibility)
    def scan_file(self, file_path: Path | str) -> List[Signal]:
        """Scan a single Python file and return all detected signals."""
        return _scan_python_file(Path(file_path))

    def extract_signals(self, files: List[Path]) -> List[Signal]:
        """Extract signals from a list of Python files."""
        all_signals: List[Signal] = []
        for f in files:
            all_signals.extend(self.scan_file(f))
        return all_signals

    def scan_project(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileSignals]:
        """Scan an entire Python project directory and return FileSignals per file."""
        return scan_python_project(root, exclude_dirs=exclude_dirs)


