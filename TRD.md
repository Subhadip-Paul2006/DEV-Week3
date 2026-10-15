# Technical Requirements Document — System Design Audit Tool (SDAT)

**Status:** 🔵 Planned (Phase 0 / 1) — v0.4.0 architecture specification (Two-Tier Swarm + Research Edition)
**Owner:** Subhadip Paul
**Last updated:** 2026-09-30

This document defines HOW SDAT achieves the requirements specified in `PRD.md`. It is normative — any code that deviates from it without a documented `PHASES.md` exception is a bug.

---

## 1. System Topology — Layered Architecture Pipeline

```text
                       TARGET REPOSITORY
                              │
                              ▼
                     Repository Discovery
                              │
                              ▼
                Language / Ecosystem Profiling
                              │
                              ▼
                   Project / Workload Profile (ProjectProfile)
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
        Language / Structural       Domain Context
             Scanners              / Knowledge Packs
                 │                         │
                 └────────────┬────────────┘
                              ▼
                         EvidenceFact
                              │
                              ▼
                    Evidence Aggregator
                              │
                              ▼
                       EvidenceBundle
                              │
                              ▼
                  Deterministic Baseline
                         Audit
                              │
                 ┌────────────┴────────────┐
                 │                         │
              NO AI                      AI ON
                 │                         │
                 │                         ▼
                 │                Research / Context
                 │                         │
                 │                         ▼
                 │                Domain / Chain-Specific
                 │                    Analysis
                 │                         │
                 │                         ▼
                 │                   DesignDelta
                 │                         │
                 └────────────┬────────────┘
                              ▼
                       Final Audit / Plan
```

**Logical pipeline layers:**

| Layer | Name | Deterministic | Uses LLM | Role |
|-------|------|---------------|----------|------|
| L0.5 | Repository Profiler | ✅ | No | Discovers source files, dependencies, manifests, and ecosystem markers |
| L1.0 | Knowledge Base & Packs | ✅ | No | Defines universal concepts, domain rules, questions, and evidence requirements |
| L1.5 | Language Scanners | ✅ | No | AST, control-flow, and config static analysis; extracts typed `EvidenceFact`s |
| L1.8 | Evidence Aggregator | ✅ | No | Correlates, indexes, and bundles facts into per-concept `EvidenceBundle`s |
| L2.0 | Project Classifier | Partial (heuristic) | Optional (refinement) | Synthesizes `ProjectProfile` across 28 categories and selects active Knowledge Packs |
| L3.0 | Deterministic Baseline | ✅ | No | Evaluates foundation and domain baseline rules (including chain-neutral Web3) |
| L3.5 | Optional AI Layer | ❌ | Yes (AI Gateway) | Researches peer/chain constraints, grounds explanations, and creates `DesignDelta` |
| L4.0 | Merger & Renderer | ✅ | No | Deduplicates decisions, resolves conflicts, and renders Archify reports/diagrams |

---

## 1.1 Canonical Knowledge Architecture Contract

SDAT establishes a strict separation of concerns across the knowledge evaluation pipeline:

```text
Language ──────► Evidence (structural EvidenceFacts)
Domain   ──────► KnowledgePack (concepts, capabilities, rules)
Concept  ──────► Rule (evaluation logic)
Rule     ──────► Evidence (grounded structural observations)
Agent    ──────► KnowledgePack execution (specialist auditor)
```

### 1.1.1 Architectural Layer Definitions
1. **Language:** "How is the software written?" (scanners emit structural `EvidenceFact`s; never determines workload).
2. **Domain:** "What kind of software/system is being built?" (Frontend, Backend, Database, Web3, ML, NLP, DevOps, etc.).
3. **Capability:** "What observable capability exists?" (Structural signal presence like RPC client or React rendering, without premature audit judgment).
4. **Concept:** "What architectural principle should be considered?" (Clean hierarchy: Core universal vs Domain-specific).
5. **Rule:** "How should that concept be evaluated?" (Evaluates evidence facts with deterministic severity and logic).
6. **Evidence:** "What concrete repository/runtime observation supports evaluation?" (Canonical `EvidenceFact`s with AST/file/line/snippet grounding).
7. **Agent:** "Which specialist execution context evaluates the relevant concepts?" (Swarm auditor bound to a `KnowledgePack`).

### 1.1.2 KnowledgePack Contract (`sdat.knowledge.models.KnowledgePack`)
- `id`: Globally unique identifier (e.g., `kp.frontend`, `kp.core.system-design`).
- `domain`: Associated domain name.
- `version`: Semantic version string.
- `concepts`: List of domain-owned `Concept` instances.
- `capabilities`: Observable capabilities defined by this pack.
- `rules`: Evaluation `Rule` instances bound to concepts.
- `evidence_requirements`: Evidence expectations per concept/rule.
- `dependencies`: Prerequisite knowledge pack IDs (e.g., `kp.frontend` depends on `kp.core`).
- `scoring_dimensions`: List of scoring dimensions for the domain.
- `recommendations`: Remediation guidance catalog.

### 1.1.3 Universal vs Domain Concept Specialization
Universal concepts (`caching`, `retry`, `timeout`, `observability`, `concurrency`, `security`, `idempotency`) live strictly in `concepts/core/`. Domain concepts in `concepts/domains/` specialize or extend them:
- `core.caching` ──► specialized by `frontend.client-caching`
- `core.retries` ──► specialized by `web3.rpc-retry`
- `core.security` ──► specialized by `web3.key-management`

### 1.1.4 4-Tier Scoring Architecture
Scores are computed deterministically through a 4-tier pipeline without hardcoded weights in concepts:
```text
Concept / Rule Results (implemented / missing / misconfigured)
        │
        ▼
Dimension Scores (e.g., Rendering, Loading, Navigation, State, Security)
        │
        ▼
Domain Scores (e.g., Frontend Score: 85/100)
        │
        ▼
Application-Level Summary (Weighted overall audit score across active domains)
```

---

## 2. Project Classifier

### 2.1 Purpose & Core Architectural Principles

Determine the observed technical and workload profile of the repository.

> **Fundamental Principle:** *"A programming language describes how software is written; project classification describes what the software is doing."*

SDAT explicitly rejects one-language-to-one-purpose mappings:
- `Python` is not inherently `backend-web`; it may be a CLI tool, game engine, ML pipeline, or Web3 client.
- `Go` is not inherently `backend-server`; it may be a network proxy, systems daemon, or blockchain client.
- `Rust` is not inherently `systems`; it may be an async microservice, embedded controller, or P2P daemon.
- `Web3` is an application architecture, not a programming language.

**Multi-Domain Classification:**
A project may belong to multiple workloads simultaneously (e.g., Python + FastAPI + Redis + Web3 RPC client maps to both `backend-web` and `blockchain-web3`). SDAT evaluates applicable rules across all matched domains.

### 2.1.1 ProjectProfile Concept (Planned Specification)

The classifier synthesizes a unified `ProjectProfile` object that acts as the single source of truth for repository characteristics:

