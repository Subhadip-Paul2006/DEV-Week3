"""PHP source code scanner for SDAT — conforms to LanguageScanner protocol.

Scans PHP source files (.php) for Laravel, Symfony, Slim, Eloquent/Doctrine,
caching (Redis, Cache::remember), queues (ShouldQueue), rate limiting, and auth.
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
    "vendor",
    "__pycache__",
    ".sdat-cache",
    ".venv",
    "venv",
    "storage",
    "bootstrap/cache",
}

PHP_PATTERNS: List[tuple[str, SignalKind, re.Pattern, str, EvidenceKind]] = [
    # Framework & Routing
    ("api.rest", SignalKind.PRESENCE, re.compile(r"Route::(?:get|post|put|delete|patch|options)\("), "php", EvidenceKind.CALL),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"\$app->(?:get|post|put|delete|group)\("), "php", EvidenceKind.CALL),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"#\[Route\([\"'][^\"']+[\"']"), "php", EvidenceKind.ANNOTATION),
    ("api.rest", SignalKind.PRESENCE, re.compile(r"extends\s+Controller\b"), "php", EvidenceKind.INHERITANCE),

    # Database & ORM
    ("data.orm", SignalKind.PRESENCE, re.compile(r"extends\s+Model\b"), "php", EvidenceKind.INHERITANCE),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"DB::table\(|DB::transaction\(|DB::connection\("), "php", EvidenceKind.CALL),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"new\s+PDO\(|PDO::ATTR_PERSISTENT"), "php", EvidenceKind.INSTANTIATION),
    ("data.orm", SignalKind.PRESENCE, re.compile(r"Doctrine\\ORM|EntityManagerInterface"), "php", EvidenceKind.IMPORT),

    # Caching
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"Cache::(?:remember|rememberForever|put|get|has)\("), "php", EvidenceKind.CALL),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"Redis::(?:set|setex|get|mget)\(|new\s+Predis\\Client|new\s+Redis\(\)"), "php", EvidenceKind.CALL),
    ("foundation.caching", SignalKind.PRESENCE, re.compile(r"use\s+Illuminate\\Support\\Facades\\Cache|use\s+Illuminate\\Support\\Facades\\Redis"), "php", EvidenceKind.IMPORT),

    # Queues & Background Jobs
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"implements\s+ShouldQueue\b"), "php", EvidenceKind.FRAMEWORK_MARKER),
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"Queue::push\(|dispatch\(|dispatchSync\("), "php", EvidenceKind.CALL),
    ("foundation.message-queues", SignalKind.PRESENCE, re.compile(r"use\s+Illuminate\\Contracts\\Queue\\ShouldQueue"), "php", EvidenceKind.IMPORT),

    # Rate Limiting
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"RateLimiter::(?:for|attempt|tooManyAttempts)\("), "php", EvidenceKind.CALL),
    ("foundation.rate-limiting", SignalKind.PRESENCE, re.compile(r"middleware\([\"']throttle:"), "php", EvidenceKind.CONFIG_KEY),

    # Logging
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"Log::(?:info|warning|error|debug|critical)\("), "php", EvidenceKind.CALL),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"Monolog\\Logger|use\s+Illuminate\\Support\\Facades\\Log"), "php", EvidenceKind.IMPORT),

    # Config & Environment
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"\benv\(|\bconfig\("), "php", EvidenceKind.CONFIG_KEY),
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"\bgetenv\(|\$_ENV\["), "php", EvidenceKind.ENV_VAR),

    # Auth & Cryptography
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"Auth::(?:user|check|attempt|login)\("), "php", EvidenceKind.CALL),
    ("foundation.auth", SignalKind.PRESENCE, re.compile(r"Hash::make\(|password_hash\(|password_verify\("), "php", EvidenceKind.CALL),

    # Health Checks
    ("foundation.health-checks", SignalKind.PRESENCE, re.compile(r"[\"']/(?:health|healthz|ping|status)[\"']"), "php", EvidenceKind.CALL),

    # CLI & Tooling
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"extends\s+Command\b"), "php", EvidenceKind.INHERITANCE),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"use\s+Symfony\\Component\\Console\\Command\\Command"), "php", EvidenceKind.IMPORT),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"protected\s+\$(?:signature|name)\s*="), "php", EvidenceKind.CONFIG_KEY),

    # Process Control & Workers
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"pcntl_fork\(|proc_open\(|pcntl_signal\("), "php", EvidenceKind.CALL),

    # HTTP Client & External Integrations
    ("networking.http-client", SignalKind.PRESENCE, re.compile(r"new\s+GuzzleHttp\\Client|use\s+GuzzleHttp\\Client"), "php", EvidenceKind.INSTANTIATION),
    ("networking.http-client", SignalKind.PRESENCE, re.compile(r"Http::(?:get|post|put|delete|timeout|withHeaders)\("), "php", EvidenceKind.CALL),
    ("networking.http-client", SignalKind.PRESENCE, re.compile(r"curl_init\(|curl_exec\("), "php", EvidenceKind.CALL),

    # Scheduled Tasks
    ("foundation.scheduling", SignalKind.PRESENCE, re.compile(r"\$schedule->(?:command|call|job)\("), "php", EvidenceKind.CALL),

    # Security Smells
    ("security.code-injection", SignalKind.WEAKNESS, re.compile(r"\beval\(|\bunserialize\("), "php", EvidenceKind.CALL),
]

PHP_SECRET_RE = re.compile(
    r"""\$(?:apiKey|api_key|secret|password|token)\s*=\s*["'][A-Za-z0-9_\-+/]{12,}["']""",
    re.IGNORECASE,
)


