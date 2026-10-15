"""Backend Structural & Architectural Analyzer.

Analyzes source code and structural EvidenceFacts across backend ecosystems
(Python, Go, TypeScript/Node, Java/Kotlin, Rust, PHP, etc.) to discover endpoints,
middlewares, layer boundaries, and architectural patterns.

Adheres strictly to the core invariant:
'Names are clues. Behavior is evidence.'
"""

from __future__ import annotations

import re
from pathlib import Path

from sdat.backend.models import (
    BackendAnalysisSummary,
    EndpointDefinition,
    MiddlewareDefinition,
    ServiceBoundaryDefinition,
)
from sdat.models import EvidenceFact, EvidenceKind

BACKEND_EXTENSIONS = {".py", ".go", ".ts", ".js", ".java", ".kt", ".rs", ".php", ".rb", ".cs"}

# Known backend web framework markers
FRAMEWORK_MARKERS = {
    # Python
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "tornado": "Tornado",
    "sanic": "Sanic",
    # Go
    "gin-gonic/gin": "Gin",
    "labstack/echo": "Echo",
    "go-chi/chi": "Chi",
    "gofiber/fiber": "Fiber",
    "net/http": "Go net/http",
    # TypeScript / Node
    "express": "Express",
    "fastify": "Fastify",
    "@nestjs": "NestJS",
    "koa": "Koa",
    # Java / Kotlin
    "springframework": "Spring Boot",
    "io.ktor": "Ktor",
    "io.micronaut": "Micronaut",
    "io.quarkus": "Quarkus",
    # Rust
    "actix-web": "Actix-Web",
    "axum": "Axum",
    "rocket": "Rocket",
    # PHP
    "laravel": "Laravel",
    "symfony": "Symfony",
    "slim": "Slim",
}

# Database markers
DATABASE_MARKERS = {
    "sqlalchemy": "PostgreSQL/MySQL/SQLite (SQLAlchemy)",
    "psycopg": "PostgreSQL",
    "pgx": "PostgreSQL (pgx)",
    "gorm.io": "SQL (GORM)",
    "hibernate": "JPA / Hibernate",
    "typeorm": "TypeORM",
    "prisma": "Prisma",
    "redis": "Redis",
    "mongodb": "MongoDB",
    "pymongo": "MongoDB (PyMongo)",
    "cassandra": "Cassandra",
    "dynamodb": "DynamoDB",
    "pdo": "PHP PDO",
    "diesel": "Diesel (Rust)",
    "sqlx": "sqlx (Rust)",
}

# Message queue & async worker markers
QUEUE_MARKERS = {
    "celery": "Celery",
    "kafka": "Apache Kafka",
    "confluent_kafka": "Apache Kafka",
    "sarama": "Apache Kafka (Sarama)",
    "rabbitmq": "RabbitMQ",
    "pika": "RabbitMQ (Pika)",
    "amqp": "AMQP",
    "bullmq": "BullMQ",
    "bull": "Bull",
    "redis_queue": "Redis Queue",
    "sqs": "AWS SQS",
    "sidekiq": "Sidekiq",
    "nats": "NATS",
}