```yaml
ProjectProfile:
  languages:
    - name: python
      version_hint: ">=3.11"
      confidence: 1.0
  frameworks:
    - name: fastapi
      confidence: 0.95
    - name: web3py
      confidence: 0.90
  ecosystems:
    - python-pip
  project_types:
    - backend-web
    - blockchain-web3
  capabilities:
    - async_event_loop
    - rpc_client
    - relational_db_access
  deployment_model: microservice
  data_stores:
    - postgresql
    - redis
  communication_patterns:
    - rest_api
    - json_rpc
  external_services:
    - alchemy_rpc
  blockchain:
    detected: true
    chains: ["polygon", "ethereum"] # or ["unknown"]
    confidence: 0.88
  applicable_rule_packs:
    - core.system-design
    - domain.backend-web
    - domain.blockchain-web3
```

### 2.1.2 KnowledgePack Concept (Planned Specification)

Knowledge is organized into modular `KnowledgePack` bundles:
```yaml
KnowledgePack:
  id: domain.blockchain-web3
  domain: blockchain-web3
  concepts:
    - blockchain-web3.rpc-retry
    - blockchain-web3.tx-idempotency
    - blockchain-web3.reorg-tolerance
  rules:
    - rule_id: web3-rpc-fallback
      severity: high
      requires_evidence:
        kind: call
        call_target: "web3.*"
  questions:
    - "Does the client implement failover across multiple RPC providers?"
    - "Are transactions idempotent with deterministic nonce allocation?"
  recommendations:
    - "Configure fallback RPC provider endpoints and retry with exponential backoff."
```

### 2.2 Classifier Inputs

1. **Manifest files**: `package.json`, `pyproject.toml`, `requirements.txt`, `Cargo.toml`, `go.mod`, `composer.json`, `Podfile`, `pubspec.yaml`, `Gemfile`, `pom.xml`, `build.gradle`, `Makefile`, `CMakeLists.txt`, `*.gemspec`, `setup.py`
2. **Directory structure**: `ios/`, `android/`, `firmware/`, `kernel/`, `contracts/`, `models/`, `agents/`, `plugins/`, `cli/`, `cmd/`, `src-tauri/`, `flow/`, etc.
3. **File extensions**: ratios of `.py` to `.rs` to `.swift`, presence of `.sol`, `.vy`, `.cu`, etc.
4. **Sample file contents**: top 5 most-recently-modified files per category directory (snippet analysis)
5. **README / docs**: first 100 lines, tag extraction
6. **CI/CD configs**: `.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`

### 2.3 Classification Logic

```
classify(target):
    signals = collect_signals(target)       # fast, sampled
    heuristic_scores = apply_heuristics(signals)   # deterministic rules
    if config.classifier.use_llm_refinement:
        refined = llm_refine(signals, heuristic_scores)  # optional LLM pass
        return merge(heuristic_scores, refined)
    else:
        return heuristic_scores
```

### 2.4 Classifier Output Schema

```json
{
  "schema_version": "1.0.0",
  "target_root": "/abs/path/to/target",
  "classified_at": "2026-09-30T14:22:01Z",
  "primary": ["backend-web", "blockchain-web3"],
  "secondary": ["rag-langchain"],
  "confidence": {
    "backend-web": 0.94,
    "blockchain-web3": 0.88,
    "rag-langchain": 0.71,
    "cli-tools": 0.18
  },
  "languages_detected": ["python", "typescript"],
  "frameworks_detected": ["fastapi", "react", "web3py"],
  "manifest_files_analyzed": ["package.json", "pyproject.toml"],
  "directory_signals": {
    "ios/": false,
    "android/": false,
    "contracts/": false,
    "kernel/": false,
    "models/": true,
    "agents/": false
  },
  "blockchain_context": {
    "detected": true,
    "chains": ["polygon"],
    "confidence": 0.85
  },
  "recommended_agents": ["D-01", "D-03", "D-09", "F-01", "F-04", "F-05", "F-06", "F-07", "F-08", "F-09", "F-13", "F-19", "F-20"],
  "skipped_agents": ["D-08", "D-11", "D-15", "D-16", "D-17"],
  "skip_reasons": {
    "D-08": "No mobile directory or mobile manifest files detected",
    "D-15": "No Terraform/Helm/Ansible manifests detected",
    "D-16": "No game engine project files detected",
    "D-17": "No sensor/IoT/SCADA imports detected"
  },
  "reasoning": "FastAPI backend with Web3 client integration. RPC endpoints targeted at Polygon network."
}
```

### 2.5 Classification Heuristics (Deterministic)

| Signal | Boosts |
|--------|--------|
| `models/` directory, `.pkl`/`.pt`/`.h5` files | `ml`, `personal-llm`, `transformers` |
| `contracts/` directory, `.sol` files, `hardhat.config.*` | `blockchain-web3` |
| `ios/` + `.swift` files | `mobile-android-ios` |
| `android/` + Kotlin + `AndroidManifest.xml` | `mobile-android-ios` |
| `pubspec.yaml` + `.dart` files | `mobile-android-ios` (Flutter variant) |
| `kernel/`, `drivers/`, `.ko` files | `os-building` |
| `firmware/`, `embedded/`, GPIO imports | `hardware-iot` |
| `Routers/`, `socket.*` usage, raw TCP/UDP | `networking` |
| `cmd/`, `cli/`, Click/Typer/Clap imports | `cli-tools` |
| Telegram/Discord/Slack bot SDK imports | `bots` |
| `.github/workflows/` with action steps | `workflow-automation` |
| Terraform/HCL/Ansible/Helm charts | `devops` |
| Game engine project files (`.unity`, `.godot`, `.uproject`) or ECS patterns | `game-development` |
| Sensor data ingestion, SCADA, telemetry, industrial protocols | `sensor-projects` |
| `kernel/`, `drivers/`, `.ko` files | `os-building` |
| LangChain / LlamaIndex imports, `vectorstore/` | `rag-langchain` |
| Multiple `agent.py` files, `tools.py`, A2A protocols | `multi-agent-orchestrator` |
| Pentest frameworks (Metasploit modules, Burp extensions) | `cybersecurity`, `hacking-tools` |
| React/Vue/Svelte/Angular + Vite/webpack | `frontend-web` |
| FastAPI/Express/NestJS/Gin/Actix + SQL/NoSQL | `backend-web` |
| SQL query files, migration scripts, custom storage engines | `database-projects` |
| PyTorch torchvision / YOLO / OpenCV imports | `computer-vision` |
| PyTorch Geometric / DGL imports | `graph-neural-networks` |
| LSTM/GRU/RNN explicit layer imports | `sequential-models` |

### 2.6 Dynamic Agent Selection

Foundation agents (F-01 through F-20) are **always-on** — they run on every project. The agent map below controls only Tier 2 (domain) agent dispatch.

```yaml
# config/swarm_agent_map.yaml
agent_map:
  backend-web: [D-01, D-02, D-03, D-22]
  frontend-web: [D-21]
  cli-tools: [D-01]
  networking: [D-18]
  cybersecurity: [D-02, D-10]
  blockchain-web3: [D-02, D-09, D-10]
  hardware-iot: [D-11, D-17]
  devops: [D-15, D-24]
  game-development: [D-16]
  sensor-projects: [D-17]
  ml: [D-03, D-04]
  nlp: [D-04]
  computer-vision: [D-05]
  graph-neural-networks: [D-06]
  sequential-models: [D-07]
  transformers: [D-04, D-20]
  rag-langchain: [D-02, D-03, D-04]
  workflow-automation: [D-23]
  plugins: [D-01]
  packages-libraries: [D-01]
  personal-llm: [D-02, D-04, D-20]
  multi-agent-orchestrator: [D-19, D-20]
  bots: [D-12]
  hacking-tools: [D-10]
  mobile-android-ios: [D-08]
  database-projects: [D-03, D-13]
  agentic-automation: [D-14]
  os-building: [D-11, D-24]

# Tier 1 — Foundation agents (always-on, cannot be skipped by classifier):
always_on: [F-01, F-02, F-03, F-04, F-05, F-06, F-07, F-08, F-09, F-10, F-11, F-12, F-13, F-14, F-15, F-16, F-17, F-18, F-19, F-20]
```

