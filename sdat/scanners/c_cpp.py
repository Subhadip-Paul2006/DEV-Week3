"""C and C++ source code scanner for SDAT — conforms to LanguageScanner protocol.

Scans C/C++ files (.c, .h, .cpp, .cc, .cxx, .hpp) for POSIX APIs, sockets,
pthreads, synchronization, IPC, memory management, RTOS, and systems architecture.
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
    "CMakeFiles",
}

# (concept_id, signal_kind, regex, language_tag, kind_enum)
C_CPP_PATTERNS: List[tuple[str, SignalKind, re.Pattern, str, EvidenceKind]] = [
    # Networking & Sockets
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"\b(?:socket|bind|listen|accept|connect)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"\b(?:epoll_create|epoll_create1|epoll_ctl|epoll_wait|kqueue|kevent)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"\b(?:select|poll|ppoll)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("networking.socket", SignalKind.PRESENCE, re.compile(r"<sys/socket\.h>|<netinet/in\.h>|<arpa/inet\.h>|<netdb\.h>"), "c_cpp", EvidenceKind.IMPORT),

    # Concurrency: Pthreads & C++11 Threads
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"\b(?:pthread_create|pthread_join|pthread_detach)\s*\("), "c_cpp", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"\b(?:pthread_mutex_init|pthread_mutex_lock|pthread_mutex_unlock|pthread_cond_wait|pthread_rwlock_rdlock)\s*\("), "c_cpp", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"<pthread\.h>|<threads\.h>"), "c_cpp", EvidenceKind.IMPORT),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"std::thread|std::jthread|std::async"), "c_cpp", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"std::mutex|std::shared_mutex|std::lock_guard|std::unique_lock|std::scoped_lock"), "c_cpp", EvidenceKind.CONCURRENCY),
    ("foundation.concurrency", SignalKind.PRESENCE, re.compile(r"<thread>|<mutex>|<condition_variable>|<future>|<atomic>"), "c_cpp", EvidenceKind.IMPORT),

    # Processes & IPC
    ("architecture.process", SignalKind.PRESENCE, re.compile(r"\b(?:fork|vfork|execve|execl|execvp|waitpid)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("architecture.ipc", SignalKind.PRESENCE, re.compile(r"\b(?:pipe|pipe2|mkfifo)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("architecture.ipc", SignalKind.PRESENCE, re.compile(r"\b(?:shm_open|shm_unlink|mmap|munmap)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("architecture.ipc", SignalKind.PRESENCE, re.compile(r"\b(?:sem_init|sem_wait|sem_post|sem_open)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("architecture.ipc", SignalKind.PRESENCE, re.compile(r"\b(?:msgget|msgsnd|msgrcv|mq_open|mq_send|mq_receive)\s*\("), "c_cpp", EvidenceKind.CALL),

    # Timeouts & Socket Options
    ("resilience.timeout", SignalKind.PRESENCE, re.compile(r"SO_RCVTIMEO|SO_SNDTIMEO"), "c_cpp", EvidenceKind.CONFIG_KEY),
    ("resilience.timeout", SignalKind.PRESENCE, re.compile(r"\b(?:alarm|timer_create|timer_settime|setitimer)\s*\("), "c_cpp", EvidenceKind.CALL),

    # Logging & Telemetry
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"\b(?:syslog|openlog|closelog)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"spdlog::(?:info|warn|error|debug)|BOOST_LOG"), "c_cpp", EvidenceKind.CALL),
    ("foundation.logging", SignalKind.PRESENCE, re.compile(r"<syslog\.h>|<spdlog/spdlog\.h>"), "c_cpp", EvidenceKind.IMPORT),

    # Memory Management & Resource Safety
    ("foundation.memory", SignalKind.PRESENCE, re.compile(r"\b(?:malloc|calloc|realloc|free|posix_memalign)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("foundation.memory", SignalKind.PRESENCE, re.compile(r"std::make_shared|std::make_unique|std::shared_ptr|std::unique_ptr"), "c_cpp", EvidenceKind.INSTANTIATION),

    # Embedded & Kernel / RTOS Patterns
    ("architecture.embedded", SignalKind.PRESENCE, re.compile(r"\b(?:module_init|module_exit|printk)\s*\("), "c_cpp", EvidenceKind.FRAMEWORK_MARKER),
    ("architecture.embedded", SignalKind.PRESENCE, re.compile(r"<linux/module\.h>|<linux/kernel\.h>|<linux/init\.h>"), "c_cpp", EvidenceKind.IMPORT),
    ("architecture.embedded", SignalKind.PRESENCE, re.compile(r"\b(?:xTaskCreate|vTaskStartScheduler|xQueueCreate|vTaskDelay)\s*\("), "c_cpp", EvidenceKind.CALL),
    ("architecture.embedded", SignalKind.PRESENCE, re.compile(r"<FreeRTOS\.h>|<task\.h>|<queue\.h>"), "c_cpp", EvidenceKind.IMPORT),

    # Configuration & Environment
    ("foundation.config", SignalKind.PRESENCE, re.compile(r"\b(?:getenv|setenv)\s*\("), "c_cpp", EvidenceKind.ENV_VAR),

    # Health & Diagnostics
    ("foundation.health-checks", SignalKind.PRESENCE, re.compile(r"[\"']/(?:health|healthz|ping|status)[\"']"), "c_cpp", EvidenceKind.CALL),

    # Buffer / Memory Manipulation
    ("security.buffer-overflow", SignalKind.WEAKNESS, re.compile(r"\b(?:gets|strcpy|strcat|sprintf|vsprintf)\s*\("), "c_cpp", EvidenceKind.CALL),

    # CLI & Tooling
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"<getopt\.h>"), "c_cpp", EvidenceKind.IMPORT),
    ("tooling.cli", SignalKind.PRESENCE, re.compile(r"\b(?:getopt|getopt_long|getopt_long_only)\s*\("), "c_cpp", EvidenceKind.CALL),

    # Graphics, Game Dev & Media
    ("game-dev.graphics", SignalKind.PRESENCE, re.compile(r"<GL/gl\.h>|<GLFW/glfw3\.h>|<SDL2/SDL\.h>|<vulkan/vulkan\.h>"), "c_cpp", EvidenceKind.IMPORT),
    ("game-dev.graphics", SignalKind.PRESENCE, re.compile(r"\b(?:SDL_Init|glfwCreateWindow|vkCreateInstance|glDrawArrays)\s*\("), "c_cpp", EvidenceKind.CALL),

    # Cryptography & SSL
    ("security.crypto", SignalKind.PRESENCE, re.compile(r"<openssl/(?:ssl|evp|sha|aes)\.h>"), "c_cpp", EvidenceKind.IMPORT),
    ("security.crypto", SignalKind.PRESENCE, re.compile(r"\b(?:SSL_connect|SSL_accept|EVP_DigestInit|EVP_EncryptInit)\s*\("), "c_cpp", EvidenceKind.CALL),

    # High-Performance Serialization & RPC
    ("networking.rpc", SignalKind.PRESENCE, re.compile(r"<grpcpp/grpcpp\.h>|google/protobuf/message\.h"), "c_cpp", EvidenceKind.IMPORT),
    ("networking.rpc", SignalKind.PRESENCE, re.compile(r"grpc::CreateChannel|grpc::ServerBuilder"), "c_cpp", EvidenceKind.CALL),
]

C_CPP_SECRET_RE = re.compile(
    r"""(?:api[_-]?key|secret|password|token)\s*\[?\s*\]?\s*=\s*["'][A-Za-z0-9_\-+/]{12,}["']""",
    re.IGNORECASE,
)


