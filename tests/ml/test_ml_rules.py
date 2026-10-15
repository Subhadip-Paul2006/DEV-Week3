"""Comprehensive unit tests for SDAT Machine Learning Stage-1 Rules.

Tests:
- ML-MATH-01: Double Softmax before CrossEntropyLoss
- ML-MATH-02: Log-Sum-Exp Stability
- ML-SCHED-01: Scheduler Step Ordering
- ML-SEC-01: Unsafe Model Deserialization

Coverage per rule:
A. Positive violating fixture
B. Positive valid fixture
C. Name-independent fixture
D. Comment-only negative fixture
E. Ambiguous fixture -> UNKNOWN
F. Valid alternative architecture

Invariants tested:
- No false positives from names
- No false positives from comments
- Deterministic repeat execution
- Secret redaction guarantees
- Line-level evidence provenance
- Multi-dimensional scoring
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sdat.ml.knowledge_pack import MLKnowledgePack
from sdat.ml.models import RuleStatus
from sdat.ml.scoring import MLScoringEngine
from sdat.models import DecisionStatus, Priority


@pytest.fixture
def ml_kp() -> MLKnowledgePack:
    return MLKnowledgePack()


@pytest.fixture
def scoring_engine() -> MLScoringEngine:
    return MLScoringEngine()


# =============================================================================
# 1. ML-MATH-01: Double Softmax Tests (A - F)
# =============================================================================


def test_ml_math_01_a_violating_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: F.softmax output passed into F.cross_entropy."""
    code = """
import torch
import torch.nn.functional as F

def compute_loss(logits, targets):
    probs = F.softmax(logits, dim=-1)
    loss = F.cross_entropy(probs, targets)
    return loss
"""
    (tmp_path / "train_bad.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-01")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.status == DecisionStatus.MISCONFIGURED
    assert res.rule.priority == Priority.CRITICAL
    assert len(res.evidence) >= 1
    assert res.evidence[0].line > 0
    assert "Double Softmax" in (res.misconfiguration or "")


def test_ml_math_01_b_valid_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: raw logits passed directly into F.cross_entropy."""
    code = """
import torch.nn.functional as F

def compute_loss(logits, targets):
    return F.cross_entropy(logits, targets)
"""
    (tmp_path / "train_good.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-01")
    assert res.status == RuleStatus.PASS
    assert res.status == DecisionStatus.IMPLEMENTED
    assert len(res.evidence) == 0


def test_ml_math_01_c_name_independent_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obfuscated helper still caught by AST dataflow."""
    code = """
import torch

def _x(_a, _b):
    _p = torch.softmax(_a, dim=-1)
    return torch.nn.functional.cross_entropy(_p, _b)
"""
    (tmp_path / "obfuscated.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-01")
    assert res.status == RuleStatus.MISCONFIGURED
    assert len(res.evidence) >= 1


def test_ml_math_01_d_comment_only_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments mentioning rule terms do not create findings."""
    code = """
# In this function we must avoid double softmax before cross_entropy loss
def calculate_score(a, b):
    return a * b + 10
"""
    (tmp_path / "comments_only.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-01")
    assert res.status == RuleStatus.UNKNOWN
    assert len(res.evidence) == 0


def test_ml_math_01_e_ambiguous_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: codebase with no loss calculation returns UNKNOWN."""
    code = """
def simple_add(x, y):
    return x + y
"""
    (tmp_path / "math_utils.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-01")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_math_01_f_valid_alternative_architecture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """F. Valid alternative: log_softmax with NLLLoss (mathematically correct)."""
    code = """
import torch
import torch.nn.functional as F

def compute_loss(logits, targets):
    log_probs = F.log_softmax(logits, dim=-1)
    return F.nll_loss(log_probs, targets)
"""
    (tmp_path / "nll_loss_arch.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-01")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 2. ML-MATH-02: Log-Sum-Exp Stability Tests (A - F)
# =============================================================================


def test_ml_math_02_a_violating_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: unstabilized manual log(sum(exp(x)))."""
    code = """
import torch

def custom_log_partition(x):
    return torch.log(torch.sum(torch.exp(x)))
"""
    (tmp_path / "partition.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-02")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.rule.priority == Priority.HIGH
    assert len(res.evidence) >= 1
    assert "log-sum-exp" in (res.misconfiguration or "").lower()


def test_ml_math_02_b_valid_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: stabilized torch.logsumexp."""
    code = """
import torch

def stable_log_partition(x):
    return torch.logsumexp(x, dim=-1)
"""
    (tmp_path / "stable_partition.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-02")
    assert res.status == RuleStatus.PASS