The orchestrator computes the dispatch set:

```python
# Tier 1: ALL 20 foundation agents are ALWAYS included
dispatch_set = {F-01, F-02, ..., F-20}  # all foundation agents

# Tier 2: domain agents selected by classification
for category in classification.primary + classification.secondary:
    dispatch_set.update(agent_map.get(category, []))

dispatch_set -= set(swarm_config.skip_agents)  # user override
dispatch_set |= set(swarm_config.force_agents)  # user override
```

---

### 2.7 Language Scanners as Capability Extractors

Language scanners are **capability extractors**, not architectural evaluators. 
- Scanners parse language ASTs, configuration manifests, and dependency declarations to emit strongly-typed `EvidenceFact` records.
- Scanners NEVER infer or enforce project workload rules:
  - `PythonScanner` extracts Python AST, call, and config facts (never assumes REST API).
  - `GoScanner` extracts Go goroutines, channels, and package calls (never assumes server rules).
  - `RustScanner` extracts Rust traits, async blocks, and crate usage (never assumes systems rules).
- The canonical pipeline remains:
  ```text
  Language Scanner → EvidenceFact[] → Evidence Aggregator → EvidenceBundle[] → Swarm / Rule Evaluation
  ```
- *Backward Compatibility:* Scanners preserve the `extract_signals()` method as a compatibility bridge, but all internal reasoning consumes `EvidenceFact`s and `EvidenceBundle`s.

### 2.8 Two-Tiered Web3 Auditing Architecture

Web3 is an application architecture and workload category, **not a programming language**. It can be written in Solidity, Rust, Go, TypeScript, Python, C++, etc. Furthermore, Web3 detection is distinct from Chain identification ("unknown chain" is a valid, normal state).

#### Tier 1 — Chain-Neutral Web3 Baseline Audit (Deterministic, Zero AI)
The core audit engine evaluates universal blockchain client responsibilities deterministically without any AI model:
- **Wallet Lifecycle:** Secure client instantiation, provider connection, session cleanup.
- **Transaction Lifecycle:** Creation, signing, submission, and confirmation tracking.
- **RPC Communication:** Timeout limits, connection failover, multi-provider redundancy.
- **Retries & Idempotency:** Exponential backoff with jitter on transient RPC drops; idempotency tokens.
- **Nonce & Sequencing:** Local nonce tracking, replacement fee handling, and sequence queues.
- **Event Processing:** Filter subscriptions, event polling, and persistent indexing.
- **On-chain / Off-chain Boundaries:** Appropriate caching of on-chain state; separating compute from storage.
- **Reorg & Finality:** Waiting for safe block confirmations before treating state as finalized.
- **Credential Protection:** Zero hardcoded private keys or mnemonic phrases; KMS or env resolution.
- **Queues & Rate Limiting:** Background queues for broadcast batches; provider rate-limit throttling.
- **Observability:** Metrics for gas spent, transaction failure rates, and RPC latency.

#### Tier 2 — Chain-Specific AI Research (Optional Enhancement)
When an AI model is configured via the AI Gateway, SDAT investigates network-specific realities:
- Context identification: Ethereum, Polygon, Arbitrum, Solana, or unknown.
- Gathers chain-specific gas volatility profiles, reorg depth conventions, and custom RPC quirks.
- **Strict Evidence Integrity:** External research findings provide context and operational recommendations. They MUST NEVER be cited as proof that the target codebase implements a pattern. Code facts come strictly from scanner `EvidenceFact`s.

### 2.9 DesignDelta Specification (Planned Concept)

The `DesignDelta` reconciles generic baseline findings with chain-specific or domain-specific research:

```yaml
DesignDelta:
  finding_id: "D09-TX-01"
  baseline_finding:
    concept_id: "blockchain-web3.transaction-confirmation"
    status: "misconfigured"
    note: "Transactions assumed final after 1 block confirmation."
  chain_context:
    chain: "polygon"
    network_id: 137
  chain_specific_consideration:
    issue: "Polygon PoS reorgs can frequently exceed 5 blocks during network congestion."
    reference: "Polygon developer documentation on reorg depth"
  architectural_implication:
    severity: "critical"
    impact: "Transactions thought confirmed may be orphaned, causing inconsistent off-chain order state."
  proposed_change:
    summary: "Increase confirmation threshold to 32 blocks or adopt the 2-step state commitment pattern."
    actionable_steps:
      - "Update ConfirmationBlocks parameter in config/web3.py from 1 to 32."
      - "Emit off-chain event status as 'unconfirmed' until finality block is mined."
  evidence_citations:
    - file: "services/tx_manager.py"
      line_range: [45, 52]
      fact_kind: "call"
      snippet: "receipt = client.wait_for_transaction_receipt(tx_hash, timeout=120)"
  research_citations:
    - "Polygon PoS Reorg Analysis & Finality Guide (2025)"
```

---

## 3. Research Agent

### 3.1 Purpose

Before the audit, gather external context: similar projects, best practices, books/articles. Produce a research report that the user reads FIRST.

### 3.2 Research Pipeline

```
1. Take classification output
2. Generate search queries:
   - "{language} {primary_category} production architecture"
   - "{language} {primary_category} best practices system design"
   - "{framework} {secondary_category} example projects github"
   - "top open source {primary_category} projects 2026"
   - "{primary_category} system design book"
3. Execute searches via web_fetch / web_search
4. Filter: only trusted domains (GitHub, arxiv.org, official docs, recognized publishers)
5. Extract: project name, language, framework, architecture highlights, system-design patterns used
6. Cluster results; deduplicate
7. Compare target's signal set vs. peer's signal set → identify gaps
8. Render research report
```

### 3.3 Research Agent Inputs

```
research/inputs/
├── classification.json          # from L2.0
├── signals-light.json           # from L1.5 (sampled)
├── target-summary.md            # 1-page auto-generated summary
└── search-strategy.yaml         # query templates
```

### 3.4 Research Agent Outputs

```
research/outputs/
├── similar-projects.json        # GitHub repos found, ranked by relevance
├── references.json              # Books, articles, docs
├── peer-patterns.json           # Patterns extracted from peers
├── custom-kb-slice/             # If no peers found: custom knowledge base slice
│   ├── concepts/
│   └── INDEX.yaml
└── research-report.json         # Structured form of 00-research-report.md
```

### 3.5 Research Report (`00-research-report.md`)