def discover_c_cpp_files(
    root: Path | str,
    exclude_dirs: Set[str] | None = None,
) -> List[Path]:
    """Discover all C/C++ files (.c, .h, .cpp, .cc, .cxx, .hpp) under root."""
    base = Path(root)
    if not base.exists() or not base.is_dir():
        return []

    effective_excludes = DEFAULT_EXCLUDE_DIRS | (exclude_dirs or set())
    discovered: List[Path] = []
    extensions = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp"}

    for path in base.rglob("*"):
        if path.is_file() and path.suffix.lower() in extensions:
            parts = set(path.parts)
            if not (parts & effective_excludes):
                discovered.append(path)

    return sorted(discovered)


def _extract_c_cpp_scope(lines: list[str], line_idx: int) -> str | None:
    """Find enclosing function or class definition."""
    fn_re = re.compile(r"^[A-Za-z_][\w:*&<>\s]+?\s+([A-Za-z_]\w*)\s*\([^;]*\)\s*\{?")
    for idx in range(line_idx, -1, -1):
        line = lines[idx].strip()
        m = fn_re.match(line)
        if m and not line.startswith("return") and not line.startswith("if"):
            return m.group(1)
    return None


def _scan_c_cpp_file(file_path: Path) -> List[Signal]:
    """Scan a C/C++ file and return detected Signal objects (legacy compatibility)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    signals: List[Signal] = []

    for concept_id, kind, pattern, lang, _ev_kind in C_CPP_PATTERNS:
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
        if C_CPP_SECRET_RE.search(line):
            signals.append(
                Signal(
                    concept_id="security.secrets-management",
                    kind=SignalKind.WEAKNESS,
                    file_path=file_path,
                    line_range=(idx, idx),
                    evidence=f"[WEAKNESS] Hardcoded credential: {line.strip()[:100]}",
                    confidence=0.9,
                    metadata={"language": "c_cpp"},
                )
            )

    return signals


def _scan_c_cpp_evidence(file_path: Path) -> List[EvidenceFact]:
    """Scan a single C/C++ file and return native EvidenceFacts."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    lines = content.splitlines()
    facts: List[EvidenceFact] = []

    detected_library: str | None = None
    if "pthread" in content:
        detected_library = "pthread"
    elif "FreeRTOS" in content:
        detected_library = "FreeRTOS"
    elif "spdlog" in content:
        detected_library = "spdlog"

    for concept_id, _sig_kind, pattern, _lang, ev_kind in C_CPP_PATTERNS:
        for idx, line in enumerate(lines, start=1):
            m = pattern.search(line)
            if m:
                matched_snippet = line.strip()[:200]
                scope = _extract_c_cpp_scope(lines, idx - 1)
                subject = m.group(0).strip("()<>;")

                timeout_observed = True if "SO_RCVTIMEO" in line or "SO_SNDTIMEO" in line or "alarm(" in line else None

                facts.append(
                    EvidenceFact(
                        kind=ev_kind,
                        subject=subject,
                        language="c_cpp",
                        file_path=file_path,
                        line_range=(idx, idx),
                        snippet=matched_snippet,
                        scope=scope,
                        library=detected_library,
                        extraction_confidence=0.95,
                        identifier_hints=(concept_id, "c_cpp"),
                        timeout_observed=timeout_observed,
                    )
                )

    for idx, line in enumerate(lines, start=1):
        if C_CPP_SECRET_RE.search(line):
            scope = _extract_c_cpp_scope(lines, idx - 1)
            facts.append(
                EvidenceFact(
                    kind=EvidenceKind.CONFIG_KEY,
                    subject="hardcoded_credential",
                    language="c_cpp",
                    file_path=file_path,
                    line_range=(idx, idx),
                    snippet=line.strip()[:200],
                    scope=scope,
                    extraction_confidence=0.9,
                    identifier_hints=("security.secrets-management", "credential"),
                )
            )

    return facts


