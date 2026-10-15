"""Comprehensive unit tests for SDAT Natural Language Processing Stage-1 Rules.

Tests:
- NLP-TENS-01: Attention Head Dimension Divisibility
- NLP-TENS-02: Attention Mask Soundness
- NLP-TOKN-02: Tokenizer / Embedding Vocabulary Alignment
- NLP-SEQL-01: Sequence / Context Bounds

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

from sdat.models import DecisionStatus, Priority
from sdat.nlp.knowledge_pack import NLPKnowledgePack
from sdat.nlp.models import RuleStatus
from sdat.nlp.scoring import NLPScoringEngine


@pytest.fixture
def nlp_kp() -> NLPKnowledgePack:
    return NLPKnowledgePack()


@pytest.fixture
def scoring_engine() -> NLPScoringEngine:
    return NLPScoringEngine()


# =============================================================================
# 1. NLP-TENS-01: Attention Head Divisibility Tests (A - F)
# =============================================================================


def test_nlp_tens_01_a_violating_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: d_model (768) % n_heads (7) != 0."""
    code = """
import torch.nn as nn

class CustomAttention(nn.Module):
    def __init__(self, d_model: int = 768, n_heads: int = 7):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
"""
    (tmp_path / "attention.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-01")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.status == DecisionStatus.MISCONFIGURED
    assert res.rule.priority == Priority.HIGH
    assert len(res.evidence) >= 1
    assert res.evidence[0].line > 0
    assert "not divisible" in res.evidence[0].snippet


def test_nlp_tens_01_b_valid_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: d_model (768) % n_heads (12) == 0."""
    code = """
import torch.nn as nn

class CustomAttention(nn.Module):
    def __init__(self, d_model: int = 768, n_heads: int = 12):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
"""
    (tmp_path / "attention_good.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-01")
    assert res.status == RuleStatus.PASS
    assert res.status == DecisionStatus.IMPLEMENTED
    assert len(res.evidence) == 0


def test_nlp_tens_01_c_name_independent_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: class named MHA with dim=512, heads=7 (indivisible)."""
    code = """
import torch.nn as nn

class MHA(nn.Module):
    def __init__(self, dim: int = 512, heads: int = 7):
        super().__init__()
        self.d_model = dim
        self.n_heads = heads
"""
    (tmp_path / "mha_indivisible.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-01")
    assert res.status == RuleStatus.MISCONFIGURED


def test_nlp_tens_01_d_comment_only_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments discussing indivisible heads do not create findings."""
    code = """
# If d_model % n_heads != 0, projection will fail
def get_layer_count():
    return 12
"""
    (tmp_path / "comments.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-01")
    assert res.status == RuleStatus.UNKNOWN
    assert len(res.evidence) == 0


def test_nlp_tens_01_e_ambiguous_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: Attention class with dynamic config dimensions returns UNKNOWN."""
    code = """
import torch.nn as nn

class ConfigurableAttention(nn.Module):
    def __init__(self, config):
        super().__init__()
        self.d_model = config.hidden_size
        self.n_heads = config.num_attention_heads
"""
    (tmp_path / "dynamic_attn.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-01")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_tens_01_f_valid_alternative_architecture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """F. Valid alternative: explicit head_dim with all_head_size = n_heads * head_dim."""
    code = """
import torch.nn as nn

class ProjectedAttention(nn.Module):
    def __init__(self, n_heads: int = 8, head_dim: int = 64):
        super().__init__()
        self.n_heads = n_heads
        self.head_dim = head_dim
        self.all_head_size = n_heads * head_dim
"""
    (tmp_path / "projected_attn.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-01")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 2. NLP-TENS-02: Attention Mask Soundness Tests (A - F)
# =============================================================================


def test_nlp_tens_02_a_violating_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: masked_fill with 0.0 before softmax."""
    code = """
import torch

def compute_attention(scores, mask):
    masked_scores = scores.masked_fill(mask == 0, 0.0)
    return torch.softmax(masked_scores, dim=-1)
"""
    (tmp_path / "attn_mask_bad.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-02")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.rule.priority == Priority.HIGH
    assert len(res.evidence) >= 1
    assert res.evidence[0].line > 0


def test_nlp_tens_02_b_valid_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: masked_fill with -inf before softmax."""
    code = """
import torch

def compute_attention(scores, mask):
    masked_scores = scores.masked_fill(mask == 0, float("-inf"))
    return torch.softmax(masked_scores, dim=-1)
"""
    (tmp_path / "attn_mask_good.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-02")
    assert res.status == RuleStatus.PASS