```markdown
# System Design Research Report

**Target:** `/abs/path/to/target`
**Classification:** backend-web + rag-langchain (confidence: 0.94, 0.71)
**Languages:** Python, TypeScript
**Frameworks:** FastAPI, React, LangChain, ChromaDB
**Generated:** 2026-09-30T14:22:01Z

---

## Similar Projects Found

7 open-source projects with similar profile:

| Project | Stars | Language | Framework | Key Patterns |
|---------|-------|----------|-----------|--------------|
| langchain-ai/langchain | 95k | Python | LangChain | RAG, vector stores, agent loops |
| run-llama/llama_index | 35k | Python | LlamaIndex | RAG, indexing, retrieval |
| ... | ... | ... | ... | ... |

(Full table with 7-10 entries)

---

## Patterns Used by Peers (Missing in Your Project)

| Pattern | Used by | Missing in Target |
|---------|---------|-------------------|
| Streaming responses (SSE) | 5 of 7 peers | Yes — no streaming detected |
| Prompt caching | 4 of 7 peers | Yes |
| Reranking step | 6 of 7 peers | Yes |
| Query rewriting | 5 of 7 peers | Yes |
| Observability (Langfuse/LangSmith) | 6 of 7 peers | Yes — no trace collection |

---

## Books & Articles Consulted

- "Designing Data-Intensive Applications" by Kleppmann — relevant chapters cited
- "LLM Engineer's Handbook" (2025)
- LangChain official docs: https://...
- Pinecone RAG best practices: https://...

---

## Self-Improvement Notes

Not applicable — sufficient peer references found.

---

## Concepts Recommended for Audit Priority

Based on peer analysis, the swarm should prioritize:
1. Streaming responses (RAG category)
2. Prompt caching (personal-llm category)
3. Reranking pipeline (rag-langchain)
4. Observability integration (always-on)
5. Query rewriting (rag-langchain)

These are surfaced to the orchestrator as `priority_overrides` for the audit phase.
```

### 3.6 Self-Improvement Mode (No References Found)

When the Research Agent cannot find ≥ 3 similar projects (novel/emerging domain):

```
1. Detect: insufficient peers (count < 3 OR all peers score < relevance_threshold)
2. Fall back to general literature:
   - Search arxiv.org for relevant academic papers
   - Search O'Reilly, Manning, Packt book catalogs
   - Search conference proceedings (NeurIPS, OSDI, SOSP, VLDB, SIGCOMM)
3. Synthesize a custom knowledge base slice:
   - Extract patterns from literature
   - Author concept files in the standard format
   - Save to .sdat-cache/research/custom-kb-slice/
4. Emit research-self-improvement.md:
   - Lists what literature was consulted
   - Lists custom concepts synthesized
   - Notes confidence level (LOW/MEDIUM/HIGH)
   - Invites user to review the custom slice
5. Use the custom slice as the KB for the audit
```

### 3.7 Research Agent Security

The Research Agent is the **first layer that makes outbound network requests**. This expands the attack surface significantly.

**Threats:**

| Threat | Mitigation |
|--------|-----------|
| Malicious search result with  | Sanitize all fetched content; cap excerpt length; never inject into prompts without validation |
| Phishing link in search results | Only fetch from allowlisted domains (github.com, arxiv.org, official docs) |
| Untrusted markdown with embedded scripts | Render with sanitization; never `eval()` fetched content |
| Network exfiltration of target code | Never include target repo content in search queries; only metadata |

See SECURITY.md §3.4 for the full threat model.

---

## 4. Component Architecture

### 4.1 Layer 1 — Knowledge Base (extended)

**`owning_agent` is now critical** — every concept MUST declare which agent owns it. Foundation concepts use `F-XX`, domain concepts use `D-XX`.

```yaml
# Foundation concept example (Tier 1)
---
id: foundation.circuit-breaker
category: foundation
owning_agent: F-04            # Circuit Breaker & Fault Tolerance Agent (always-on)
maturity: stable
languages: [any]
tags: [reliability, fault-tolerance, pattern]
related: [foundation.retries, foundation.bulkhead, foundation.timeout]
---

# Domain concept example (Tier 2)
---
id: blockchain-web3.gas-optimization
category: blockchain-web3
owning_agent: D-09            # Blockchain / Web3 Agent (classification-driven)
maturity: stable
languages: [solidity, rust]
tags: [gas, optimization, smart-contract]
related: [blockchain-web3.reentrancy-guard, blockchain-web3.event-emission]
---
```

**Foundation concept categories** (always-on, run on every project):

- `foundation.caching` (F-01)
- `foundation.hld` (F-02)
- `foundation.lld` (F-03)
- `foundation.circuit-breaker` (F-04)
- `foundation.retries` (F-05)
- `foundation.connection-pooling` (F-06)
- `foundation.message-queues` (F-07)
- `foundation.fault-tolerance` (F-08)
- `foundation.idempotency` (F-09)
- `foundation.cap-consistency` (F-10)
- `foundation.database-scaling` (F-11)
- `foundation.consistent-hashing` (F-12)
- `foundation.rate-limiting` (F-13)
- `foundation.load-balancers` (F-14)
- `foundation.proxies` (F-15)
- `foundation.protocols` (F-16)
- `foundation.client-server` (F-17)
- `foundation.latency-bandwidth` (F-18)
- `foundation.observability` (F-19)
- `foundation.security-fundamentals` (F-20)

**Domain concept categories** (classification-driven):

- `backend-web-*`
- `frontend-web-*`
- `cli-tools-*`
- `networking-*`
- `cybersecurity-*`
- `blockchain-web3-*`
- `hardware-iot-*`
- `ml-*` (computer vision, GNN, sequential, transformer sub-categories)
- `nlp-*`
- `rag-langchain-*`
- `workflow-automation-*`
- `plugins-*`
- `packages-libraries-*`
- `personal-llm-*`
- `multi-agent-orchestrator-*`
- `bots-*`
- `hacking-tools-*`
- `mobile-android-ios-*`
- `database-internals-*`
- `database-projects-*`
- `agentic-automation-*`
- `os-building-*`
- `devops-*` (NEW)
- `game-development-*` (NEW)
- `sensor-projects-*` (NEW)

### 4.2 Layer 1.5 — Language Scanners (Common Evidence Model)

Scanners are **concept-agnostic fact extractors**. They inspect source files using AST parsing, control-flow analysis, call-graph analysis, and configuration inspection, emitting typed `EvidenceFact` records.

> **Principle:** A scanner reports *what it observed* (imports, decorators, call patterns, control flow, config keys). An agent decides *what it means* (whether a concept is implemented, missing, or misconfigured).

#### Scanner Protocol (`sdat/scanners/base.py`)

```python
@runtime_checkable
class LanguageScanner(Protocol):
    language_id: str
    file_extensions: tuple[str, ...]

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: set[str] | None = None,
    ) -> list[Path]:
        """Discover source files matching this scanner's extensions."""
        ...

    def extract_evidence(self, files: list[Path]) -> list[EvidenceFact]:
        """Extract typed, structural EvidenceFacts from a collection of files."""
        ...

    def scan_file(self, file_path: Path | str) -> list[EvidenceFact]:
        """Scan a single source file and return detected EvidenceFacts."""
        ...

    def scan_project(
        self,
        root: Path | str,
        exclude_dirs: set[str] | None = None,
    ) -> list[FileEvidence]:
        """Scan entire project directory and return FileEvidence records."""
        ...

    # Backward compatibility bridge:
    def extract_signals(self, files: list[Path]) -> list[Signal]:
        """Legacy signal extraction method, bridged to EvidenceFact."""
        ...
```