def scan_c_cpp_project_evidence(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileEvidence]:
    """Scan a C/C++ project and return FileEvidence per file."""
    files = discover_c_cpp_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileEvidence] = []
    for f in files:
        facts = _scan_c_cpp_evidence(f)
        if facts:
            results.append(FileEvidence(file=str(f), facts=tuple(facts)))
    return results


def scan_c_cpp_project(
    target_root: str | Path,
    exclude_dirs: Set[str] | None = None,
) -> List[FileSignals]:
    """Scan a C/C++ project and return FileSignals per file (legacy)."""
    files = discover_c_cpp_files(target_root, exclude_dirs=exclude_dirs)
    results: List[FileSignals] = []
    for f in files:
        sigs = _scan_c_cpp_file(f)
        if sigs:
            results.append(FileSignals(file=str(f), signals=sigs))
    return results


class CCppScanner:
    """Authoritative C and C++ source code scanner for SDAT.

    Scans C/C++ codebases for POSIX system APIs, socket networking, pthreads,
    IPC, memory management, and embedded/RTOS patterns.
    Conforms to the LanguageScanner protocol.
    """

    language_id: str = "c_cpp"
    file_extensions: tuple[str, ...] = (".c", ".h", ".cpp", ".cc", ".cxx", ".hpp")

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: Set[str] | None = None,
    ) -> List[Path]:
        return discover_c_cpp_files(root, exclude_dirs=exclude_dirs)

    def scan_file_evidence(self, file_path: Path | str) -> List[EvidenceFact]:
        return _scan_c_cpp_evidence(Path(file_path))

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
        return scan_c_cpp_project_evidence(root, exclude_dirs=exclude_dirs)

    def scan_file(self, file_path: Path | str) -> List[Signal]:
        return _scan_c_cpp_file(Path(file_path))

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
        return scan_c_cpp_project(root, exclude_dirs=exclude_dirs)
