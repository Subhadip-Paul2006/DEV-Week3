"""Unit tests for Swarm Orchestration, Concurrency, Retries, and Failure Isolation."""

from __future__ import annotations

import threading
import time
from typing import Any

from sdat.cache.store import ContentCache
from sdat.models import DecisionStatus
from sdat.swarm.orchestrator import SwarmOrchestrator
from sdat.telemetry.tracker import AuditTelemetry


class MockSuccessfulAgent:
    def __init__(self, agent_id: str, concept: str) -> None:
        self.agent_id = agent_id
        self.agent_name = f"mock_{agent_id}"
        self.concept = concept

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": "test_run",
            "target_root": project_context.get("target_root", ""),
            "concepts_evaluated": 1,
            "decisions": [
                {
                    "concept_id": self.concept,
                    "concept_name": self.concept,
                    "status": DecisionStatus.IMPLEMENTED.value,
                    "confidence": 0.95,
                    "evidence": [],
                    "misconfiguration": None,
                    "gaps": [],
                    "recommendation": None,
                    "priority": "info",
                }
            ],
        }


class MockFailingAgent:
    def __init__(self, agent_id: str, fail_count: int = 999) -> None:
        self.agent_id = agent_id
        self.agent_name = f"failing_{agent_id}"
        self.fail_count = fail_count
        self.calls = 0

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError(f"Simulated crash in {self.agent_id} (attempt {self.calls})")
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": "test_run",
            "target_root": "",
            "concepts_evaluated": 1,
            "decisions": [
                {
                    "concept_id": f"recovered.{self.agent_id}",
                    "concept_name": "Recovered",
                    "status": DecisionStatus.IMPLEMENTED.value,
                    "confidence": 0.8,
                    "evidence": [],
                    "misconfiguration": None,
                    "gaps": [],
                    "recommendation": None,
                    "priority": "info",
                }
            ],
        }


class MockSlowAgent:
    def __init__(self, agent_id: str, sleep_seconds: float) -> None:
        self.agent_id = agent_id
        self.agent_name = f"slow_{agent_id}"
        self.sleep_seconds = sleep_seconds

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        time.sleep(self.sleep_seconds)
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": "test_run",
            "target_root": "",
            "concepts_evaluated": 1,
            "decisions": [],
        }


def test_swarm_concurrency_and_successful_merging():
    telem = AuditTelemetry()
    orchestrator = SwarmOrchestrator(max_workers=3, telemetry=telem)

    agents = [
        MockSuccessfulAgent("F-01", "foundation.caching"),
        MockSuccessfulAgent("D-01", "api.rest"),
        MockSuccessfulAgent("D-21", "frontend.rendering"),
    ]

    context = {"target_root": "/test", "evidence_facts": []}
    merged = orchestrator.run_swarm(agents, context)

    assert len(merged.decisions) == 3
    concept_ids = {d.concept_id for d in merged.decisions}
    assert concept_ids == {"foundation.caching", "api.rest", "frontend.rendering"}
    assert all(d.status == DecisionStatus.IMPLEMENTED for d in merged.decisions)


def test_swarm_failure_isolation():
    """One failing agent must NOT terminate the swarm or fail other agents."""
    telem = AuditTelemetry()
    orchestrator = SwarmOrchestrator(max_workers=4, max_retries=1, backoff_base_seconds=0.01, telemetry=telem)

    agents = [
        MockSuccessfulAgent("Backend", "foundation.api"),
        MockFailingAgent("Frontend", fail_count=999),  # Always fails
        MockSuccessfulAgent("Database", "data.orm"),
        MockSuccessfulAgent("Security", "foundation.auth"),
    ]

    context = {"target_root": "/test", "evidence_facts": []}
    merged = orchestrator.run_swarm(agents, context)

    # All successful agents produce their decisions
    concept_ids = {d.concept_id for d in merged.decisions}
    assert "foundation.api" in concept_ids
    assert "data.orm" in concept_ids
    assert "foundation.auth" in concept_ids

    # Failing agent produces an isolated fallback failure record
    assert "agent.Frontend.status" in concept_ids
    failed_decision = next(d for d in merged.decisions if d.concept_id == "agent.Frontend.status")
    assert failed_decision.status == DecisionStatus.UNKNOWN
    assert any("Simulated crash" in g for g in failed_decision.gaps)

    # Telemetry properly records the failure and retries
    assert len(telem.failed_agents) == 1
    assert telem.failed_agents[0]["agent_id"] == "Frontend"
    assert telem.retry_counts.get("Frontend", 0) == 1


