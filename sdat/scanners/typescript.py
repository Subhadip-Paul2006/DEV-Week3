"""TypeScript / Node.js source file scanner for SDAT.

Reads TypeScript (.ts, .tsx) and JavaScript (.js, .jsx) files and produces
Signal objects for system-design concepts across 35+ concept categories,
including Node.js backend frameworks and React/Next.js frontend heuristics.
"""

from __future__ import annotations

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
CONFIG_PATTERNS: List[tuple] = [
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"from\s+['\"]dotenv['\"]|require\(['\"]dotenv['\"]\)|dotenv\.config"), "typescript"),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"process\.env\.[A-Z0-9_]+|process\.env\[['\"][A-Z0-9_]+['\"]\]"), "typescript"),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"@nestjs/config|ConfigService|ConfigModule"), "typescript"),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"from\s+['\"]config['\"]|require\(['\"]config['\"]\)|convict"), "typescript"),
]

# Foundation: Logging
LOGGING_PATTERNS: List[tuple] = [
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"from\s+['\"]winston['\"]|require\(['\"]winston['\"]\)|winston\.createLogger"), "typescript"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"from\s+['\"]pino['\"]|require\(['\"]pino['\"]\)|pino\("), "typescript"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"from\s+['\"]bunyan['\"]|require\(['\"]bunyan['\"]\)|bunyan\.createLogger"), "typescript"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"from\s+['\"]morgan['\"]|require\(['\"]morgan['\"]\)|morgan\("), "typescript"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"class\s+\w*Logger\w*|implements\s+LoggerService"), "typescript"),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"console\.(info|warn|error|debug)\("), "typescript"),
]

# Foundation: Caching
CACHING_PATTERNS: List[tuple] = [
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"from\s+['\"]ioredis['\"]|require\(['\"]ioredis['\"]\)|new\s+Redis\("), "typescript"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"from\s+['\"]redis['\"]|require\(['\"]redis['\"]\)|createClient\("), "typescript"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"from\s+['\"]node-cache['\"]|from\s+['\"]lru-cache['\"]|new\s+LRUCache"), "typescript"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"from\s+['\"]cache-manager['\"]|CacheModule\.register"), "typescript"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"@tanstack/react-query|from\s+['\"]swr['\"]|useQuery|useSWR|QueryClient"), "typescript"),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"revalidatePath|revalidateTag|unstable_cache|next:\s*\{\s*revalidate"), "typescript"),
]

# Foundation: Error Handling
ERROR_HANDLING_PATTERNS: List[tuple] = [
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"try\s*\{"), "typescript"),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"\((?:err|error),\s*req,\s*res,\s*next\)\s*=>"), "typescript"),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"class\s+\w*Error\s+extends\s+Error|class\s+\w*Exception\s+extends\s+Error"), "typescript") ,
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"@Catch\(|ExceptionFilter|implements\s+ExceptionFilter"), "typescript"),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"from\s+['\"]http-errors['\"]|createError\("), "typescript"),
]

# Foundation: Validation
VALIDATION_PATTERNS: List[tuple] = [
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+['\"]zod['\"]|require\(['\"]zod['\"]\)|z\.object|z\.string"), "typescript"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+['\"]joi['\"]|require\(['\"]joi['\"]\)|Joi\.object"), "typescript"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+['\"]yup['\"]|require\(['\"]yup['\"]\)|yup\.object"), "typescript"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+['\"]class-validator['\"]|@IsString|@IsNotEmpty|@IsEmail|@IsNumber"), "typescript"),
    ("foundation.validation", SignalKind.PRESENCE, re.compile(r"from\s+['\"]class-transformer['\"]|plainToInstance|plainToClass"), "typescript"),
]