def test_nlp_tens_02_c_name_independent_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obfuscated function with 0.0 masked_fill."""
    code = """
import torch

def _mask_calc(_s, _m):
    return torch.softmax(_s.masked_fill(_m, 0.0), dim=-1)
"""
    (tmp_path / "obfuscated_mask.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-02")
    assert res.status == RuleStatus.MISCONFIGURED


def test_nlp_tens_02_d_comment_only_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments discussing attention masks do not create findings."""
    code = """
# Remember that masked_fill(mask == 0, 0.0) is a dangerous bug
def add_vectors(a, b):
    return a + b
"""
    (tmp_path / "mask_comments.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-02")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_tens_02_e_ambiguous_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: general tensor operations without attention masks return UNKNOWN."""
    code = """
import torch

def norm_tensor(x):
    return torch.norm(x, p=2)
"""
    (tmp_path / "tensor_math.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-02")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_tens_02_f_valid_alternative_architecture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """F. Valid alternative: additive mask directly before softmax."""
    code = """
import torch

def additive_attention(scores, additive_mask):
    return torch.softmax(scores + additive_mask, dim=-1)
"""
    (tmp_path / "additive_mask.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TENS-02")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 3. NLP-TOKN-02: Tokenizer Embedding Vocabulary Sync Tests (A - F)
# =============================================================================


def test_nlp_tokn_02_a_violating_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: add_special_tokens called without resize_token_embeddings."""
    code = """
from transformers import AutoTokenizer, AutoModel

def setup_pipeline():
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = AutoModel.from_pretrained("bert-base-uncased")
    tokenizer.add_special_tokens({"additional_special_tokens": ["[TAG]"]})
    return tokenizer, model
"""
    (tmp_path / "pipeline_bad.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TOKN-02")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.rule.priority == Priority.HIGH
    assert len(res.evidence) >= 1
    assert "without model embedding capacity expansion" in (res.misconfiguration or "")


def test_nlp_tokn_02_b_valid_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: add_special_tokens followed by resize_token_embeddings."""
    code = """
from transformers import AutoTokenizer, AutoModel

def setup_pipeline():
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    model = AutoModel.from_pretrained("bert-base-uncased")
    tokenizer.add_special_tokens({"additional_special_tokens": ["[TAG]"]})
    model.resize_token_embeddings(len(tokenizer))
    return tokenizer, model
"""
    (tmp_path / "pipeline_good.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TOKN-02")
    assert res.status == RuleStatus.PASS


def test_nlp_tokn_02_c_name_independent_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obscure function calling add_tokens without resize."""
    code = """
def _mod_tok(_t):
    _t.add_tokens(["token_a", "token_b"])
"""
    (tmp_path / "mod_tok.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TOKN-02")
    assert res.status == RuleStatus.MISCONFIGURED


def test_nlp_tokn_02_d_comment_only_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments discussing add_tokens do not create findings."""
    code = """
# Remember to call resize_token_embeddings after add_tokens
def load_labels():
    return ["pos", "neg"]
"""
    (tmp_path / "vocab_comment.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TOKN-02")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_tokn_02_e_ambiguous_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: tokenizer loaded without token mutations returns UNKNOWN."""
    code = """
from transformers import AutoTokenizer

def get_tokenizer():
    return AutoTokenizer.from_pretrained("bert-base-uncased")
"""
    (tmp_path / "no_vocab_mutation.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TOKN-02")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_tokn_02_f_valid_alternative_architecture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """F. Valid alternative: static tokenizer without dynamic token insertion."""
    code = """
class StaticTokenizerWrapper:
    def __init__(self, vocab_file: str):
        self.vocab = open(vocab_file).read().splitlines()
"""
    (tmp_path / "static_tok.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-TOKN-02")
    assert res.status == RuleStatus.UNKNOWN


# =============================================================================
# 4. NLP-SEQL-01: Sequence Length Bounds Tests (A - F)
# =============================================================================


def test_nlp_seql_01_a_violating_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """A. Positive violating fixture: tokenizer call without truncation and max_length."""
    code = """
def process_user_input(tokenizer, user_text):
    return tokenizer(user_text)
"""
    (tmp_path / "service_bad.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-SEQL-01")
    assert res.status == RuleStatus.MISCONFIGURED
    assert res.rule.priority == Priority.HIGH
    assert len(res.evidence) >= 1
    assert "Unbounded text ingestion" in (res.misconfiguration or "")