Scanner catalog:

```
scanners/
├── python_scanner.py
├── typescript_scanner.py
├── go_scanner.py
├── rust_scanner.py              # NEW
├── c_cpp_scanner.py             # NEW (combined C/C++)
├── php_scanner.py
├── java_scanner.py
├── ruby_scanner.py
├── swift_scanner.py             # NEW
├── dart_scanner.py              # NEW (Flutter)
├── react_scanner.py
├── vue_scanner.py
├── svelte_scanner.py
└── angular_scanner.py
```

`scanners/registry.yaml` updated with the new entries.

### 4.2.1 Layer 1.8 — Evidence Aggregator

**Location:** `sdat/evidence/aggregator.py`

The Evidence Aggregator consumes the raw stream of `EvidenceFact`s emitted by all active scanners, correlates facts across files and languages, and packages them into per-concept `EvidenceBundle`s:

1. **Correlation:** Connects import facts with instantiation facts and downstream call-graph facts (e.g. `import redis` + `client = redis.Redis()` + `client.get()`).
2. **Indexing:** Groups facts against concept IDs using the knowledge base concept criteria and rules.
3. **Absence Synthesis:** Analyzes what structural patterns were expected for detected architectures but absent (e.g., external HTTP calls with no retry or circuit breaker wrapper).
4. **Bundle Generation:** Emits `EvidenceBundle(concept_id, facts, peer_patterns, literature_findings)` delivered directly to the owning agent.

### 4.3 Layer 2.0 — Classifier

**Location:** `classifier/` directory.

```
classifier/
├── classify.py                  # entry point
├── manifest_parser.py           # reads package.json, pyproject.toml, etc.
├── directory_analyzer.py        # walks directory structure
├── framework_detector.py        # regex/AST for framework markers
├── heuristics.yaml              # deterministic rule set
├── llm_refiner.py               # optional LLM-based refinement (off by default)
└── output_schema.json
```

### 4.4 Layer 2.5 — Research Agent

**Location:** `research/` directory.

```
research/
├── research_agent.py            # entry point
├── web_search.py                # uses web_search / web_fetch primitives
├── github_search.py             # GitHub-specific search (REST API: search/repositories)
├── reference_filter.py          # allowlist of trusted domains
├── peer_analyzer.py             # extracts patterns from peer READMEs
├── literature_search.py         # arxiv, book catalogs
├── custom_kb_builder.py         # synthesizes concept files from literature
└── research_report_renderer.py
```

The Research Agent uses the same provider adapters as the swarm, but is independently configurable:

```yaml
research:
  provider: claude-code
  enabled: true
  max_search_queries: 10
  max_peers_to_analyze: 5
  peer_min_relevance: 0.6
  literature_min_papers: 3
  build_custom_kb_on_no_peers: true
  network_timeout_seconds: 30
  trusted_domains_only: true
  allowed_domains:
    - github.com
    - raw.githubusercontent.com
    - arxiv.org
    - openreview.net
    - langchain.com
    - python.org
    - rust-lang.org
    - nodejs.org
    - kubernetes.io
    - docker.com
    - soliditylang.org
```

### 4.5 Layer 3.0 — Orchestrator + Swarm

**Location:** `swarm/` directory (unchanged, but dispatch logic now reads classifier output).

```
swarm/
├── orchestrator.py              # now reads classification.json to build dispatch set
├── merger.py
├── agents/
│   ├── f01_caching_agent/                 # F-01 (Tier 1 — always-on)
│   ├── f02_hld_agent/                     # F-02 (Tier 1 — always-on)
│   ├── f03_lld_agent/                     # F-03 (Tier 1 — always-on)
│   ├── f04_circuit_breaker_agent/         # F-04 (Tier 1 — always-on)
│   ├── f05_retries_agent/                 # F-05 (Tier 1 — always-on)
│   ├── f06_connection_pooling_agent/      # F-06 (Tier 1 — always-on)
│   ├── f07_message_queues_agent/          # F-07 (Tier 1 — always-on)
│   ├── f08_fault_tolerance_agent/         # F-08 (Tier 1 — always-on)
│   ├── f09_idempotency_agent/             # F-09 (Tier 1 — always-on)
│   ├── f10_cap_consistency_agent/         # F-10 (Tier 1 — always-on)
│   ├── f11_db_scaling_agent/              # F-11 (Tier 1 — always-on)
│   ├── f12_consistent_hashing_agent/      # F-12 (Tier 1 — always-on)
│   ├── f13_rate_limiting_agent/           # F-13 (Tier 1 — always-on)
│   ├── f14_load_balancers_agent/          # F-14 (Tier 1 — always-on)
│   ├── f15_proxies_agent/                 # F-15 (Tier 1 — always-on)
│   ├── f16_protocols_agent/               # F-16 (Tier 1 — always-on)
│   ├── f17_client_server_agent/           # F-17 (Tier 1 — always-on)
│   ├── f18_latency_bandwidth_agent/       # F-18 (Tier 1 — always-on)
│   ├── f19_observability_agent/           # F-19 (Tier 1 — always-on)
│   ├── f20_security_fundamentals_agent/   # F-20 (Tier 1 — always-on)
│   ├── d01_api_design_agent/              # D-01 (Tier 2)
│   ├── d02_billing_agent/                 # D-02 (Tier 2)
│   ├── d03_data_layer_agent/              # D-03 (Tier 2)
│   ├── d04_ai_llm_agent/                  # D-04 (Tier 2)
│   ├── d05_computer_vision_agent/         # D-05 (Tier 2)
│   ├── d06_gnn_agent/                     # D-06 (Tier 2)
│   ├── d07_sequential_agent/              # D-07 (Tier 2)
│   ├── d08_mobile_agent/                  # D-08 (Tier 2)
│   ├── d09_blockchain_agent/              # D-09 (Tier 2)
│   ├── d10_security_pentest_agent/        # D-10 (Tier 2)
│   ├── d11_os_embedded_agent/             # D-11 (Tier 2)
│   ├── d12_bot_agent/                     # D-12 (Tier 2)
│   ├── d13_database_internals_agent/      # D-13 (Tier 2)
│   ├── d14_agentic_automation_agent/      # D-14 (Tier 2)
│   ├── d15_devops_agent/                  # D-15 (Tier 2)
│   ├── d16_game_dev_agent/                # D-16 (Tier 2)
│   ├── d17_sensor_iot_agent/              # D-17 (Tier 2)
│   ├── d18_networking_agent/              # D-18 (Tier 2)
│   ├── d19_multi_agent_agent/             # D-19 (Tier 2)
│   ├── d20_personal_llm_agent/            # D-20 (Tier 2)
│   ├── d21_frontend_agent/                # D-21 (Tier 2)
│   ├── d22_backend_agent/                 # D-22 (Tier 2)
│   ├── d23_workflow_agent/                # D-23 (Tier 2)
│   ├── d24_infrastructure_agent/          # D-24 (Tier 2)
│   └── f99_general_agent/                 # F-99: Fallback
└── swarm_report_renderer.py
```

**Dispatch flow (extended):**

