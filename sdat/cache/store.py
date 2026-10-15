"""SDAT Cache & Deduplication Subsystem.

Provides deterministic, thread-safe in-memory and persistent caching for:
- File-level scanner results (keyed by file content SHA-256 hash)
- Agent concept evaluation results (keyed by EvidenceBundle hash)
- Deduplication of redundant tasks

Security & Invariant Enforcement (SECURITY.md Boundary T-4):
- Automatic secret and credential sanitization before writing to cache
- Private keys, mnemonics, and hardcoded API tokens are redacted
- Cache schema versioning (CACHE_VERSION) to invalidate incompatible entries
- Safe handling of corrupted persistent cache files without audit termination
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Any, Optional

from sdat.telemetry.tracker import AuditTelemetry

# Regex pattern detecting secret assignments for cache sanitization
SECRET_PATTERN = re.compile(
    r"(?i)((?:api[_-]?key|secret|password|token|mnemonic|private[_-]?key|credential)\s*[:=]\s*['\"])[^'\"]{8,}(['\"])",
)
TOKEN_PATTERN = re.compile(
    r"\b(?:sk-[a-zA-Z0-9_\-]{10,}|ghp_[a-zA-Z0-9]{20,}|xox[baprs]-[a-zA-Z0-9\-]{10,})\b"
)
PEM_PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----",
)


class ContentCache:
    """Thread-safe content-hashed cache with versioning, security sanitization, and persistence."""

    CACHE_VERSION: str = "v1"

    def __init__(self, cache_dir: Optional[Path | str] = None, telemetry: Optional[AuditTelemetry] = None) -> None:
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.telemetry = telemetry
        self._lock = threading.Lock()
        self._memory_cache: dict[str, Any] = {}

        if self.cache_dir:
            try:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.cache_dir = None

    @staticmethod
    def hash_content(content: str | bytes) -> str:
        """Compute SHA-256 hash of text or binary content."""
        if isinstance(content, str):
            content = content.encode("utf-8", errors="replace")
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def hash_file(file_path: Path | str) -> str:
        """Compute SHA-256 hash of a file's contents."""
        path = Path(file_path)
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return ""

    @classmethod
    def sanitize_for_cache(cls, data: Any) -> Any:
        """Recursively sanitize data to guarantee no plaintext secrets are stored in cache."""
        if isinstance(data, str):
            sanitized = SECRET_PATTERN.sub(r"\1[REDACTED_SECRET]\2", data)
            sanitized = TOKEN_PATTERN.sub("[REDACTED_SECRET]", sanitized)
            return PEM_PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", sanitized)
        elif isinstance(data, dict):
            clean_dict: dict[str, Any] = {}
            for k, v in data.items():
                if isinstance(k, str) and any(
                    s in k.lower() for s in ("password", "private_key", "secret", "mnemonic", "seed", "api_key", "token", "credential", "auth")
                ):
                    clean_dict[k] = "[REDACTED_SECRET]"
                else:
                    clean_dict[k] = cls.sanitize_for_cache(v)
            return clean_dict
        elif isinstance(data, list):
            return [cls.sanitize_for_cache(item) for item in data]
        elif isinstance(data, tuple):
            return tuple(cls.sanitize_for_cache(item) for item in data)
        return data

    def get(self, key: str) -> Any | None:
        """Retrieve cached value by key. Updates telemetry if configured."""
        with self._lock:
            # 1. Check in-memory cache
            if key in self._memory_cache:
                if self.telemetry:
                    self.telemetry.record_cache_hit()
                return self._memory_cache[key]

            # 2. Check persistent disk cache
            if self.cache_dir:
                file_path = self.cache_dir / f"{key}.json"
                if file_path.exists():
                    try:
                        raw = json.loads(file_path.read_text(encoding="utf-8"))
                        if isinstance(raw, dict) and raw.get("__sdat_cache_version__") == self.CACHE_VERSION:
                            data = raw.get("payload")
                            self._memory_cache[key] = data
                            if self.telemetry:
                                self.telemetry.record_cache_hit()
                            return data
                        else:
                            # Incompatible or unversioned cache entry -> invalidate safely
                            try:
                                file_path.unlink()
                            except OSError:
                                pass
                    except (OSError, json.JSONDecodeError):
                        # Corrupted file -> remove safely
                        try:
                            file_path.unlink()
                        except OSError:
                            pass

            if self.telemetry:
                self.telemetry.record_cache_miss()
            return None

    def put(self, key: str, value: Any) -> None:
        """Store sanitized value in memory and optionally on disk."""
        sanitized_value = self.sanitize_for_cache(value)
        with self._lock:
            self._memory_cache[key] = sanitized_value

            if self.cache_dir:
                file_path = self.cache_dir / f"{key}.json"
                try:
                    payload = {
                        "__sdat_cache_version__": self.CACHE_VERSION,
                        "key": key,
                        "payload": sanitized_value,
                    }
                    file_path.write_text(json.dumps(payload), encoding="utf-8")
                except OSError:
                    pass

    def has(self, key: str) -> bool:
        """Check whether a key exists in memory or disk cache without telemetry mutation."""
        with self._lock:
            if key in self._memory_cache:
                return True
            if self.cache_dir:
                return (self.cache_dir / f"{key}.json").exists()
            return False

    def clear(self) -> None:
        """Clear memory cache and remove persistent files."""
        with self._lock:
            self._memory_cache.clear()
            if self.cache_dir and self.cache_dir.exists():
                for f in self.cache_dir.glob("*.json"):
                    try:
                        f.unlink()
                    except OSError:
                        pass
