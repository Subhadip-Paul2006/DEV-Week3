# AGENTS.md — Agent Contract for SDAT Swarm

**Version:** 2.0.0 (Two-Tier Swarm)
**Last updated:** 2026-09-30

This document defines the interface every agent in SDAT must implement. Agents are the workhorses of the audit — they receive project signals, evaluate system-design concepts, and return structured decisions.

---

## 1. Agent Identity & KnowledgePack Binding

Each agent has:
- **Agent ID:** `F-01` through `F-20` (Foundation) or `D-01` through `D-24` (Domain)
- **Directory name:** `f01_caching_agent/` or `d01_api_design_agent/`
- **Concept file:** The YAML file under `concepts/` that declares `owning_agent: F-XX` or `D-XX`
- **KnowledgePack Binding:** An agent executes in the context of a domain `KnowledgePack` (`sdat/knowledge/models.py`), evaluating owned domain/core concepts using canonical rules.

### Canonical Separation & Knowledge Relationship
```text
Language ──────► Evidence (AST facts, configurations, calls)
Domain   ──────► KnowledgePack (concepts, capabilities, rules)
Concept  ──────► Rule (evaluation logic)
Rule     ──────► Evidence (verifiable facts)
Agent    ──────► KnowledgePack execution (specialist auditor)
```
- **"Names are clues. Behavior is evidence."**
- A programming language tells SDAT how code is written, never what the system does. Agents must be activated by Domain / KnowledgePack requirements, not by language detection alone.

---

## 2. Agent Input Contract

Every agent receives a **project_context** bundle containing:

```json
{
  "target_root": "/abs/path/to/project",
  "project_profile": {
    "languages": [{"name": "python", "confidence": 1.0}, {"name": "typescript", "confidence": 1.0}],
    "frameworks": [{"name": "fastapi", "confidence": 0.95}, {"name": "react", "confidence": 0.90}],
    "project_types": ["backend-web", "blockchain-web3"],
    "blockchain": {"detected": true, "chains": ["polygon"], "confidence": 0.88},
    "applicable_rule_packs": ["core.system-design", "domain.backend-web", "domain.blockchain-web3"]
  },
  "classification": {
    "primary": ["backend-web", "blockchain-web3"],
    "secondary": ["rag-langchain"],
    "languages_detected": ["python", "typescript"],
    "frameworks_detected": ["fastapi", "react"]
  },
  "research_report": {
    "peer_patterns": ["..."],
    "literature_findings": ["..."],
    "custom_kb": {"added_concepts": []}
  },
  "concepts": [
    {
      "id": "foundation.caching",
      "category": "foundation",
      "definition": "Storing frequently accessed data...",
      "signals": {
        "present": ["redis import", "cache decorator", "cache.get calls"],
        "absent": ["no TTL configured", "no eviction policy", "no invalidation strategy"]
      },
      "smells": [
        "Cache without TTL → stale data",
        "Cache on write but never invalidate on update",
        "Caching user-specific data without namespace isolation"
      ],
      "related": ["foundation.circuit-breaker"]
    }
  ],
  "evidence_facts": [
    {
      "kind": "import",
      "subject": "redis",
      "language": "python",
      "file_path": "app/cache.py",
      "line_range": [3, 3],
      "snippet": "import redis",
      "library": "redis-py",
      "framework": null,
      "extraction_confidence": 1.0
    },
    {
      "kind": "instantiation",
      "subject": "redis.Redis",
      "language": "python",
      "file_path": "app/cache.py",
      "line_range": [5, 5],
      "snippet": "client = redis.Redis(host='localhost', port=6379)",
      "scope": "get_redis_client",
      "extraction_confidence": 0.95
    },
    {
      "kind": "call",
      "subject": "client.set",
      "language": "python",
      "file_path": "app/cache.py",
      "line_range": [8, 8],
      "snippet": "client.set('user_profile', data)",
      "call_target": "redis.Redis.set",
      "call_args_schema": "(str, any)",
      "ttl_observed": false,
      "extraction_confidence": 0.95,
      "identifier_hints": ["cache"]
    }
  ],
  "signals": [
    {"signal": "redis import", "file": "app/cache.py", "line": 3, "snippet": "import redis"},
    {"signal": "no TTL configured", "file": "app/cache.py", "line": 8, "snippet": "client.set('user_profile', data)"}
  ]
}
```