```python
classification = load_classification()
research = load_research_report()        # optional, may be None if offline

dispatch_set = compute_dispatch_set(
    classification,
    swarm_config.always_on,
    swarm_config.force_agents,
    swarm_config.skip_agents,
)

# Apply research priority overrides (peer analysis boosts certain concepts)
priority_overrides = extract_priority_overrides(research)

# Dispatch agents in parallel, bounded by max_concurrent_agents
results = dispatch_agents(dispatch_set, classification, research)

# Merge
unified = merger.merge(results)
unified = merger.apply_priority_overrides(unified, priority_overrides)

# Render
renderer.render_all(unified, classification, research, results)
```

### 4.6 Layer 4 — Renderer (extended for research + swarm reports)

```
renderer/
├── render_research_report.py    # NEW
├── render_swarm_report.py
├── render_inventory.py
├── render_gaps.py
├── render_misconfigurations.py
└── templates/
    ├── research_report.md.j2   # NEW
    ├── swarm_report.md.j2
    ├── inventory.md.j2
    ├── gaps.md.j2
    └── misconfigurations.md.j2
```

Output:

```
docs/audit/
├── 00-research-report.md      # NEW — read this first
├── 01-swarm-report.md
├── 02-inventory.md
├── 03-gaps.md
└── 04-misconfigurations.md
```

### 4.7 Frontend Auditing Architecture & KnowledgePack

Frontend auditing in SDAT is fundamentally a **workload and system-design audit**, not visual inspection or programming language syntax analysis. Language scanners (JavaScript, TypeScript, etc.) emit structural `EvidenceFact`s; the Project Classifier detects the `frontend-web` workload; the **Frontend KnowledgePack** and **D-21 Frontend Agent** evaluate architectural principles across 15 core dimensions.

```text
Target Repository
       ↓
Language Scanners (JS, TS, HTML)
       ↓
structural EvidenceFacts
       +
Optional Browser Runtime Evidence (Offline marks unmeasured)
       ↓
Frontend Page Analyzer (Routes, Complexity, Rendering models)
       ↓
Frontend KnowledgePack (15 System-Design Rule Categories)
       ↓
Frontend Scoring Engine (Explainable Dimensional Scores)
       ↓
D-21 Agent Decisions (AGENTS.md Contract)
```

#### 4.7.1 Rule Dimensions (15 Categories)
1. **Rendering Architecture**: SSR, SSG, CSR, Hydration, Streaming, and server/client component boundaries.
2. **Page / Route Architecture**: SPA vs MPA, dynamic route matching, and 404/not-found fallbacks.
3. **Loading Strategy**: Dynamic imports, code-splitting, lazy loading, and Suspense progressive loading.
4. **Runtime Performance**: Memoization (`useMemo`, `useCallback`), DOM depth, and list virtualization.
5. **DOM / Component Architecture**: Component boundaries, hook limits, and structural nesting.
6. **Responsive Design**: Viewport meta, CSS media queries, and fluid layout behavior.
7. **Asset Architecture**: Native lazy loading, Next/Image optimization, and modern asset handling.
8. **State Management**: Separation of local, shared, and global state (e.g. Redux, Zustand, Pinia).
9. **Data Fetching**: REST, GraphQL, WebSockets, Server-Sent Events, and request waterfall prevention.
10. **Caching & Client Storage**: Stale-while-revalidate queries, cache invalidation, and localStorage discipline.
11. **Error Handling & Loading UX**: Error boundaries, fallback UIs, and skeleton screens.
12. **Accessibility**: Semantic HTML5 tags, ARIA roles, alt descriptions, and keyboard navigability.
13. **Frontend Security**: XSS prevention, raw HTML sanitization (`dangerouslySetInnerHTML`), and client-side secret shielding.
14. **Network / API Architecture**: AbortController request cancellation and timeout wrappers.
15. **UX & Perceived Latency**: Progressive section loading and separating perceived latency from runtime latency.
*Web3 Intersection*: Evaluates wallet connection lifecycles, transaction states, and RPC fallbacks when a frontend interacts with Web3.

#### 4.7.2 Page-Specific vs Application-Level Analysis
The `FrontendPageAnalyzer` maps route hierarchies and generates `PageAnalysis` objects before application aggregation. High complexity on a single page is evaluated in context (e.g., dashboards with virtualization) rather than blindly penalizing element counts.

#### 4.7.3 Static vs Runtime Evidence Separation
SDAT strictly distinguishes static potential hazards from empirical runtime observations:
- Static analysis flags potential request waterfalls, eager heavy assets, or missing skeletons.
- The `RuntimePerformanceLayer` captures actual page load time, route transition time, TFR, and resource waterfalls when connected to telemetry.
- If runtime measurement is unavailable (offline run), SDAT explicitly flags metrics as `unmeasured` without fabricating synthetic numbers.

### 4.8 SDAT Internal Architecture — Production-Grade Swarm & Resilience Engine

Because SDAT is a system design audit tool, SDAT's own codebase must serve as a production-grade reference implementation of the distributed systems principles it evaluates.

```text
                     CLI / Invocations (sdat audit .)
                                  ↓
                       Multi-Language Scanners
                     (Bounded Concurrency & Cache)
                                  ↓
                        Evidence Aggregator
                (Correlations, Bundles, Telemetry)
                                  ↓
                       Swarm Orchestrator
         ┌────────────────────────┴────────────────────────┐
         ↓                                                 ↓
  Worker Limits & Queue                             Failure Isolation
  (ThreadPoolExecutor)                             (Per-Agent Timeouts)
         ↓                                                 ↓
  Transient Retries                                Content Cache Store
(Exp Backoff + Jitter)                            (SHA-256 Deduplication)
         └────────────────────────┬────────────────────────┘
                                  ↓
                       Deterministic Merger
                                  ↓
                      Renderer & Audit Reports
                      + Structured Telemetry
```

#### 4.8.1 Swarm Concurrency, Worker Limits & Queue Management
- **Bounded Concurrency:** The `SwarmOrchestrator` schedules tasks using a bounded worker pool (`ThreadPoolExecutor(max_workers=N)`), preventing unbound OS thread or process exhaustion on large target repositories.
- **Queue Observability:** Tracks `queue_depth` and `active_agents` throughout the execution lifecycle.

#### 4.8.2 Failure Isolation & Graceful Degradation
- **Fault-Tolerant Boundary:** An agent that crashes, throws an unhandled exception, or exceeds its timeout limit **never terminates the entire audit**.
- **Partial Audit Production:** Other agents continue execution and succeed. The failed agent produces an isolated diagnostics decision (`status: unknown`, `priority: high`, error details in `gaps`) and records the failure in `failed_agents` telemetry.

#### 4.8.3 Per-Agent Timeouts & Cancellation
- Every agent invocation is bounded by `agent_timeout_seconds` (default: 30s).
- Stalled or hanging agent threads are isolated as a timeout failure without blocking the orchestrator or subsequent agents.

#### 4.8.4 Transient Error Retries with Exponential Backoff
- Agents encountering transient network, I/O, or parsing faults are retried up to `max_retries` attempts.
- Uses exponential backoff with randomized jitter: $\text{delay} = \text{base} \times 2^{(\text{attempt}-1)} + \text{jitter}$ to prevent retry storms.

#### 4.8.5 Content-Hashed Caching & Task Deduplication
- Implemented via `ContentCache` (`sdat/cache/store.py`).
- **File Scanner Caching:** Keyed by scanner ID and SHA-256 file content hash. Unmodified source files are retrieved instantly without re-parsing ASTs.
- **Agent Task Deduplication:** Identical concept payloads are fingerprinted to guarantee idempotent execution.
- Integrates with telemetry to report real-time `cache_hits` and `cache_misses`.