def test_swarm_retry_with_eventual_recovery():
    """Transient failures are retried and can recover successfully."""
    telem = AuditTelemetry()
    orchestrator = SwarmOrchestrator(max_workers=2, max_retries=2, backoff_base_seconds=0.01, telemetry=telem)

    # Fails once, then recovers on second attempt
    flaky_agent = MockFailingAgent("FlakyService", fail_count=1)
    context = {"target_root": "/test", "evidence_facts": []}
    merged = orchestrator.run_swarm([flaky_agent], context)

    assert len(merged.decisions) == 1
    assert merged.decisions[0].concept_id == "recovered.FlakyService"
    assert telem.retry_counts.get("FlakyService") == 1
    assert len(telem.failed_agents) == 0


def test_swarm_per_agent_timeout():
    """Slow agent exceeding timeout is isolated as a timeout failure without blocking others."""
    telem = AuditTelemetry()
    orchestrator = SwarmOrchestrator(
        max_workers=2,
        agent_timeout_seconds=0.05,
        max_retries=0,
        telemetry=telem,
    )

    slow_agent = MockSlowAgent("Slowpoke", sleep_seconds=0.3)
    fast_agent = MockSuccessfulAgent("FastOne", "foundation.cache")

    context = {"target_root": "/test", "evidence_facts": []}
    merged = orchestrator.run_swarm([slow_agent, fast_agent], context)

    concept_ids = {d.concept_id for d in merged.decisions}
    assert "foundation.cache" in concept_ids
    assert any("Slowpoke" in cid for cid in concept_ids)
    assert any(f.get("is_timeout") for f in telem.failed_agents)


def test_swarm_task_caching_and_deduplication():
    telem = AuditTelemetry()
    cache = ContentCache(telemetry=telem)
    orchestrator = SwarmOrchestrator(max_workers=2, cache=cache, telemetry=telem)

    agent = MockSuccessfulAgent("CachedWorker", "foundation.dedup")
    context = {"target_root": "/test", "evidence_facts": [{"dummy": 1}]}

    # First execution: executes and populates cache
    merged1 = orchestrator.run_swarm([agent], context)
    assert len(merged1.decisions) == 1

    # Second execution: retrieved from cache
    merged2 = orchestrator.run_swarm([agent], context)
    assert len(merged2.decisions) == 1
    assert telem.cache_hits >= 1


class MockConcurrencyTrackingAgent:
    """Agent that monitors concurrent active worker count."""

    def __init__(self, agent_id: str, tracker: dict[str, Any], sleep_seconds: float = 0.04) -> None:
        self.agent_id = agent_id
        self.agent_name = f"concurrency_{agent_id}"
        self.tracker = tracker
        self.sleep_seconds = sleep_seconds

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        with self.tracker["lock"]:
            self.tracker["current"] += 1
            if self.tracker["current"] > self.tracker["max_seen"]:
                self.tracker["max_seen"] = self.tracker["current"]

        time.sleep(self.sleep_seconds)

        with self.tracker["lock"]:
            self.tracker["current"] -= 1

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "run_id": "test_run",
            "target_root": "",
            "concepts_evaluated": 1,
            "decisions": [
                {
                    "concept_id": f"concurrency.{self.agent_id}",
                    "concept_name": "concurrency",
                    "status": DecisionStatus.IMPLEMENTED.value,
                    "confidence": 0.9,
                    "evidence": [],
                    "misconfiguration": None,
                    "gaps": [],
                    "recommendation": None,
                    "priority": "info",
                }
            ],
        }


