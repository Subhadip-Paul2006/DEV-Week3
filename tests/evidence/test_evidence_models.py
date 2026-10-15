"""Tests for Phase 2.5 Common Evidence Model dataclasses and enums."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from sdat.models import (
    EvidenceBundle,
    EvidenceFact,
    EvidenceKind,
    FileEvidence,
)


class TestEvidenceKind:
    """Validate canonical EvidenceKind enum members."""

    def test_structural_kinds_exist(self):
        assert EvidenceKind.IMPORT.value == "import"
        assert EvidenceKind.CALL.value == "call"
        assert EvidenceKind.DECORATOR.value == "decorator"
        assert EvidenceKind.INHERITANCE.value == "inheritance"
        assert EvidenceKind.INSTANTIATION.value == "instantiation"
        assert EvidenceKind.ANNOTATION.value == "annotation"

    def test_behavioral_and_config_kinds_exist(self):
        assert EvidenceKind.CONTROL_FLOW.value == "control_flow"
        assert EvidenceKind.ASYNC_PATTERN.value == "async_pattern"
        assert EvidenceKind.CONCURRENCY.value == "concurrency"
        assert EvidenceKind.CONFIG_KEY.value == "config_key"
        assert EvidenceKind.ENV_VAR.value == "env_var"

    def test_storage_and_absence_kinds_exist(self):
        assert EvidenceKind.DB_QUERY.value == "db_query"
        assert EvidenceKind.SCHEMA_DEF.value == "schema_def"
        assert EvidenceKind.MIGRATION.value == "migration"
        assert EvidenceKind.ABSENT_PATTERN.value == "absent_pattern"
        assert EvidenceKind.LEGACY_SIGNAL.value == "legacy_signal"


class TestEvidenceFact:
    """Validate EvidenceFact behavior, immutability, validation, and serialization."""

    def test_construction_minimal(self):
        fact = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
        )
        assert fact.kind == EvidenceKind.IMPORT
        assert fact.subject == "redis"
        assert fact.language == "python"
        assert fact.file_path == Path("app/cache.py")
        assert fact.line_range == (1, 1)
        assert fact.snippet == "import redis"
        assert fact.extraction_confidence == 1.0
        assert fact.identifier_hints == ()
        assert fact.scope is None

    def test_construction_full(self):
        fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="client.set",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(12, 14),
            snippet="client.set('key', val, ex=60)",
            scope="save_cache",
            call_target="redis.Redis.set",
            call_args_schema="(key: str, val: Any, ex: int)",
            parent_symbol="CacheService",
            value_observed="60",
            value_schema="int",
            extraction_confidence=0.95,
            identifier_hints=("cache", "redis_call"),
            framework="fastapi",
            library="redis",
            ttl_observed=True,
            timeout_observed=None,
            retry_count_observed=None,
            circuit_breaker_threshold=None,
        )
        assert fact.call_target == "redis.Redis.set"
        assert fact.ttl_observed is True
        assert fact.identifier_hints == ("cache", "redis_call")

    def test_immutability(self):
        fact = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
        )
        with pytest.raises(FrozenInstanceError):
            fact.subject = "something_else"  # type: ignore

    def test_confidence_validation(self):
        with pytest.raises(ValueError, match="extraction_confidence"):
            EvidenceFact(
                kind=EvidenceKind.IMPORT,
                subject="redis",
                language="python",
                file_path=Path("app/cache.py"),
                line_range=(1, 1),
                snippet="import redis",
                extraction_confidence=1.5,
            )

        with pytest.raises(ValueError, match="extraction_confidence"):
            EvidenceFact(
                kind=EvidenceKind.IMPORT,
                subject="redis",
                language="python",
                file_path=Path("app/cache.py"),
                line_range=(1, 1),
                snippet="import redis",
                extraction_confidence=-0.1,
            )

    def test_snippet_bounding(self):
        long_snippet = "x" * 500
        fact = EvidenceFact(
            kind=EvidenceKind.CONFIG_KEY,
            subject="SECRET",
            language="python",
            file_path=Path("settings.py"),
            line_range=(5, 5),
            snippet=long_snippet,
        )
        assert len(fact.snippet) == 200

    def test_serialization_round_trip(self):
        fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="requests.get",
            language="python",
            file_path=Path("app/client.py"),
            line_range=(10, 12),
            snippet="requests.get(url, timeout=5)",
            call_target="requests.get",
            timeout_observed=True,
            extraction_confidence=0.9,
            identifier_hints=("http", "client"),
        )
        d = fact.to_dict()
        # Verify JSON serializability
        json_str = json.dumps(d)
        decoded = json.loads(json_str)

        fact2 = EvidenceFact.from_dict(decoded)
        assert fact == fact2
        assert fact2.kind == EvidenceKind.CALL
        assert fact2.file_path == Path("app/client.py")
        assert fact2.line_range == (10, 12)
        assert fact2.timeout_observed is True


class TestFileEvidence:
    """Validate FileEvidence collection."""

    def test_file_evidence_lifecycle(self):
        f1 = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
        )
        fe = FileEvidence(file="app/cache.py", facts=[f1])
        assert fe.file == "app/cache.py"
        assert len(fe.facts) == 1
        assert isinstance(fe.facts, tuple)

        d = fe.to_dict()
        fe2 = FileEvidence.from_dict(d)
        assert fe == fe2


class TestEvidenceBundle:
    """Validate EvidenceBundle packaging and serialization."""

    def test_bundle_creation_and_serialization(self):
        fact = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
        )
        bundle = EvidenceBundle(
            concept_id="foundation.caching",
            facts=[fact],
            peer_patterns=["redis-cache-aside"],
            literature_findings=["Martin Fowler: Cache-Aside pattern"],
        )
        assert bundle.concept_id == "foundation.caching"
        assert len(bundle.facts) == 1
        assert bundle.peer_patterns == ("redis-cache-aside",)
        assert bundle.literature_findings == ("Martin Fowler: Cache-Aside pattern",)

        d = bundle.to_dict()
        bundle2 = EvidenceBundle.from_dict(d)
        assert bundle == bundle2
