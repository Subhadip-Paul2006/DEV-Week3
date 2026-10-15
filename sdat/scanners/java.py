"""Java and Kotlin source code scanner for SDAT — conforms to LanguageScanner protocol.

Scans Java (.java) and Kotlin (.kt) files for Spring Boot, Resilience4j,
HikariCP connection pooling, Kafka/RabbitMQ messaging, Micrometer, and Coroutines.
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
    SignalKind,
)

DEFAULT_EXCLUDE_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "target",
    ".gradle",
    "__pycache__",
    "vendor",
    ".sdat-cache",
    ".idea",
    ".vscode",
    "bin",
    "obj",
}

JAVA_PATTERNS: List[tuple[str, SignalKind, re.Pattern, str, EvidenceKind]] = [
    # Spring Web & REST
    ("api.rest", SignalKind.PRESENCE, re.compile(r"@RestController|@Controller"), "java", EvidenceKind.ANNOTATION),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"@GetMapping|@PostMapping|@PutMapping|@DeleteMapping|@PatchMapping|@RequestMapping"), "java", EvidenceKind.ANNOTATION),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"@SpringBootApplication"), "java", EvidenceKind.FRAMEWORK_MARKER),

    # Circuit Breaker & Resilience4j
    ("foundation.circuit-breaker", SignalKind.PRESENCE, re.compile(r"@CircuitBreaker\b|CircuitBreakerRegistry|CircuitBreakerConfig"), "java", EvidenceKind.ANNOTATION),
    ("foundation.circuit-breaker", SignalKind.PRESENCE, re.compile(r"io\.github\.resilience4j:resilience4j-circuitbreaker|import\s+io\.github\.resilience4j\.circuitbreaker"), "java", EvidenceKind.IMPORT),

    # Retries & Backoff
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"@Retryable\b|@Retry\b|RetryTemplate|RetryRegistry"), "java", EvidenceKind.ANNOTATION),
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"@Recover\b|backoff\s*=\s*@Backoff"), "java", EvidenceKind.ANNOTATION),
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"import\s+org\.springframework\.retry|import\s+io\.github\.resilience4j\.retry"), "java", EvidenceKind.IMPORT),

    # Database, ORM & Connection Pooling
    ("data.orm", SignalKind.PRESENCE, re.compile(r"@Entity\b|@Table\b|extends\s+(?:JpaRepository|CrudRepository)"), "java", EvidenceKind.ANNOTATION),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"@Transactional\b"), "java", EvidenceKind.ANNOTATION),
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"HikariDataSource|HikariConfig|com\.zaxxer\.hikari"), "java", EvidenceKind.INSTANTIATION),
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"maximumPoolSize|minimumIdle|connectionTimeout"), "java", EvidenceKind.CONFIG_KEY),

    # Caching
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"@Cacheable\b|@CachePut\b|@CacheEvict\b|CacheManager"), "java", EvidenceKind.ANNOTATION),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"RedisTemplate|StringRedisTemplate|RedissonClient"), "java", EvidenceKind.INSTANTIATION),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"import\s+org\.springframework\.data\.redis|import\s+org\.redisson"), "java", EvidenceKind.IMPORT),

    # Message Queues (Kafka & RabbitMQ)
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"@KafkaListener\b|KafkaTemplate|@RabbitListener\b|RabbitTemplate"), "java", EvidenceKind.ANNOTATION),
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"import\s+org\.springframework\.kafka|import\s+org\.springframework\.amqp"), "java", EvidenceKind.IMPORT),

    # Rate Limiting
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"@RateLimiter\b|RateLimiterRegistry|Bucket4j|Bandwidth"), "java", EvidenceKind.ANNOTATION),

    # Observability & Metrics
    ("foundation.observability", SignalKind.PRESENCE, re.compile(r"MeterRegistry|io\.micrometer|prometheus"), "java", EvidenceKind.INSTANTIATION),
    ("foundation.health-checks", SignalKind.PRESENCE, re.compile(r"/actuator/health|HealthIndicator|@Endpoint"), "java", EvidenceKind.ANNOTATION),

    # Logging
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"LoggerFactory\.getLogger|@Slf4j|org\.slf4j\.Logger"), "java", EvidenceKind.INSTANTIATION),

    # Concurrency & Async
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"@Async\b|CompletableFuture|ExecutorService|ThreadPoolTaskExecutor"), "java", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"suspend\s+fun\b|CoroutineScope|Dispatchers\.IO|withContext"), "java", EvidenceKind.ASYNC_PATTERN),

    # Auth & Security
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"@EnableWebSecurity|SecurityFilterChain|@PreAuthorize|PasswordEncoder"), "java", EvidenceKind.ANNOTATION),

    # CLI & Tooling
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"picocli\.CommandLine|@Command\b|CommandLine\.call|CommandLine\.run"), "java", EvidenceKind.CALL),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"org\.apache\.commons\.cli|Options\(\)|CommandLineParser"), "java", EvidenceKind.INSTANTIATION),

    # Raw Networking & Sockets
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"new\s+ServerSocket\(|new\s+Socket\(|SocketChannel\.open|ServerSocketChannel\.open"), "java", EvidenceKind.CALL),
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"io\.netty\.bootstrap\.(?:ServerBootstrap|Bootstrap)"), "java", EvidenceKind.INSTANTIATION),

    # Android / Mobile Client
    ("client.android", SignalKind.PRESENCE, re.compile(r"extends\s+(?:Activity|AppCompatActivity)\b|import\s+android\.(?:app\.Activity|os\.Bundle)"), "java", EvidenceKind.INHERITANCE),

    # Web3 & Blockchain Integration
    ("web3.client", SignalKind.PRESENCE, re.compile(r"import\s+org\.web3j\.|org\.web3j\.protocol\.Web3j"), "java", EvidenceKind.IMPORT),
    ("web3.rpc", SignalKind.PRESENCE, re.compile(r"Web3j\.build\(|HttpService\(|WebSocketService\("), "java", EvidenceKind.CALL),
    ("web3.contract", SignalKind.PRESENCE, re.compile(r"Contract\.deploy\(|Contract\.load\(|RemoteCall<"), "java", EvidenceKind.CALL),
    ("web3.transaction", SignalKind.PRESENCE, re.compile(r"TransactionManager|RawTransaction|FastRawTransactionManager"), "java", EvidenceKind.INSTANTIATION),
    ("web3.transaction", SignalKind.PRESENCE, re.compile(r"sendFunds\(|sendTransaction\(|ethSendRawTransaction\("), "java", EvidenceKind.CALL),
    ("web3.transaction", SignalKind.PRESENCE, re.compile(r"ethGetTransactionReceipt\(|waitForTransactionReceipt\("), "java", EvidenceKind.CALL),
    ("web3.event", SignalKind.PRESENCE, re.compile(r"ethLogFlowable\(|replayPastAndFutureEventsFlowable\("), "java", EvidenceKind.CALL),
    ("web3.transaction", SignalKind.PRESENCE, re.compile(r"getNonce\("), "java", EvidenceKind.CALL),
]

JAVA_SECRET_RE = re.compile(
    r"""(?:String|val|var)\s+(?:apiKey|api_key|secret|password|token)\s*=\s*["'][A-Za-z0-9_\-+/]{12,}["']""",
    re.IGNORECASE,
)