# Foundation: Authentication
AUTH_PATTERNS: List[tuple] = [
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"from\s+['\"]jsonwebtoken['\"]|require\(['\"]jsonwebtoken['\"]\)|jwt\.sign|jwt\.verify"), "typescript"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"from\s+['\"]passport['\"]|require\(['\"]passport['\"]\)|passport\.authenticate|passport\.use"), "typescript"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"from\s+['\"]next-auth['\"]|from\s+['\"]@auth/|NextAuth\("), "typescript"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"from\s+['\"]bcrypt['\"]|from\s+['\"]bcryptjs['\"]|bcrypt\.hash|bcrypt\.compare"), "typescript"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"from\s+['\"]argon2['\"]|argon2\.hash|argon2\.verify"), "typescript"),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"from\s+['\"]lucia['\"]|lucia\.createSession"), "typescript"),
]

# Foundation: Authorization
AUTHORIZATION_PATTERNS: List[tuple] = [
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"from\s+['\"]@casl/|AbilityBuilder|createMongoAbility"), "typescript"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"from\s+['\"]accesscontrol['\"]|new\s+AccessControl"), "typescript"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"@Roles\(|@Permissions\(|CanActivate|implements\s+CanActivate"), "typescript"),
    ("foundation.authorization", SignalKind.PRESENCE, re.compile(r"hasRole|checkRole|isAuthorized|checkPermission"), "typescript"),
]

# Foundation: Rate Limiting
RATE_LIMITING_PATTERNS: List[tuple] = [
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"from\s+['\"]express-rate-limit['\"]|rateLimit\("), "typescript"),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"from\s+['\"]rate-limiter-flexible['\"]|RateLimiterRedis|RateLimiterMemory"), "typescript"),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"@nestjs/throttler|ThrottlerModule|ThrottlerGuard"), "typescript"),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"from\s+['\"]express-slow-down['\"]|slowDown\("), "typescript"),
]

# Foundation: Client-Server & Web Frameworks
CLIENT_SERVER_PATTERNS: List[tuple] = [
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"from\s+['\"]express['\"]|require\(['\"]express['\"]\)|express\(\)"), "typescript"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"from\s+['\"]fastify['\"]|require\(['\"]fastify['\"]\)|fastify\(\)"), "typescript"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"@nestjs/common|@Controller\(|NestFactory\.create"), "typescript"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"from\s+['\"]next/server['\"]|NextRequest|NextResponse"), "typescript"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"from\s+['\"]axios['\"]|require\(['\"]axios['\"]\)|axios\.(get|post|put|delete|create)"), "typescript"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"fetch\(['\"`]|from\s+['\"]node-fetch['\"]|from\s+['\"]got['\"]|from\s+['\"]ky['\"]"), "typescript"),
    ("foundation.client-server", SignalKind.PRESENCE, re.compile(r"from\s+['\"]react['\"]|import\s+React|React\.FC|useState|useEffect"), "typescript"),
]

# Foundation: OpenAPI
OPENAPI_PATTERNS: List[tuple] = [
    ("foundation.openapi", SignalKind.PRESENCE, re.compile(r"from\s+['\"]swagger-ui-express['\"]|swaggerUi\.setup"), "typescript"),
    ("foundation.openapi", SignalKind.PRESENCE, re.compile(r"@nestjs/swagger|SwaggerModule|DocumentBuilder|@ApiProperty|@ApiOperation"), "typescript"),
    ("foundation.openapi", SignalKind.PRESENCE, re.compile(r"from\s+['\"]tsoa['\"]|@Route\(|@SuccessResponse"), "typescript"),
    ("foundation.openapi", SignalKind.PRESENCE, re.compile(r"openapi\.json|swagger\.json|openapi:|swagger:"), "typescript"),
]

# Data: ORM & Database Access
DATA_ORM_PATTERNS: List[tuple] = [
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]@prisma/client['\"]|new\s+PrismaClient|prisma\.\w+\.(find|create|update|delete)"), "typescript"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]typeorm['\"]|@Entity\(|@PrimaryGeneratedColumn|new\s+DataSource"), "typescript"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]sequelize['\"]|new\s+Sequelize|sequelize\.define"), "typescript"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]mongoose['\"]|mongoose\.connect|mongoose\.model|new\s+Schema\("), "typescript"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]drizzle-orm['\"]|drizzle\("), "typescript"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]knex['\"]|knex\("), "typescript"),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"from\s+['\"]pg['\"]|new\s+Pool\(|new\s+Client\("), "typescript"),
]

