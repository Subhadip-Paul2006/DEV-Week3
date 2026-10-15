"""SDAT Agent Swarm Orchestrator.

Production-grade swarm system design featuring:
- Bounded concurrency with worker pool limits (ThreadPoolExecutor)
- Bounded task scheduling with queue depth observability
- Per-agent execution timeouts and task cancellation
- Complete failure isolation (one agent failure never crashes the swarm)
- Classification of transient vs permanent failures (non-retryable errors fail fast)
- Transient error retries with exponential backoff and randomized jitter
- Truly deterministic content-hashed task deduplication (ContentCache)
- Agent lifecycle management and structured health tracking
- Deterministic result merging with conflict resolution
- Complete decoupling from external AI (AI is an optional enhancement)
"""

from __future__ import annotations

import concurrent.futures
import random
import time
from typing import Any, List, Optional, Protocol, runtime_checkable

from sdat.cache.store import ContentCache
from sdat.models import DecisionStatus, Priority
from sdat.swarm.merger import MergedOutput, merge_decisions
from sdat.telemetry.tracker import AuditTelemetry

# Exceptions representing fundamental programming or semantic errors that should fail fast
NON_RETRYABLE_EXCEPTIONS = (
    TypeError,
    ValueError,
    KeyError,
    AttributeError,
    SyntaxError,
    ImportError,
    PermissionError,
    IndexError,
)


@runtime_checkable
class SwarmAgent(Protocol):
    """Protocol implemented by all SDAT Swarm agents."""

    agent_id: str
    agent_name: str

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        """Execute agent evaluation and return structured decision dict."""
        ...