> **Note on Compatibility:** `evidence_facts` is the primary, strongly-typed structural input. `signals` is preserved as a legacy view during the v0.4.0 migration.

---

## 3. Agent Output Contract

Every agent MUST return a JSON object matching this schema:

```json
{
  "agent_id": "F-01",
  "agent_name": "caching_agent",
  "run_id": "abc-123",
  "target_root": "/abs/path/to/project",
  "concepts_evaluated": 1,
  "decisions": [
    {
      "concept_id": "foundation.caching",
      "concept_name": "caching",
      "status": "implemented",
      "confidence": 0.92,
      "evidence": [
        {"file": "app/cache.py", "line": 3, "snippet": "import redis", "note": "Redis client initialized"}
      ],
      "misconfiguration": null,
      "gaps": [],
      "recommendation": null,
      "priority": "info"
    },
    {
      "concept_id": "foundation.circuit-breaker",
      "concept_name": "circuit-breaker",
      "status": "missing",
      "confidence": 0.85,
      "evidence": [],
      "misconfiguration": null,
      "gaps": ["No circuit-breaker library imported (no pybreaker, no resilience4j, no opossum)", "All external HTTP calls are direct without fallback wrapper"],
      "recommendation": "Add pybreaker or tenacity with circuit-breaker pattern around all external HTTP calls. Start with failure_threshold=5, recovery_timeout=30.",
      "priority": "critical"
    },
    {
      "concept_id": "foundation.retries",
      "concept_name": "retries",
      "status": "misconfigured",
      "confidence": 0.88,
      "evidence": [
        {"file": "app/payment.py", "line": 45, "snippet": "requests.post(url, json=data)", "note": "Direct HTTP call with no retry wrapper"}
      ],
      "misconfiguration": "Retries exist but use fixed delay (1s) without jitter. No max_retries limit. No backoff strategy. Risk: retry storm on upstream failures.",
      "gaps": ["No jitter", "No max retries", "No exponential backoff"],
      "recommendation": "Replace with tenacity with retry=stop_after_attempt(3), wait=exponential(multiplier=1, min=1, max=10). Add jitter via retry_jitter.",
      "priority": "high"
    }
  ]
}
```

### Status values:
- `"implemented"` — concept is correctly present
- `"missing"` — concept is absent and should be added
- `"misconfigured"` — concept exists but has problems
- `"unknown"` — agent could not determine status (insufficient signals)

### Priority values:
- `"critical"` — likely to cause system crash or data loss
- `"high"` — significant reliability or performance risk
- `"medium"` — should be addressed; technical debt
- `"low"` — nice-to-have improvement
- `"info"` — informational; concept is in good shape

---

## 4. Agent Structure (Directory Layout)

Each agent directory contains:

```
f01_caching_agent/
├── agent.yaml           # Agent metadata
├── agent.md             # Full prompt (agent's instructions)
├── README.md            # What this agent audits, its philosophy
└── tests/
    ├── test_fixtures/   # Sample projects for testing
    └── test_agent.py    # Unit tests
```

### `agent.yaml` (metadata)

```yaml
id: F-01
name: caching_agent
tier: 1                          # 1 = foundation (always-on), 2 = domain (classification-driven)
concept_category: foundation
concepts_owned:
  - foundation.caching
description: Audits caching strategies, eviction policies, TTL, invalidation, and cache consistency patterns.
languages: [any]
frameworks: []
always_on: true
```

### `agent.md` (the prompt)

