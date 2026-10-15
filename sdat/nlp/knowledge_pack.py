"""Natural Language Processing KnowledgePack — Rule definitions and deterministic evaluation engine.

Implements the 4 red-team approved Stage-1 static system-design rules for NLP:
- NLP-TENS-01: Attention Head Dimension Divisibility (HIGH)
- NLP-TENS-02: Attention Mask Soundness (HIGH)
- NLP-TOKN-02: Tokenizer / Embedding Vocabulary Alignment (HIGH)
- NLP-SEQL-01: Sequence / Context Bounds (HIGH)
"""

from __future__ import annotations

import ast
from pathlib import Path

from sdat.models import Decision, DecisionStatus, Evidence, EvidenceFact, Priority
from sdat.nlp.models import NLPRule, NLPRuleEvaluationResult, RuleStatus


class NLPKnowledgePack:
    """Authoritative knowledge pack for natural language processing system-design auditing."""

    id: str = "kp.natural-language-processing"
    domain: str = "nlp"
    version: str = "1.0.0"
    dependencies: list[str] = ["core", "ml"]
    scoring_dimensions: list[str] = [
        "transformer_tensor_soundness",
        "tokenization_and_sequence_contract",
    ]

    RULES: list[NLPRule] = [
        # 1. Transformer Tensor Contracts
        NLPRule(
            id="NLP-TENS-01",
            dimension="transformer_tensor_soundness",
            name="Attention Head Dimension Divisibility",
            description="Verifies hidden dimension (d_model) is evenly divisible by number of attention heads (n_heads) in multi-head attention.",
            priority=Priority.HIGH,
            concept_id="nlp.tensor-contracts",
            remediation_guidance="Ensure d_model is an integer multiple of n_heads so that d_k = d_model / n_heads produces uniform integer projection subspaces.",
        ),
        NLPRule(
            id="NLP-TENS-02",
            dimension="transformer_tensor_soundness",
            name="Attention Mask Numerical Soundness",
            description="Verifies additive attention masking uses sufficiently large negative constants (-inf or -1e4/-1e9) before softmax.",
            priority=Priority.HIGH,
            concept_id="nlp.attention-masking",
            remediation_guidance="Use -inf (or -1e4/-1e9) when adding attention masks to logit matrices before softmax, or use boolean masked_fill(mask == 0, -inf) so masked positions have zero probability mass.",
        ),
        # 2. Tokenization and Sequence Bounds
        NLPRule(
            id="NLP-TOKN-02",
            dimension="tokenization_and_sequence_contract",
            name="Tokenizer & Embedding Vocabulary Synchronization",
            description="Verifies that tokenizer vocabulary additions (add_tokens, add_special_tokens) are synchronized with model embedding matrix resizing.",
            priority=Priority.HIGH,
            concept_id="nlp.tokenization-pipeline",
            remediation_guidance="Call model.resize_token_embeddings(len(tokenizer)) immediately after adding new tokens to prevent out-of-bounds CUDA index panics during embedding lookups.",
        ),
        NLPRule(
            id="NLP-SEQL-01",
            dimension="tokenization_and_sequence_contract",
            name="Sequence Context Length Bounds",
            description="Detects unbounded text input ingestion in tokenizers lacking max_length and truncation controls.",
            priority=Priority.HIGH,
            concept_id="nlp.sequence-budget",
            remediation_guidance="Specify truncation=True and an explicit max_length parameter when tokenizing external or variable-length inputs to prevent OOM denial-of-service.",
        ),
    ]

    def evaluate(
        self,
        facts: list[EvidenceFact],
        target_root: Path | None = None,
    ) -> list[NLPRuleEvaluationResult]:
        """Deterministically evaluate NLP Stage-1 rules over EvidenceFacts and target AST."""
        results: list[NLPRuleEvaluationResult] = []
        rules_by_id = {r.id: r for r in self.RULES}

        # Collect unique Python files
        files_to_check: dict[Path, str] = {}
        if target_root and target_root.exists():
            for p in target_root.rglob("*.py"):
                if "test" not in p.parts and "venv" not in p.parts and ".git" not in p.parts:
                    try:
                        files_to_check[p] = p.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        pass
        for f in facts:
            fp = Path(f.file_path)
            if fp.exists() and fp.suffix == ".py" and fp not in files_to_check:
                try:
                    files_to_check[fp] = fp.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass

        # 1. NLP-TENS-01: Attention Head Divisibility
        r_tens01 = rules_by_id["NLP-TENS-01"]
        results.append(self._eval_attention_divisibility(r_tens01, facts, files_to_check))

        # 2. NLP-TENS-02: Attention Mask Soundness
        r_tens02 = rules_by_id["NLP-TENS-02"]
        results.append(self._eval_attention_mask(r_tens02, facts, files_to_check))

        # 3. NLP-TOKN-02: Tokenizer Embedding Alignment
        r_tokn02 = rules_by_id["NLP-TOKN-02"]
        results.append(self._eval_vocab_sync(r_tokn02, facts, files_to_check))

        # 4. NLP-SEQL-01: Sequence Context Bounds
        r_seql01 = rules_by_id["NLP-SEQL-01"]
        results.append(self._eval_sequence_bounds(r_seql01, facts, files_to_check))

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Rule Evaluators
    # ─────────────────────────────────────────────────────────────────────────

    def _eval_attention_divisibility(
        self,
        rule: NLPRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> NLPRuleEvaluationResult:
        """NLP-TENS-01: Verify d_model % n_heads == 0."""
        violations: list[tuple[Path, int, str]] = []
        valid_attention_seen = False

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                # Custom MultiHeadAttention class definition
                if isinstance(node, ast.ClassDef) and any(
                    term in node.name.lower() for term in ("attention", "mha", "multihead")
                ):
                    d_model: int | None = None
                    n_heads: int | None = None

                    # Check __init__ default arguments or body assignments
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                            # Check arguments defaults
                            args = item.args
                            # Match arg names to default values
                            pos_args = [a.arg for a in args.args]
                            defaults = [None] * (len(pos_args) - len(args.defaults)) + list(args.defaults)
                            for arg_name, dflt in zip(pos_args, defaults, strict=False):
                                if dflt and isinstance(dflt, ast.Constant) and isinstance(dflt.value, int):
                                    if arg_name in ("d_model", "embed_dim", "hidden_size", "dim"):
                                        d_model = dflt.value
                                    elif arg_name in ("n_heads", "num_heads", "heads"):
                                        n_heads = dflt.value

                            # Also check self.d_model = ... or self.n_heads = ... inside __init__
                            for stmt in item.body:
                                if isinstance(stmt, ast.Assign):
                                    for tgt in stmt.targets:
                                        if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) and tgt.value.id == "self":
                                            if tgt.attr in ("d_model", "embed_dim", "hidden_size") and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, int):
                                                d_model = stmt.value.value
                                            elif tgt.attr in ("n_heads", "num_heads", "heads") and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, int):
                                                n_heads = stmt.value.value

                    # Also check valid alternative architectures where an explicit head_dim is specified
                    # and all_head_size / inner projection is computed as n_heads * head_dim
                    for stmt in ast.walk(node):
                        if isinstance(stmt, ast.Assign):
                            for tgt in stmt.targets:
                                if isinstance(tgt, ast.Attribute) and tgt.attr in ("all_head_size", "inner_dim"):
                                    if isinstance(stmt.value, ast.BinOp) and isinstance(stmt.value.op, ast.Mult):
                                        valid_attention_seen = True

                    if d_model is not None and n_heads is not None and n_heads > 0:
                        if d_model % n_heads != 0:
                            violations.append((
                                fpath,
                                node.lineno,
                                f"Class {node.name}: d_model ({d_model}) is not divisible by n_heads ({n_heads}), remainder: {d_model % n_heads}",
                            ))
                        else:
                            valid_attention_seen = True

        if violations:
            ev_list = [
                Evidence(
                    file=str(v[0]),
                    line=v[1],
                    snippet=v[2],
                    note="Attention head dimension mismatch: Incommensurate projection dimension causes runtime tensor reshape failure.",
                )
                for v in violations
            ]
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=ev_list,
                misconfiguration=f"Attention head dimension indivisibility detected in {len(violations)} class(es).",
                recommendation=rule.remediation_guidance,
                applicability_context="custom multi-head attention class with static dimensions",
            )

        if valid_attention_seen:
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[],
                applicability_context="custom multi-head attention class with static dimensions",
            )

        return NLPRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No custom multi-head attention classes with statically defined integer dimensions discovered."],
            applicability_context="custom multi-head attention not observed or dimensions dynamic",
        )

    def _eval_attention_mask(
        self,
        rule: NLPRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> NLPRuleEvaluationResult:
        """NLP-TENS-02: Verify attention mask uses negative values before softmax."""
        violations: list[tuple[Path, int, str]] = []
        sound_masking_seen = False

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    callee = self._resolve_call_name(node.func)
                    # Check masked_fill
                    if "masked_fill" in callee:
                        if len(node.args) >= 2:
                            val_arg = node.args[1]
                            is_negative = False
                            if isinstance(val_arg, ast.UnaryOp) and isinstance(val_arg.op, ast.USub):
                                is_negative = True
                            elif isinstance(val_arg, ast.Constant):
                                if isinstance(val_arg.value, (int, float)) and val_arg.value < -1000:
                                    is_negative = True
                                elif val_arg.value == float("-inf"):
                                    is_negative = True
                            elif isinstance(val_arg, ast.Call):
                                inner_callee = self._resolve_call_name(val_arg.func)
                                if inner_callee == "float" and val_arg.args:
                                    if isinstance(val_arg.args[0], ast.Constant) and "-inf" in str(val_arg.args[0].value):
                                        is_negative = True

                            if is_negative:
                                sound_masking_seen = True
                            else:
                                violations.append((
                                    fpath,
                                    node.lineno,
                                    f"masked_fill called with non-negative/weak mask value at line {node.lineno}",
                                ))

                    # Check explicit addition of mask before softmax: e.g. softmax(scores + mask)
                    if callee.endswith("softmax") or callee in ("softmax", "F.softmax", "torch.softmax", "nn.functional.softmax"):
                        if node.args and isinstance(node.args[0], ast.BinOp):
                            bin_op = node.args[0]
                            if isinstance(bin_op.op, (ast.Add, ast.Sub)):
                                sound_masking_seen = True

        if violations:
            ev_list = [
                Evidence(
                    file=str(v[0]),
                    line=v[1],
                    snippet=v[2],
                    note="Masked tokens will not receive zero probability mass because mask does not use sufficiently negative values.",
                )
                for v in violations
            ]
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=ev_list,
                misconfiguration=f"Unsound attention masking detected in {len(violations)} location(s).",
                recommendation=rule.remediation_guidance,
                applicability_context="custom attention masking before softmax",
            )

        if sound_masking_seen:
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[],
                applicability_context="custom attention masking before softmax",
            )

        return NLPRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No custom attention masking calls observed."],
            applicability_context="attention masking not observed",
        )

    def _eval_vocab_sync(
        self,
        rule: NLPRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> NLPRuleEvaluationResult:
        """NLP-TOKN-02: Verify add_tokens/add_special_tokens followed by resize_token_embeddings."""
        add_tokens_seen: list[tuple[Path, int, str]] = []
        resize_seen: list[tuple[Path, int]] = []

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    callee = self._resolve_call_name(node.func)
                    if callee.endswith("add_tokens") or callee.endswith("add_special_tokens"):
                        add_tokens_seen.append((fpath, node.lineno, f"{callee}()"))
                    elif callee.endswith("resize_token_embeddings"):
                        resize_seen.append((fpath, node.lineno))

        if add_tokens_seen:
            if not resize_seen:
                ev_list = [
                    Evidence(
                        file=str(a[0]),
                        line=a[1],
                        snippet=a[2],
                        note="Added vocabulary tokens without corresponding model.resize_token_embeddings() call.",
                    )
                    for a in add_tokens_seen
                ]
                return NLPRuleEvaluationResult(
                    rule=rule,
                    status=RuleStatus.MISCONFIGURED,
                    confidence=0.95,
                    evidence=ev_list,
                    misconfiguration=f"Tokenizer vocabulary added in {len(add_tokens_seen)} place(s) without model embedding capacity expansion.",
                    recommendation=rule.remediation_guidance,
                    applicability_context="tokenizer vocabulary mutation",
                )
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.95,
                evidence=[Evidence(file=str(resize_seen[0][0]), line=resize_seen[0][1], snippet="resize_token_embeddings(...)")],
                applicability_context="tokenizer vocabulary mutation",
            )

        return NLPRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No custom tokenizer vocabulary additions (add_tokens/add_special_tokens) detected."],
            applicability_context="tokenizer vocabulary mutation not observed",
        )

    def _eval_sequence_bounds(
        self,
        rule: NLPRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> NLPRuleEvaluationResult:
        """NLP-SEQL-01: Detect unbounded text input ingestion in tokenizers."""
        unbounded_calls: list[tuple[Path, int, str]] = []
        bounded_calls: list[tuple[Path, int, str]] = []

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    callee = self._resolve_call_name(node.func)
                    is_tokenizer_call = (
                        "tokenizer" in callee.lower()
                        or callee.endswith(".encode")
                        or callee.endswith(".batch_encode_plus")
                    )
                    if is_tokenizer_call and node.args:
                        has_truncation = False
                        has_max_length = False

                        for kw in node.keywords:
                            if kw.arg == "truncation":
                                if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                    has_truncation = True
                                elif isinstance(kw.value, ast.Name) and kw.value.id in ("True", "truncation"):
                                    has_truncation = True
                            elif kw.arg == "max_length":
                                has_max_length = True

                        # Valid alternative: explicit slice on input, e.g. text[:512]
                        has_explicit_slice = False
                        if isinstance(node.args[0], ast.Subscript) and isinstance(node.args[0].slice, ast.Slice):
                            has_explicit_slice = True

                        if (has_truncation and has_max_length) or has_explicit_slice:
                            bounded_calls.append((fpath, node.lineno, f"{callee}(...) with bounded length"))
                        elif not has_truncation and not has_max_length:
                            unbounded_calls.append((fpath, node.lineno, f"{callee}() without truncation/max_length"))

        if unbounded_calls:
            ev_list = [
                Evidence(
                    file=str(u[0]),
                    line=u[1],
                    snippet=u[2],
                    note="Unbounded sequence length: Missing truncation=True and max_length exposes server to OOM.",
                )
                for u in unbounded_calls
            ]
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.90,
                evidence=ev_list,
                misconfiguration=f"Unbounded text ingestion detected across {len(unbounded_calls)} tokenizer call(s).",
                recommendation=rule.remediation_guidance,
                applicability_context="tokenizer text encoding invocation",
            )

        if bounded_calls:
            return NLPRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[Evidence(file=str(bounded_calls[0][0]), line=bounded_calls[0][1], snippet=bounded_calls[0][2])],
                applicability_context="tokenizer text encoding invocation",
            )

        return NLPRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No tokenizer text encoding invocations observed."],
            applicability_context="tokenizer text encoding not observed",
        )

    def _resolve_call_name(self, node: ast.AST) -> str:
        """Resolve an AST call node func to a qualified string."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""

    def _ast_to_name(self, node: ast.AST) -> str:
        """Helper to get variable or attribute name."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return ""

    def to_decisions(self, results: list[NLPRuleEvaluationResult]) -> list[Decision]:
        """Convert NLP evaluation results to canonical SDAT Decisions."""
        decisions: list[Decision] = []
        for r in results:
            dec_status = r.rule_status.to_decision_status() if hasattr(r, "rule_status") else (
                r.status if isinstance(r.status, DecisionStatus) else DecisionStatus.UNKNOWN
            )
            decisions.append(
                Decision(
                    concept_id=r.rule.concept_id,
                    concept_name=r.rule.concept_id.split(".")[-1],
                    status=dec_status,
                    confidence=r.confidence,
                    evidence=r.evidence,
                    misconfiguration=r.misconfiguration,
                    gaps=r.gaps,
                    recommendation=r.recommendation or (r.rule.remediation_guidance if dec_status == DecisionStatus.MISCONFIGURED else None),
                    priority=r.rule.priority if dec_status == DecisionStatus.MISCONFIGURED else Priority.INFO,
                )
            )
        return decisions
