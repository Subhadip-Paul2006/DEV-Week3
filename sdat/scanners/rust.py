"""Rust source code scanner for SDAT — conforms to LanguageScanner protocol.

Scans Rust source files (.rs) for distributed systems patterns, async runtimes
(Tokio, Actix, Axum), synchronization primitives (Arc, Mutex, channels),
connection pools, caching, message queues, and embedded patterns.
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
    "__pycache__",
    "vendor",
    ".sdat-cache",
    ".venv",
    "venv",
    "bin",
    "obj",
}

# (concept_id, signal_kind, regex, language_tag, kind_enum)
RUST_PATTERNS: List[tuple[str, SignalKind, re.Pattern, str, EvidenceKind]] = [
    # Async Runtime & Web Frameworks
    ("api.rest", SignalKind.PRESENCE, re.compile(r"use\s+axum::|use\s+actix_web::|use\s+warp::|use\s+hyper::"), "rust", EvidenceKind.IMPORT),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"#\[tokio::main\]|#\[actix_web::main\]"), "rust", EvidenceKind.FRAMEWORK_MARKER),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"Router::new\(\)|App::new\(\)|warp::path\("), "rust", EvidenceKind.INSTANTIATION),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"\.route\([\"'][^\"']+[\"'],\s*(?:get|post|put|delete)\("), "rust", EvidenceKind.CALL),

    # Concurrency & Async
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"tokio::spawn\b"), "rust", EvidenceKind.ASYNC_PATTERN),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"async\s+fn\b"), "rust", EvidenceKind.ASYNC_PATTERN),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"Arc<(?:Mutex|RwLock)<"), "rust", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"use\s+std::sync::(?:Arc|Mutex|RwLock)|use\s+parking_lot::"), "rust", EvidenceKind.IMPORT),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"tokio::sync::mpsc|std::sync::mpsc|crossbeam_channel|flume"), "rust", EvidenceKind.IMPORT),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"mpsc::channel|mpsc::unbounded_channel"), "rust", EvidenceKind.CALL),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"tokio::select!\s*\{"), "rust", EvidenceKind.CONTROL_FLOW),

    # Timeouts & Cancellation
    ("resilience.timeout", SignalKind.PRESENCE, re.compile(r"tokio::time::timeout|tokio::time::sleep"), "rust", EvidenceKind.CALL),
    ("resilience.timeout", SignalKind.PRESENCE, re.compile(r"timeout\s*=\s*Duration::from_"), "rust", EvidenceKind.CONFIG_KEY),

    # Database & Connection Pooling
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"use\s+sqlx::|use\s+diesel::|use\s+sea_orm::|use\s+deadpool|use\s+bb8"), "rust", EvidenceKind.IMPORT),
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"PgPoolOptions::new\(\)|sqlx::Pool|PgPool::connect|bb8::Pool|r2d2::Pool"), "rust", EvidenceKind.INSTANTIATION),
    ("foundation.connection-pooling", SignalKind.PRESENCE, re.compile(r"\.max_connections\(|\.min_connections\(|\.idle_timeout\("), "rust", EvidenceKind.CALL),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"sqlx::query!|sqlx::query_as!|diesel::insert_into"), "rust", EvidenceKind.DB_QUERY),

    # Caching
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"use\s+redis::|use\s+bb8_redis::|use\s+deadpool_redis::|use\s+moka::"), "rust", EvidenceKind.IMPORT),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"redis::Client::open|moka::future::Cache::new"), "rust", EvidenceKind.INSTANTIATION),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"\.set_ex\(|\.get\(|\.mget\("), "rust", EvidenceKind.CALL),

    # Retries & Resilience
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"use\s+backoff::|use\s+tower::retry|use\s+tokio_retry"), "rust", EvidenceKind.IMPORT),
    ("foundation.retries", SignalKind.PRESENCE, re.compile(r"backoff::future::retry|ExponentialBackoff::default"), "rust", EvidenceKind.CALL),
    ("foundation.circuit-breaker", SignalKind.PRESENCE, re.compile(r"use\s+failsafe::|failsafe::Config"), "rust", EvidenceKind.IMPORT),

    # Message Queues
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"use\s+rdkafka::|use\s+lapin::|use\s+async_nats::"), "rust", EvidenceKind.IMPORT),
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"FutureProducer::|Client::connect.*lapin|async_nats::connect"), "rust", EvidenceKind.INSTANTIATION),

    # Logging & Observability
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"use\s+tracing::|use\s+log::|use\s+env_logger"), "rust", EvidenceKind.IMPORT),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"tracing::(?:info|warn|error|debug)!|log::(?:info|warn|error|debug)!"), "rust", EvidenceKind.CALL),
    ("foundation.observability", SignalKind.PRESENCE, re.compile(r"use\s+opentelemetry::|use\s+prometheus::"), "rust", EvidenceKind.IMPORT),
    ("foundation.observability", SignalKind.PRESENCE, re.compile(r"prometheus::Registry|opentelemetry::global::tracer"), "rust", EvidenceKind.INSTANTIATION),

    # Config & Environment
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"use\s+dotenvy::|use\s+dotenv::|use\s+figment::"), "rust", EvidenceKind.IMPORT),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"std::env::var|dotenvy::dotenv"), "rust", EvidenceKind.ENV_VAR),

    # Health Checks
    ("foundation.health-checks", SignalKind.PRESENCE, re.compile(r"[\"']/(?:health|healthz|readyz|livez)[\"']"), "rust", EvidenceKind.CALL),

    # Embedded / no_std
    ("architecture.embedded", SignalKind.PRESENCE, re.compile(r"#\!\[no_std\]|use\s+cortex_m::|use\s+embedded_hal::"), "rust", EvidenceKind.FRAMEWORK_MARKER),

    # Auth & Cryptography
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"use\s+jsonwebtoken::|use\s+argon2::|use\s+bcrypt::"), "rust", EvidenceKind.IMPORT),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"jsonwebtoken::encode|jsonwebtoken::decode|Argon2::default"), "rust", EvidenceKind.CALL),

    # Rate Limiting
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"use\s+governor::|tower::limit::RateLimit"), "rust", EvidenceKind.IMPORT),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"RateLimiter::direct|Quota::per_second"), "rust", EvidenceKind.CALL),

    # Raw Networking & Sockets
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"std::net::(?:TcpListener|TcpStream|UdpSocket)|tokio::net::(?:TcpListener|TcpStream|UdpSocket)"), "rust", EvidenceKind.IMPORT),
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"TcpListener::bind|UdpSocket::bind"), "rust", EvidenceKind.CALL),

    # P2P & Distributed Systems
    ("networking.p2p", SignalKind.PRESENCE, re.compile(r"use\s+libp2p::|libp2p::swarm|SwarmBuilder"), "rust", EvidenceKind.IMPORT),

    # CLI, Tooling & Process Execution
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"use\s+clap::|#\[derive\(Parser\)\]|#\[derive\(Subcommand\)\]"), "rust", EvidenceKind.FRAMEWORK_MARKER),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"std::process::Command::new|Command::new\("), "rust", EvidenceKind.CALL),

    # RPC & Microservices
    ("networking.rpc", SignalKind.PRESENCE, re.compile(r"use\s+tonic::|tonic::transport"), "rust", EvidenceKind.IMPORT),

    # Blockchain / Web3 Client Integration (Structural Evidence)
    ("blockchain-web3.rpc", SignalKind.PRESENCE, re.compile(r"use\s+(?:ethers|alloy|web3|solana_client|subxt)::"), "rust", EvidenceKind.IMPORT),
    ("blockchain-web3.rpc", SignalKind.PRESENCE, re.compile(r"Provider::<Http>::try_from|Provider::new_client|RpcClient::new"), "rust", EvidenceKind.INSTANTIATION),
    ("blockchain-web3.contract", SignalKind.PRESENCE, re.compile(r"Contract::new|abigen!"), "rust", EvidenceKind.CALL),
    ("blockchain-web3.transaction", SignalKind.PRESENCE, re.compile(r"TransactionRequest::new|TypedTransaction"), "rust", EvidenceKind.CALL),
    ("blockchain-web3.signing", SignalKind.PRESENCE, re.compile(r"SignerMiddleware|LocalWallet|\.sign_transaction\("), "rust", EvidenceKind.CALL),
    ("blockchain-web3.submission", SignalKind.PRESENCE, re.compile(r"\.send_transaction\(|\.send_raw_transaction\("), "rust", EvidenceKind.CALL),
    ("blockchain-web3.events", SignalKind.PRESENCE, re.compile(r"\.subscribe_logs\(|\.subscribe_blocks\(|\.watch_blocks\("), "rust", EvidenceKind.CALL),
]

RUST_HARDCODED_SECRET_RE = re.compile(
    r"""(?:api[_-]?key|secret|password|token|private[_-]?key)\s*(?::\s*&str)?\s*=\s*["'][A-Za-z0-9_\-+/]{12,}["']""",
    re.IGNORECASE,
)