The prompt must:
1. State the agent's role and scope
2. Reference the concept definitions from the KB
3. Process the `evidence_facts` (and legacy signals) structurally, examining call paths, imports, configuration keys, and control flow
4. Treat identifier names and filenames as weak hints, never as conclusive evidence
5. Apply judgment using the concept's smells and recommendations
6. Output strictly valid JSON matching the output schema
7. Cite file paths and line numbers for every evidence entry
8. Include `confidence` scores (0.0–1.0) representing the agent's architectural assessment certainty

---

## 5. Agent Execution Rules

1. **Stick to owned concepts only.** If the input includes concepts not owned by this agent, ignore them. The merger handles cross-agent decisions.
2. **Cite structural facts or don't claim.** Every `implemented` or `misconfigured` decision must have at least one concrete evidence entry (file + line + snippet). Filenames, class names, or comments alone are weak corroborating hints, not architectural truth. If structural proof is absent, mark as `missing` or `unknown`.
3. **Use confidence honestly.** High confidence (>0.8) = strong structural evidence (call graph, configuration, control flow). Low confidence (<0.5) = weak hint or ambiguous pattern. Note: agent `confidence` is architectural certainty, distinct from scanner `extraction_confidence`.
4. **Don't duplicate.** If another agent already covered a related concept, trust their output and move on.
5. **Report only actionable findings.** No fluff. Every `missing` must have a `recommendation`. Every `misconfigured` must explain what's wrong and how to fix it.
6. **Research provides context, NOT target proof.** Peer patterns and literature findings provide architectural context, expected patterns, and severity justification. A peer or reference project using a pattern is **NEVER** proof that the target project implements it. Target repository implementation truth comes strictly from scanner `EvidenceFact`s.
7. **Never infer project purpose from language alone.** A programming language describes how software is written, not what it does. Do not evaluate backend REST rules on a Python codebase if the `ProjectProfile` classifies it as game development or a CLI tool.
8. **No hallucinated files.** Only reference files that exist in `target_root`. Verify paths before citing.

---

## 6. Agent Communication

Agents do NOT communicate directly with each other. Communication is through the merger:

```
Agent F-01 → {decisions}
Agent F-02 → {decisions}
Agent F-03 → {decisions}
       ↓
   Merger (merger.py)
       ↓
  Unified JSON (all decisions, deduplicated)
       ↓
   Renderer → Reports
```

If two agents emit decisions for the same concept, the merger:
1. Prefers the agent that **owns** the concept (per `owning_agent` in the KB)
2. If tie: prefers higher confidence
3. Logs a warning for manual review

---

## 7. Agent Template (Copy-Paste for New Agents)

```markdown
# [Agent Name] — System Design Auditor

You are the **[concept name] auditor** for a system-design audit tool.

## Your scope
You audit ONLY these concepts:
- `[concept-id]`: [one-line definition]

## Input you receive
- `project_context.project_profile`: structured repository profile (languages, frameworks, workloads, rule packs)
- `project_context.evidence_facts`: structured AST, control-flow, and config facts from code scanners
- `project_context.signals`: legacy signal list (for backward compatibility)
- `project_context.concepts`: the KB entries for concepts you own
- `project_context.research_report`: optional peer analysis and literature findings (external context only, never target proof)
- `project_context.target_root`: absolute path to the project being audited

## Your task
For each concept you own:
1. Scan `evidence_facts` for structural evidence of implementation, absence, or misconfiguration
2. Look past symbol/file names to verify actual behavioral execution and configuration
3. Never infer project workload from language alone; align your evaluation with `project_profile.project_types`
4. Use `research_report` for external architectural context and pattern expectations, NEVER as proof of target implementation
5. Apply the concept's "smells" checklist
6. Decide: `implemented` | `missing` | `misconfigured` | `unknown`
7. Output a structured decision with evidence, gaps, and recommendations

## Output format
Output ONLY valid JSON matching this schema:
{
  "agent_id": "F-XX",
  "decisions": [
    {
      "concept_id": "...",
      "status": "...",
      "confidence": 0.0-1.0,
      "evidence": [{"file": "...", "line": N, "snippet": "...", "note": "..."}],
      "misconfiguration": "... or null",
      "gaps": ["..."],
      "recommendation": "... or null",
      "priority": "critical|high|medium|low|info"
    }
  ]
}
```

