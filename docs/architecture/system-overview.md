# SDAT Architecture — System Overview

**Internal Codename:** NIRĪKṢĀ (*तन्त्रविन्यास-निरीक्षा*)  
**Version:** 0.4.0 (Two-Tier Swarm + AI Gateway)  
**Status:** Active Production Architecture  

---

## 1. Purpose and Philosophy

The **System Design Audit Tool (SDAT)** is a portable, language-agnostic architecture auditor designed to accompany software repositories without invasive dependencies. Rather than checking for surface code syntax or generic linting errors, SDAT audits **distributed system design patterns**, structural reliability guarantees, and high-level architectural health.

### Core Philosophy: AI is Strictly Optional
As mandated by [AGENTS.md](../../AGENTS.md#11-ai-layer-integration--developer-invariants):
1. **Core Audit Engine Independence:** Scanners, rule engines, knowledge base evaluators, result mergers, and reporting operate with 100% determinism without any AI model configured.
2. **Deterministic Evidence is Authoritative:** Structural facts extracted from the Abstract Syntax Tree (AST) are ground truth. AI models cannot invent, override, or suppress verified scanner facts.
3. **Pluggable AI Enhancement:** AI models (local or cloud) serve strictly as an optional reasoning and plain-language explanation layer.

---

## 2. High-Level Subsystems

SDAT is architected around five cleanly decoupled subsystems:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SDAT CLI (sdat/cli.py)                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               1. Discovery & Scanner Engine (sdat/scanners/)           │
│  - File discovery & security boundary checks (is_secret_file)          │
│  - Multi-language AST Scanners (Python, TS, Go, Rust, C/C++, PHP, Java)│
│  - Content-hashed file caching (sdat/cache/store.py)                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Emits list[EvidenceFact])
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               2. Common Evidence Subsystem (sdat/evidence/)            │
│  - Typed Structural Observations (EvidenceFact)                        │
│  - Cross-File Correlation & Deduplication (EvidenceAggregator)         │
│  - Backward Compatibility Signal Bridge (SignalBridge)                 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Provides EvidenceBundle / Context)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               3. Knowledge & Swarm Layer (sdat/swarm/, sdat/knowledge/)│
│  - Canonical Concept Knowledge Base (concepts/core/, concepts/domains/)│
│  - Foundation Agents (F-01..F-20) evaluating core system design        │
│  - Domain Agents (D-01..D-24) & KnowledgePack Agents (ML, NLP, Backend)│
│  - Swarm Orchestrator with bounded concurrency, retries, and timeouts  │
│  - Deterministic Result Merger with conflict resolution (merger.py)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (Emits list[Decision])
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│            4. AI Enhancement Gateway (sdat/ai/) [OPTIONAL]             │
│  - Provider-agnostic gateway abstraction (sdat/ai/gateway.py)          │
│  - OpenRouter / Gemma adapters & offline cache matching                │
│  - Remediation narrative generation (fail-open to deterministic text)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               5. Report & Telemetry Generation (sdat/renderer/)        │
│  - Deterministic Jinja2 rendering: 01-inventory, 02-gaps, 03-misconfig │
│  - Rich CLI console summary cards and remediation steps               │
│  - Structured JSON telemetry: execution timing, memory, cache stats    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Breakdown and Boundaries

### 3.1 Scanner Ecosystem (`sdat/scanners/`)
SDAT does not rely on fragile regular expressions for architectural truth; it employs AST-level structural scanners configured in `sdat/scanners/registry.py`.

* **Implemented and Verified:**
  * `PythonScanner` (`.py`): Inspects AST for imports (`redis`, `pydantic`), decorators (`@retry`, `@cache`), client instantiations, control flow, and timeouts.
  * `TypeScriptScanner` (`.ts`, `.tsx`, `.js`, `.jsx`): Scans Express, React, Axios, Fetch, connection pools, and client-side caching.
  * `GoScanner` (`.go`): Detects Goroutine concurrency, context deadlines, channels, and HTTP client wrappers.
  * `RustScanner` (`.rs`): Scans Tokio async runtimes, connection pools (`r2d2`, `sqlx`), and retry patterns.
  * `CCppScanner` (`.c`, `.h`, `.cpp`): Analyzes POSIX threading, memory lifecycle, socket calls, and synchronization primitives.
  * `PhpScanner` (`.php`): Checks PDO connection configurations, cURL options, and cache drivers.
  * `JavaScanner` (`.java`): Detects Resilience4j circuit breakers, Spring cache annotations, and JDBC connection pools.
