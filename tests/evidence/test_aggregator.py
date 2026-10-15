"""Tests for EvidenceAggregator correlation, concept indexing, absence synthesis, and bundling."""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceFact, EvidenceKind


class TestEvidenceAggregator:
    """Validate cross-file, cross-language, absence synthesis, and bundling behaviors."""

    def setup_method(self):
        self.aggregator = EvidenceAggregator()

    def test_same_file_correlation_deduplication(self):
        f1 = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
        )
        f2 = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
        )
        correlated = self.aggregator.correlate([f1, f2])
        assert len(correlated) == 1

    def test_cross_file_correlation(self):
        f_import = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/deps.py"),
            line_range=(1, 1),
            snippet="import redis",
            library="redis",
        )
        f_inst = EvidenceFact(
            kind=EvidenceKind.INSTANTIATION,
            subject="Redis",
            language="python",
            file_path=Path("app/deps.py"),
            line_range=(5, 5),
            snippet="client = redis.Redis(host='localhost')",
            call_target="redis.Redis",
            library="redis",
        )
        f_call = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="get",
            language="python",
            file_path=Path("app/views.py"),
            line_range=(20, 20),
            snippet="data = client.get('user_profile')",
            call_target="client.get",
            library="redis",
        )

        all_facts = [f_import, f_inst, f_call]
        chains = self.aggregator.find_call_chains(all_facts, "redis")
        assert len(chains) == 3
        files_involved = {f.file_path.as_posix() for f in chains}
        assert files_involved == {"app/deps.py", "app/views.py"}

    def test_cross_language_correlation(self):
        py_fact = EvidenceFact(
            kind=EvidenceKind.INSTANTIATION,
            subject="Redis",
            language="python",
            file_path=Path("backend/cache.py"),
            line_range=(5, 5),
            snippet="client = redis.Redis()",
            library="redis",
        )
        ts_fact = EvidenceFact(
            kind=EvidenceKind.INSTANTIATION,
            subject="Redis",
            language="typescript",
            file_path=Path("frontend/server.ts"),
            line_range=(8, 8),
            snippet="const redis = new Redis();",
            library="ioredis",
        )

        bundles = self.aggregator.bundle_by_concept([py_fact, ts_fact])
        caching_bundles = [b for b in bundles if b.concept_id == "foundation.caching"]
        assert len(caching_bundles) == 1
        bundle = caching_bundles[0]
        assert len(bundle.facts) == 2
        langs = {f.language for f in bundle.facts}
        assert langs == {"python", "typescript"}

    def test_absence_synthesis_http_without_timeout(self):
        call_fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="requests.get",
            language="python",
            file_path=Path("app/client.py"),
            line_range=(15, 15),
            snippet="res = requests.get('https://api.external.com/data')",
            call_target="requests.get",
            timeout_observed=False,
        )
        absence_facts = self.aggregator.synthesize_absence([call_fact])
        subjects = [f.subject for f in absence_facts]
        assert "timeout" in subjects
        assert "retries" in subjects

        timeout_absence = next(f for f in absence_facts if f.subject == "timeout")
        assert timeout_absence.kind == EvidenceKind.ABSENT_PATTERN
        assert "without explicit timeout safeguard" in timeout_absence.snippet

    def test_absence_not_synthesized_when_timeout_present(self):
        call_fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="requests.get",
            language="python",
            file_path=Path("app/client.py"),
            line_range=(15, 15),
            snippet="res = requests.get('https://api.external.com/data', timeout=5)",
            call_target="requests.get",
            timeout_observed=True,
        )
        retry_fact = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="tenacity",
            language="python",
            file_path=Path("app/client.py"),
            line_range=(2, 2),
            snippet="import tenacity",
            library="tenacity",
        )
        absence_facts = self.aggregator.synthesize_absence([call_fact, retry_fact])
        assert len(absence_facts) == 0

    def test_absence_not_synthesized_when_no_http_calls_exist(self):
        calc_fact = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="math.sqrt",
            language="python",
            file_path=Path("app/math_util.py"),
            line_range=(5, 5),
            snippet="math.sqrt(4)",
        )
        absence_facts = self.aggregator.synthesize_absence([calc_fact])
        assert len(absence_facts) == 0

    def test_absence_synthesis_cache_write_without_ttl(self):
        cache_write = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="client.set",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(25, 25),
            snippet="client.set('user_123', payload)",
            call_target="client.set",
            ttl_observed=False,
            library="redis",
        )
        absence_facts = self.aggregator.synthesize_absence([cache_write])
        ttl_absence = [f for f in absence_facts if f.subject == "ttl"]
        assert len(ttl_absence) == 1
        assert ttl_absence[0].kind == EvidenceKind.ABSENT_PATTERN
        assert "without explicit TTL expiration" in ttl_absence[0].snippet

    def test_bundle_generation_deterministic_ordering(self):
        f1 = EvidenceFact(
            kind=EvidenceKind.CALL,
            subject="client.get",
            language="python",
            file_path=Path("b_file.py"),
            line_range=(10, 10),
            snippet="client.get('k')",
            library="redis",
        )
        f2 = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("a_file.py"),
            line_range=(1, 1),
            snippet="import redis",
            library="redis",
        )
        bundles1 = self.aggregator.bundle_by_concept([f1, f2])
        bundles2 = self.aggregator.bundle_by_concept([f2, f1])

        # Both orders must produce identical bundle ordering and fact ordering
        assert [b.concept_id for b in bundles1] == [b.concept_id for b in bundles2]
        caching1 = next(b for b in bundles1 if b.concept_id == "foundation.caching")
        caching2 = next(b for b in bundles2 if b.concept_id == "foundation.caching")
        assert [str(f.file_path) for f in caching1.facts] == ["a_file.py", "b_file.py"]
        assert caching1.facts == caching2.facts

    def test_unrelated_facts_remain_unrelated(self):
        redis_fact = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="redis",
            language="python",
            file_path=Path("app/cache.py"),
            line_range=(1, 1),
            snippet="import redis",
            library="redis",
        )
        jwt_fact = EvidenceFact(
            kind=EvidenceKind.IMPORT,
            subject="jwt",
            language="python",
            file_path=Path("app/auth.py"),
            line_range=(1, 1),
            snippet="import jwt",
            library="jwt",
        )
        bundles = self.aggregator.bundle_by_concept([redis_fact, jwt_fact])
        caching_bundle = next((b for b in bundles if b.concept_id == "foundation.caching"), None)
        auth_bundle = next((b for b in bundles if b.concept_id == "foundation.auth"), None)

        assert caching_bundle is not None
        assert auth_bundle is not None
        assert redis_fact in caching_bundle.facts
        assert redis_fact not in auth_bundle.facts
        assert jwt_fact in auth_bundle.facts
        assert jwt_fact not in caching_bundle.facts