def test_nlp_seql_01_b_valid_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """B. Positive valid fixture: tokenizer call with truncation=True and max_length."""
    code = """
def process_user_input(tokenizer, user_text):
    return tokenizer(user_text, truncation=True, max_length=512)
"""
    (tmp_path / "service_good.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-SEQL-01")
    assert res.status == RuleStatus.PASS


def test_nlp_seql_01_c_name_independent_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """C. Name-independent fixture: obfuscated encoding call without bounds."""
    code = """
def _enc(_tok, _txt):
    return _tok.encode(_txt)
"""
    (tmp_path / "obf_enc.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-SEQL-01")
    assert res.status == RuleStatus.MISCONFIGURED


def test_nlp_seql_01_d_comment_only_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """D. Comment-only fixture: comments discussing truncation do not create findings."""
    code = """
# Always pass truncation=True and max_length to avoid OOM
def sanitize_input(text):
    return text.strip()
"""
    (tmp_path / "trunc_comment.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-SEQL-01")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_seql_01_e_ambiguous_fixture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """E. Ambiguous fixture: code with no tokenizer calls returns UNKNOWN."""
    code = """
def count_words(text):
    return len(text.split())
"""
    (tmp_path / "word_counter.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-SEQL-01")
    assert res.status == RuleStatus.UNKNOWN


def test_nlp_seql_01_f_valid_alternative_architecture(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """F. Valid alternative: explicit slice bound on input before tokenizer."""
    code = """
def process_user_input(tokenizer, user_text):
    return tokenizer(user_text[:512])
"""
    (tmp_path / "sliced_input.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    res = next(r for r in results if r.rule.id == "NLP-SEQL-01")
    assert res.status == RuleStatus.PASS


# =============================================================================
# 5. Domain Invariants & Additional Verifications
# =============================================================================


def test_misleading_names_not_flagged_as_nlp(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """Names are clues, behavior is evidence: credit card tokenization in auth must not trigger NLP rules."""
    code = """
import hashlib

def tokenize_credit_card(card_number: str) -> str:
    salt = "secure_salt"
    return hashlib.sha256((card_number + salt).encode()).hexdigest()
"""
    (tmp_path / "auth_tokens.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    for r in results:
        assert r.status == RuleStatus.UNKNOWN
        assert len(r.evidence) == 0


def test_secret_hygiene_invariant_nlp(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """Evidence snippets must never retain sensitive authentication credentials."""
    code = """
AUTH_TOKEN = "hf_private_secret_token_abcdef123456"

def tokenize_data(tokenizer, raw_text):
    return tokenizer(raw_text)
"""
    (tmp_path / "secrets_nlp.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    for r in results:
        for ev in r.evidence:
            assert "hf_private_secret_token_abcdef123456" not in ev.snippet


def test_deterministic_repeat_execution_nlp(nlp_kp: NLPKnowledgePack, tmp_path: Path):
    """Deterministic guarantee: 5 consecutive evaluations on identical inputs produce identical results."""
    code = """
import torch.nn as nn

class CustomAttention(nn.Module):
    def __init__(self, d_model: int = 512, n_heads: int = 7):
        super().__init__()
        self.d_model = d_model
        self.n_heads = n_heads
"""
    (tmp_path / "det_nlp.py").write_text(code, encoding="utf-8")

    first_run = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    for _ in range(4):
        subsequent_run = nlp_kp.evaluate(facts=[], target_root=tmp_path)
        assert len(first_run) == len(subsequent_run)
        for r1, r2 in zip(first_run, subsequent_run, strict=True):
            assert r1.rule.id == r2.rule.id
            assert r1.status == r2.status
            assert r1.confidence == r2.confidence
            assert len(r1.evidence) == len(r2.evidence)


def test_nlp_scoring_engine_integration(nlp_kp: NLPKnowledgePack, scoring_engine: NLPScoringEngine, tmp_path: Path):
    """Scoring integration: defect impacts dimension score and to_decisions generates valid Decisions."""
    code = """
def encode_raw(tokenizer, text):
    return tokenizer(text)
"""
    (tmp_path / "server_nlp.py").write_text(code, encoding="utf-8")

    results = nlp_kp.evaluate(facts=[], target_root=tmp_path)
    dim_scores, overall, status = scoring_engine.compute_scores(results)

    assert overall is not None
    assert status in ("warning", "critical")
    decisions = nlp_kp.to_decisions(results)
    assert len(decisions) == 4
    seq_dec = next(d for d in decisions if d.concept_id == "nlp.sequence-budget")
    assert seq_dec.status == DecisionStatus.MISCONFIGURED