# Data: Migrations
DATA_MIGRATIONS_PATTERNS: List[tuple] = [
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"prisma\s+migrate|prisma\.migrate"), "typescript"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"typeorm\s+migration|MigrationInterface|queryRunner\.(createTable|dropTable)"), "typescript"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"knex\.schema\.createTable|knex\.migrate"), "typescript"),
    ("data.migrations", SignalKind.PRESENCE, re.compile(r"up\s*:\s*async\s*\(queryInterface|down\s*:\s*async\s*\(queryInterface"), "typescript"),
]

# Data: Indexing
DATA_INDEXING_PATTERNS: List[tuple] = [
    ("data.indexing", SignalKind.PRESENCE, re.compile(r"@Index\(|createIndex\(|unique:\s*true|indexes:\s*\["), "typescript"),
    ("data.indexing", SignalKind.PRESENCE, re.compile(r"@@index|@@unique|\.index\("), "typescript"),
]

# Data: Backup
DATA_BACKUP_PATTERNS: List[tuple] = [
    ("data.backup", SignalKind.PRESENCE, re.compile(r"pg_dump|mongodump|mysqldump|createDBSnapshot"), "typescript"),
]

# Security: CORS
SECURITY_CORS_PATTERNS: List[tuple] = [
    ("security.cors", SignalKind.PRESENCE, re.compile(r"from\s+['\"]cors['\"]|require\(['\"]cors['\"]\)|app\.use\(cors|fastify\.register\(cors"), "typescript"),
    ("security.cors", SignalKind.PRESENCE, re.compile(r"Access-Control-Allow-Origin"), "typescript"),
]

# Security: Security Headers
SECURITY_HEADERS_PATTERNS: List[tuple] = [
    ("security.headers", SignalKind.PRESENCE, re.compile(r"from\s+['\"]helmet['\"]|require\(['\"]helmet['\"]\)|app\.use\(helmet"), "typescript"),
    ("security.headers", SignalKind.PRESENCE, re.compile(r"Content-Security-Policy|Strict-Transport-Security|X-Frame-Options"), "typescript"),
]

# Security: Dependency Scan
SECURITY_DEPENDENCY_SCAN_PATTERNS: List[tuple] = [
    ("security.dependency-scan", SignalKind.PRESENCE, re.compile(r"audit-ci|npm\s+audit|snyk|trivy"), "typescript"),
]

# Security: Secrets Management
SECURITY_SECRETS_MANAGEMENT_PATTERNS: List[tuple] = [
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"@aws-sdk/client-secrets-manager|SecretsManagerClient|GetSecretValueCommand"), "typescript"),
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"node-vault|from\s+['\"]vault['\"]|@azure/keyvault-secrets|SecretClient"), "typescript"),
    ("security.secrets-management", SignalKind.PRESENCE, re.compile(r"doppler|sops"), "typescript"),
]

# Security: HTTPS
SECURITY_HTTPS_PATTERNS: List[tuple] = [
    ("security.https", SignalKind.PRESENCE, re.compile(r"https\.createServer|key:\s*fs\.readFileSync|cert:\s*fs\.readFileSync"), "typescript"),
    ("security.https", SignalKind.PRESENCE, re.compile(r"https://|forceHTTPS|requireSSL"), "typescript"),
]

# Security: Input Sanitization
SECURITY_SANITIZATION_PATTERNS: List[tuple] = [
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"from\s+['\"]dompurify['\"]|DOMPurify\.sanitize"), "typescript"),
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"from\s+['\"]sanitize-html['\"]|sanitizeHtml\("), "typescript"),
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"from\s+['\"]xss['\"]|xss\("), "typescript"),
    ("security.sanitization", SignalKind.PRESENCE, re.compile(r"validator\.escape|escapeHtml"), "typescript"),
]