def discover_rust_files(
    root: Path | str,
    exclude_dirs: Set[str] | None = None,
) -> List[Path]:
    """Discover all Rust source files (*.rs) under root obeying exclusions."""
    base = Path(root)
    if not base.exists() or not base.is_dir():
        return []

    effective_excludes = DEFAULT_EXCLUDE_DIRS | (exclude_dirs or set())
    discovered: List[Path] = []

    for path in base.rglob("*.rs"):
        parts = set(path.parts)
        if not (parts & effective_excludes):
            discovered.append(path)

    return sorted(discovered)


def _extract_rust_scope(lines: list[str], line_idx: int) -> str | None:
    """Find enclosing fn, struct, or impl block name."""
    fn_re = re.compile(r"^(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?fn\s+([A-Za-z_]\w*)")
    impl_re = re.compile(r"^impl(?:\s+<[^>]+>)?\s+(?:[A-Za-z_]\w*\s+for\s+)?([A-Za-z_]\w*)")
    for idx in range(line_idx, -1, -1):
        line = lines[idx].strip()
        m_fn = fn_re.match(line)
        if m_fn:
            return m_fn.group(1)
        m_impl = impl_re.match(line)
        if m_impl:
            return f"impl {m_impl.group(1)}"
    return None


def _scan_rust_file(file_path: Path) -> List[Signal]:
    """Scan a Rust file and return detected Signal objects (legacy compatibility)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    signals: List[Signal] = []

    for concept_id, kind, pattern, lang, _ev_kind in RUST_PATTERNS:
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
        if RUST_HARDCODED_SECRET_RE.search(line):
            signals.append(
                Signal(
                    concept_id="security.secrets-management",
                    kind=SignalKind.WEAKNESS,
                    file_path=file_path,
                    line_range=(idx, idx),
                    evidence=f"[WEAKNESS] Hardcoded credential: {line.strip()[:100]}",
                    confidence=0.9,
                    metadata={"language": "rust"},
                )
            )

    return signals


def _scan_rust_evidence(file_path: Path) -> List[EvidenceFact]:
    """Scan a single Rust source file and return native EvidenceFacts."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    facts: List[EvidenceFact] = []

    # Detect framework context
    detected_framework: str | None = None
    if "axum::" in content or "axum" in content:
        detected_framework = "axum"
    elif "actix_web::" in content:
        detected_framework = "actix-web"
    elif "warp::" in content:
        detected_framework = "warp"

    detected_library: str | None = None
    if "sqlx::" in content:
        detected_library = "sqlx"
    elif "tokio::" in content:
        detected_library = "tokio"
    elif "redis::" in content:
        detected_library = "redis-rs"
    elif "ethers::" in content or "alloy::" in content:
        detected_library = "ethers"
    elif "libp2p" in content:
        detected_library = "libp2p"
    elif "clap" in content:
        detected_library = "clap"

    for concept_id, _sig_kind, pattern, _lang, ev_kind in RUST_PATTERNS:
        for idx, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if m:
                matched_snippet = line.strip()[:200]
                scope = _extract_rust_scope(lines, idx - 1)
                subject = m.group(0).strip("()")

                timeout_observed = True if "timeout" in line or "Duration::from_" in line else None
                ttl_observed = True if ".set_ex(" in line else None

                facts.append(
                    EvidenceFact(
                        kind=ev_kind,
                        subject=subject,
                        language="rust",
                        file_path=file_path,
                        line_range=(idx, idx),
                        snippet=matched_snippet,
                        scope=scope,
                        framework=detected_framework,
                        library=detected_library,
                        extraction_confidence=0.95,
                        identifier_hints=(concept_id, "rust"),
                        timeout_observed=timeout_observed,
                        ttl_observed=ttl_observed,
                    )
                )

    for idx, line in enumerate(lines, start=1):
        if RUST_HARDCODED_SECRET_RE.search(line):
            scope = _extract_rust_scope(lines, idx - 1)
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.CONFIG_KEY,
                    subject="hardcoded_credential",
                    language="rust",
                    file_path=file_path,
                    line_range=(idx, idx),
                    snippet=line.strip()[:200],
                    scope=scope,
                    extraction_confidence=0.9,
                    identifier_hints=("security.secrets-management", "credential"),
                )
            )

    return facts


def scan_rust_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan a Rust project and return FileEvidence per file."""
    files = discover_rust_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in files:
        facts = _scan_rust_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


def scan_rust_project(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileSignals]:
    """Scan a Rust project and return FileSignals per file (legacy)."""
    files = discover_rust_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in files:
        sigs = _scan_rust_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


class RustScanner:
    """Authoritative Rust source code scanner for SDAT.

    Scans Rust codebases for system design patterns, async runtimes,
    concurrency and memory-safety patterns, connection pooling, and resilience.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "rust"
    file_extensions: tuple[str, ...] = (".rs",)

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        return discover_rust_files(root, exclude_dirs=exclude_dirs)

    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        return _scan_rust_evidence(Path(file_path))

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
        return scan_rust_project_evidence(root, exclude_dirs=exclude_dirs)

    def scan_file(self, file_path: Path | str) -> List[Signal]:
        return _scan_rust_file(Path(file_path))

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
        return scan_rust_project(root, exclude_dirs=exclude_dirs)