def test_ml_math_02_c_name_independent_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obscure function name with unstable logsumexp."""
    code = """
import torch

def _foo(_z):
    return torch.log(torch.sum(torch.exp(_z)))
"""
    (tmp_path / "obscure.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-02")
    assert res.status == RuleStatus.MISCONFIGURED


def test_ml_math_02_d_comment_only_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments mentioning log(sum(exp(x))) do not create findings."""
    code = """
# Compute log(sum(exp(x))) with extreme precision
def compute_val(x):
    return x * 2.0
"""
    (tmp_path / "comment.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-02")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_math_02_e_ambiguous_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: general math without log-partition returns UNKNOWN."""
    code = """
import math

def get_log(x):
    return math.log(x)
"""
    (tmp_path / "unrelated_math.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-02")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_math_02_f_valid_alternative_architecture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """F. Valid alternative: manual max-subtraction stabilization."""
    code = """
import torch

def stabilized_log_partition(x):
    c = torch.max(x)
    return c + torch.log(torch.sum(torch.exp(x - c)))
"""
    (tmp_path / "max_sub.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-MATH-02")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 3. ML-SCHED-01: Scheduler Step Order Tests (A - F)
# =============================================================================


def test_ml_sched_01_a_violating_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: scheduler.step() called before optimizer.step()."""
    code = """
def train_epoch(model, dataloader, optimizer, scheduler):
    for batch in dataloader:
        optimizer.zero_grad()
        loss = model(batch)
        loss.backward()
        scheduler.step()
        optimizer.step()
"""
    (tmp_path / "trainer_bad.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SCHED-01")
    assert res.status == RuleStatus.MISCONFIGURED
    assert "Invalid scheduler step order" in (res.misconfiguration or "")
    assert len(res.evidence) >= 1
    assert res.evidence[0].line > 0


def test_ml_sched_01_b_valid_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: optimizer.step() followed by scheduler.step()."""
    code = """
def train_epoch(model, dataloader, optimizer, scheduler):
    for batch in dataloader:
        optimizer.zero_grad()
        loss = model(batch)
        loss.backward()
        optimizer.step()
        scheduler.step()
"""
    (tmp_path / "trainer_good.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SCHED-01")
    assert res.status == RuleStatus.PASS


def test_ml_sched_01_c_name_independent_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obfuscated function names with inverted step order."""
    code = """
def _proc(_opt, _sched):
    for _ in range(10):
        _sched.step()
        _opt.step()
"""
    (tmp_path / "step_fn.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SCHED-01")
    assert res.status == RuleStatus.MISCONFIGURED


def test_ml_sched_01_d_comment_only_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comment mentioning scheduler.step() does not create evidence."""
    code = """
# Make sure scheduler.step() is called after optimizer.step()
def run_loop(items):
    for item in items:
        print(item)
"""
    (tmp_path / "comments.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SCHED-01")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_sched_01_e_ambiguous_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: only optimizer.step() present (no scheduler) returns UNKNOWN."""
    code = """
def train_step(model, batch, optimizer):
    loss = model(batch)
    loss.backward()
    optimizer.step()
"""
    (tmp_path / "optimizer_only.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SCHED-01")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_sched_01_f_valid_alternative_architecture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """F. Valid alternative: optimizer inside batch loop, scheduler at epoch boundary."""
    code = """
def train_full(model, dataloader, optimizer, scheduler, epochs):
    for epoch in range(epochs):
        for batch in dataloader:
            optimizer.step()
        scheduler.step()
"""
    (tmp_path / "epoch_scheduler.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SCHED-01")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 4. ML-SEC-01: Unsafe Model Deserialization Tests (A - F)
# =============================================================================


def test_ml_sec_01_a_violating_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: unsafe pickle.load or torch.load without weights_only=True."""
    code = """
import pickle
import torch

def load_weights(path):
    w = torch.load(path, weights_only=False)
    with open("meta.pkl", "rb") as f:
        meta = pickle.load(f)
    return w, meta