#### 4.8.6 Structured Telemetry & Observability
- Implemented via `AuditTelemetry` (`sdat/telemetry/tracker.py`).
- Captures:
  - `audit_duration_ms`, `aggregation_duration_ms`, `report_generation_duration_ms`
  - Per-scanner durations (`scanner_duration_ms`) and per-agent durations (`agent_duration_ms`)
  - `queue_depth`, `active_agents`, and `failed_agents`
  - `retry_counts` and `cache_hits` / `cache_misses`
  - Evidence pipeline counts (raw $\rightarrow$ correlated $\rightarrow$ concept bundles)
  - Peak memory utilization (`memory_mb`) via memory tracing
  - AI request durations and isolated AI/research failure counters
- Emits structured `telemetry.json` and renders an observability section in `01-inventory.md`.

#### 4.8.7 Self-Auditing & Dogfooding
- SDAT supports self-auditing without special shortcuts:
  ```bash
  python -m sdat.cli audit . --output-dir docs/audit
  ```
- SDAT audits its own Python engine, TypeScript/Frontend rules, Go/Rust/C/PHP/Java fixtures, and outputs complete reports alongside its own telemetry.

---

## 5. Data Models

### 5.0 Common Evidence Model (`EvidenceFact` & `EvidenceKind`)

```python
class EvidenceKind(str, Enum):
    # Structural
    IMPORT = "import"                     # Module/package imported
    CALL = "call"                         # Function or method invocation
    DECORATOR = "decorator"               # Decorator applied to function/class/method
    INHERITANCE = "inheritance"           # Class inheritance hierarchy
    INSTANTIATION = "instantiation"       # Object or class instantiation
    ANNOTATION = "annotation"             # Type hint or structural annotation
    # Behavioral & Control Flow
    CONTROL_FLOW = "control_flow"         # Loop, try/except/retry, fallback branch
    ASYNC_PATTERN = "async_pattern"       # Async/await, coroutine, event loop interaction
    CONCURRENCY = "concurrency"           # Threads, multiprocessing, worker pool
    # Configuration & Environment
    CONFIG_KEY = "config_key"             # Key-value declaration in settings/config
    ENV_VAR = "env_var"                   # Environment variable access or definition
    # Data & Storage
    DB_QUERY = "db_query"                 # SQL statement, ORM query, transaction block
    SCHEMA_DEF = "schema_def"             # DB model, migration table, Pydantic/Zod schema
    MIGRATION = "migration"               # Schema migration step
    # Architecture & Manifest
    DEPENDENCY = "dependency"             # Manifest package dependency (package.json, pyproject.toml)
    FRAMEWORK_MARKER = "framework_marker" # Sentinel file or framework-specific boilerplate
    ARCHITECTURE_PATTERN = "architecture_pattern" # High-level architectural pattern
    # Explicit Absence
    ABSENT_PATTERN = "absent_pattern"     # Explicitly verified absence of required safeguard
    # Backward Compatibility
    LEGACY_SIGNAL = "legacy_signal"       # Bridge representation for legacy Signal instances


@dataclass(frozen=True)
class EvidenceFact:
    """A typed, structural, concept-agnostic observation in source code."""
    kind: EvidenceKind
    subject: str                         # Target symbol/module/key (e.g. 'redis', 'retry')
    language: str                        # 'python', 'typescript', etc.
    file_path: Path
    line_range: tuple[int, int] | None
    snippet: str                         # Verbatim source code snippet (<= 200 chars)
    scope: str | None = None             # Enclosing function or class name
    call_target: str | None = None       # Resolved/qualified call target
    call_args_schema: str | None = None  # Summary of arguments passed
    parent_symbol: str | None = None     # Base class or decorated symbol
    value_observed: str | None = None    # Config or constant value
    value_schema: str | None = None      # Type/format of observed value
    extraction_confidence: float = 1.0   # Scanner extraction certainty (not architectural verdict)
    identifier_hints: list[str] = field(default_factory=list) # Weak corroborating hints only
    framework: str | None = None         # 'fastapi', 'express', etc.
    library: str | None = None           # 'tenacity', 'redis-py', etc.
    ttl_observed: bool | None = None
    retry_count_observed: int | None = None
    timeout_observed: bool | None = None
    circuit_breaker_threshold: int | None = None


@dataclass(frozen=True)
class FileEvidence:
    """Collection of EvidenceFacts extracted from a single source file."""
    file: str
    facts: list[EvidenceFact] = field(default_factory=list)


@dataclass(frozen=True)
class EvidenceBundle:
    """Pre-correlated bundle of facts dispatched to an agent for concept evaluation."""
    concept_id: str
    facts: list[EvidenceFact]
    peer_patterns: list[str] = field(default_factory=list)
    literature_findings: list[str] = field(default_factory=list)
```

### 5.1 Classification Output

See §2.4.

### 5.2 Research Output

```python
@dataclass(frozen=True)
class ResearchOutput:
    similar_projects: list[PeerProject]
    references: list[Reference]              # books, articles, papers
    peer_patterns: list[PatternUsage]        # pattern -> peers using it -> present_in_target
    custom_kb_slice_path: Path | None        # populated if no peers found
    priority_overrides: dict[ConceptID, Priority]
    confidence: Literal["high", "medium", "low"]

@dataclass(frozen=True)
class PeerProject:
    name: str
    url: str
    stars: int
    language: str
    framework: str
    architecture_highlights: list[str]
    patterns_observed: list[ConceptID]
    relevance_score: float
```

### 5.3 Per-Agent Decision & Citations

```python
@dataclass(frozen=True)
class EvidenceCitation:
    """Ground-truth citation attached to an agent's decision."""
    file: str
    line: int
    snippet: str
    note: str = ""

@dataclass(frozen=True)
class Decision:
    """An evaluated verdict on a concept by its owning agent."""
    concept_id: str
    concept_name: str
    status: DecisionStatus              # IMPLEMENTED | MISSING | MISCONFIGURED | UNKNOWN
    confidence: float                   # 0.0 - 1.0 (Agent's architectural confidence)
    priority: Priority = Priority.INFO  # CRITICAL | HIGH | MEDIUM | LOW | INFO | N_A
    evidence: list[EvidenceCitation] = field(default_factory=list)
    misconfiguration: str | None = None
    gaps: list[str] = field(default_factory=list)
    recommendation: str | None = None
```

### 5.4 Unified Decision Output

The merger consolidates all agent `Decision` records into a canonical `decisions.json`, validating ownership and breaking ties with higher confidence scores.

### 5.5 Manifest (extended)

```json
{
  "run_id": "2026-09-30T14:22:01Z",
  "sdat_version": "0.3.0",
  "kb_version": "1.6.0",
  "auditor_provider": "claude-code",
  "research_provider": "claude-code",
  "classification": {
    "primary": ["backend-web", "rag-langchain"],
    "confidence_avg": 0.82
  },
  "research": {
    "similar_projects_found": 7,
    "references_consulted": 12,
    "peer_patterns_extracted": 18,
    "priority_overrides_emitted": 5
  },
  "agents_dispatched": 6,
  "agents_succeeded": 6,
  "agents_failed": 0,
  "agents_skipped_by_classification": 14,
  "concepts_total": 127,
  "concepts_evaluated": 41,
  "concepts_skipped_no_signals": 70,
  "concepts_skipped_no_agent": 16,
  "findings_implemented": 14,
  "findings_missing": 19,
  "findings_misconfigured": 8,
  "redirects_total": 2,
  "duration_seconds": 412.5
}
```