# Observability: Metrics
OBS_METRICS_PATTERNS: List[tuple] = [
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"from\s+['\"]prom-client['\"]|require\(['\"]prom-client['\"]\)|new\s+(Counter|Histogram|Gauge|Summary)\("), "typescript"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"from\s+['\"]hot-shots['\"]|new\s+StatsD"), "typescript"),
    ("observability.metrics", SignalKind.PRESENCE, re.compile(r"@opentelemetry/metrics|meterProvider"), "typescript"),
]

# Observability: Tracing
OBS_TRACING_PATTERNS: List[tuple] = [
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"@opentelemetry/api|trace\.getTracer|NodeTracerProvider|SimpleSpanProcessor|BatchSpanProcessor"), "typescript"),
    ("observability.tracing", SignalKind.PRESENCE, re.compile(r"from\s+['\"]jaeger-client['\"]|initTracer"), "typescript"),
]

# Observability: Alerting
OBS_ALERTING_PATTERNS: List[tuple] = [
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"@sentry/node|@sentry/react|@sentry/nextjs|Sentry\.init|Sentry\.captureException"), "typescript"),
    ("observability.alerting", SignalKind.PRESENCE, re.compile(r"@pagerduty/pdjs|opsgenie"), "typescript"),
]

# Resilience: Circuit Breaker
RES_CIRCUIT_BREAKER_PATTERNS: List[tuple] = [
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"from\s+['\"]opossum['\"]|new\s+CircuitBreaker|new\s+Opossum"), "typescript"),
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"from\s+['\"]brakes['\"]|new\s+Brakes"), "typescript"),
    ("resilience.circuit-breaker", SignalKind.PRESENCE, re.compile(r"cockatiel|circuitBreaker"), "typescript"),
]

# Resilience: Retries
RES_RETRIES_PATTERNS: List[tuple] = [
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"from\s+['\"]async-retry['\"]|retry\("), "typescript"),
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"from\s+['\"]p-retry['\"]|pRetry\("), "typescript"),
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"from\s+['\"]axios-retry['\"]|axiosRetry\("), "typescript"),
    ("resilience.retries", SignalKind.PRESENCE, re.compile(r"backoff|exponentialBackoff"), "typescript"),
]

# Resilience: Timeouts
RES_TIMEOUTS_PATTERNS: List[tuple] = [
    ("resilience.timeouts", SignalKind.PRESENCE, re.compile(r"timeout:\s*\d+|timeout\s*=|timeout\("), "typescript"),
    ("resilience.timeouts", SignalKind.PRESENCE, re.compile(r"AbortController|AbortSignal\.timeout"), "typescript"),
]

# Resilience: Dead Letter Queue
RES_DEAD_LETTER_PATTERNS: List[tuple] = [
    ("resilience.dead-letter", SignalKind.PRESENCE, re.compile(r"deadLetter|dead_letter|dlq|DLQ|DeadLetterTargetArn"), "typescript"),
]

# Deployment: Health Checks
DEPLOY_HEALTHCHECKS_PATTERNS: List[tuple] = [
    ("deployment.healthchecks", SignalKind.PRESENCE, re.compile(r"['\"]/health['\"]|['\"]/healthz['\"]|['\"]/ready['\"]|['\"]/live['\"]"), "typescript"),
    ("deployment.healthchecks", SignalKind.PRESENCE, re.compile(r"@nestjs/terminus|HealthCheckService|TerminusModule"), "typescript"),
]

# Performance: Connection Pooling
PERF_CONNECTION_POOL_PATTERNS: List[tuple] = [
    ("performance.connection-pool", SignalKind.PRESENCE, re.compile(r"new\s+Pool\(|poolSize|connectionLimit|max:\s*\d+,\s*min:\s*\d+"), "typescript"),
    ("performance.connection-pool", SignalKind.PRESENCE, re.compile(r"generic-pool|createPool"), "typescript"),
]