---

## 8. Testing an Agent

Each agent should be tested against known projects:

```bash
# In the agent's test directory:
pytest test_agent.py

# test_agent.py should:
# 1. Load a fixture project (a small repo with known system-design patterns)
# 2. Run the agent against it
# 3. Assert expected decisions (implemented/missing/misconfigured)
# 4. Assert no hallucinated file paths
# 5. Assert all evidence has file+line+snippet
```

---

## 9. Adding a New Concept to an Existing Agent

1. Add the concept YAML file under `concepts/<category>/`
2. Set `owning_agent: F-XX` or `D-XX` to point to the correct agent
3. Update the agent's `agent.yaml` `concepts_owned` list
4. Update the agent's `agent.md` to include the new concept
5. Add test fixtures for the new concept
6. Run tests

---

## 10. Agent Execution Order

1. Foundation agents (F-01 through F-20) run first — they're the bedrock
2. Domain agents (D-01 through D-24) run in parallel with each other
3. F-99 (general) runs last as a fallback for any concepts no other agent claimed
4. Within each tier, agents run in parallel (bounded by `max_concurrent_agents` in config)

---

## 11. AI Layer Integration & Developer Invariants

When developing or integrating agents and downstream enhancement tools:

1. **SDAT Core Independence:**
   - The core audit engine (scanners, rules, knowledge base, merger, and deterministic reporting) MUST remain fully functional without any AI model configured.
   - AI is strictly an **optional enhancement layer**. Never introduce a mandatory runtime AI dependency into the core audit path.

2. **AI Gateway / Provider Abstraction:**
   - Any AI interaction must pass through the **AI Gateway** abstraction layer (`sdat/ai/gateway.py`).
   - Agents and tools must never bind directly to a single provider (e.g. OpenAI, Anthropic, Gemini, Groq, Ollama).
   - Local models (Qwen Coder, DeepSeek, GPT-OSS, Devstral, Gemma, Phi, GLM), hosted free-access APIs, and Bring-Your-Own-Key (BYOK) providers must remain plug-and-play interchangeable.

3. **Deterministic Evidence is Authoritative:**
   - AI models assist in generating plain-language explanations, executive summaries, and conversational Q&A.
   - AI MUST NEVER silently modify, invent, suppress, or override factual evidence, detection status, or severity scores produced by deterministic scanners and verified rules.

4. **Context Grounding for Chatbot & Multimodal Tools:**
   - Future conversational assistants and multimodal tools (e.g., architecture diagram understanding) must operate with strictly bounded, grounded context drawn from SDAT findings.
   - If a selected model lacks vision or tool capabilities, the feature must gracefully degrade while core SDAT continues normal execution.

5. **Secret Hygiene:**
   - Never embed, log, or commit API keys or authentication tokens into source files, fixtures, or version-controlled configs. All credentials must resolve via environment variables or secure storage.

6. **Solution Phase Placement:**
   - The interactive, guided remediation "Solution Phase" is strictly reserved as the **final implementation phase** of SDAT, after all audit, gateway, reporting, and evaluation capabilities are solid.
   - Any future solution workflow must operate in an interactive proposal mode requiring explicit human consent before touching user code.

---

*This document is the single source of truth for all SDAT agents. Any agent that doesn't match this contract is broken.*

## graphify

This project uses a local, code-only knowledge graph at graphify-out/ to answer repository questions with focused context.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>" --budget 800` when graphify-out/graph.json exists. Raise the budget only when the result lacks needed detail. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. Prefer these scoped results over GRAPH_REPORT.md or broad raw source dumps.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