class MockFatalAgent:
    """Agent that fails immediately with a non-retryable exception."""

    def __init__(self, agent_id: str, exception_cls: type = TypeError) -> None:
        self.agent_id = agent_id
        self.agent_name = f"fatal_{agent_id}"
        self.exception_cls = exception_cls
        self.call_count = 0

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        raise self.exception_cls(f"Fatal non-retryable error in {self.agent_id}")


def test_bounded_worker_concurrency():
    """Verify that active worker count is strictly bounded by max_workers."""
    tracker = {"current": 0, "max_seen": 0, "lock": threading.Lock()}
    telem = AuditTelemetry()
    max_workers = 2
    orchestrator = SwarmOrchestrator(max_workers=max_workers, telemetry=telem)

    agents = [MockConcurrencyTrackingAgent(f"Agent_{i}", tracker, sleep_seconds=0.04) for i in range(6)]
    context = {"target_root": "/test", "evidence_facts": []}

    merged = orchestrator.run_swarm(agents, context)

    assert len(merged.decisions) == 6
    assert tracker["max_seen"] <= max_workers, f"Active workers exceeded limit: {tracker['max_seen']} > {max_workers}"
    assert tracker["current"] == 0


def test_failure_isolation_quad_matrix():
    """Verify Agent A (crash), Agent B (success), Agent C (success), Agent D (timeout).

    Expected:
    - B and C complete normally
    - A and D recorded as failed/isolated
    - Overall audit continues
    - Final output identifies partial/incomplete domains
    - Telemetry records both failures
    - Merger remains valid
    """
    telem = AuditTelemetry()
    orchestrator = SwarmOrchestrator(
        max_workers=4,
        agent_timeout_seconds=0.05,
        max_retries=1,
        backoff_base_seconds=0.01,
        telemetry=telem,
    )

    agent_a_crash = MockFailingAgent("Agent_A_Crash", fail_count=999)
    agent_b_success = MockSuccessfulAgent("Agent_B_Success", "api.rest")
    agent_c_success = MockSuccessfulAgent("Agent_C_Success", "data.storage")
    agent_d_timeout = MockSlowAgent("Agent_D_Timeout", sleep_seconds=0.3)

    context = {"target_root": "/test", "evidence_facts": []}
    merged = orchestrator.run_swarm([agent_a_crash, agent_b_success, agent_c_success, agent_d_timeout], context)

    # Decisions for all 4 agents exist in the merged result
    decision_map = {d.concept_id: d for d in merged.decisions}

    # B and C succeeded
    assert "api.rest" in decision_map
    assert decision_map["api.rest"].status == DecisionStatus.IMPLEMENTED
    assert "data.storage" in decision_map
    assert decision_map["data.storage"].status == DecisionStatus.IMPLEMENTED

    # A (crash) and D (timeout) recorded as isolated failures
    assert "agent.Agent_A_Crash.status" in decision_map
    assert decision_map["agent.Agent_A_Crash.status"].status == DecisionStatus.UNKNOWN
    assert any("Simulated crash" in g for g in decision_map["agent.Agent_A_Crash.status"].gaps)

    assert "agent.Agent_D_Timeout.timeout" in decision_map
    assert decision_map["agent.Agent_D_Timeout.timeout"].status == DecisionStatus.UNKNOWN
    assert any("timed out" in g for g in decision_map["agent.Agent_D_Timeout.timeout"].gaps)

    # Telemetry captures both failed agents
    failed_ids = {f["agent_id"] for f in telem.failed_agents}
    assert "Agent_A_Crash" in failed_ids
    assert "Agent_D_Timeout" in failed_ids
    assert any(f["agent_id"] == "Agent_D_Timeout" and f.get("is_timeout") for f in telem.failed_agents)


