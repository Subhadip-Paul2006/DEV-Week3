# Product Requirements Document — System Design Audit Tool (SDAT)

**Status:** Active — v0.4.0 specification (Two-Tier Swarm + Research Edition)
**Owner:** Subhadip Paul
**Last updated:** 2026-09-30

SDAT is a portable, submodule-deployable system-design auditor. It **classifies** the project type across 24+ categories, **researches similar projects** on the internet, then dispatches a **two-tier swarm**: 20 always-on foundation agents (caching, circuit breaker, connection pooling, message queues, fault tolerance, idempotency, CAP theorem, consistent hashing, rate limiting, load balancers, proxies, protocols, client-server, latency, HLD/LLD, and more) plus up to 24 domain-specific agents selected by classification. Produces five reports: research, swarm transparency, inventory, gaps, misconfigurations.

SDAT pairs with **[Archify](https://github.com/tt-a1i/archify)** for interactive diagram generation from audit findings.

---

## 1. Product Vision

SDAT is an open-source, provider-agnostic, portable system-design auditing tool that bridges the gap between *theoretical* architecture knowledge and *practical* codebase verification. It operates in two complementary modes:

```
SDAT WITHOUT AI = FULLY FUNCTIONAL CORE AUDITING TOOL
SDAT WITH AI    = CORE AUDITING + AI-ENHANCED EXPERIENCE
```

1. **Core Audit Mode (Without AI):**
   - 100% deterministic, self-contained, and offline-capable.
   - Dispatches language scanners, classifiers, and 44 swarm agents (20 foundation + up to 24 domain agents).
   - Collects typed structural `EvidenceFact`s, verifies system design smells, and assigns confidence/priority.
   - Generates comprehensive, evidence-cited markdown reports and diagrams via the **Archify** foundation.
   - **Zero AI dependencies, zero API keys, zero local LLM runtimes required.**

2. **AI-Enhanced Mode (Optional Layer):**
   - Activated via a provider-agnostic **AI Gateway** supporting Local models (e.g., Qwen Coder, DeepSeek, Gemma, Phi), Hosted/Free endpoints (e.g., Groq, NVIDIA), or user API keys (e.g., Gemini, OpenAI, Anthropic, Kimi).
   - Augments Archify reports with executive summaries, plain-language translations, and "Why This Matters" contextual analysis.
   - Unlocks an interactive **SDAT Chatbot** for grounded audit Q&A and general architecture concepts.
   - Adds **multimodal visual inspection** (architecture diagram understanding & screenshot analysis) when a vision-capable model is selected.
   - Lays the foundation for the future **Guided Solution Phase** (step-by-step interactive remediation proposals).

**The Core Tenets:**
- **Universal** — supports 14+ languages, 5+ frontend frameworks, 28 project categories
- **Foundational** — 20 always-on agents ensure core system-design concepts are never skipped
- **Evidence-Driven** — operates on deep structural evidence (AST, control flow, call relationships, configurations) rather than superficial identifier names or comments
- **Provider-Agnostic** — no vendor lock-in; interchangeable local runtimes, free-tier endpoints, and commercial APIs
- **Archify Foundation** — structured, deterministic visual reporting format that preserves factual ground truth
- **AI-Optional** — AI enhances readability and exploration, but the core audit engine never depends on an AI model to discover issues

---

## 2. User Personas

### 2.1 Open-Source Contributor

**Goal:** Understand a new project's architecture and identify risk areas.
**Scenario:** Subhadip joins a Rust project. SDAT classifies it, researches similar Rust projects, then runs all 20 foundation agents + relevant domain agents.

### 2.2 Hackathon Team

**Goal:** Assess a forked starter and identify what needs building.
**Scenario:** Team forks a Flutter + FastAPI + Web3 starter. SDAT detects 4 project types, runs foundation agents + matching domain agents, produces combined audit.

### 2.3 Engineering Auditor

**Goal:** Review a project with evidence-based suggestions.
**Scenario:** An engineer runs SDAT on a Go + Kubernetes + ML project. Foundation agents catch universal issues; domain agents catch ML-specific patterns.

### 2.4 System Design Learner

**Goal:** See how textbook concepts map onto real code.
**Scenario:** A student audits projects in different domains. Foundation agents give consistent coverage; domain agents show specialization.

### 2.5 Niche Domain Engineer

**Goal:** Audit projects in blockchain, IoT, OS dev, game dev, agentic automation.
**Scenario:** A blockchain engineer runs SDAT on a Solidity project. Foundation agents run (auth, rate limiting, observability, etc.) plus D-09 (Blockchain/Web3) for smart-contract-specific patterns.

### 2.6 OS / Systems Engineer

**Goal:** Audit C/Rust projects for kernel-level, embedded, or OS-level design patterns.
**Scenario:** An engineer building a kernel module runs SDAT. Foundation agents catch general issues; D-11 (OS/Embedded) catches memory safety and driver patterns.

### 2.7 Research Scientist

**Goal:** Audit ML/NLP/AI projects for research-grade vs. production-grade design.
**Scenario:** A researcher runs SDAT on a PyTorch + RAG + agent project. Foundation agents catch general reliability; D-04 (AI/LLM) catches RAG-specific patterns.

---

## 3. Project Classification Taxonomy

> **Fundamental Principle:** *"A programming language describes how software is written; project classification describes what the software is doing."*

SDAT classifies the target repository across 28 project categories. A project can match **one or more** types simultaneously (multi-label classification). For example, a repository combining Python + FastAPI + Redis + Web3 RPC client will be classified under both `Backend (Web)` and `Blockchain / Web3`.

SDAT strictly separates language detection from project classification:
- **Language ("How is the software written?"):** Discovered via language scanners emitting structural `EvidenceFact`s.
- **Domain ("What kind of software/system is being built?"):** Discovered via project classification, mapped to domain `KnowledgePack`s.
- **Capability ("What observable capability exists?"):** Observable technical capabilities (e.g. RPC client, React rendering) without premature audit conclusions.
- **Concept ("What architectural principle should be considered?"):** Clean hierarchy separating Core concepts (caching, retry, security) from Domain concepts (client caching, RPC retry).
- **Rule ("How should that concept be evaluated?"):** Evaluates structural evidence with deterministic severity weights.
- **Evidence ("What concrete repository/runtime observation supports evaluation?"):** Grounded `EvidenceFact`s with AST/file/line/snippet backing.
- **Agent ("Which specialist execution context evaluates the relevant concepts?"):** Executes KnowledgePacks and audits domain concepts.

Canonical Relationship:
```text
Language ──────► Evidence (structural EvidenceFacts)
Domain   ──────► KnowledgePack (concepts, capabilities, rules)
Concept  ──────► Rule (evaluation logic)
Rule     ──────► Evidence (AST facts, configurations, calls)
Agent    ──────► KnowledgePack execution (specialist audit)
```
- **"Names are clues. Behavior is evidence."** Isolated names, comments, or directory structures do not constitute architectural proof.

| # | Category | Detection Signals |
|---|----------|-------------------|
| 1 | **Networking** | Socket code, TCP/UDP servers, packet handling, network protocols, DNS |
| 2 | **Cybersecurity** | Encryption, auth flows, pentest tools, WAF, SIEM, zero-trust configs |
| 3 | **Blockchain / Web3** | Smart contracts, Solidity/Vyper, wallet integration, RPC calls, consensus code, Merkle trees (Ecosystem/workload, not a programming language) |
| 4 | **Hardware / IoT** | Embedded C, microcontrollers, sensor drivers, firmware, GPIO, MQTT, LoRa |
| 5 | **Sensor Projects** | Sensor data collection, telemetry, time-series ingestion, industrial IoT, SCADA |
| 6 | **Machine Learning** | Training loops, model weights, PyTorch/TensorFlow, feature pipelines, GPU code |
| 7 | **NLP** | Tokenization, embeddings, transformer models, text classification, spaCy/HuggingFace |
| 8 | **Computer Vision** | CNN, R-CNN, YOLO, image pipelines, OpenCV, object detection |
| 9 | **Graph Neural Networks** | PyG/DGL, graph datasets, node/edge features, GAT/GCN layers |
| 10 | **Sequential Models** | RNN, LSTM, GRU, time-series forecasting, sequence-to-sequence |
| 11 | **Transformers** | Attention layers, HuggingFace models, tokenizers, LLM serving, vLLM/Triton |
| 12 | **Frontend (Web)** | React, Vue, Svelte, Angular, Next.js, SPA patterns, routing |
| 13 | **Backend (Web)** | REST/GraphQL/gRPC APIs, server frameworks, middleware, ORMs |
| 14 | **RAG / LangChain** | Retrieval pipelines, vector DBs, chunking, embedding stores, agent chains |
| 15 | **CLI Tools** | Click/Typer/Clap, terminal UI, stdin/stdout processing, shell completions |
| 16 | **Workflow / Automation** | CI/CD pipelines, Airflow, Prefect, job schedulers, DAGs |
| 17 | **Plugins** | Plugin architectures, hook systems, extension points, plugin loaders |
| 18 | **Packages / Libraries** | Published packages, SDKs, public APIs, library documentation |
| 19 | **Personal LLM / Fine-tuning** | LoRA/PEFT, GGUF quantization, Ollama models, local inference |
| 20 | **Multi-Agent Orchestration** | Agent frameworks, task delegation, A2A protocols, agent swarms |
| 21 | **Bots (Telegram/Discord/Slack)** | Bot APIs, webhook handlers, message handlers, slash commands |
| 22 | **Security / Hacking Tools** | Pentest frameworks, exploit modules, fuzzers, scanners |
| 23 | **Mobile (Android / iOS)** | Swift/Kotlin, Flutter/Dart, mobile SDKs, app bundles, platform-specific APIs |
| 24 | **Database Projects** | Query engines, ORMs, migration tools, connection pooling, replication |
| 25 | **Agentic Automation** | Browser automation, RPA, tool-use agents, task automation |
| 26 | **DevOps** | IaC, Terraform, Ansible, monitoring stacks, deployment pipelines, infrastructure automation |
| 27 | **Game Development** | Game engines (Unity/Unreal/Godot), ECS, physics, rendering, game networking, input handling |
| 28 | **OS Building** | Kernel modules, bootloaders, system calls, memory management, process scheduling |

**Classification output** (`project-classification.json`):

```json
{
  "primary": ["backend-web", "blockchain-web3"],
  "secondary": ["rag-langchain"],
  "confidence": {
    "backend-web": 0.94,
    "blockchain-web3": 0.88,
    "rag-langchain": 0.71
  },
  "languages_detected": ["python", "typescript"],
  "frameworks_detected": ["fastapi", "react", "web3py"],
  "recommended_domain_agents": ["D-01", "D-03", "D-09"],
  "skipped_domain_agents": ["D-16", "D-17"],
  "reasoning": "FastAPI backend with Web3 blockchain integration"
}
```

---

## 4. Functional Requirements

### FR-1 — Submodule Deployment

SDAT deploys as a Git submodule inside the target repository at `.system-design-tool/`.

### FR-2 — Scanner Layer & Common Evidence Model

14 language scanners + 4 frontend framework scanners (full list in TRD §4.2). Scanners are **capability extractors**, not architectural evaluators. They do not make architectural conclusions or pre-assign concept verdicts based on keywords. Instead, scanners extract typed, structural `EvidenceFact` records (AST nodes, call targets, argument patterns, decorators, control-flow graphs, configuration keys, and manifest dependencies). The Evidence Aggregator groups these facts into concept `EvidenceBundle`s for agent and rule reasoning.

### FR-2.1 — Language Scanners as Capability Extractors
Language scanners extract structural evidence from their respective syntax and ecosystems:
- `PythonScanner` → Python structural facts
- `GoScanner` → Go structural facts
- `RustScanner` → Rust structural facts
Scanners never assume a project purpose. A Go scanner does not assume server rules, and a Python scanner does not assume backend REST rules. Applicable rules are decided by the project classification and domain knowledge packs.

### FR-2.2 — ProjectProfile (Planned Architectural Concept)
SDAT captures the target repository's holistic characteristics in a structured `ProjectProfile`:
```
ProjectProfile
├── languages (detected languages and versions)
├── frameworks (detected web/system/specialized frameworks)
├── ecosystems (runtime environments and package managers)
├── project_types (multi-label workload classifications)
├── capabilities (structural capabilities detected by scanners)
├── deployment_model (monolith, microservice, serverless, embedded)
├── data_stores (relational, document, key-value, vector, cache)
├── communication_patterns (sync REST, gRPC, async messaging, P2P)
├── external_services (third-party APIs, SaaS, cloud services)
├── blockchain
│   ├── detected (boolean)
│   ├── chains (list of identified chains or ["unknown"])
│   └── confidence (0.0 - 1.0)
└── applicable_rule_packs (list of KnowledgePack IDs to evaluate)
```
*Rule:* `ProjectProfile` is derived from verified structural evidence across multiple sources, never from language name alone.

### FR-2.3 — Knowledge Packs / Domain Rule Packs (Planned Concept)
System design evaluation is decoupled into reusable packs:
```
KnowledgePack
├── domain (e.g. Core System Design, Web Apps, Distributed Systems, Web3)
├── concepts (cataloged design patterns)
├── rules (architectural requirements and heuristics)
├── questions (audit questions to verify)
├── evidence_requirements (required EvidenceFact kinds and signatures)
├── severity (critical, high, medium, low, info)
└── recommendations (remediation guidance)
```
- **Core System Design Pack:** Universal concepts applicable across all software workloads.
- **Domain Knowledge Packs:** Specialized requirements (e.g., Web3 transaction lifecycles, Game ECS loops, IoT sensor timeouts) activated based on `ProjectProfile.project_types`.
- *Rule:* Knowledge packs dictate what *should* be verified; target repository `EvidenceFacts` provide the *proof* of what is actually implemented.

### FR-3 — Project Classifier

Before agent evaluation, SDAT classifies the target project against 28 categories using manifest analysis, directory structure, framework detection, and sampled file content. Output populates the `ProjectProfile` and drives Tier 2 agent and KnowledgePack selection.

### FR-4 — Two-Tier Swarm Architecture

**Tier 1 — Foundation Agents (20, always-on):**

F-01 Caching, F-02 HLD, F-03 LLD, F-04 Circuit Breaker & Fault Tolerance, F-05 Retries & Backoff, F-06 Connection Pooling, F-07 Message Queues & Event Streaming, F-08 Fault Tolerance & Reliability, F-09 Idempotency, F-10 CAP Theorem & Consistency, F-11 Database Scaling, F-12 Consistent Hashing, F-13 Rate Limiting, F-14 Load Balancers, F-15 Proxies, F-16 Protocols, F-17 Client-Server Model, F-18 Latency/Timeout/Bandwidth, F-19 Observability, F-20 Security Fundamentals.

These run on EVERY project. They are not optional. They are the foundation.

**Tier 2 — Domain Agents (24, classification-driven):**

D-01 API Design, D-02 Billing & Tokenization, D-03 Data Layer, D-04 AI/LLM Integration, D-05 Computer Vision, D-06 GNN/Graph, D-07 Sequential Models, D-08 Mobile Development, D-09 Blockchain/Web3, D-10 Security/Pentest, D-11 OS/Embedded, D-12 Bot/Integration, D-13 Database Internals, D-14 Agentic Automation, D-15 DevOps/CI-CD, D-16 Game Development, D-17 Sensor/IoT, D-18 Networking, D-19 Multi-Agent Orchestration, D-20 Personal LLM/Fine-tuning, D-21 Frontend, D-22 Backend, D-23 Workflow/Automation, D-24 Infrastructure & Deployment.

These run based on classifier output.

**Total: 44 specialist agents. 20 always-on + up to 24 domain-specific.**

Each concept in the knowledge base MUST declare its `owning_agent` in frontmatter. Foundation concepts get `F-01` through `F-20`. Domain concepts get `D-01` through `D-24`.

### FR-4.5 — Redirects

When an agent finds evidence of a concept outside its scope, it MUST emit a redirect record pointing to the correct owning agent.

### FR-5 — Research Agent (Pre-Audit Intelligence)

Before the audit, the Research Agent searches the internet for similar projects, compares peer architectures, extracts patterns, and produces a research report. If no peers found, it enters self-improvement mode and synthesizes a custom knowledge base slice from literature.
*Authoritative Rule:* Research findings provide external context, industry patterns, and recommendations. Research findings MUST NEVER be treated as proof that the target repository implements a pattern. Target repository facts come strictly from scanner `EvidenceFact`s.

### FR-5.1 — Two-Tiered Web3 Auditing
Web3 is evaluated in two distinct operational tiers:
1. **Tier 1 — Chain-Neutral Baseline Audit (Deterministic, Zero AI):**
   - Evaluates universal blockchain client responsibilities across wallet lifecycle, transaction signing/submission, nonce tracking, RPC error handling, retries, idempotency, event indexing, on-chain/off-chain data boundaries, reorg tolerance, key protection, and background queues.
   - Fully operational offline without any AI or external API.
2. **Tier 2 — Chain-Specific AI Research (Optional Enhancement):**
   - When AI is active, determines or receives chain context (e.g. Polygon, Ethereum, Arbitrum, or unknown).
   - Researches chain-specific parameters (gas limits, block confirmation times, reorg depth conventions, bridge/RPC quirks).
   - Generates contextual recommendations without fabricating code evidence.

### FR-5.2 — DesignDelta Architectural Plan (Planned, Optional AI)
When chain-specific or domain-specific AI research is enabled, SDAT synthesizes a `DesignDelta`:
```
DesignDelta
├── baseline_finding (finding from deterministic audit)
├── chain_specific_consideration (gas volatility, finality time, reorg risk)
├── architectural_implication (e.g. queue stalling, orphaned state)
├── proposed_change (concrete architectural modification)
├── rationale (why this matters for the identified chain)
└── evidence_and_research_citations (traceable scanner facts + research sources)
```
`DesignDelta` bridges generic baseline findings and chain-specific realities into an actionable architecture improvement plan.

### FR-5.5 — Research Agent Security

The Research Agent only makes outbound requests to a configured allowlist of trusted domains. It never sends host-repo source code in queries. All responses are schema-validated before LLM ingestion.

### FR-6 — Five Report Types

| Report | File | Purpose |
|--------|------|---------|
| **Research Report** | `00-research-report.md` | Classification, peer comparison, best-practice references |
| **Swarm Report** | `01-swarm-report.md` | Foundation agents (all 20), domain agents (dispatched), redirects, coverage |
| **Inventory** | `02-inventory.md` | Implemented concepts with evidence |
| **Gaps** | `03-gaps.md` | Missing concepts, priority-ranked |
| **Misconfigurations** | `04-misconfigurations.md` | Fragile or broken implementations |

### FR-7 — AI Gateway & Provider Abstraction (Optional Layer)

SDAT features a generic **AI Gateway** abstraction layer (`sdat/ai/gateway.py`) that decouples the audit engine from individual model vendors. SDAT agents and reporting tools interact with a standardized interface rather than binding directly to a single provider.

Supported Provider Classes:
1. **Local / Open-Source Models:** Local model runtimes (Ollama, llama.cpp, OpenAI-compatible local servers) supporting model families such as Qwen Coder, DeepSeek, GPT-OSS, Devstral, Gemma (e.g. Gemma 4), Phi, GLM, and compatible models.
2. **Hosted / Free-Access Providers:** Cloud-hosted or developer-tier endpoints offering free or community access (e.g., Groq, NVIDIA inference endpoints).
3. **Bring-Your-Own-Key (BYOK) / Paid APIs:** Direct API integration using user-supplied keys (Google Gemini, OpenAI, Anthropic, Kimi, and custom OpenAI-compatible endpoints).

**Model Capability Discovery:**
The AI Gateway dynamically probes and exposes supported capabilities:
- `text_generation`, `reasoning`, `coding`, `structured_output`, `tool_calling`, `vision`, `long_context`, `streaming`.
Unsupported capabilities gracefully disable corresponding features (e.g. vision for multimodal diagram parsing) while leaving core auditing fully intact.

### FR-8 — Report Generation & Archify Integration

SDAT uses **Archify** as the reporting and visualization foundation:
- Produces clean, readable, structured markdown reports and interactive architecture diagrams.
- Reports are 100% deterministic and complete when running with zero AI.
- All findings remain traceable to verified `EvidenceFact` citations (file path + line range + snippet).

### FR-9 — AI-Enhanced Reporting Experience (Optional)

When an AI model is configured, Archify reports are enriched with an interpretive presentation layer:
- **Executive Summary:** High-level synthesis of architecture posture and top risks.
- **"Why This Matters":** Practical business and reliability impact explanations for technical findings.
- **Plain-Language Translations:** Clear explanations of complex distributed systems concepts without jargon.
- **Integrity Rule:** AI commentary is visually distinct and MUST NOT alter, override, or suppress deterministic detection statuses, line citations, or severity scores.

### FR-10 — Dedicated SDAT Chatbot (Optional)

An interactive conversational assistant available strictly when an AI model is configured and reachable:
- **SDAT-Aware Questions:** Grounded strictly in audit results (e.g., "Why did connection pooling fail in `db.py`?"). Hallucinating nonexistent audit issues is prohibited.
- **General Conceptual Questions:** Explains theoretical concepts (e.g., "What is a circuit breaker?", "Explain CAP theorem") grounded in SDAT Knowledge Base definitions.
- **Tool-Assisted:** Uses explicit SDAT tools/functions to inspect findings on demand.

### FR-11 — Multimodal Visual Inspection (Optional)

Enabled only when the selected model supports `vision`:
1. **Architecture Diagram Understanding:** Allows users to provide a system architecture diagram or image; correlates depicted components with SDAT audit findings.
2. **Screenshot / Visual Finding Explanation:** Allows users to supply screenshots of dashboards, trace logs, or error screens to contextualize architecture smells.

### FR-12 — Productivity & User-Friendly Features

Practical enhancements to minimize time-to-insight:
- "Explain Simply" one-click action for any finding.
- "Summarize Report" action for quick team sharing.
- Finding search and category filters.
- Quick navigation links directly to affected source lines.
- Export-friendly formats for team reviews.

### FR-13 — Guided Solution Phase (Reserved for Final Implementation Stage)

When AI models are active, SDAT will eventually provide an interactive, step-by-step remediation guide:
```
Finding → Understand Problem → Why It Matters → Proposed Solution → Step 1 → Validate → Step 2 → Final Verification
```
- **Strict Human-in-the-Loop Discipline:** Operates in a guided proposal mode. Zero automatic or silent modifications to user code. Explicit user confirmation is mandatory before applying any patch.

---

## 5. Non-Functional Requirements

### NFR-1 — Performance

| Stage | Budget | Notes |
|-------|--------|-------|
| Lightweight classification scan | 15s | ~5% file sample |
| Research Agent web searches | 30–120s | Network-bound; fails gracefully |
| Full scanner invocation | 60s | AST + config facts |
| 20 foundation agents (parallel) | ~180s typical | With max_concurrent=4, ~5 batches × ~36s avg |
| Domain agents (0–24 additional) | ~0–90s | Only if classification triggers them |
| Merger + Rendering (Archify) | <2s | Deterministic markdown & diagrams |
| AI Report Enhancement (optional) | 10–30s | Local or hosted LLM pass |
| **Total (without AI)** | **<8 minutes** | Pure deterministic core audit |
| **Total (with AI & research)** | **<15 minutes** | Full pipeline with summaries |

### NFR-2 through NFR-6

Portability, Determinism, Safety, Extensibility, Offline Graceful Degradation.

### NFR-6 — Foundation Agent Guarantee

A user MUST be able to trust that the 20 foundation agents always run. This is a product guarantee. Skipping them requires explicit user action with a clear warning.

### NFR-7 — Mandatory AI Optionality

SDAT without AI is a first-class, fully functional system design auditing tool. No feature required for core scanning, evidence collection, concept evaluation, scoring, or Archify report generation may require an AI model or API key.

### NFR-8 — Provider Agnosticism & Secret Hygiene

SDAT core code must contain zero vendor-specific lock-in or credentials. All API keys and secrets must resolve via environment variables or secure credential storage, never committed to version control or printed in reports.

---

## 6. Success Metrics

| Metric | Target |
|--------|--------|
| Foundation agent coverage | 100% — all 20 agents run on every audit by default |
| Project categories recognized | 28+ categories with ≥ 85% accuracy |
| Languages supported | 14+ (Python, TS, Go, Rust, C/C++, PHP, Java, Ruby, Swift, Dart) |
| Evidence extraction fidelity | ≥90% accurate AST/call/config structural fact detection |
| Classification accuracy | ≥85% on test fixtures |
| Research reference quality | ≥3 similar projects found for ≥70% of common project types |
| Self-improvement triggers | Correctly identifies novel domains |
| Audit duration | <15 min for 100k LOC (with research) |
| False positive rate | <5% by eliminating reliance on naming/keyword heuristics |
| Offline graceful | Research Agent never blocks the audit |
| KB concept count | 150+ across all categories (foundation + domain) |

---

## 7. Extended Language Support & Implementation Status

| Language | Extensions | Scanner | Status |
|----------|-----------|---------|--------|
| Python | `.py` | `python_scanner.py` | **Implemented** (Phase 2) |
| TypeScript / JS | `.ts`, `.tsx`, `.js`, `.jsx` | `typescript_scanner.py` | **Implemented** (Phase 2) |
| Go | `.go` | `go_scanner.py` | **Implemented** (Phase 4A) |
| Rust | `.rs` | `rust_scanner.py` | **Implemented** (Phase 4B) |
| C / C++ | `.c`, `.cpp`, `.h`, `.hpp` | `c_cpp_scanner.py` | **Implemented** (Phase 4C) |
| PHP | `.php` | `php_scanner.py` | **Implemented** (Phase 4D) |
| Java / Kotlin | `.java`, `.kt` | `java_scanner.py` | **Implemented** (Phase 4E) |
| Ruby | `.rb` | `ruby_scanner.py` | *Planned / In Progress* (Phase 4F) |
| Swift | `.swift` | `swift_scanner.py` | *Planned / In Progress* (Phase 4G) |
| Dart / Flutter | `.dart` | `dart_scanner.py` | *Planned / In Progress* (Phase 4H) |
| React | `.jsx`, `.tsx` | `react_scanner.py` | *Planned* |
| Vue | `.vue` | `vue_scanner.py` | *Planned* |
| Svelte | `.svelte` | `svelte_scanner.py` | *Planned* |
| Angular | `.ts` + templates | `angular_scanner.py` | *Planned* |

---

## 8. Glossary

| Term | Definition |
|------|-----------|
| **Foundation Agent** | Tier 1 agent (F-01 through F-20) — always-on, covers universal system-design capabilities |
| **Domain Agent** | Tier 2 agent (D-01 through D-24) — classification-driven, covers specialized workload concepts |
| **Classifier / Profiler** | Module that identifies languages, frameworks, and project types across 28 categories |
| **ProjectProfile** | Structured profile capturing observed languages, ecosystems, workloads, and applicable rule packs (Planned) |
| **KnowledgePack** | Domain rule pack containing specialized architectural rules, questions, and evidence requirements (Planned) |
| **EvidenceFact** | Canonical, strongly-typed AST/config structural fact emitted by language scanners (file, line range, AST node, snippet) |
| **EvidenceBundle** | Grouped and correlated collection of `EvidenceFact`s mapped to a specific system-design concept |
| **Research Agent** | Module that searches external peers and literature to extract best-practice context (context only, never target proof) |
| **Two-Tier Swarm** | Foundation agents (always-on) + Domain agents (classification-driven) |
| **Two-Tier Web3** | Chain-neutral deterministic baseline audit (Tier 1) + optional chain-specific AI research & DesignDelta (Tier 2) |
| **DesignDelta** | Planned structured plan reconciling baseline findings with chain/domain-specific research (Planned) |
| **Decision** | Architectural verdict: `implemented`, `missing`, `misconfigured`, or `unknown` |
| **Concept** | System-design pattern defined in the knowledge base (e.g. `foundation.circuit-breaker`) |
| **Signal** | Legacy string-based pattern match preserved for backward compatibility |