# Performance: Async & Non-blocking I/O
PERF_ASYNC_PATTERNS: List[tuple] = [
    ("performance.async", SignalKind.PRESENCE, re.compile(r"async\s+(?:function|\([^)]*\)|[a-zA-Z0-9_]+\s*\()"), "typescript"),
    ("performance.async", SignalKind.PRESENCE, re.compile(r"\bawait\b|Promise\.all|Promise\.allSettled|new\s+Promise"), "typescript"),
    ("performance.async", SignalKind.PRESENCE, re.compile(r"from\s+['\"]cluster['\"]|cluster\.fork"), "typescript"),
]

# Performance: Pagination
PERF_PAGINATION_PATTERNS: List[tuple] = [
    ("performance.pagination", SignalKind.PRESENCE, re.compile(r"(?:limit|offset|take|skip|cursor)\s*[:=]|\.limit\(|\.offset\("), "typescript"),
    ("performance.pagination", SignalKind.PRESENCE, re.compile(r"paginate|pageSize|pageIndex|pageNumber|page_size|\.page\b|query\.page|query\.limit"), "typescript"),
]

# Streaming: Message Broker
STREAM_MSG_BROKER_PATTERNS: List[tuple] = [
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"from\s+['\"]kafkajs['\"]|new\s+Kafka|KafkaProducer|KafkaConsumer"), "typescript"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"from\s+['\"]amqplib['\"]|amqp\.connect"), "typescript"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"from\s+['\"]bull['\"]|from\s+['\"]bullmq['\"]|new\s+Queue\("), "typescript"),
    ("streaming.message-broker", SignalKind.PRESENCE, re.compile(r"from\s+['\"]nats['\"]|connect\(.*servers"), "typescript"),
]

# Streaming: WebSockets
STREAM_WEBSOCKETS_PATTERNS: List[tuple] = [
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"from\s+['\"]ws['\"]|new\s+WebSocket|new\s+WebSocketServer"), "typescript"),
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"from\s+['\"]socket\.io['\"]|new\s+Server\(.*ws|io\.on\(['\"]connection"), "typescript"),
    ("streaming.websockets", SignalKind.PRESENCE, re.compile(r"@WebSocketGateway|@SubscribeMessage"), "typescript"),
]

# UX: Accessibility (a11y)
UX_ACCESSIBILITY_PATTERNS: List[tuple] = [
    ("ux.accessibility", SignalKind.PRESENCE, re.compile(r"aria-label|aria-hidden|aria-describedby|role=['\"][a-zA-Z]+['\"]"), "typescript"),
    ("ux.accessibility", SignalKind.PRESENCE, re.compile(r"alt=['\"][^'\"]*['\"]"), "typescript"),
]

# Integration: GraphQL
INTEG_GRAPHQL_PATTERNS: List[tuple] = [
    ("integration.graphql", SignalKind.PRESENCE, re.compile(r"from\s+['\"]@apollo/server['\"]|from\s+['\"]graphql['\"]|ApolloServer|buildSchema"), "typescript"),
    ("integration.graphql", SignalKind.PRESENCE, re.compile(r"@Resolver|@Query|@Mutation|GraphQLModule"), "typescript"),
]

