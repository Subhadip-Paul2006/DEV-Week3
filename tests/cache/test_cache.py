"""Unit tests for SDAT Content-Hashed Cache Subsystem."""

from __future__ import annotations

from pathlib import Path

from sdat.cache.store import ContentCache
from sdat.telemetry.tracker import AuditTelemetry


def test_content_hashing():
    h1 = ContentCache.hash_content("hello system design")
    h2 = ContentCache.hash_content("hello system design")
    h3 = ContentCache.hash_content("different text")

    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_in_memory_cache_hit_and_miss():
    telem = AuditTelemetry()
    cache = ContentCache(telemetry=telem)

    assert cache.get("missing_key") is None
    assert telem.cache_misses == 1
    assert telem.cache_hits == 0

    cache.put("my_key", {"data": [1, 2, 3]})
    assert cache.has("my_key") is True

    retrieved = cache.get("my_key")
    assert retrieved == {"data": [1, 2, 3]}
    assert telem.cache_hits == 1


def test_persistent_disk_cache(tmp_path: Path):
    telem = AuditTelemetry()
    cache_dir = tmp_path / ".sdat_cache"
    cache1 = ContentCache(cache_dir=cache_dir, telemetry=telem)

    sample_file = tmp_path / "sample.py"
    sample_file.write_text("import redis\nclient = redis.Redis()", encoding="utf-8")
    file_hash = ContentCache.hash_file(sample_file)

    cache1.put(file_hash, [{"subject": "redis", "kind": "import"}])
    assert telem.cache_hits == 0

    # Create a fresh cache instance pointing to the same disk directory
    cache2 = ContentCache(cache_dir=cache_dir, telemetry=telem)
    retrieved = cache2.get(file_hash)

    assert retrieved == [{"subject": "redis", "kind": "import"}]
    assert telem.cache_hits == 1

    cache2.clear()
    assert cache2.get(file_hash) is None
    assert telem.cache_misses == 1


def test_cache_security_redaction(tmp_path: Path):
    """Verify secrets and private keys are never persisted in plaintext."""
    cache_dir = tmp_path / ".sdat_cache"
    cache = ContentCache(cache_dir=cache_dir)

    secret_payload = {
        "api_key": "sk-live-1234567890abcdef",
        "nested": [
            "password = 'SuperSecretPassword123'",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----",
        ],
    }
    cache.put("secret_task", secret_payload)

    # Read the raw file from disk
    raw_file = cache_dir / "secret_task.json"
    assert raw_file.exists()
    disk_content = raw_file.read_text(encoding="utf-8")

    # Assert raw secrets are NOT in the file
    assert "sk-live-1234567890abcdef" not in disk_content
    assert "SuperSecretPassword123" not in disk_content
    assert "MIIEowIBAAKCAQEA0" not in disk_content

    # Assert redacted indicators are present
    assert "[REDACTED_SECRET]" in disk_content
    assert "[REDACTED_PRIVATE_KEY]" in disk_content


def test_cache_version_invalidation(tmp_path: Path):
    """Verify cache version change invalidates incompatible entries."""
    cache_dir = tmp_path / ".sdat_cache"
    cache_v1 = ContentCache(cache_dir=cache_dir)
    cache_v1.put("task_key", {"data": 42})

    # Assert v1 can retrieve it
    assert cache_v1.get("task_key") == {"data": 42}

    # Simulate version bump by temporarily overriding CACHE_VERSION
    original_version = ContentCache.CACHE_VERSION
    try:
        ContentCache.CACHE_VERSION = "v2"
        cache_v2 = ContentCache(cache_dir=cache_dir)
        # Old v1 entry must be treated as miss and invalidated
        assert cache_v2.get("task_key") is None
    finally:
        ContentCache.CACHE_VERSION = original_version


def test_cache_corruption_resilience(tmp_path: Path):
    """Verify corrupted cache files are handled safely as misses without raising errors."""
    cache_dir = tmp_path / ".sdat_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    corrupted_file = cache_dir / "corrupted_task.json"
    corrupted_file.write_text("{invalid_json: truncated...", encoding="utf-8")

    cache = ContentCache(cache_dir=cache_dir)
    assert cache.get("corrupted_task") is None
    # Corrupted file is cleaned up safely
    assert not corrupted_file.exists()