def discover_java_files(
    root: Path | str,
    exclude_dirs: Set[str] | None = None,
) -> List[Path]:
    """Discover all Java (*.java) and Kotlin (*.kt) files under root."""
    base = Path(root)
    if not base.exists() or not base.is_dir():
        return []

    effective_excludes = DEFAULT_EXCLUDE_DIRS | (exclude_dirs or set())
    discovered: List[Path] = []
    extensions = {".java", ".kt"}

    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            parts = set(path.parts)
            if not (parts & effective_excludes):
                discovered.append(path)

    return sorted(discovered)


def _extract_java_scope(lines: list[str], line_idx: int) -> str | None:
    """Find enclosing class, method, or function."""
    cls_re = re.compile(r"^(?:public|protected|private|abstract|final|\s)*class\s+([A-Za-z_]\w*)")
    fn_re = re.compile(r"^(?:public|protected|private|static|final|\s)*(?:fun|[A-Za-z_][\w<>[\],\s]*)\s+([A-Za-z_]\w*)\s*\([^)]*\)")
    for idx in range(line_idx, -1, -1):
        line = lines[idx].strip()
        m_cls = cls_re.match(line)
        if m_cls:
            return f"class {m_cls.group(1)}"
        m_fn = fn_re.match(line)
        if m_fn and not line.startswith("return") and not line.startswith("if"):
            return m_fn.group(1)
    return None