# Integration: Webhooks
INTEG_WEBHOOKS_PATTERNS: List[tuple] = [
    ("integration.webhooks", SignalKind.PRESENCE, re.compile(r"webhook|verifyWebhookSignature|stripe\.webhooks\.constructEvent"), "typescript"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Concept groups for absence checking
# ─────────────────────────────────────────────────────────────────────────────

CONCEPT_GROUPS: list[tuple] = [
    ("foundation.config", CONFIG_PATTERNS),
    ("foundation.logging", LOGGING_PATTERNS),
    ("foundation.caching", CACHING_PATTERNS),
    ("foundation.error-handling", ERROR_HANDLING_PATTERNS),
    ("foundation.validation", VALIDATION_PATTERNS),
    ("foundation.auth", AUTH_PATTERNS),
    ("foundation.authorization", AUTHORIZATION_PATTERNS),
    ("foundation.rate-limiting", RATE_LIMITING_PATTERNS),
    ("foundation.client-server", CLIENT_SERVER_PATTERNS),
    ("foundation.openapi", OPENAPI_PATTERNS),
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
    ("deployment.healthchecks", DEPLOY_HEALTHCHECKS_PATTERNS),
    ("performance.connection-pool", PERF_CONNECTION_POOL_PATTERNS),
    ("performance.async", PERF_ASYNC_PATTERNS),
    ("performance.pagination", PERF_PAGINATION_PATTERNS),
    ("streaming.message-broker", STREAM_MSG_BROKER_PATTERNS),
    ("streaming.websockets", STREAM_WEBSOCKETS_PATTERNS),
    ("ux.accessibility", UX_ACCESSIBILITY_PATTERNS),
    ("integration.graphql", INTEG_GRAPHQL_PATTERNS),
    ("integration.webhooks", INTEG_WEBHOOKS_PATTERNS),
]

# Misconfiguration patterns
EMPTY_CATCH_RE = re.compile(r"catch\s*(?:\([^)]*\))?\s*\{\s*\}")
WILDCARD_CORS_RE = re.compile(r"origin\s*:\s*['\"]\*['\"]|Access-Control-Allow-Origin.*\*")
HARDCODED_SECRET_RE = re.compile(
    r"(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
    re.IGNORECASE,
)
PLAINTEXT_PW_RE = re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE)

MISCONFIG_PATTERNS: List[tuple] = [
    ("foundation.error-handling", SignalKind.WEAKNESS, EMPTY_CATCH_RE, "typescript"),
    ("security.cors", SignalKind.WEAKNESS, WILDCARD_CORS_RE, "typescript"),
    ("security.secrets-management", SignalKind.WEAKNESS, HARDCODED_SECRET_RE, "typescript"),
    ("foundation.auth", SignalKind.WEAKNESS, PLAINTEXT_PW_RE, "typescript"),
]


# ─────────────────────────────────────────────────────────────────────────────
# TypeScript / JavaScript file scanner
# ─────────────────────────────────────────────────────────────────────────────

def _scan_typescript_file(file_path: Path | str) -> List[Signal]:
    """Scan a single TypeScript or JavaScript file and return all signals found."""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return []

    signals: List[Signal] = []
    seen_evidence: Set[str] = set()

    # Detect framework markers for metadata
    framework = "nodejs"
    if "from \"next" in content or "from 'next" in content or "NextRequest" in content:
        framework = "nextjs"
    elif "from \"react\"" in content or "from 'react'" in content or "React." in content:
        framework = "react"

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
                        confidence=0.75,
                        metadata={"language": lang, "framework": framework},
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
                metadata={"language": "typescript"},
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
                confidence=0.65,
                metadata={"language": lang, "type": "misconfiguration"},
            ))

    return signals


# ─────────────────────────────────────────────────────────────────────────────
# File discovery
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx"}
DEFAULT_EXCLUDE_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    ".next",
    "out",
    "coverage",
    ".turbo",
    ".cache",
    ".nuxt",
    ".output",
    "vendor",
}


def discover_typescript_files(target_root: str | Path, exclude_dirs: Set[str] | None = None) -> List[Path]:
    """Find all TypeScript and JavaScript files under target_root."""
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS
    root = Path(target_root)
    if not root.exists() or not root.is_dir():
        return []

    found: List[Path] = []
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
            if not any(part in exclude_dirs for part in f.parts):
                found.append(f)
    return sorted(found)


def scan_typescript_project(target_root: str | Path, exclude_dirs: Set[str] | None = None) -> List[FileSignals]:
    """Scan a TypeScript/JavaScript project and return FileSignals per file."""
    ts_files = discover_typescript_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in ts_files:
        sigs = _scan_typescript_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2.5: Structural EvidenceFact extraction for TypeScript / JavaScript
# ─────────────────────────────────────────────────────────────────────────────

