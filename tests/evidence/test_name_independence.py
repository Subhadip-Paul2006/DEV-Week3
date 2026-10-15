"""Name-independence validation tests for Phase 2.5 Common Evidence Model.

Demonstrates that:
1. Meaningless identifier names (x1, A7, z13, q9.py) still produce rich structural evidence
   when real architectural operations are performed.
2. Misleading identifier names (retryPayment, circuitBreakerFallback) containing keywords
   do NOT fabricate architectural evidence when no real structural pattern exists.
"""

from __future__ import annotations

from pathlib import Path

from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import EvidenceKind
from sdat.scanners.python import PythonScanner


class TestNameIndependence:
    """Validate that AST/structural observations supersede identifier naming."""

    def setup_method(self):
        self.scanner = PythonScanner()
        self.aggregator = EvidenceAggregator()

    def test_meaningless_names_produce_structural_evidence(self, tmp_path: Path):
        code = """
import redis

class A7:
    def __init__(self):
        self.z13 = redis.Redis(host="localhost", port=6379)

    def x1(self, k, v):
        self.z13.set(k, v, ex=300)
        return self.z13.get(k)
"""
        obfuscated_file = tmp_path / "q9.py"
        obfuscated_file.write_text(code, encoding="utf-8")

        facts = self.scanner.scan_file_evidence(obfuscated_file)

        # 1. Structural import verified
        import_facts = [f for f in facts if f.kind == EvidenceKind.IMPORT and f.subject == "redis"]
        assert len(import_facts) >= 1

        # 2. Structural instantiation verified
        inst_facts = [f for f in facts if f.kind == EvidenceKind.INSTANTIATION and f.subject == "Redis"]
        assert len(inst_facts) >= 1
        assert inst_facts[0].call_target == "redis.Redis"

        # 3. Structural call verified with TTL argument extracted
        set_facts = [f for f in facts if f.kind == EvidenceKind.CALL and f.subject == "set"]
        assert len(set_facts) >= 1
        assert set_facts[0].call_target == "self.z13.set"
        assert set_facts[0].ttl_observed is True

        # 4. Aggregator bundles this into caching based on structural facts
        bundles = self.aggregator.bundle_by_concept(facts)
        caching_bundle = next((b for b in bundles if b.concept_id == "foundation.caching"), None)
        assert caching_bundle is not None
        assert len(caching_bundle.facts) >= 3

    def test_misleading_names_do_not_fabricate_architectural_evidence(self, tmp_path: Path):
        code = """
def retryPayment():
    # Looks like retry from identifier, but is completely empty
    pass

def circuitBreakerFallback():
    # Looks like circuit breaker from identifier, but has no resilience logic
    return None
"""
        fake_file = tmp_path / "fake_resilience.py"
        fake_file.write_text(code, encoding="utf-8")

        facts = self.scanner.scan_file_evidence(fake_file)

        # 1. No CALL facts to tenacity, retry, pybreaker, opossum
        call_facts = [f for f in facts if f.kind == EvidenceKind.CALL]
        assert len(call_facts) == 0

        # 2. No DECORATOR facts
        decorator_facts = [f for f in facts if f.kind == EvidenceKind.DECORATOR]
        assert len(decorator_facts) == 0

        # 3. Aggregator bundling: no implementation facts for retries or circuit breaker
        bundles = self.aggregator.bundle_by_concept(facts)
        retry_bundle = next((b for b in bundles if b.concept_id == "foundation.retries"), None)
        cb_bundle = next((b for b in bundles if b.concept_id == "foundation.circuit-breaker"), None)

        assert retry_bundle is None
        assert cb_bundle is None
