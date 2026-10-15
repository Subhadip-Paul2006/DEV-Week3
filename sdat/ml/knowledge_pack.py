"""Machine Learning KnowledgePack — Rule definitions and deterministic evaluation engine.

Implements the 4 red-team approved Stage-1 static system-design rules for ML:
- ML-MATH-01: Double Softmax / Logit-Probability Mismatch (CRITICAL)
- ML-MATH-02: Log-Sum-Exp Numerical Stability (HIGH)
- ML-SCHED-01: Learning Rate Scheduler Step Ordering (HIGH)
- ML-SEC-01: Unsafe Model Deserialization (CRITICAL)
"""

from __future__ import annotations

import ast
from pathlib import Path

from sdat.ml.models import MLRule, MLRuleEvaluationResult, RuleStatus
from sdat.models import Decision, DecisionStatus, Evidence, EvidenceFact, Priority


class MLKnowledgePack:
    """Authoritative knowledge pack for machine learning system-design auditing."""

    id: str = "kp.machine-learning"
    domain: str = "ml"
    version: str = "1.0.0"
    dependencies: list[str] = ["core"]
    scoring_dimensions: list[str] = [
        "mathematical_numerical_stability",
        "training_optimization_hygiene",
        "reproducibility_and_safety",
    ]

    RULES: list[MLRule] = [
        # 1. Mathematical Stability
        MLRule(
            id="ML-MATH-01",
            dimension="mathematical_numerical_stability",
            name="Double Softmax / Logit-Probability Mismatch",
            description="Detects explicit probability transformations (softmax/sigmoid) immediately preceding cross-entropy loss expecting raw logits.",
            priority=Priority.CRITICAL,
            concept_id="ml.mathematical-correctness",
            remediation_guidance="Pass unconstrained raw logits directly to CrossEntropyLoss or F.cross_entropy. Remove preceding nn.Softmax() or F.softmax() calls.",
        ),
        MLRule(
            id="ML-MATH-02",
            dimension="mathematical_numerical_stability",
            name="Log-Sum-Exp Numerical Stability",
            description="Detects manual log(sum(exp(x))) calculations prone to numerical underflow/overflow instead of stabilized logsumexp.",
            priority=Priority.HIGH,
            concept_id="ml.mathematical-correctness",
            remediation_guidance="Replace manual log(sum(exp(x))) with torch.logsumexp or scipy.special.logsumexp to guarantee numerical stability via max-subtraction.",
        ),
        # 2. Optimization Hygiene
        MLRule(
            id="ML-SCHED-01",
            dimension="training_optimization_hygiene",
            name="Learning Rate Scheduler Step Ordering",
            description="Verifies scheduler.step() executes after optimizer.step() within training update scopes.",
            priority=Priority.HIGH,
            concept_id="ml.optimization-hygiene",
            remediation_guidance="Place scheduler.step() strictly after optimizer.step() in training loops to avoid skipped initial learning rates and PyTorch runtime warnings.",
        ),
        # 3. Serialization Safety
        MLRule(
            id="ML-SEC-01",
            dimension="reproducibility_and_safety",
            name="Unsafe Model Deserialization",
            description="Detects unsafe model deserialization via standard pickle or torch.load without safe weights_only guards.",
            priority=Priority.CRITICAL,
            concept_id="ml.serialization-safety",
            remediation_guidance="Use safetensors (safetensors.torch.load_file) or pass weights_only=True to torch.load() to prevent Arbitrary Code Execution (RCE).",
        ),
    ]

    def evaluate(
        self,
        facts: list[EvidenceFact],
        target_root: Path | None = None,
    ) -> list[MLRuleEvaluationResult]:
        """Deterministically evaluate ML Stage-1 rules over EvidenceFacts and target AST."""
        results: list[MLRuleEvaluationResult] = []

        # Map rules by ID
        rules_by_id = {r.id: r for r in self.RULES}

        # Collect unique Python files referenced in facts or target_root
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

        # ─────────────────────────────────────────────────────────────────────
        # 1. Evaluate ML-MATH-01: Double Softmax
        # ─────────────────────────────────────────────────────────────────────
        r_math01 = rules_by_id["ML-MATH-01"]
        math01_res = self._eval_double_softmax(r_math01, facts, files_to_check)
        results.append(math01_res)

        # ─────────────────────────────────────────────────────────────────────
        # 2. Evaluate ML-MATH-02: Log-Sum-Exp Stability
        # ─────────────────────────────────────────────────────────────────────
        r_math02 = rules_by_id["ML-MATH-02"]
        math02_res = self._eval_logsumexp(r_math02, facts, files_to_check)
        results.append(math02_res)

        # ─────────────────────────────────────────────────────────────────────
        # 3. Evaluate ML-SCHED-01: Scheduler Step Ordering
        # ─────────────────────────────────────────────────────────────────────
        r_sched01 = rules_by_id["ML-SCHED-01"]
        sched01_res = self._eval_scheduler_ordering(r_sched01, facts, files_to_check)
        results.append(sched01_res)

        # ─────────────────────────────────────────────────────────────────────
        # 4. Evaluate ML-SEC-01: Unsafe Deserialization
        # ─────────────────────────────────────────────────────────────────────
        r_sec01 = rules_by_id["ML-SEC-01"]
        sec01_res = self._eval_unsafe_deserialization(r_sec01, facts, files_to_check)
        results.append(sec01_res)

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Evaluator Implementations
    # ─────────────────────────────────────────────────────────────────────────

    def _eval_double_softmax(
        self,
        rule: MLRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> MLRuleEvaluationResult:
        """ML-MATH-01: Detects softmax output passed to cross-entropy expecting logits."""
        # 1. Fact-based or AST-based check
        violations: list[tuple[Path, int, str]] = []
        valid_ce_seen = False

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                # Check call to cross_entropy, CrossEntropyLoss, or BCEWithLogitsLoss
                if isinstance(node, ast.Call):
                    func_name = self._resolve_call_name(node.func)
                    if func_name in (
                        "cross_entropy",
                        "F.cross_entropy",
                        "nn.CrossEntropyLoss",
                        "CrossEntropyLoss",
                        "torch.nn.functional.cross_entropy",
                        "nn.BCEWithLogitsLoss",
                        "BCEWithLogitsLoss",
                        "F.binary_cross_entropy_with_logits",
                    ):
                        valid_ce_seen = True
                        # Check arguments directly passed: e.g. cross_entropy(softmax(x), y)
                        if node.args:
                            first_arg = node.args[0]
                            if isinstance(first_arg, ast.Call):
                                inner_func = self._resolve_call_name(first_arg.func)
                                if any(s in inner_func.lower() for s in ("softmax", "sigmoid")):
                                    violations.append((
                                        fpath,
                                        node.lineno,
                                        f"Direct pass of {inner_func}() into {func_name}()",
                                    ))
                    # Valid mathematical alternatives: NLLLoss with log_softmax or BCELoss with sigmoid
                    elif "nllloss" in func_name.lower() or "nll_loss" in func_name.lower():
                        if node.args and isinstance(node.args[0], ast.Call):
                            inner_func = self._resolve_call_name(node.args[0].func)
                            if "log_softmax" in inner_func.lower():
                                valid_ce_seen = True
                    elif "bceloss" in func_name.lower() or (
                        "binary_cross_entropy" in func_name.lower() and "with_logits" not in func_name.lower()
                    ):
                        if node.args and isinstance(node.args[0], ast.Call):
                            inner_func = self._resolve_call_name(node.args[0].func)
                            if "sigmoid" in inner_func.lower():
                                valid_ce_seen = True

                # Check sequential assignments and returns in the same block:
                # pred = softmax(logits)
                # return cross_entropy(pred, targets)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    assigned_softmax_vars: dict[str, int] = {}
                    assigned_log_softmax_vars: dict[str, int] = {}
                    ce_instances: set[str] = set()

                    for stmt in node.body:
                        # track criterion = CrossEntropyLoss() or BCEWithLogitsLoss()
                        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                            callee = self._resolve_call_name(stmt.value.func)
                            if any(k in callee for k in ("CrossEntropyLoss", "BCEWithLogitsLoss")):
                                for tgt in stmt.targets:
                                    if isinstance(tgt, ast.Name):
                                        ce_instances.add(tgt.id)
                            # track pred = softmax(x) or F.softmax(x)
                            inner = self._resolve_call_name(stmt.value.func)
                            if any(s in inner.lower() for s in ("softmax", "sigmoid")) and "log_softmax" not in inner.lower():
                                for tgt in stmt.targets:
                                    if isinstance(tgt, ast.Name):
                                        assigned_softmax_vars[tgt.id] = stmt.lineno
                            elif "log_softmax" in inner.lower():
                                for tgt in stmt.targets:
                                    if isinstance(tgt, ast.Name):
                                        assigned_log_softmax_vars[tgt.id] = stmt.lineno

                        # inspect any call in stmt (Assign, Return, Expr)
                        call_nodes: list[ast.Call] = []
                        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
                            call_nodes.append(stmt.value)
                        elif isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                            call_nodes.append(stmt.value)
                        elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                            call_nodes.append(stmt.value)

                        for call_node in call_nodes:
                            callee = self._resolve_call_name(call_node.func)
                            is_ce = callee in ce_instances or any(
                                k in callee for k in ("cross_entropy", "binary_cross_entropy_with_logits")
                            )
                            if is_ce:
                                valid_ce_seen = True
                                if call_node.args:
                                    arg0 = call_node.args[0]
                                    if isinstance(arg0, ast.Name) and arg0.id in assigned_softmax_vars:
                                        violations.append((
                                            fpath,
                                            stmt.lineno,
                                            f"Transformed probability variable '{arg0.id}' passed into cross-entropy at line {stmt.lineno}",
                                        ))
                            elif any(k in callee.lower() for k in ("nllloss", "nll_loss")):
                                if call_node.args:
                                    arg0 = call_node.args[0]
                                    if (isinstance(arg0, ast.Name) and arg0.id in assigned_log_softmax_vars) or (
                                        isinstance(arg0, ast.Call) and "log_softmax" in self._resolve_call_name(arg0.func).lower()
                                    ):
                                        valid_ce_seen = True

        if violations:
            ev_list = [
                Evidence(
                    file=str(v[0]),
                    line=v[1],
                    snippet=v[2],
                    note="Mathematically invalid: CrossEntropyLoss applies LogSoftmax internally; passing softmax causes distorted gradients.",
                )
                for v in violations
            ]
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=ev_list,
                misconfiguration=f"Double Softmax detected: Probabilities explicitly transformed before cross-entropy loss in {len(violations)} location(s).",
                recommendation=rule.remediation_guidance,
                applicability_context="intra-procedural loss calculation",
            )

        if valid_ce_seen:
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[],
                applicability_context="intra-procedural loss calculation",
            )

        return MLRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No cross-entropy loss calculations observed in target codebase."],
            applicability_context="loss calculation not observed",
        )

    def _eval_logsumexp(
        self,
        rule: MLRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> MLRuleEvaluationResult:
        """ML-MATH-02: Detects manual log(sum(exp(x))) calculations."""
        violations: list[tuple[Path, int, str]] = []
        stable_seen = False

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    callee = self._resolve_call_name(node.func)
                    if "logsumexp" in callee.lower():
                        stable_seen = True

                    # Detect log(sum(exp(...)))
                    # callee is log or torch.log or math.log or np.log
                    if callee in ("log", "torch.log", "np.log", "math.log", "tf.math.log"):
                        if node.args and isinstance(node.args[0], ast.Call):
                            mid_call = node.args[0]
                            mid_func = self._resolve_call_name(mid_call.func)
                            if mid_func in ("sum", "torch.sum", "np.sum", "math.fsum", "tf.reduce_sum"):
                                if mid_call.args and isinstance(mid_call.args[0], ast.Call):
                                    inner_call = mid_call.args[0]
                                    inner_func = self._resolve_call_name(inner_call.func)
                                    if inner_func in ("exp", "torch.exp", "np.exp", "math.exp", "tf.math.exp"):
                                         # Check if inner_call argument has subtraction: e.g. exp(x - max_x)
                                         is_stabilized = False
                                         if inner_call.args and isinstance(inner_call.args[0], ast.BinOp):
                                             if isinstance(inner_call.args[0].op, ast.Sub):
                                                 is_stabilized = True

                                         if is_stabilized:
                                             stable_seen = True
                                         else:
                                             violations.append((
                                                 fpath,
                                                 node.lineno,
                                                 f"Unstable calculation: {callee}({mid_func}({inner_func}(...)))",
                                             ))

        if violations:
            ev_list = [
                Evidence(
                    file=str(v[0]),
                    line=v[1],
                    snippet=v[2],
                    note="Numerically unstable log(sum(exp(x))) prone to overflow/underflow on extreme values.",
                )
                for v in violations
            ]
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=ev_list,
                misconfiguration=f"Numerically unstable log-sum-exp calculation detected in {len(violations)} location(s).",
                recommendation=rule.remediation_guidance,
                applicability_context="log-partition calculation",
            )

        if stable_seen:
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[],
                applicability_context="log-partition calculation",
            )

        return MLRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No custom log-sum-exp or log-partition computations detected."],
            applicability_context="log-partition computation not observed",
        )

    def _eval_scheduler_ordering(
        self,
        rule: MLRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> MLRuleEvaluationResult:
        """ML-SCHED-01: Detects scheduler.step() executed before optimizer.step()."""
        violations: list[tuple[Path, int, str]] = []
        correct_ordering_seen = False

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                # Inspect loop bodies (for or while)
                if isinstance(node, (ast.For, ast.While, ast.FunctionDef)):
                    opt_steps: list[int] = []
                    sched_steps: list[int] = []

                    for stmt in ast.walk(node):
                        if isinstance(stmt, ast.Call):
                            call_name = self._resolve_call_name(stmt.func)
                            if call_name.endswith("optimizer.step") or call_name.endswith("opt.step") or call_name == "optimizer.step":
                                opt_steps.append(stmt.lineno)
                            elif call_name.endswith("scheduler.step") or call_name.endswith("sched.step") or call_name == "scheduler.step":
                                sched_steps.append(stmt.lineno)

                    if opt_steps and sched_steps:
                        min_opt = min(opt_steps)
                        min_sched = min(sched_steps)
                        if min_sched < min_opt:
                            violations.append((
                                fpath,
                                min_sched,
                                f"scheduler.step() on line {min_sched} executed before optimizer.step() on line {min_opt}",
                            ))
                        else:
                            correct_ordering_seen = True

        if violations:
            ev_list = [
                Evidence(
                    file=str(v[0]),
                    line=v[1],
                    snippet=v[2],
                    note="PyTorch scheduler.step() called before optimizer.step() skips initial LR and desynchronizes updates.",
                )
                for v in violations
            ]
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=ev_list,
                misconfiguration=f"Invalid scheduler step order detected in {len(violations)} loop(s).",
                recommendation=rule.remediation_guidance,
                applicability_context="intra-procedural training update scope",
            )

        if correct_ordering_seen:
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[],
                applicability_context="intra-procedural training update scope",
            )

        return MLRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No co-occurring optimizer.step() and scheduler.step() loops detected."],
            applicability_context="training loop not observed",
        )

    def _eval_unsafe_deserialization(
        self,
        rule: MLRule,
        facts: list[EvidenceFact],
        files: dict[Path, str],
    ) -> MLRuleEvaluationResult:
        """ML-SEC-01: Detects unsafe model/weight deserialization."""
        violations: list[tuple[Path, int, str]] = []
        safe_deserialization_seen = False

        for fpath, code in files.items():
            try:
                tree = ast.parse(code, filename=str(fpath))
            except Exception:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    callee = self._resolve_call_name(node.func)
                    # Safe: safetensors.torch.load_file or torch.load(..., weights_only=True)
                    if "safetensors" in callee.lower() and "load" in callee.lower():
                        safe_deserialization_seen = True
                    elif callee in ("torch.load", "load"):
                        has_weights_only = False
                        weights_only_val = None
                        for kw in node.keywords:
                            if kw.arg == "weights_only":
                                has_weights_only = True
                                if isinstance(kw.value, ast.Constant):
                                    weights_only_val = kw.value.value

                        if has_weights_only and weights_only_val is True:
                            safe_deserialization_seen = True
                        elif has_weights_only and weights_only_val is False:
                            violations.append((
                                fpath,
                                node.lineno,
                                "torch.load(..., weights_only=False) explicitly allows arbitrary code execution",
                            ))
                        elif not has_weights_only:
                            # In pre-2.4 PyTorch, default was weights_only=False
                            violations.append((
                                fpath,
                                node.lineno,
                                f"{callee}() called without weights_only=True guard",
                            ))

                    elif callee in ("pickle.load", "pickle.loads", "_pickle.load"):
                        violations.append((
                            fpath,
                            node.lineno,
                            f"Unsafe {callee}() used for deserialization without code execution defense",
                        ))

        if violations:
            ev_list = [
                Evidence(
                    file=str(v[0]),
                    line=v[1],
                    snippet=v[2],
                    note="Arbitrary code execution risk: Deserializing model checkpoints using unsafe pickle or unshielded torch.load.",
                )
                for v in violations
            ]
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.MISCONFIGURED,
                confidence=0.95,
                evidence=ev_list,
                misconfiguration=f"Unsafe model deserialization detected in {len(violations)} location(s).",
                recommendation=rule.remediation_guidance,
                applicability_context="checkpoint deserialization invocation",
            )

        if safe_deserialization_seen:
            return MLRuleEvaluationResult(
                rule=rule,
                status=RuleStatus.PASS,
                confidence=0.90,
                evidence=[],
                applicability_context="checkpoint deserialization invocation",
            )

        return MLRuleEvaluationResult(
            rule=rule,
            status=RuleStatus.UNKNOWN,
            confidence=0.5,
            gaps=["No checkpoint loading or deserialization invocations detected."],
            applicability_context="checkpoint deserialization not observed",
        )

    def _resolve_call_name(self, node: ast.AST) -> str:
        """Resolve an AST call node func to a qualified string."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            val = self._resolve_call_name(node.value)
            return f"{val}.{node.attr}" if val else node.attr
        return ""

    def to_decisions(self, results: list[MLRuleEvaluationResult]) -> list[Decision]:
        """Convert ML evaluation results to canonical SDAT Decisions."""
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