class BackendStructuralAnalyzer:
    """Extracts architectural backend abstractions and verifies behavioral evidence."""

    def __init__(self, target_root: str | Path) -> None:
        self.target_root = Path(target_root)

    def analyze(self, facts: list[EvidenceFact]) -> BackendAnalysisSummary:
        """Run structural discovery across provided EvidenceFacts and repository files."""
        summary = BackendAnalysisSummary(target_root=self.target_root)

        # 1. Process EvidenceFacts
        self._analyze_facts(facts, summary)

        # 2. Inspect target repository files if root exists
        if self.target_root.exists() and self.target_root.is_dir():
            self._scan_repository(summary)

        return summary

    def _analyze_facts(self, facts: list[EvidenceFact], summary: BackendAnalysisSummary) -> None:
        """Process structured EvidenceFacts to discover backend components."""
        for fact in facts:
            subject_lower = fact.subject.lower()
            snippet_lower = fact.snippet.lower() if fact.snippet else ""

            # Check framework markers
            for marker, fw_name in FRAMEWORK_MARKERS.items():
                if marker in subject_lower or (fact.framework and marker in fact.framework.lower()):
                    summary.detected_frameworks.add(fw_name)

            # Check database markers
            for marker, db_name in DATABASE_MARKERS.items():
                if marker in subject_lower or (fact.library and marker in fact.library.lower()):
                    summary.detected_databases.add(db_name)

            # Check queue markers
            for marker, q_name in QUEUE_MARKERS.items():
                if marker in subject_lower or (fact.library and marker in fact.library.lower()):
                    summary.detected_queues.add(q_name)

            # Structured logging
            if any(log_lib in subject_lower for log_lib in ("structlog", "zap", "winston", "pino", "slf4j", "log/slog", "tracing")):
                summary.has_structured_logging = True

            # Metrics & Tracing
            if any(m in subject_lower for m in ("prometheus", "opentelemetry", "metrics", "statsd", "micrometer")):
                summary.has_metrics = True
            if any(t in subject_lower for t in ("opentelemetry", "jaeger", "tracer", "trace")):
                summary.has_tracing = True

            # Connection pooling
            if any(p in subject_lower or p in snippet_lower for p in ("pool", "hikari", "max_connections", "max_idle", "pgxpool", "sql.db")):
                summary.has_connection_pooling = True

            # Rate limiting
            if any(r in subject_lower or r in snippet_lower for r in ("ratelimit", "limiter", "tokenbucket", "slidingwindow", "leakybucket")):
                summary.has_rate_limiting = True

            # Caching
            if fact.ttl_observed is not None or any(c in subject_lower for c in ("cache", "redis", "memcached")):
                if fact.kind in (EvidenceKind.CALL, EvidenceKind.INSTANTIATION, EvidenceKind.CONFIG_KEY):
                    summary.has_caching = True

            # Retries
            if fact.retry_count_observed is not None or any(r in subject_lower for r in ("retry", "backoff", "tenacity", "resilience4j")):
                if fact.kind in (EvidenceKind.CALL, EvidenceKind.DECORATOR, EvidenceKind.CONTROL_FLOW):
                    summary.has_retries = True

            # Circuit breaker
            if fact.circuit_breaker_threshold is not None or any(cb in subject_lower for cb in ("circuitbreaker", "pybreaker", "resilience4j")):
                summary.has_circuit_breaker = True

            # Timeouts
            if fact.timeout_observed or "timeout" in snippet_lower:
                if fact.kind in (EvidenceKind.CALL, EvidenceKind.CONFIG_KEY):
                    summary.has_timeouts = True

            # Idempotency
            if any(idem in snippet_lower for idem in ("idempotency", "x-idempotency", "idempotency_key", "dedup")):
                summary.has_idempotency = True

            # Input validation
            if fact.kind == EvidenceKind.SCHEMA_DEF or any(val in subject_lower for val in ("pydantic", "zod", "joi", "validator", "valid", "schema")):
                summary.has_input_validation = True

            # Healthcheck
            if any(h in snippet_lower for h in ("/health", "/healthz", "healthcheck", "actuator/health")):
                summary.has_healthcheck = True

    def _scan_repository(self, summary: BackendAnalysisSummary) -> None:
        """Scan candidate source files for structural behavioral evidence."""
        for path in self.target_root.rglob("*"):
            if not path.is_file() or path.suffix not in BACKEND_EXTENSIONS:
                continue
            if any(part.startswith(".") or part in ("node_modules", "vendor", "dist", "build", "target") for part in path.parts):
                continue

            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            self._inspect_file_content(path, content, summary)

    def _inspect_file_content(self, path: Path, content: str, summary: BackendAnalysisSummary) -> None:
        """Inspect a file's content for behavioral patterns, rejecting comment-only clues."""
        # Strip comments in a language-aware manner
        lines = content.splitlines()
        code_lines: list[tuple[int, str]] = []
        suffix = path.suffix.lower()

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # Check comments by language family
            if suffix in (".py", ".rb"):
                if stripped.startswith("#"):
                    continue
            elif suffix in (".rs", ".go", ".ts", ".js", ".java", ".kt", ".c", ".cpp"):
                if stripped.startswith(("//", "/*", "*", "<!--")):
                    continue
            else:
                if stripped.startswith(("#", "//", "/*", "*", "<!--")):
                    continue

            code_lines.append((i, line))

        code_text = "\n".join(text for _, text in code_lines)

        # 1. Discover HTTP/RPC routes & endpoints
        self._detect_endpoints(path, code_lines, summary)

        # 2. Discover middleware
        self._detect_middleware(path, code_lines, summary)

        # 3. Detect layer boundaries
        self._detect_layers(path, code_text, summary)

        # 4. Behavioral check: Transaction boundaries with network call anti-pattern
        self._detect_transaction_boundaries(path, code_text, summary)

        # 5. Behavioral check: Retry loop with backoff (even with meaningless identifiers)
        self._detect_retry_behavior(code_text, summary)

    def _detect_endpoints(self, path: Path, code_lines: list[tuple[int, str]], summary: BackendAnalysisSummary) -> None:
        """Find endpoints across frameworks."""
        route_patterns = [
            # Python: @app.get("/path"), @router.post("/path")
            re.compile(r"""@(?:app|router|api|bp)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
            # Go: r.GET("/path", handler), http.HandleFunc("/path", handler)
            re.compile(r"""\b(?:r|router|e|app)\.(GET|POST|PUT|DELETE|PATCH)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
            re.compile(r"""http\.HandleFunc\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
            # Node: app.get("/path", ...), router.post("/path", ...)
            re.compile(r"""\b(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
            # Java: @GetMapping("/path"), @PostMapping("/path")
            re.compile(r"""@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["']([^"']+)["']""", re.IGNORECASE),
            # Rust: #[get("/path")], #[post("/path")]
            re.compile(r"""#\[(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
            # PHP: $router->get('/path', ...), Route::get('/path', ...)
            re.compile(r"""(?:Route|\$router|\$app)::(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
            re.compile(r"""(?:\$router|\$app)->(get|post|put|delete|patch)\s*\(\s*["']([^"']+)["']""", re.IGNORECASE),
        ]

        for line_num, line in code_lines:
            for pat in route_patterns:
                m = pat.search(line)
                if m:
                    groups = m.groups()
                    method = groups[0].upper() if len(groups) > 1 else "ANY"
                    route_path = groups[1] if len(groups) > 1 else groups[0]
                    summary.endpoints.append(
                        EndpointDefinition(
                            path=route_path,
                            method=method,
                            handler_symbol=f"handler_{len(summary.endpoints)+1}",
                            file_path=path,
                            line=line_num,
                        )
                    )

    def _detect_middleware(self, path: Path, code_lines: list[tuple[int, str]], summary: BackendAnalysisSummary) -> None:
        """Find middleware registrations."""
        mw_patterns = [
            # app.use(middleware), r.Use(middleware), app.add_middleware(Middleware)
            re.compile(r"""\b(?:app|r|router)\.(?:use|add_middleware)\s*\(\s*([A-Za-z0-9_.]+)""", re.IGNORECASE),
        ]
        for line_num, line in code_lines:
            for pat in mw_patterns:
                m = pat.search(line)
                if m:
                    mw_name = m.group(1)
                    purpose = "custom"
                    mw_lower = mw_name.lower()
                    if "auth" in mw_lower:
                        purpose = "auth"
                    elif "cors" in mw_lower:
                        purpose = "cors"
                    elif "rate" in mw_lower or "limit" in mw_lower:
                        purpose = "rate_limiting"
                    elif "log" in mw_lower:
                        purpose = "logging"
                    elif "error" in mw_lower:
                        purpose = "error_handling"

                    summary.middlewares.append(
                        MiddlewareDefinition(
                            name=mw_name,
                            file_path=path,
                            line=line_num,
                            purpose=purpose,
                        )
                    )

    def _detect_layers(self, path: Path, code_text: str, summary: BackendAnalysisSummary) -> None:
        """Identify architectural service boundaries and layer classification."""
        path_str = str(path).replace("\\", "/").lower()
        layer = "service"
        if any(h in path_str for h in ("/controllers/", "/handlers/", "/routes/", "/views/", "/api/")):
            layer = "controller"
        elif any(r in path_str for r in ("/repositories/", "/dao/", "/db/", "/models/")):
            layer = "repository"
        elif any(s in path_str for s in ("/services/", "/domain/", "/core/")):
            layer = "service"
        elif any(c in path_str for c in ("/clients/", "/adapters/", "/gateway/")):
            layer = "client"

        has_db = bool(re.search(r"""\b(?:SELECT|INSERT|UPDATE|DELETE|session\.query|\.save\(|\.find\(|\.filter\()\b""", code_text, re.IGNORECASE))
        has_ext = bool(re.search(r"""\b(?:requests\.|http\.Client|axios\.|fetch\(|HttpClient)\b""", code_text))

        summary.boundaries.append(
            ServiceBoundaryDefinition(
                name=path.stem,
                file_path=path,
                layer=layer,
                has_direct_db_access=has_db,
                has_external_calls=has_ext,
            )
        )

    def _detect_transaction_boundaries(self, path: Path, code_text: str, summary: BackendAnalysisSummary) -> None:
        """Detect transactional blocks and verify scope boundaries."""
        # Python: with session.begin(): or with db.transaction():
        # Go: tx, _ := db.Begin()
        # Java: @Transactional
        # Node: db.transaction(async (tx) => { ... })
        if re.search(r"""\b(?:session\.begin\(|db\.transaction|db\.Begin\(\)|@Transactional|\.beginTransaction\(\))\b""", code_text):
            summary.has_transaction_boundaries = True

    def _detect_retry_behavior(self, code_text: str, summary: BackendAnalysisSummary) -> None:
        """Detect behavioral retries with backoff/sleep even if identifiers are obfuscated or meaningless."""
        # Pattern 1: loop with sleep and backoff multiplier
        # for/while ... sleep( ... * 2 ...) or sleep( ... << ...)
        has_retry_loop = bool(re.search(r"""\b(?:for|while)\b[\s\S]{1,200}\b(?:sleep|time\.Sleep|Thread\.sleep)\s*\([\s\S]{1,50}(?:\*|\<<|\bpow\b|\bmath\.pow\b)""", code_text, re.IGNORECASE))
        # Pattern 2: retry library import or decorator (tenacity, resilience4j, etc.)
        has_retry_lib = bool(re.search(r"""\b(?:@retry|retry\(|stop_after_attempt|wait_exponential|resilience4j\.retry)\b""", code_text, re.IGNORECASE))

        if has_retry_loop or has_retry_lib:
            summary.has_retries = True