TS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:(?:\*\s+as\s+\w+)|(?:\{[^}]+\})|(?:\w+))?\s*from\s*['\"]([^'\"]+)['\"])|(?:require\(['\"]([^'\"]+)['\"]\))"
)
TS_NEW_RE = re.compile(r"new\s+([A-Z]\w*(?:\.[A-Z]\w*)*)\s*\(([^)]*)\)")
TS_DECORATOR_RE = re.compile(r"@(\w+)(?:\(([^)]*)\))?")
TS_CLASS_EXTENDS_RE = re.compile(r"class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w\s,]+))?")
TS_ENV_RE = re.compile(r"process\.env(?:\.([A-Z0-9_]+)|\[['\"]([A-Z0-9_]+)['\"]\])")
TS_ASYNC_RE = re.compile(r"async\s+(?:function\s+(\w+)|\(?(\w*)\)?\s*=>)")
TS_HTTP_CALL_RE = re.compile(r"(?:fetch|axios\.(?:get|post|put|delete|patch|request)|http\.request)\s*\(([^)]*)\)")


def _scan_typescript_evidence(path: Path) -> List[EvidenceFact]:
    """Scan a TypeScript or JavaScript file and return native EvidenceFacts."""
    path = Path(path)
    if not path.exists() or not path.is_file():
        return []

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    facts: List[EvidenceFact] = []
    lang = "typescript" if path.suffix.lower() in (".ts", ".tsx") else "javascript"

    def get_lines(start_idx: int, end_idx: int) -> tuple[int, int]:
        l_start = content[:start_idx].count("\n") + 1
        l_end = content[:end_idx].count("\n") + 1
        return l_start, l_end

    # 1. Imports
    for m in TS_IMPORT_RE.finditer(content):
        mod = m.group(1) or m.group(2) or ""
        if mod:
            lr = get_lines(m.start(), m.end())
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.IMPORT,
                    subject=mod,
                    language=lang,
                    file_path=path,
                    line_range=lr,
                    snippet=m.group(0)[:200],
                    library=mod.split("/")[0] if not mod.startswith(".") else None,
                    extraction_confidence=1.0,
                )
            )

    # 2. Instantiations
    for m in TS_NEW_RE.finditer(content):
        cls_name = m.group(1)
        args_str = m.group(2)
        lr = get_lines(m.start(), m.end())
        ttl_obs = None
        if "redis" in cls_name.lower() or "cache" in cls_name.lower():
            if "ttl" in args_str.lower() or "maxAge" in args_str:
                ttl_obs = True

        facts.append(
            EvidenceFact(
                kind=EvidenceKind.INSTANTIATION,
                subject=cls_name,
                language=lang,
                file_path=path,
                line_range=lr,
                snippet=m.group(0)[:200],
                call_target=cls_name,
                call_args_schema=args_str[:100] if args_str else None,
                ttl_observed=ttl_obs,
                extraction_confidence=0.95,
            )
        )

    # 3. Decorators
    for m in TS_DECORATOR_RE.finditer(content):
        dec_name = m.group(1)
        lr = get_lines(m.start(), m.end())
        facts.append(
            EvidenceFact(
                kind=EvidenceKind.DECORATOR,
                subject=dec_name,
                language=lang,
                file_path=path,
                line_range=lr,
                snippet=m.group(0)[:200],
                extraction_confidence=1.0,
            )
        )

    # 4. Class inheritance
    for m in TS_CLASS_EXTENDS_RE.finditer(content):
        cls_name = m.group(1)
        base_name = m.group(2) or (m.group(3).strip() if m.group(3) else None)
        if base_name:
            lr = get_lines(m.start(), m.end())
            is_schema = any(x in base_name.lower() for x in ("entity", "schema", "model"))
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.SCHEMA_DEF if is_schema else EvidenceKind.INHERITANCE,
                    subject=cls_name,
                    language=lang,
                    file_path=path,
                    line_range=lr,
                    snippet=m.group(0)[:200],
                    parent_symbol=base_name,
                    extraction_confidence=1.0,
                )
            )

    # 5. Environment Variables
    for m in TS_ENV_RE.finditer(content):
        var_name = m.group(1) or m.group(2) or ""
        lr = get_lines(m.start(), m.end())
        facts.append(
            EvidenceFact(
                kind=EvidenceKind.ENV_VAR,
                subject=var_name,
                language=lang,
                file_path=path,
                line_range=lr,
                snippet=m.group(0)[:200],
                value_observed=None,
                extraction_confidence=1.0,
            )
        )

    # 6. Async Functions
    for m in TS_ASYNC_RE.finditer(content):
        fn_name = m.group(1) or m.group(2) or "anonymous"
        lr = get_lines(m.start(), m.end())
        facts.append(
            EvidenceFact(
                kind=EvidenceKind.ASYNC_PATTERN,
                subject=fn_name,
                language=lang,
                file_path=path,
                line_range=lr,
                snippet=m.group(0)[:200],
                extraction_confidence=1.0,
            )
        )

    # 7. External HTTP Calls
    for m in TS_HTTP_CALL_RE.finditer(content):
        args = m.group(1) or ""
        lr = get_lines(m.start(), m.end())
        timeout_obs = bool("timeout" in args.lower() or "signal" in args.lower())
        facts.append(
            EvidenceFact(
                kind=EvidenceKind.CALL,
                subject=m.group(0).split("(")[0].strip(),
                language=lang,
                file_path=path,
                line_range=lr,
                snippet=m.group(0)[:200],
                call_args_schema=args[:100] if args else None,
                timeout_observed=timeout_obs,
                extraction_confidence=0.95,
            )
        )

    # 8. Bridge presence and weakness pattern signals into facts
    legacy_sigs = _scan_typescript_file(path)
    for sig in legacy_sigs:
        if sig.kind != SignalKind.ABSENCE:
            fact = SignalBridge.to_evidence_fact(sig)
            if not any(
                f.file_path == fact.file_path
                and f.line_range == fact.line_range
                and f.subject == fact.subject
                for f in facts
            ):
                facts.append(fact)

    return facts