* **Planned or Framework Specific:**
  * Ruby, Swift, Dart scanners are defined as future extensions in the project specification.

### 3.2 Evidence Aggregator (`sdat/evidence/`)
The **Common Evidence Model (CEM)** strips concept bias from scanner output. Scanners emit `EvidenceFact` records (e.g., "function call to `redis.set` at line 42 with missing TTL argument").
* `EvidenceAggregator` gathers facts across files, removes exact duplicate snippets, indexes calls by scope and target, and groups related facts into `EvidenceBundle` objects.
* `SignalBridge` translates between modern typed `EvidenceFact` objects and legacy `Signal` structures for backward compatibility.

### 3.3 Two-Tier Agent Swarm (`sdat/swarm/`)
System design concepts are evaluated by specialized agents executing concurrently:
1. **Tier 1 (Foundation Agents F-01 to F-20):** Always active across all audits. They evaluate universal architectural tenets: caching, circuit breakers, retries, rate limiting, connection pooling, idempotency, observability, and security fundamentals.
2. **Tier 2 (Domain Agents D-01 to D-24):** Classification-driven specialists (e.g., Backend Web, Frontend Web, Machine Learning, NLP).
3. **KnowledgePack Agents:** Adapt deterministic knowledge packs (such as `MLKnowledgePack` and `NLPKnowledgePack`) into the swarm contract without requiring dedicated LLM prompts.
4. **Deterministic Merger (`sdat/swarm/merger.py`):** Collects decisions from all agents, deduplicates evaluations per concept, gives precedence to designated concept owners, and handles tie-breaking via confidence scoring.

### 3.4 AI Provider Gateway (`sdat/ai/`)
When `--no-ai` is not passed, SDAT invokes the AI Gateway to generate human-readable remediation cards, executive summaries, and architectural diagrams.
* **Architecture:** Implements an abstract `AIProvider` contract.
* **Fail-Open Design:** If network calls time out, API keys are missing, or JSON responses are malformed, SDAT logs the condition and seamlessly falls back to pre-defined deterministic markdown remediation.
* **Zero Leakage:** No source code or confidential credentials are ever transmitted without explicit opt-in; secret files are automatically excluded during the discovery phase.

### 3.5 Renderer Subsystem (`sdat/renderer/`)
Reports are produced deterministically using Jinja2 templates located in `sdat/renderer/templates/`:
* `01-inventory.md`: Complete audit evidence inventory of implemented patterns.
* `02-gaps.md`: Architectural gaps where recommended patterns are missing.
* `03-misconfigurations.md`: Implemented patterns identified as having dangerous parameters or smells.
* `04-remediation.md`: Concrete, actionable fix cards generated deterministically or enriched by AI.
* `telemetry.json`: Granular run metrics including per-scanner durations, cache hit ratios, and memory delta.

---

## 4. Architectural Invariants and Implementation Status

| Capability / Component | Implementation Status | Verification Evidence |
| :--- | :--- | :--- |
| Multi-language AST Scanners | **Implemented & Verified** | 468/468 unit tests passing in `tests/scanners/` |
| Content-Hashed Disk Caching | **Implemented & Verified** | Verified in `tests/cache/test_cache.py` |
| Common Evidence Model (CEM) | **Implemented & Verified** | Tested across `tests/evidence/` |
| Resilient Swarm Orchestrator | **Implemented & Verified** | Verified in `tests/swarm/test_swarm_orchestrator.py` |
| Knowledge Base Concepts | **Implemented & Verified** | 100+ concept definitions in `concepts/` |
| AI Gateway with OpenRouter/Gemma | **Implemented & Verified** | Validated in `tests/ai/test_ai_layer.py` |
| Offline Cached AI Reasoning | **Implemented & Verified** | Cached artifacts verified in `docs/audit/` |
| CLI NIRĪKṢĀ Rich Interface | **Implemented & Verified** | Executable via `sdat audit` |
| Interactive "Solution Phase" Auto-fixer | **Planned (Future Phase)** | Reserved as final phase per `AGENTS.md` §11.6 |
| Automated PyPI CI/CD Pipeline | **Planned / In-Progress** | Documented in `docs/releases/documentation-release-process.md` |