def _scan_java_file(file_path: Path) -> List[Signal]:
    """Scan a Java/Kotlin file and return detected Signal objects (legacy compatibility)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    signals: List[Signal] = []

    for concept_id, kind, pattern, lang, _ev_kind in JAVA_PATTERNS:
        for idx, line in enumerate(lines, start=1):
            if pattern.search(line):
                signals.append(
                    Signal(
                        concept_id=concept_id,
                        kind=kind,
                        file_path=file_path,
                        line_range=(idx, idx),
                        evidence=line.strip()[:200],
                        confidence=0.95,
                        metadata={"language": lang},
                    )
                )

    for idx, line in enumerate(lines, start=1):
        if JAVA_SECRET_RE.search(line):
            signals.append(
                Signal(
                    concept_id="security.secrets-management",
                    kind=SignalKind.WEAKNESS,
                    file_path=file_path,
                    line_range=(idx, idx),
                    evidence=f"[WEAKNESS] Hardcoded credential: {line.strip()[:100]}",
                    confidence=0.9,
                    metadata={"language": "java"},
                )
            )

    return signals


def _scan_java_evidence(file_path: Path) -> List[EvidenceFact]:
    """Scan a single Java/Kotlin source file and return native EvidenceFacts."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    facts: List[EvidenceFact] = []
    lang = "kotlin" if file_path.suffix.lower() == ".kt" else "java"

    detected_framework: str | None = None
    if "springframework" in content or "@SpringBootApplication" in content or "@RestController" in content:
        detected_framework = "spring-boot"

    detected_library: str | None = None
    if "resilience4j" in content:
        detected_library = "resilience4j"
    elif "hikari" in content.lower():
        detected_library = "hikaricp"
    elif "micrometer" in content:
        detected_library = "micrometer"
    elif "web3j" in content.lower():
        detected_library = "web3j"
    elif "netty" in content.lower():
        detected_library = "netty"
    elif "picocli" in content.lower():
        detected_library = "picocli"

    for concept_id, _sig_kind, pattern, _lang, ev_kind in JAVA_PATTERNS:
        for idx, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if m:
                matched_snippet = line.strip()[:200]
                scope = _extract_java_scope(lines, idx - 1)
                subject = m.group(0).strip("()")

                facts.append(
                    EvidenceFact(
                        kind=ev_kind,
                        subject=subject,
                        language=lang,
                        file_path=file_path,
                        line_range=(idx, idx),
                        snippet=matched_snippet,
                        scope=scope,
                        framework=detected_framework,
                        library=detected_library,
                        extraction_confidence=0.95,
                        identifier_hints=(concept_id, lang),
                    )
                )

    for idx, line in enumerate(lines, start=1):
        if JAVA_SECRET_RE.search(line):
            scope = _extract_java_scope(lines, idx - 1)
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.CONFIG_KEY,
                    subject="hardcoded_credential",
                    language=lang,
                    file_path=file_path,
                    line_range=(idx, idx),
                    snippet=line.strip()[:200],
                    scope=scope,
                    extraction_confidence=0.9,
                    identifier_hints=("security.secrets-management", "credential"),
                )
            )

    return facts


def scan_java_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan a Java/Kotlin project and return FileEvidence per file."""
    files = discover_java_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in files:
        facts = _scan_java_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


def scan_java_project(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileSignals]:
    """Scan a Java/Kotlin project and return FileSignals per file (legacy)."""
    files = discover_java_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in files:
        sigs = _scan_java_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


class JavaScanner:
    """Authoritative Java and Kotlin source code scanner for SDAT.

    Scans Java and Kotlin codebases for Spring Boot patterns, Resilience4j,
    HikariCP, Kafka, Micrometer, and Kotlin coroutines.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "java"
    file_extensions: tuple[str, ...] = (".java", ".kt")

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        return discover_java_files(root, exclude_dirs=exclude_dirs)

    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        return _scan_java_evidence(Path(file_path))

    def extract_evidence(self, files: List[Path]) -> List[EvidenceFact]:
        all_facts: List[EvidenceFact] = []
        for f in files:
            all_facts.extend(self.scan_file_evidence(f))
        return all_facts

    def scan_project_evidence(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileEvidence]:
        return scan_java_project_evidence(root, exclude_dirs=exclude_dirs)

    def scan_file(self, file_path: Path | str) -> List[Signal]:
        return _scan_java_file(Path(file_path))

    def extract_signals(self, files: List[Path]) -> List[Signal]:
        all_signals: List[Signal] = []
        for f in files:
            all_signals.extend(self.scan_file(f))
        return all_signals

    def scan_project(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileSignals]:
        return scan_java_project(root, exclude_dirs=exclude_dirs)
