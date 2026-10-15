"""Go source code scanner for SDAT — conforms to LanguageScanner protocol.

Scans Go source files (.go) for distributed systems design patterns,
concurrency primitives, context timeouts, connection pooling, caching,
circuit breakers, retries, message queues, and architectural smells.
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
    "__pycache__",
    "vendor",
    ".sdat-cache",
    ".venv",
    "venv",
    "bin",
    "obj",
}

# ─────────────────────────────────────────────────────────────────────────────
# Concept Signal & Pattern Definitions for Go
# ─────────────────────────────────────────────────────────────────────────────

# (concept_id, signal_kind, regex, language_tag, kind_enum)
GO_PATTERNS: List[tuple[str, SignalKind, re.Pattern, str, EvidenceKind]] = [
    # Caching
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"github\.com/(?:redis/go-redis|go-redis/redis)|go-redis"), "go", EvidenceKind.IMPORT),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"redis\.NewClient|redis\.NewClusterClient"), "go", EvidenceKind.INSTANTIATION),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"\bclient\.Set\(|\.Get\(ctx|\.SetEX\(|\.MGet\("), "go", EvidenceKind.CALL),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"bradfitz/gomemcache|allegro/bigcache|dgraph-io/ristretto|coocood/freecache"), "go", EvidenceKind.IMPORT),

    # Circuit Breaker
    ("foundation.circuit-breaker", SignalKind.PRESENCE, re.compile(r"github\.com/(?:sony/gobreaker|afex/hystrix-go|cep21/circuit)"), "go", EvidenceKind.IMPORT),
    ("foundation.circuit-breaker", SignalKind.PRESENCE, re.compile(r"gobreaker\.NewCircuitBreaker|hystrix\.ConfigureCommand|circuit\.New"), "go", EvidenceKind.INSTANTIATION),
    ("foundation.circuit-breaker", SignalKind.PRESENCE, re.compile(r"\.Execute\(func\(\)\s*\(any,\s*error\)|\.Do\(func\(\)\s*error"), "go", EvidenceKind.CALL),

    # Retries & Backoff
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"github\.com/(?:cenkalti/backoff|avast/retry-go)"), "go", EvidenceKind.IMPORT),
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"backoff\.NewExponentialBackOff|backoff\.Retry|retry\.Do\("), "go", EvidenceKind.CALL),
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"for\s+(?:\w+\s*:=\s*0|;\s*attempts\s*<|;\s*retries\s*<).*(?:time\.Sleep|backoff)"), "go", EvidenceKind.CONTROL_FLOW),

    # Connection Pooling
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"\.SetMaxOpenConns\(|\.SetMaxIdleConns\(|\.SetConnMaxLifetime\(|\.SetConnMaxIdleTime\("), "go", EvidenceKind.CALL),
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"pgxpool\.New|pgxpool\.Connect|sql\.Open"), "go", EvidenceKind.INSTANTIATION),
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"MaxOpenConns|MaxIdleConns|ConnMaxLifetime"), "go", EvidenceKind.CONFIG_KEY),

    # Concurrency & Goroutines
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"\bgo\s+(?:func|[a-zA-Z_]\w*\s*\()"), "go", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"sync\.WaitGroup|sync\.Mutex|sync\.RWMutex|sync\.Pool|sync\.Map"), "go", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"make\s*\(\s*chan\s+"), "go", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"\bselect\s*\{"), "go", EvidenceKind.CONTROL_FLOW),

    # Context & Timeouts / Cancellation
    ("resilience.timeout", SignalKind.PRESENCE, re.compile(r"context\.WithTimeout|context\.WithDeadline"), "go", EvidenceKind.CALL),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"context\.WithCancel|context\.Background|context\.TODO"), "go", EvidenceKind.CALL),
    ("resilience.timeout", SignalKind.PRESENCE, re.compile(r"http\.Client\{[^}]*Timeout:|client\.Timeout\s*="), "go", EvidenceKind.CONFIG_KEY),

    # Message Queues & Streaming
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"github\.com/(?:segmentio/kafka-go|confluentinc/confluent-kafka-go|Shopify/sarama|IBM/sarama)"), "go", EvidenceKind.IMPORT),
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"github\.com/(?:streadway/amqp|rabbitmq/amqp091-go|nats-io/nats\.go)"), "go", EvidenceKind.IMPORT),
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"kafka\.NewWriter|kafka\.NewReader|amqp\.Dial|nats\.Connect"), "go", EvidenceKind.INSTANTIATION),

    # Logging
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"go\.uber\.org/zap|github\.com/rs/zerolog|github\.com/sirupsen/logrus|log/slog"), "go", EvidenceKind.IMPORT),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"zap\.NewProduction|zap\.NewDevelopment|zerolog\.New|logrus\.New|slog\.New"), "go", EvidenceKind.INSTANTIATION),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"\blogger\.(?:Info|Warn|Error|Debug)|slog\.(?:Info|Warn|Error|Debug)|log\.Printf"), "go", EvidenceKind.CALL),

    # Config & Environment
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"github\.com/(?:spf13/viper|joho/godotenv|kelseyhightower/envconfig)"), "go", EvidenceKind.IMPORT),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"os\.Getenv|os\.LookupEnv"), "go", EvidenceKind.ENV_VAR),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"viper\.ReadInConfig|viper\.GetString|godotenv\.Load"), "go", EvidenceKind.CALL),

    # HTTP / REST / Routing
    ("api.rest", SignalKind.PRESENCE, re.compile(r"github\.com/(?:gin-gonic/gin|labstack/echo|gofiber/fiber|go-chi/chi|gorilla/mux)"), "go", EvidenceKind.IMPORT),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"gin\.Default|echo\.New|fiber\.New|chi\.NewRouter|mux\.NewRouter"), "go", EvidenceKind.INSTANTIATION),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"\.(?:GET|POST|PUT|DELETE|PATCH)\([\"'][^\"']+[\"']"), "go", EvidenceKind.CALL),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"http\.HandleFunc|http\.ListenAndServe|http\.NewServeMux"), "go", EvidenceKind.CALL),

    # Rate Limiting
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"golang\.org/x/time/rate|github\.com/ulule/limiter"), "go", EvidenceKind.IMPORT),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"rate\.NewLimiter|\.Allow\(\)|\.Wait\(ctx\)"), "go", EvidenceKind.CALL),

    # Observability & Metrics
    ("foundation.observability", SignalKind.PRESENCE, re.compile(r"github\.com/prometheus/client_golang|go\.opentelemetry\.io/otel"), "go", EvidenceKind.IMPORT),
    ("foundation.observability", SignalKind.PRESENCE, re.compile(r"prometheus\.NewCounter|prometheus\.NewHistogram|promhttp\.Handler"), "go", EvidenceKind.CALL),
    ("foundation.observability", SignalKind.PRESENCE, re.compile(r"otel\.Tracer|trace\.SpanFromContext"), "go", EvidenceKind.CALL),

    # Health Checks
    ("foundation.health-checks", SignalKind.PRESENCE, re.compile(r"[\"']/(?:health|healthz|readyz|livez)[\"']"), "go", EvidenceKind.CALL),

    # Auth & Tokens
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"golang\.org/x/crypto/bcrypt|github\.com/(?:golang-jwt/jwt|dgrijalva/jwt-go)"), "go", EvidenceKind.IMPORT),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"bcrypt\.GenerateFromPassword|bcrypt\.CompareHashAndPassword|jwt\.Parse"), "go", EvidenceKind.CALL),

    # Idempotency
    ("foundation.idempotency", SignalKind.PRESENCE, re.compile(r"X-Idempotency-Key|Idempotency-Key|idempotency_key", re.IGNORECASE), "go", EvidenceKind.CONFIG_KEY),

    # Error Handling & Panic Recovery
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"recover\(\)|gin\.Recovery|echo\.Recover"), "go", EvidenceKind.CALL),
    ("foundation.error-handling", SignalKind.PRESENCE, re.compile(r"if\s+err\s*!=\s*nil\s*\{"), "go", EvidenceKind.CONTROL_FLOW),

    # Database / ORM
    ("data.orm", SignalKind.PRESENCE, re.compile(r"gorm\.io/gorm|github\.com/jmoiron/sqlx|entgo\.io/ent"), "go", EvidenceKind.IMPORT),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"gorm\.Open|sqlx\.Connect|ent\.NewClient"), "go", EvidenceKind.INSTANTIATION),

    # Raw Networking & Sockets
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"\bnet\.(?:Listen|ListenTCP|ListenUDP|Dial|DialTimeout)\("), "go", EvidenceKind.CALL),
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"\bnet\.(?:Conn|Listener|PacketConn)\b"), "go", EvidenceKind.CONCURRENCY),
    ("networking.proxy", SignalKind.PRESENCE, re.compile(r"httputil\.NewSingleHostReverseProxy|httputil\.ReverseProxy"), "go", EvidenceKind.INSTANTIATION),

    # CLI, Tooling & Process Execution
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"github\.com/(?:spf13/cobra|urfave/cli)"), "go", EvidenceKind.IMPORT),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"flag\.(?:Parse|StringVar|IntVar|BoolVar)\("), "go", EvidenceKind.CALL),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"exec\.Command|exec\.CommandContext"), "go", EvidenceKind.CALL),

    # RPC & Microservices
    ("networking.rpc", SignalKind.PRESENCE, re.compile(r"google\.golang\.org/grpc|net/rpc"), "go", EvidenceKind.IMPORT),
    ("networking.rpc", SignalKind.PRESENCE, re.compile(r"grpc\.NewServer|grpc\.Dial|grpc\.NewClient|rpc\.NewServer"), "go", EvidenceKind.INSTANTIATION),

    # Blockchain / Web3 Client Integration (Structural Evidence)
    ("blockchain-web3.rpc", SignalKind.PRESENCE, re.compile(r"github\.com/ethereum/go-ethereum/(?:ethclient|rpc)"), "go", EvidenceKind.IMPORT),
    ("blockchain-web3.rpc", SignalKind.PRESENCE, re.compile(r"ethclient\.Dial|ethclient\.DialContext|rpc\.Dial|rpc\.DialContext"), "go", EvidenceKind.INSTANTIATION),
    ("blockchain-web3.contract", SignalKind.PRESENCE, re.compile(r"bind\.NewBoundContract|accounts/abi"), "go", EvidenceKind.CALL),
    ("blockchain-web3.transaction", SignalKind.PRESENCE, re.compile(r"types\.NewTransaction|types\.NewTx|bind\.NewKeyedTransactorWithChainID"), "go", EvidenceKind.CALL),
    ("blockchain-web3.signing", SignalKind.PRESENCE, re.compile(r"types\.SignTx|crypto\.Sign\b|bind\.SignerFn"), "go", EvidenceKind.CALL),
    ("blockchain-web3.submission", SignalKind.PRESENCE, re.compile(r"\.SendTransaction\("), "go", EvidenceKind.CALL),
    ("blockchain-web3.confirmation", SignalKind.PRESENCE, re.compile(r"\.TransactionReceipt\(|bind\.WaitMined|bind\.WaitDeployed"), "go", EvidenceKind.CALL),
    ("blockchain-web3.events", SignalKind.PRESENCE, re.compile(r"\.SubscribeFilterLogs\(|\.FilterLogs\(|\.SubscribeNewHead\("), "go", EvidenceKind.CALL),
    ("blockchain-web3.state", SignalKind.PRESENCE, re.compile(r"\.PendingNonceAt\(|\.NonceAt\(|\.BalanceAt\(|\.CodeAt\("), "go", EvidenceKind.CALL),
]

HARDCODED_SECRET_RE = re.compile(
    r"""(?:api[_-]?key|secret|password|token|private[_-]?key)\s*(?::=|=)\s*["'][A-Za-z0-9_\-+/]{12,}["']""",
    re.IGNORECASE,
)

