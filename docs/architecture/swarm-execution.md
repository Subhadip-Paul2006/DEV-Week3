# SDAT Architecture — Swarm Execution

**Status:** Implemented & Verified in Codebase  
**Core Source:** [sdat/swarm/orchestrator.py](../../sdat/swarm/orchestrator.py), [sdat/swarm/merger.py](../../sdat/swarm/merger.py), [sdat/swarm/agents/](../../sdat/swarm/agents/)

---

## 1. Swarm Architecture Principles

The SDAT Swarm is designed as a **resilient, concurrent, distributed multi-agent evaluation engine**. Rather than running a monolithic auditor that sequentially processes hundreds of rules, SDAT dispatches specialized agents that independently evaluate distinct subsets of system design concepts.

### Key Operational Invariants
1. **Complete Decoupling from AI:** All swarm agents are fully deterministic by default. An agent does not require external LLM calls to evaluate AST facts against knowledge base rules.
2. **Absolute Failure Isolation:** A fatal crash or timeout in Agent A (e.g., `MLAgent`) will never abort Agent B (e.g., `FoundationAgent`). Unhandled exceptions are logged to telemetry, and the swarm proceeds.
3. **Bounded Concurrency & Task Caching:** Work is scheduled through a bounded worker pool (`ThreadPoolExecutor`), with content-hashed task caching to eliminate duplicate computation.

---

## 2. Swarm Agent Contract (`SwarmAgent`)

Every agent participating in the swarm implements the `SwarmAgent` runtime-checkable protocol defined in [sdat/swarm/orchestrator.py](../../sdat/swarm/orchestrator.py#L41):

```python
@runtime_checkable
class SwarmAgent(Protocol):
    agent_id: str      # e.g., 'F-01', 'D-21', 'D-backend'
    agent_name: str    # e.g., 'foundation_rules_agent', 'frontend_agent'

    def run(self, project_context: dict[str, Any]) -> dict[str, Any]:
        """Execute evaluation and return structured decision dictionary."""
        ...
```

### Agent Input Contract (`project_context`)
Agents receive a standardized context dictionary:
* `target_root`: Absolute path to the inspected codebase.
* `run_id`: Unique identifier for the audit session.
* `project_type`: Detected or user-specified classification (e.g. `backend`, `frontend`, `ml`).
* `evidence_facts`: List of typed `EvidenceFact` objects emitted by scanners.
* `bundles`: Correlated `EvidenceBundle` instances grouped by concept.
* `signals`: Legacy signal list provided for backward compatibility.

### Agent Output Contract (`agent_result`)
Agents return a structured dictionary conforming to [AGENTS.md](../../AGENTS.md#3-agent-output-contract):
```json
{
  "agent_id": "F-01",
  "agent_name": "foundation_rules_agent",
  "run_id": "audit_1710000000",
  "target_root": "/path/to/project",
  "concepts_evaluated": 5,
  "decisions": [
    {
      "concept_id": "foundation.caching",
      "concept_name": "caching",
      "status": "implemented",
      "confidence": 0.95,
      "priority": "info",
      "evidence": [
        {"file": "app/cache.py", "line": 12, "snippet": "client = redis.Redis(...)", "note": "Redis client initialized"}
      ],
      "misconfiguration": null,
      "gaps": [],
      "recommendation": null
    }
  ]
}
```

---

## 3. Orchestration & Resilience Mechanisms

The `SwarmOrchestrator` implements industrial-grade task coordination:

### 3.1 Bounded Worker Pool
* Initialized with `max_workers` (default: 4 concurrent threads).
* Tasks are submitted to a `ThreadPoolExecutor` and tracked via `concurrent.futures`.

### 3.2 Task-Level Content-Hashed Deduplication
Before executing an agent, the orchestrator computes a deterministic SHA-256 digest based on the agent's ID, target root, and the exact content hashes of all `EvidenceFact` snippets in the context:
```python
cache_key = self._compute_task_cache_key(agent_id, project_context)
```
If an identical codebase state was evaluated previously, results are retrieved instantly from disk cache, skipping redundant re-evaluation.

### 3.3 Per-Agent Timeouts & Cancellation
Each agent execution is wrapped in a hard timeout (`agent_timeout_seconds`, default: 30.0s). If an agent blocks or runs into an infinite loop:
1. `future.result(timeout=...)` raises `TimeoutError`.
2. The orchestrator calls `future.cancel()`.
3. The failure is recorded in `AuditTelemetry`.
4. Other agents continue unaffected.

### 3.4 Exception Classification & Jittered Retries
Errors during agent execution are classified into two categories:
* **Non-Retryable Exceptions:** Fundamental logic errors (`TypeError`, `ValueError`, `KeyError`, `AttributeError`, `SyntaxError`, `ImportError`, `PermissionError`, `IndexError`). These fail fast without burning retry budget.
* **Transient Exceptions:** I/O or operational errors. Retried up to `max_retries` (default: 2) with exponential backoff and randomized jitter:
  $$\text{delay} = \text{backoff\_base} \times 2^{\text{attempt}} + \text{random}(0, 0.1)$$

---

## 4. Result Merging & Conflict Resolution

Because multiple agents can evaluate related concepts, `sdat/swarm/merger.py` applies deterministic conflict resolution:

```
[Agent F-01 Decisions] ──┐
[Agent D-01 Decisions] ──┼──► Swarm Merger (merger.py) ──► Unified Decisions
[Agent KP-ML Decisions] ──┘
```

### Resolution Rules:
1. **Owning Agent Priority:** If Agent A is declared in the Knowledge Base as the primary owner of concept `C`, its verdict takes precedence over secondary opinions.
2. **Confidence Tie-Breaking:** If ownership is tied or undeclared, the decision with the higher architectural `confidence` score is selected.
3. **Deduplication:** Concept findings are unified so that final reports contain exactly one authoritative verdict per evaluated concept.

---

## 5. Current Agent Roles and Implementation Status

| Agent Class / Role | Module Path | Implemented Status | Verification Evidence |
| :--- | :--- | :--- | :--- |
| `FoundationAgent` | `sdat/swarm/agents/foundation.py` | **Implemented & Verified** | Tests pass in `tests/swarm/` |
| `KnowledgePackAgent` | `sdat/swarm/agents/knowledge_pack.py` | **Implemented & Verified** | Adapts ML and NLP packs in `tests/` |
| `BackendAgent` | `sdat/backend/agent.py` | **Implemented & Verified** | Tested in `tests/backend/` |
| `FrontendAgent` | `sdat/frontend/agent.py` | **Implemented & Verified** | Tested in `tests/frontend/` |
| `MLKnowledgePack` | `sdat/ml/knowledge_pack.py` | **Implemented & Verified** | Tested in `tests/ml/` |
| `NLPKnowledgePack` | `sdat/nlp/knowledge_pack.py` | **Implemented & Verified** | Tested in `tests/nlp/` |
| `SwarmOrchestrator` | `sdat/swarm/orchestrator.py` | **Implemented & Verified** | Validated in `tests/swarm/test_swarm_orchestrator.py` |
| `Result Merger` | `sdat/swarm/merger.py` | **Implemented & Verified** | Tested in `tests/swarm/` |
| Full 24 Domain Agent Prompts | `concepts/domains/` | **Partially Implemented** | Backend, Frontend, ML, NLP active; others stubbed |