"""
    (tmp_path / "loader_bad.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SEC-01")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.rule.priority == Priority.CRITICAL
    assert len(res.evidence) >= 1
    assert "Unsafe model deserialization" in (res.misconfiguration or "")


def test_ml_sec_01_b_valid_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: torch.load with explicit weights_only=True."""
    code = """
import torch

def load_safe(path):
    return torch.load(path, weights_only=True)
"""
    (tmp_path / "loader_good.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SEC-01")
    assert res.status == RuleStatus.PASS


def test_ml_sec_01_c_name_independent_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obfuscated function calling pickle.loads."""
    code = """
import pickle

def _unserialize(_b):
    return pickle.loads(_b)
"""
    (tmp_path / "unserialize.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SEC-01")
    assert res.status == RuleStatus.MISCONFIGURED


def test_ml_sec_01_d_comment_only_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments discussing pickle do not create security findings."""
    code = """
# Never use pickle.load or torch.load without weights_only=True
def read_json_model(path):
    import json
    return json.load(open(path))
"""
    (tmp_path / "safe_comments.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SEC-01")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_sec_01_e_ambiguous_fixture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: codebase with standard file read (no deserializer) returns UNKNOWN."""
    code = """
def read_config(path):
    with open(path, "r") as f:
        return f.read()
"""
    (tmp_path / "reader.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SEC-01")
    assert res.status == RuleStatus.UNKNOWN


def test_ml_sec_01_f_valid_alternative_architecture(ml_kp: MLKnowledgePack, tmp_path: Path):
    """F. Valid alternative: safetensors model deserialization."""
    code = """
import safetensors.torch

def load_checkpoint(filepath):
    return safetensors.torch.load_file(filepath)
"""
    (tmp_path / "safetensors_loader.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "ML-SEC-01")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 5. Domain Invariants & Additional Verifications
# =============================================================================


def test_misleading_names_not_flagged_as_ml(ml_kp: MLKnowledgePack, tmp_path: Path):
    """Names are clues, behavior is evidence: UserModel and Redis pipeline must not trigger ML defects."""
    code = """
class UserModel:
    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email

def execute_pipeline(redis_client):
    pipeline = redis_client.pipeline()
    pipeline.set("user:1", "active")
    pipeline.execute()
"""
    (tmp_path / "database_models.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    for r in results:
        assert r.status == RuleStatus.UNKNOWN
        assert len(r.evidence) == 0


def test_secret_hygiene_invariant(ml_kp: MLKnowledgePack, tmp_path: Path):
    """Evidence snippets must never retain API keys or secrets."""
    code = """
import pickle

API_KEY = "sk-live-secret-token-12345"
def load_data(f):
    return pickle.load(f)
"""
    (tmp_path / "secrets.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    for r in results:
        for ev in r.evidence:
            assert "sk-live-secret-token-12345" not in ev.snippet


def test_deterministic_repeat_execution(ml_kp: MLKnowledgePack, tmp_path: Path):
    """Deterministic guarantee: 5 consecutive evaluations on identical inputs produce identical results."""
    code = """
import torch
import torch.nn.functional as F

def step(opt, sched):
    sched.step()
    opt.step()
"""
    (tmp_path / "det.py").write_text(code, encoding="utf-8")

    first_run = ml_kp.evaluate(facts=[], target_root=tmp_path)
    for _ in range(4):
        subsequent_run = ml_kp.evaluate(facts=[], target_root=tmp_path)
        assert len(first_run) == len(subsequent_run)
        for r1, r2 in zip(first_run, subsequent_run, strict=True):
            assert r1.rule.id == r2.rule.id
            assert r1.status == r2.status
            assert r1.confidence == r2.confidence
            assert len(r1.evidence) == len(r2.evidence)


def test_ml_scoring_engine_integration(ml_kp: MLKnowledgePack, scoring_engine: MLScoringEngine, tmp_path: Path):
    """Scoring integration: critical defect lowers score and sets critical status."""
    code = """
import pickle

def load_m(f):
    return pickle.load(f)
"""
    (tmp_path / "server.py").write_text(code, encoding="utf-8")

    results = ml_kp.evaluate(facts=[], target_root=tmp_path)
    dim_scores, overall, status = scoring_engine.compute_scores(results)

    assert overall is not None
    assert overall < 50.0
    assert status == "critical"
    # Ensure to_decisions generates valid canonical Decisions
    decisions = ml_kp.to_decisions(results)
    assert len(decisions) == 4
    sec_dec = next(d for d in decisions if d.concept_id == "ml.serialization-safety")
    assert sec_dec.status == DecisionStatus.MISCONFIGURED