EMPTY_ERR_BLOCK_RE = re.compile(r"if\s+err\s*!=\s*nil\s*\{\s*\}")


# ─────────────────────────────────────────────────────────────────────────────
# File Discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_go_files(
    root: Path | str,
    exclude_dirs: Set[str] | None = None,
) -> List[Path]:
    """Recursively discover all Go files (*.go) under root, obeying exclusions."""
    base = Path(root)
    if not base.exists() or not base.is_dir():
        return []

    effective_excludes = DEFAULT_EXCLUDE_DIRS | (exclude_dirs or set())
    discovered: List[Path] = []

    for path in base.rglob("*.go"):
        parts = set(path.parts)
        if not (parts & effective_excludes):
            discovered.append(path)

    return sorted(discovered)


# ─────────────────────────────────────────────────────────────────────────────
# Structural Scanning & Evidence Extraction
# ─────────────────────────────────────────────────────────────────────────────

def _extract_go_scope(lines: list[str], line_idx: int) -> str | None:
    """Find enclosing function or method signature for a given line."""
    func_re = re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Za-z_]\w*)")
    for idx in range(line_idx, -1, -1):
        m = func_re.match(lines[idx].strip())
        if m:
            return m.group(1)
    return None


def _scan_go_file(file_path: Path) -> List[Signal]:
    """Scan a Go file and return detected Signal objects (legacy compatibility)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    signals: List[Signal] = []

    # 1. Pattern scanning
    for concept_id, kind, pattern, lang, _ev_kind in GO_PATTERNS:
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

    # 2. Hardcoded secrets weakness
    for idx, line in enumerate(lines, start=1):
        if HARDCODED_SECRET_RE.search(line):
            signals.append(
                Signal(
                    concept_id="security.secrets-management",
                    kind=SignalKind.WEAKNESS,
                    file_path=file_path,
                    line_range=(idx, idx),
                    evidence=f"[WEAKNESS] Hardcoded credential: {line.strip()[:100]}",
                    confidence=0.9,
                    metadata={"language": "go"},
                )
            )

    # 3. Empty error handling weakness
    for idx, line in enumerate(lines, start=1):
        if EMPTY_ERR_BLOCK_RE.search(line):
            signals.append(
                Signal(
                    concept_id="foundation.error-handling",
                    kind=SignalKind.WEAKNESS,
                    file_path=file_path,
                    line_range=(idx, idx),
                    evidence=f"[WEAKNESS] Empty error block: {line.strip()[:100]}",
                    confidence=0.85,
                    metadata={"language": "go"},
                )
            )

    return signals


def _scan_go_evidence(file_path: Path) -> List[EvidenceFact]:
    """Scan a single Go source file and return native typed EvidenceFacts."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    facts: List[EvidenceFact] = []

    # Detect package and imports for metadata
    pkg_match = re.search(r"^package\s+([A-Za-z_]\w*)", content, re.MULTILINE)
    pkg_name = pkg_match.group(1) if pkg_match else None

    # Track framework/library context
    detected_framework: str | None = None
    detected_library: str | None = None
    if "gin-gonic/gin" in content:
        detected_framework = "gin"
    elif "labstack/echo" in content:
        detected_framework = "echo"
    elif "gofiber/fiber" in content:
        detected_framework = "fiber"
    elif "go-chi/chi" in content:
        detected_framework = "chi"

    if "go-redis" in content or "redis/go-redis" in content:
        detected_library = "go-redis"
    elif "pgx" in content:
        detected_library = "pgx"
    elif "gorm" in content:
        detected_library = "gorm"
    elif "go-ethereum" in content or "ethclient" in content:
        detected_library = "go-ethereum"
    elif "grpc" in content:
        detected_library = "grpc"
    elif "cobra" in content:
        detected_library = "cobra"

    for concept_id, sig_kind, pattern, lang, ev_kind in GO_PATTERNS:
        for idx, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if m:
                matched_snippet = line.strip()[:200]
                scope = _extract_go_scope(lines, idx - 1)
                subject = m.group(0).strip("()")

                # Additional structural properties
                timeout_observed = None
                ttl_observed = None
                if "context.WithTimeout" in line or "Timeout:" in line:
                    timeout_observed = True
                if "client.Set(" in line or ".SetEX(" in line:
                    ttl_observed = True if any(x in line for x in ("time.", "Second", "Minute", "Hour", "time.Duration")) else False

                facts.append(
                    EvidenceFact(
                        kind=ev_kind,
                        subject=subject,
                        language="go",
                        file_path=file_path,
                        line_range=(idx, idx),
                        snippet=matched_snippet,
                        scope=scope,
                        framework=detected_framework,
                        library=detected_library,
                        extraction_confidence=0.95,
                        identifier_hints=(concept_id, pkg_name or "go"),
                        timeout_observed=timeout_observed,
                        ttl_observed=ttl_observed,
                    )
                )

    # Hardcoded secrets
    for idx, line in enumerate(lines, start=1):
        if HARDCODED_SECRET_RE.search(line):
            scope = _extract_go_scope(lines, idx - 1)
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.CONFIG_KEY,
                    subject="hardcoded_credential",
                    language="go",
                    file_path=file_path,
                    line_range=(idx, idx),
                    snippet=line.strip()[:200],
                    scope=scope,
                    extraction_confidence=0.9,
                    identifier_hints=("security.secrets-management", "credential"),
                )
            )

    return facts


