"""Negative Tests for Backend System-Design Auditing.

Strictly verifies the core invariant:
'Names are clues. Behavior is evidence.'

Mandatory negative tests:
1. function named `retryPayment()` without retry behavior -> must NOT create strong retry evidence
2. function named `authenticateUser()` without authentication logic -> must NOT prove authentication
3. file named `cache_service.py` with no cache behavior -> must NOT prove caching
4. file named `api.py` containing unrelated logic -> must NOT prove API architecture
5. comments describing retries -> must NOT establish retry implementation
6. actual retry/backoff structure with meaningless identifiers -> SHOULD be detected
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from sdat.backend.agent import BackendAgent
from sdat.backend.analyzer import BackendStructuralAnalyzer
from sdat.models import DecisionStatus


def test_negative_1_function_named_retryPayment_without_retry_behavior() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "payment.py"
        code_file.write_text(
            """
def retryPayment(payment_id: str):
    # Just a mock payment call with no retry loop, no backoff, no retry decorator
    print("processing payment:", payment_id)
    return {"status": "success"}
""",
            encoding="utf-8",
        )

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze([])

        # The analyzer must NOT detect retries from function name alone
        assert summary.has_retries is False


def test_negative_2_function_named_authenticateUser_without_auth_logic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "auth_helper.py"
        code_file.write_text(
            """
def authenticateUser(name: str):
    # Dummy placeholder function, no token validation, no crypto, no sessions
    return name == "admin"
""",
            encoding="utf-8",
        )

        agent = BackendAgent()
        result = agent.audit({"target_root": str(root), "evidence_facts": []})
        decisions = {d["concept_id"]: d for d in result["decisions"]}

        # Name 'authenticateUser' without middleware or crypto verification must NOT prove auth
        assert decisions["backend.authentication"]["status"] in (DecisionStatus.MISSING.value, DecisionStatus.UNKNOWN.value)


def test_negative_3_file_named_cache_service_py_with_no_cache_behavior() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "cache_service.py"
        code_file.write_text(
            """
# This file is named cache_service.py but merely does arithmetic calculation
def compute_sum(a: int, b: int) -> int:
    return a + b
""",
            encoding="utf-8",
        )

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze([])

        # The analyzer must NOT detect caching from filename alone
        assert summary.has_caching is False


def test_negative_4_file_named_api_py_containing_unrelated_logic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "api.py"
        code_file.write_text(
            """
# This file is named api.py but contains purely mathematical formulas
def calculate_standard_deviation(values: list[float]) -> float:
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5
""",
            encoding="utf-8",
        )

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze([])

        # The analyzer must NOT detect endpoints from filename alone
        assert len(summary.endpoints) == 0


def test_negative_5_comments_describing_retries_do_not_establish_implementation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "network.py"
        code_file.write_text(
            """
def make_call():
    # TODO: Implement exponential backoff retry with jitter
    # We should retry 3 times with 100ms, 200ms, 400ms sleep
    return 200
""",
            encoding="utf-8",
        )

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze([])

        # Comments describing retries must NOT be treated as behavioral retry execution
        assert summary.has_retries is False


def test_negative_6_meaningless_identifiers_with_actual_retry_backoff_is_detected() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        code_file = root / "worker.py"
        code_file.write_text(
            """
import time

def _f1(_p):
    _a = 0
    while _a < 3:
        try:
            return _p()
        except Exception:
            _a += 1
            time.sleep(0.1 * (2 ** _a))
    raise RuntimeError("exhausted")
""",
            encoding="utf-8",
        )

        analyzer = BackendStructuralAnalyzer(root)
        summary = analyzer.analyze([])

        # Even with meaningless identifiers (_f1, _p, _a), actual retry loop with backoff sleep IS detected!
        assert summary.has_retries is True