def scan_typescript_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan a TypeScript/JavaScript project and return FileEvidence per file."""
    ts_files = discover_typescript_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in ts_files:
        facts = _scan_typescript_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Official TypeScriptScanner conforming to LanguageScanner protocol
# ─────────────────────────────────────────────────────────────────────────────

class TypeScriptScanner:
    """Authoritative TypeScript / Node.js source code scanner for SDAT.

    Scans TypeScript and JavaScript codebases for system design patterns,
    presence/absence signals, and architectural smells across 35+ concept categories.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "typescript"
    file_extensions: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx")

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        """Walk root and return discovered TypeScript and JavaScript source files."""
        return discover_typescript_files(root, exclude_dirs=exclude_dirs)

    # Phase 2.5 Common Evidence Model
    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        """Scan a single TypeScript or JavaScript file and return native EvidenceFacts."""
        return _scan_typescript_evidence(Path(file_path))

    def extract_evidence(self, files: List[Path]) -> List[EvidenceFact]:
        """Extract concept-agnostic EvidenceFacts from a list of TypeScript/JavaScript files."""
        all_facts: List[EvidenceFact] = []
        for f in files:
            all_facts.extend(self.scan_file_evidence(f))
        return all_facts

    def scan_project_evidence(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileEvidence]:
        """Scan an entire project directory and return FileEvidence per file."""
        return scan_typescript_project_evidence(root, exclude_dirs=exclude_dirs)

    # Legacy Signal Protocol (backward compatibility)
    def scan_file(self, file_path: Path | str) -> List[Signal]:
        """Scan a single TypeScript or JavaScript file and return all detected signals."""
        return _scan_typescript_file(Path(file_path))

    def extract_signals(self, files: List[Path]) -> List[Signal]:
        """Extract signals from a list of TypeScript and JavaScript files."""
        all_signals: List[Signal] = []
        for f in files:
            all_signals.extend(self.scan_file(f))
        return all_signals

    def scan_project(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileSignals]:
        """Scan an entire project directory and return FileSignals per file."""
        return scan_typescript_project(root, exclude_dirs=exclude_dirs)