def discover_php_files(
    root: Path | str,
    exclude_dirs: Set[str] | None = None,
) -> List[Path]:
    """Discover all PHP source files (*.php) under root obeying exclusions."""
    base = Path(root)
    if not base.exists() or not base.is_dir():
        return []

    effective_excludes = DEFAULT_EXCLUDE_DIRS | (exclude_dirs or set())
    discovered: List[Path] = []

    for path in base.rglob("*.php"):
        parts = set(path.parts)
        if not (parts & effective_excludes):
            discovered.append(path)

    return sorted(discovered)


def _extract_php_scope(lines: list[str], line_idx: int) -> str | None:
    """Find enclosing function, method, or class name."""
    fn_re = re.compile(r"^(?:public|protected|private|static|\s)*function\s+([A-Za-z_]\w*)")
    cls_re = re.compile(r"^(?:abstract|final|\s)*class\s+([A-Za-z_]\w*)")
    for idx in range(line_idx, -1, -1):
        line = lines[idx].strip()
        m_fn = fn_re.match(line)
        if m_fn:
            return m_fn.group(1)
        m_cls = cls_re.match(line)
        if m_cls:
            return f"class {m_cls.group(1)}"
    return None


def _scan_php_file(file_path: Path) -> List[Signal]:
    """Scan a PHP file and return detected Signal objects (legacy compatibility)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    signals: List[Signal] = []

    for concept_id, kind, pattern, lang, _ev_kind in PHP_PATTERNS:
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
        if PHP_SECRET_RE.search(line):
            signals.append(
                Signal(
                    concept_id="security.secrets-management",
                    kind=SignalKind.WEAKNESS,
                    file_path=file_path,
                    line_range=(idx, idx),
                    evidence=f"[WEAKNESS] Hardcoded credential: {line.strip()[:100]}",
                    confidence=0.9,
                    metadata={"language": "php"},
                )
            )

    return signals


def _scan_php_evidence(file_path: Path) -> List[EvidenceFact]:
    """Scan a single PHP source file and return native EvidenceFacts."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    facts: List[EvidenceFact] = []

    detected_framework: str | None = None
    if "Illuminate\\" in content or "Route::" in content:
        detected_framework = "laravel"
    elif "Symfony\\" in content:
        detected_framework = "symfony"
    elif "Slim\\" in content:
        detected_framework = "slim"

    detected_library: str | None = None
    if "guzzle" in content.lower():
        detected_library = "guzzle"
    elif "monolog" in content.lower():
        detected_library = "monolog"
    elif "predis" in content.lower() or "redis" in content.lower():
        detected_library = "redis"

    for concept_id, _sig_kind, pattern, _lang, ev_kind in PHP_PATTERNS:
        for idx, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if m:
                matched_snippet = line.strip()[:200]
                scope = _extract_php_scope(lines, idx - 1)
                subject = m.group(0).strip("()")

                ttl_observed = True if "Cache::remember" in line or "setex" in line else None

                facts.append(
                    EvidenceFact(
                        kind=ev_kind,
                        subject=subject,
                        language="php",
                        file_path=file_path,
                        line_range=(idx, idx),
                        snippet=matched_snippet,
                        scope=scope,
                        framework=detected_framework,
                        library=detected_library,
                        extraction_confidence=0.95,
                        identifier_hints=(concept_id, "php"),
                        ttl_observed=ttl_observed,
                    )
                )

    for idx, line in enumerate(lines, start=1):
        if PHP_SECRET_RE.search(line):
            scope = _extract_php_scope(lines, idx - 1)
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.CONFIG_KEY,
                    subject="hardcoded_credential",
                    language="php",
                    file_path=file_path,
                    line_range=(idx, idx),
                    snippet=line.strip()[:200],
                    scope=scope,
                    extraction_confidence=0.9,
                    identifier_hints=("security.secrets-management", "credential"),
                )
            )

    return facts


def scan_php_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan a PHP project and return FileEvidence per file."""
    files = discover_php_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in files:
        facts = _scan_php_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


def scan_php_project(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileSignals]:
    """Scan a PHP project and return FileSignals per file (legacy)."""
    files = discover_php_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in files:
        sigs = _scan_php_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


class PhpScanner:
    """Authoritative PHP source code scanner for SDAT.

    Scans PHP codebases for web frameworks, database ORMs, caching strategies,
    background queues, and configuration patterns.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "php"
    file_extensions: tuple[str, ...] = (".php",)

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        return discover_php_files(root, exclude_dirs=exclude_dirs)

    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        return _scan_php_evidence(Path(file_path))

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
        return scan_php_project_evidence(root, exclude_dirs=exclude_dirs)

    def scan_file(self, file_path: Path | str) -> List[Signal]:
        return _scan_php_file(Path(file_path))

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
        return scan_php_project(root, exclude_dirs=exclude_dirs)