def test_non_retryable_exceptions_fail_fast():
    """Verify that permanent errors (TypeError, SyntaxError, etc.) are not blindly retried."""
    telem = AuditTelemetry()
    orchestrator = SwarmOrchestrator(max_workers=2, max_retries=3, backoff_base_seconds=0.01, telemetry=telem)

    fatal_agent = MockFatalAgent("FatalAgent", exception_cls=TypeError)
    context = {"target_root": "/test", "evidence_facts": []}

    merged = orchestrator.run_swarm([fatal_agent], context)

    assert len(merged.decisions) == 1
    # Call count MUST be 1 - no retries attempted for TypeError
    assert fatal_agent.call_count == 1
    assert telem.retry_counts.get("FatalAgent", 0) == 0
    assert len(telem.failed_agents) == 1
    assert telem.failed_agents[0]["agent_id"] == "FatalAgent"


def test_audit_determinism_across_runs():
    """Verify that identical repo + configuration produces deterministic audit decisions despite jitter."""
    context = {"target_root": "/test", "evidence_facts": []}

    agents_run1 = [
        MockSuccessfulAgent("F-01", "foundation.caching"),
        MockFailingAgent("D-01", fail_count=1),  # retries once then recovers
        MockSuccessfulAgent("D-21", "frontend.rendering"),
    ]
    orchestrator1 = SwarmOrchestrator(max_workers=3, max_retries=2, backoff_base_seconds=0.01)
    merged1 = orchestrator1.run_swarm(agents_run1, context)

    agents_run2 = [
        MockSuccessfulAgent("F-01", "foundation.caching"),
        MockFailingAgent("D-01", fail_count=1),
        MockSuccessfulAgent("D-21", "frontend.rendering"),
    ]
    orchestrator2 = SwarmOrchestrator(max_workers=3, max_retries=2, backoff_base_seconds=0.01)
    merged2 = orchestrator2.run_swarm(agents_run2, context)

    decisions1 = [(d.concept_id, d.status, d.confidence, d.priority) for d in merged1.decisions]
    decisions2 = [(d.concept_id, d.status, d.confidence, d.priority) for d in merged2.decisions]

    assert decisions1 == decisions2


def test_fact_digest_cache_invalidation():
    """Verify changing evidence fact snippet invalidates task cache entry."""
    telem = AuditTelemetry()
    cache = ContentCache(telemetry=telem)
    orchestrator = SwarmOrchestrator(max_workers=2, cache=cache, telemetry=telem)

    agent = MockSuccessfulAgent("WorkerA", "foundation.cache")

    # Initial execution
    ctx_v1 = {"target_root": "/test", "evidence_facts": [{"file_path": "a.py", "snippet": "redis.v1()"}]}
    orchestrator.run_swarm([agent], ctx_v1)
    assert telem.cache_hits == 0

    # Repeat with exact same facts -> Cache hit
    orchestrator.run_swarm([agent], ctx_v1)
    assert telem.cache_hits == 1

    # Repeat with modified snippet -> Cache miss and re-execution
    ctx_v2 = {"target_root": "/test", "evidence_facts": [{"file_path": "a.py", "snippet": "redis.v2()"}]}
    orchestrator.run_swarm([agent], ctx_v2)
    assert telem.cache_hits == 1  # Hits did not increment


def test_telemetry_thread_safety_high_concurrency():
    """Verify telemetry counters and lifecycle updates are thread-safe under concurrent stress."""
    telem = AuditTelemetry()

    def worker_activity(worker_idx: int):
        for _ in range(50):
            telem.record_cache_hit()
            telem.record_cache_miss()
            telem.record_retry(f"agent_{worker_idx}")
            with telem.time_agent(f"agent_{worker_idx}"):
                pass
            telem.record_agent_failure(f"agent_{worker_idx}", "transient warning", is_timeout=False)

    threads = [threading.Thread(target=worker_activity, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 8 threads * 50 = 400
    assert telem.cache_hits == 400
    assert telem.cache_misses == 400
    assert sum(telem.retry_counts.values()) == 400
    assert len(telem.failed_agents) == 400
    assert len(telem.active_agents) == 0
    assert telem.to_dict()["cache_hits"] == 400