def scan_go_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan an entire Go project and return FileEvidence per file."""
    files = discover_go_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in files:
        facts = _scan_go_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


def scan_go_project(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileSignals]:
    """Scan an entire Go project and return FileSignals per file (legacy)."""
    files = discover_go_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in files:
        sigs = _scan_go_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Authoritative GoScanner conforming to LanguageScanner
# ─────────────────────────────────────────────────────────────────────────────

class GoScanner:
    """Authoritative Go source code scanner for SDAT.

    Scans Go codebases for system design patterns, concurrency structures,
    resilience patterns, and architecture facts.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "go"
    file_extensions: tuple[str, ...] = (".go",)

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        """Walk root and return discovered Go source files."""
        return discover_go_files(root, exclude_dirs=exclude_dirs)

    # Phase 2.5 Common Evidence Model
    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        """Scan a single Go file and return native EvidenceFacts."""
        return _scan_go_evidence(Path(file_path))

    def extract_evidence(self, files: List[Path]) -> List[EvidenceFact]:
        """Extract concept-agnostic EvidenceFacts from a list of Go files."""
        all_facts: List[EvidenceFact] = []
        for f in files:
            all_facts.extend(self.scan_file_evidence(f))
        return all_facts

    def scan_project_evidence(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileEvidence]:
        """Scan an entire Go project directory and return FileEvidence per file."""
        return scan_go_project_evidence(root, exclude_dirs=exclude_dirs)

    # Legacy Signal Protocol
    def scan_file(self, file_path: Path | str) -> List[Signal]:
        """Scan a single Go file and return all detected signals."""
        return _scan_go_file(Path(file_path))

    def extract_signals(self, files: List[Path]) -> List[Signal]:
        """Extract signals from a list of Go files."""
        all_signals: List[Signal] = []
        for f in files:
            all_signals.extend(self.scan_file(f))
        return all_signals

    def scan_project(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[FileSignals]:
        """Scan an entire Go project directory and return FileSignals per file."""
        return scan_go_project(root, exclude_dirs=exclude_dirs)
