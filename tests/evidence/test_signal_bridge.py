"""Tests for SignalBridge bidirectional translation between Signal and EvidenceFact."""

from __future__ import annotations

from pathlib import Path

from sdat.models import (
    EvidenceFact,
    EvidenceKind,
    Signal,
    SignalBridge,
    SignalKind,
)


class TestSignalBridge:
    """Validate legacy Signal <-> EvidenceFact conversions."""

    def test_legacy_presence_signal_to_evidence_fact(self):
        sig = Signal(
            concept_id="foundation.caching",
            kind=SignalKind.PRESENCE,
            file_path=Path("app/cache.py"),
            line_range=(3, 3),
            evidence="import redis",
            confidence=0.7,
            metadata={"language": "python", "library": "redis"},
        )
        fact = SignalBridge.to_evidence_fact(sig)
        assert fact.subject == "foundation.caching"
        assert fact.kind == EvidenceKind.LEGACY_SIGNAL
        assert fact.language == "python"
        assert fact.file_path == Path("app/cache.py")
        assert fact.line_range == (3, 3)
        assert fact.snippet == "import redis"
        assert fact.extraction_confidence == 0.7
        assert fact.library == "redis"

    def test_legacy_absence_signal_to_evidence_fact(self):
        sig = Signal(
            concept_id="foundation.circuit-breaker",
            kind=SignalKind.ABSENCE,
            file_path=Path("app/client.py"),
            line_range=(1, 1),
            evidence="(not found in this file)",
            confidence=0.3,
            metadata={"language": "python"},
        )
        fact = SignalBridge.to_evidence_fact(sig)
        assert fact.kind == EvidenceKind.ABSENT_PATTERN
        assert fact.subject == "foundation.circuit-breaker"
        assert fact.extraction_confidence == 0.3

    def test_legacy_config_signal_to_evidence_fact(self):
        sig = Signal(
            concept_id="foundation.config",
            kind=SignalKind.CONFIG,
            file_path=Path(".env"),
            line_range=(1, 1),
            evidence="DATABASE_URL=postgres://localhost",
            confidence=0.9,
            metadata={"language": "text"},
        )
        fact = SignalBridge.to_evidence_fact(sig)
        assert fact.kind == EvidenceKind.CONFIG_KEY
        assert fact.snippet == "DATABASE_URL=postgres://localhost"

    def test_evidence_fact_to_legacy_signal(self):
        fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="client.set",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(15, 15),
            snippet="client.set('key', val)",
            extraction_confidence=0.95,
            call_target="redis.Redis.set",
            ttl_observed=False,
            library="redis",
        )
        sig = SignalBridge.to_legacy_signal(fact, concept_id="foundation.caching")
        assert sig.concept_id == "foundation.caching"
        assert sig.kind == SignalKind.PRESENCE
        assert sig.file_path == Path("app/cache.py")
        assert sig.line_range == (15, 15)
        assert sig.evidence == "client.set('key', val)"
        assert sig.confidence == 0.95
        assert sig.metadata["call_target"] == "redis.Redis.set"
        assert sig.metadata["ttl_observed"] is False
        assert sig.metadata["library"] == "redis"

    def test_round_trip_preserves_metadata(self):
        fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="requests.get",
            language="python",
            file_path=Path("app/service.py"),
            line_range=(42, 42),
            snippet="requests.get('https://api.example.com', timeout=10)",
            extraction_confidence=0.88,
            call_target="requests.get",
            timeout_observed=True,
            scope="fetch_data",
        )
        sig = SignalBridge.to_legacy_signal(fact, concept_id="resilience.timeout")
        recovered_fact = SignalBridge.to_evidence_fact(sig)

        assert recovered_fact.file_path == fact.file_path
        assert recovered_fact.line_range == fact.line_range
        assert recovered_fact.snippet == fact.snippet
        assert recovered_fact.extraction_confidence == fact.extraction_confidence
        assert recovered_fact.timeout_observed is True
        assert recovered_fact.scope == "fetch_data"
        assert recovered_fact.call_target == "requests.get"