---

## 6. Storage & State

| Artifact | Location | Lifecycle |
|----------|----------|-----------|
| Knowledge base | `concepts/` | Versioned via Git |
| ProjectProfile / Classification | `.sdat-cache/run-<ts>/project_profile.json` | Per-run |
| EvidenceFacts (canonical) | `.sdat-cache/run-<ts>/evidence_facts.json` | Per-run |
| Signals (legacy compatibility) | `.sdat-cache/run-<ts>/signals.json` | Per-run |
| Research output | `.sdat-cache/run-<ts>/research/` | Per-run, optional |
| Custom KB slice | `.sdat-cache/run-<ts>/research/custom-kb-slice/` | Per-run, optional |
| DesignDelta (AI research) | `.sdat-cache/run-<ts>/design_delta.json` | Per-run, optional |
| Per-agent I/O | `.sdat-cache/run-<ts>/agents/<id>/` | Per-run |
| Decisions | `.sdat-cache/run-<ts>/decisions.json` | Per-run |
| Reports | `docs/audit/*.md` | Per-run, overwritten |
| Manifest | `.sdat-cache/run-<ts>/manifest.json` | Per-run |

---

## 7. Configuration (extended)

```yaml
scanners:
  enabled: [python, typescript, rust, go, c_cpp, php, java, ruby, swift, dart, react, vue, svelte, angular]
  lightweight_sample_rate: 0.05   # for classifier scan

classifier:
  enabled: true
  use_llm_refinement: false       # deterministic by default
  min_confidence_threshold: 0.5
  max_categories: 5               # cap primary + secondary

research:
  enabled: true
  provider: claude-code
  max_search_queries: 10
  max_peers_to_analyze: 5
  peer_min_relevance: 0.6
  literature_min_papers: 3
  build_custom_kb_on_no_peers: true
  network_timeout_seconds: 30
  trusted_domains_only: true
  allowed_domains:
    - github.com
    - arxiv.org
    - python.org
    - rust-lang.org
    - nodejs.org
    - langchain.com

swarm:
  mode: auto                      # auto | all | manual
  always_on: [A-06, A-07]
  force_agents: []                # always include regardless of classification
  skip_agents: []                 # never include
  max_concurrent_agents: 4
  per_agent_timeout_seconds: 600
  total_timeout_seconds: 1800
  dispatch_strategy: concurrent-all
  reroute_redirects: true

# ... rest of config (auditor, renderer) unchanged
```

---

## 8. Error Handling

| Failure | Behavior |
|---------|----------|
| Classifier heuristic fails on a manifest | Log warning, fall back to language-only classification |
| Classifier LLM refinement times out | Use heuristic result as-is |
| Research Agent cannot reach internet | Skip research, proceed to audit, log in swarm report |
| Research Agent finds 0 peers | Trigger self-improvement mode, build custom KB slice |
| Custom KB slice generation fails | Proceed with main KB only, log warning |
| Dispatched agent crashes | Mark its concepts `unknown`, surface in swarm report |
| Agent emits decisions for out-of-scope concepts | Reject, route to `redirects[]` |
| Two agents emit decisions for same concept | Higher-confidence wins, log warning |
| All dispatched agents fail | Fail the audit with clear message and partial results |

---

## 9. Performance Budget

| Stage | Budget | Notes |
|-------|--------|-------|
| Lightweight classification scan | 15s | ~5% file sample |
| Classification heuristics | <1s | Pure Python |
| Research Agent web searches | 30–120s | Network-bound; fails gracefully |
| Research Agent peer analysis | 30–60s | Per-peer file fetch + analyze |
| Full scanner invocation | 60s | Full scan after classification |
| Per-agent context build | <2s | |
| Per-agent invocation | 600s timeout, parallel up to `max_concurrent_agents` | |
| All agents complete | 600s typical, 1800s hard ceiling | |
| Merger | <1s | |
| Rendering | <2s | |
| **Total** | **<15 minutes** | With research; <10 minutes without |

---

## 10. Architectural Decisions Log

| ADR | Decision | Reason |
|-----|----------|--------|
| ADR-001 to ADR-024 | (v0.2.0 decisions) | Unchanged |
| ADR-025 | **Classifier before Research Agent** | Classification output drives search queries; can't research without knowing the category |
| ADR-026 | **Research Agent before Swarm** | Peer patterns inform priority overrides; cheaper than re-running agents |
| ADR-027 | **Self-improvement mode when no peers found** | Don't fail on novel domains; synthesize custom KB |
| ADR-028 | **Dynamic agent selection from classification** | Don't dispatch D-05 (Computer Vision) on a CLI tool; bounded work |
| ADR-029 | **Always-on: F-01 through F-20** | Foundation system-design concepts (caching, HLD, LLD, circuit breaker, retries, connection pooling, message queues, fault tolerance, idempotency, CAP, database scaling, consistent hashing, rate limiting, load balancers, proxies, protocols, client-server, latency, observability, security) apply to every project |
| ADR-030 | **Network access limited to allowlisted domains** | Defends against injection from search results |
| ADR-031 | **28-category taxonomy covers emerging domains** | Web3, IoT, OS dev, agentic automation, RAG, multi-agent, DevOps, game dev, sensors all require specialized agents |
| ADR-032 | **20 foundation agents + 24 domain agents + F-99 general** | Tier 1: universal concepts (F-01–F-20) always-on; Tier 2: domain-specific (D-01–D-24); F-99 catches uncategorized |
| ADR-033 | **Two-tier swarm architecture** | Foundation agents are the bedrock; domain agents extend coverage to niche areas |
| ADR-034 | **Research output feeds `priority_overrides`** | Peer consensus elevates concepts to audit priority |
| ADR-035 | **Custom KB slice lives in `.sdat-cache/` only** | Don't pollute the main KB with auto-generated, lower-confidence concepts |
| ADR-036 | **Common Evidence Model** | Scanners emit typed, structural `EvidenceFact`s rather than pre-assigning concepts; decouples syntax from architectural evaluation |
| ADR-037 | **Concept-Agnostic Scanners** | Scanners report what was observed (imports, AST nodes, call patterns, configs). Agents determine whether concepts are implemented, missing, or misconfigured |
| ADR-038 | **Evidence Aggregation & Legacy Signal Bridge** | Layer 1.8 groups facts into `EvidenceBundle`s per concept. Legacy `Signal` records are converted via `SignalBridge` for backward compatibility |

---

## 11. Migration from v0.2.0

v0.2.0 users (single-agent design, no classifier) can upgrade to v0.3.0:

1. Pull the latest `config.yaml` (adds `classifier:`, `research:` blocks)
2. Add new scanners to `scanners/registry.yaml` (Rust, C/C++, Swift, Dart)
3. Add `owning_agent` to any concept without one (defaults to `A-99`)
4. Optionally enable `swarm.mode: auto` (vs. legacy `manual`)

The five-report structure replaces the previous four-report structure; old reports are auto-archived.