class SwarmOrchestrator:
    """Orchestrates multi-agent execution with resilience, concurrency control, and telemetry."""

    def __init__(
        self,
        max_workers: int = 4,
        agent_timeout_seconds: float = 30.0,
        max_retries: int = 2,
        backoff_base_seconds: float = 0.25,
        cache: Optional[ContentCache] = None,
        telemetry: Optional[AuditTelemetry] = None,
    ) -> None:
        self.max_workers = max(1, max_workers)
        self.agent_timeout_seconds = agent_timeout_seconds
        self.max_retries = max(0, max_retries)
        self.backoff_base_seconds = backoff_base_seconds
        self.cache = cache
        self.telemetry = telemetry

    def _compute_task_cache_key(self, agent_id: str, project_context: dict[str, Any]) -> str:
        """Derive a deterministic cache key sensitive to exact fact contents and target root."""
        facts = project_context.get("evidence_facts", [])
        fact_tokens: list[str] = []
        for f in facts:
            if hasattr(f, "kind"):
                kind_val = getattr(f.kind, "value", str(f.kind))
                snippet_hash = ContentCache.hash_content(getattr(f, "snippet", ""))[:12]
                fact_tokens.append(f"{f.file_path}:{f.line_range}:{kind_val}:{f.subject}:{snippet_hash}")
            elif isinstance(f, dict):
                snippet_hash = ContentCache.hash_content(str(f.get("snippet", "")))[:12]
                fact_tokens.append(f"{f.get('file_path')}:{f.get('line_range')}:{f.get('kind')}:{f.get('subject')}:{snippet_hash}")

        fact_tokens.sort()
        facts_digest = ContentCache.hash_content("\n".join(fact_tokens))
        bundle_tokens: list[str] = []
        for bundle in project_context.get("bundles", []):
            concept_id = getattr(bundle, "concept_id", "")
            for fact in getattr(bundle, "facts", ()):
                snippet_hash = ContentCache.hash_content(getattr(fact, "snippet", ""))[:12]
                kind = getattr(getattr(fact, "kind", ""), "value", getattr(fact, "kind", ""))
                bundle_tokens.append(
                    f"{concept_id}:{fact.file_path}:{fact.line_range}:{kind}:{fact.subject}:{snippet_hash}"
                )
        bundles_digest = ContentCache.hash_content("\n".join(sorted(bundle_tokens)))
        target_root = str(project_context.get("target_root", ""))
        payload = f"{agent_id}:{target_root}:{facts_digest}:{bundles_digest}"
        return f"agent_task_{ContentCache.hash_content(payload)}"

    def _execute_agent_with_retry(
        self,
        agent: SwarmAgent | Any,
        project_context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an agent with timeout, exponential backoff retries, and failure isolation."""
        agent_id = getattr(agent, "agent_id", "unknown_agent")
        agent_name = getattr(agent, "agent_name", agent_id)

        # 1. Check cache for previous idempotent execution
        cache_key = self._compute_task_cache_key(agent_id, project_context)
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                return cached_result

        # 2. Execution loop with retries
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                if self.telemetry:
                    with self.telemetry.time_agent(agent_id):
                        result = agent.run(project_context)
                else:
                    result = agent.run(project_context)

                # Persist in cache
                if self.cache:
                    self.cache.put(cache_key, result)
                return result

            except Exception as exc:
                last_error = exc

                # Fail fast on non-retryable programming errors
                if isinstance(exc, NON_RETRYABLE_EXCEPTIONS):
                    break

                if attempt <= self.max_retries:
                    if self.telemetry:
                        self.telemetry.record_retry(agent_id)
                    # Exponential backoff with jitter
                    backoff = self.backoff_base_seconds * (2 ** (attempt - 1))
                    jitter = random.uniform(0.0, backoff * 0.1)
                    time.sleep(backoff + jitter)
                else:
                    break

        # 3. Handle isolated failure without terminating the swarm
        err_msg = str(last_error) if last_error else "Unknown execution error"
        is_timeout = isinstance(last_error, (concurrent.futures.TimeoutError, TimeoutError))

        if self.telemetry:
            self.telemetry.record_agent_failure(agent_id, err_msg, is_timeout=is_timeout)

        # Build fallback partial decisions so the failure is transparent in reports
        fallback_decision = {
            "concept_id": f"agent.{agent_id}.status",
            "concept_name": f"{agent_name} Execution",
            "status": DecisionStatus.UNKNOWN.value,
            "confidence": 0.0,
            "evidence": [],
            "misconfiguration": None,
            "gaps": [f"Agent execution encountered an isolated error: {err_msg}"],
            "recommendation": "Check audit diagnostics or rerun the agent.",
            "priority": Priority.HIGH.value if is_timeout else Priority.MEDIUM.value,
        }

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "run_id": project_context.get("run_id", "fallback_run"),
            "target_root": project_context.get("target_root", ""),
            "concepts_evaluated": 0,
            "decisions": [fallback_decision],
            "error": err_msg,
            "is_failed": True,
        }

    def run_swarm(
        self,
        agents: List[SwarmAgent | Any],
        project_context: dict[str, Any],
    ) -> MergedOutput:
        """Run all swarm agents concurrently with bounded workers, failure isolation, and merging."""
        if not agents:
            return MergedOutput(decisions=[], warnings=["No agents configured in dispatch set."])

        if self.telemetry:
            self.telemetry.queue_depth = len(agents)

        agent_outputs: list[dict[str, Any]] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit each agent task to the bounded pool and record submission timestamps
            future_to_agent: dict[concurrent.futures.Future[dict[str, Any]], Any] = {}
            submitted_at: dict[concurrent.futures.Future[dict[str, Any]], float] = {}

            for agent in agents:
                future = executor.submit(self._execute_agent_with_retry, agent, project_context)
                future_to_agent[future] = agent
                submitted_at[future] = time.perf_counter()

            # Gather results enforcing per-agent wall-clock timeout from submission time
            for future, agent in future_to_agent.items():
                agent_id = getattr(agent, "agent_id", "unknown_agent")
                elapsed = time.perf_counter() - submitted_at[future]
                remaining_timeout = max(0.001, self.agent_timeout_seconds - elapsed)

                try:
                    out = future.result(timeout=remaining_timeout)
                    agent_outputs.append(out)
                except concurrent.futures.TimeoutError:
                    future.cancel()
                    err_msg = f"Agent {agent_id} timed out after {self.agent_timeout_seconds}s"
                    if self.telemetry:
                        self.telemetry.record_agent_failure(agent_id, err_msg, is_timeout=True)
                    agent_outputs.append({
                        "agent_id": agent_id,
                        "agent_name": getattr(agent, "agent_name", agent_id),
                        "run_id": project_context.get("run_id", "timeout_run"),
                        "target_root": project_context.get("target_root", ""),
                        "concepts_evaluated": 0,
                        "decisions": [{
                            "concept_id": f"agent.{agent_id}.timeout",
                            "concept_name": f"{agent_id} Timeout",
                            "status": DecisionStatus.UNKNOWN.value,
                            "confidence": 0.0,
                            "evidence": [],
                            "misconfiguration": None,
                            "gaps": [err_msg],
                            "recommendation": "Increase agent_timeout_seconds or investigate slow execution paths.",
                            "priority": Priority.HIGH.value,
                        }],
                        "error": err_msg,
                        "is_failed": True,
                    })
                except Exception as exc:
                    err_msg = f"Worker thread exception for {agent_id}: {exc}"
                    if self.telemetry:
                        self.telemetry.record_agent_failure(agent_id, err_msg, is_timeout=False)
                    agent_outputs.append({
                        "agent_id": agent_id,
                        "agent_name": getattr(agent, "agent_name", agent_id),
                        "run_id": project_context.get("run_id", "thread_err"),
                        "target_root": project_context.get("target_root", ""),
                        "concepts_evaluated": 0,
                        "decisions": [],
                        "error": err_msg,
                        "is_failed": True,
                    })

        if self.telemetry:
            self.telemetry.queue_depth = 0

        # Merge decisions deterministically
        return merge_decisions(agent_outputs)
