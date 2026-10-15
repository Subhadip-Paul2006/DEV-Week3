# SDAT — System Design Audit Tool

**Version:** 0.4.0 (Two-Tier Swarm + Research Edition + AI Gateway)
**Status:** 🔵 Active Development
**License:** MIT

An open-source, provider-agnostic, portable system-design auditor that rides along with any repository. SDAT scans codebases for distributed system patterns, evaluates architecture health across 28 domains, and produces evidence-grounded reports powered by **Archify**.

---

## The Core Philosophy: AI is Optional

SDAT is architected so that **auditing never requires an AI model**:

```
SDAT WITHOUT AI = FULLY FUNCTIONAL CORE AUDITING TOOL
SDAT WITH AI    = CORE AUDITING + AI-ENHANCED EXPERIENCE
```

- **Without AI:** Scanners perform deep AST and control-flow analysis, 44 specialist agents audit concepts, and the **Archify** reporting engine outputs structured markdown reports and architecture diagrams. 100% deterministic, private, and offline.
- **With AI:** An optional **AI Gateway** layer adds plain-language executive summaries, "Why This Matters" contextual analysis, an interactive conversational **Chatbot**, and multimodal architecture diagram understanding.

---

SDAT analyzes codebases across system-design concepts using a two-tier swarm of **44 specialist agents**:
- **Tier 1 (20 Foundation Agents — Always-On):** Caching, Circuit Breaker, Retries & Backoff, Connection Pooling, Message Queues, Rate Limiting, Idempotency, CAP Consistency, Database Scaling, Load Balancers, Proxies, Observability, Security Fundamentals, and more.
- **Tier 2 (24 Domain Agents — Classification-Driven):** Microservices, AI/LLM, RAG pipelines, Mobile, Web3/Blockchain, IoT/Sensors, Kernel/OS, DevOps, Game Dev, and more.

All reports are grounded in verified **`EvidenceFact`** citations (exact file paths, line ranges, and AST snippets).

---

## Core Architectural Principles

### 1. Language Describes How; Classification Describes What
> **Fundamental Principle:** *"A programming language describes how software is written; project classification describes what the software is doing."*

SDAT never assumes fixed mappings such as `Python = backend`, `Go = backend`, `Rust = systems`, `PHP = web`, or `Dart = mobile`. A single language can power diverse workloads:
- **Python** may be a FastAPI backend, a PyGame game engine, an automation script, a cybersecurity pentest tool, or a Web3 dApp client.
- **Go** may be an API microservice, a high-throughput network proxy, a CLI developer tool, or a blockchain node.
- **Rust** may be a systems driver, an embedded controller, an async web service, a P2P networking daemon, or a smart contract engine.

Scanners extract structural code evidence; project profiling determines which domain rules apply.

**Concrete Example 1 (Non-Web3 Workload Separation):**
Consider a Python repository using PyGame with a game loop, sprite rendering, input handling, and asset loading:
- The Python scanner extracts Python/PyGame structural `EvidenceFact`s.
- Project profiling classifies the codebase as a **Game Development** workload.
- SDAT evaluates **Game Development + Core System Design** rules.
- SDAT does **NOT** apply generic Python-backend rules (e.g. demanding REST API rate limiters or SQL connection pooling) merely because the repository is written in Python.
- Similarly, Go with sockets and epoll-like behavior indicates a **Networking / Systems** workload, whereas Go with RPC client calls, wallet signing, and consensus listeners indicates a **Web3 / Blockchain** workload. Same language; completely different system-design criteria.

**Concrete Example 2 (Multi-Domain Workloads):**
A repository can belong to multiple workloads simultaneously (e.g., Python + FastAPI + Redis + Web3 RPC client). SDAT assigns multiple applicable categories (`Backend / Web API` + `Web3`) and evaluates rule packs for Core System Design, Backend, Web3, and Resilience concurrently.

### 2. Names are Clues; Behavior is Evidence
- **Weak evidence:** Filenames (e.g., `polygonService.ts`), class names, function names, variable names, comments, and isolated keywords.
- **Authoritative evidence:** AST relationships, invocations, call graphs, control-flow paths, configuration declarations, concurrency primitives, and manifest dependencies.
- *Rule:* Isolated names, comments, or keywords must never independently establish architectural conclusions or activate domain auditors.

### 3. Canonical Knowledge Architecture
SDAT cleanly separates the architectural layers:
- **Language ("How is the software written?"):** Discovered via language scanners producing structural `EvidenceFact`s.
- **Domain ("What kind of software/system is being built?"):** Workload categories (e.g., frontend, backend, web3, ml) mapped to domain `KnowledgePack`s.
- **Capability ("What observable capability exists?"):** What appears to exist structurally without making a premature audit judgment.
- **Concept ("What architectural principle should be considered?"):** Clean hierarchy separating Core concepts (caching, retry, observability) from Domain concepts (frontend rendering, web3 rpc-retry).
- **Rule ("How should that concept be evaluated?"):** Evaluates concrete structural evidence against explicit criteria and severity weights.
- **Evidence ("What concrete repository/runtime observation supports evaluation?"):** Grounded, verifiable `EvidenceFact`s with AST/file/line/snippet backing.
- **Agent ("Which specialist execution context evaluates relevant concepts?"):** Executes KnowledgePacks and evaluates domain concepts.

Canonical Relationship:
```text
Language ──────► Evidence (structural EvidenceFacts)
Domain   ──────► KnowledgePack (concepts, capabilities, rules)
Concept  ──────► Rule (evaluation criteria)
Rule     ──────► Evidence (AST facts, configurations, calls)
Agent    ──────► KnowledgePack execution (specialist audit)
```

### 4. Canonical Reference Domain Modules
SDAT implements deep, language-neutral domain modules:
- **Frontend Architecture (`sdat/frontend/`):** First reference domain auditing client-side rendering, routing, loading strategies, component trees, state management, and browser performance.
- **Backend Architecture (`sdat/backend/`):** Second reference domain auditing API routing, request lifecycle, service boundaries, auth, input validation, bounded timeouts, retries with jitter, idempotency, connection pooling, and transaction scope containment across Python, Go, Node/TS, Java, Rust, and PHP.

### 5. Layered Pipeline Architecture

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

### 4. Two-Tiered Web3 Auditing
Web3 / Blockchain is an application architecture and workload category, **not a programming language**. It can be implemented across Solidity, Rust, Go, TypeScript, Python, C++, etc. Furthermore, Web3 detection is distinct from Chain identification ("unknown chain" is a valid, normal state).

Web3 auditing operates across two distinct tiers:
1. **Tier 1 — Chain-Neutral Baseline (Deterministic, Zero AI):**
   Evaluates universal blockchain client responsibilities without AI or external APIs:
   - Wallet lifecycle & key protection (zero secrets in code)
   - Transaction lifecycle (creation, signing, submission, confirmation)
   - RPC communication, timeout handling, retries, and idempotency
   - Nonce management & transaction sequencing
   - Event processing, listening, and indexing
   - On-chain vs. off-chain data boundaries
   - Reorganization (reorg) tolerance and finality handling
   - Background queues, rate limiting, and failure recovery
2. **Tier 2 — Chain-Specific AI Research (Optional Enhancement):**
   - If AI is active and a chain context is identified (e.g. **Polygon** or **Ethereum**), the research layer investigates network-specific constraints (e.g. Polygon gas spikes, reorg depth conventions, custom RPC endpoints, bridge dynamics).
   - **Research is never proof:** Research findings establish context, external constraints, and recommended practices; they NEVER count as proof that the target code implements them. Target code truth comes strictly from scanner `EvidenceFact`s.
   - **`DesignDelta`:** The AI compares chain-specific research against observed `EvidenceFact`s to generate a structured `DesignDelta` proposing concrete, grounded architectural improvements tailored to the target chain.

> **SDAT Architectural Axiom:**
> *"Language tells SDAT how the code is written.
> Project classification tells SDAT what the system is doing.
> Evidence tells SDAT what the repository actually implements.
> Knowledge packs tell SDAT what should be checked.
> AI research adds domain/chain-specific context.
> DesignDelta turns grounded findings into a proposed architecture improvement plan."*


---

## AI Gateway: Freedom of Choice (Local, Hosted, BYOK)

When AI enhancement is enabled, SDAT never locks you into a single vendor. Choose what fits your workflow:

1. **Local / Open-Source Models:** Run 100% locally on your machine via runtimes like **Ollama** or **llama.cpp**. Compatible with open model families such as **Qwen Coder**, **DeepSeek**, **GPT-OSS**, **Devstral**, **Gemma** (e.g. Gemma 4), **Phi**, and **GLM**.
2. **Hosted / Free-Access Providers:** Fast developer inference via endpoints like **Groq** or **NVIDIA**.
3. **Bring-Your-Own-Key (BYOK):** Direct commercial APIs including **Google Gemini**, **OpenAI**, **Anthropic**, **Kimi**, or any custom OpenAI-compatible endpoint.
4. **Continue Without AI:** Decline AI configuration with a single keystroke. Core auditing remains completely functional.

*(Note: Model families like Gemma or Qwen are supported options; no single model is ever mandatory.)*

---

## Interactive Capabilities (Optional AI Layer)

- **AI-Enhanced Archify Reports:** Executive summaries, simplified technical breakdowns, and risk prioritizations layered over deterministic findings.
- **SDAT Chatbot (`sdat chat`):** Ask grounded questions about your audit (*"Why did rate limiting fail?"*) or general architecture questions (*"Explain the circuit breaker pattern"*).
- **Multimodal Visual Inspection:** Upload system architecture diagrams or screenshots to compare your intended design against what SDAT discovered in code.
- **Guided Solution Phase (Coming in Final Stage):** Interactive, step-by-step proposals to resolve architectural smells with explicit human-in-the-loop approval.

---

## Quick Start

### 1. Add SDAT to your project:
```bash
git submodule add https://github.com/subhadip-paul/system-design-audit-tool .system-design-tool
cd .system-design-tool
```

### 2. Run the audit (Core Mode — Zero AI Required):
```bash
make audit TARGET=../
```

### 3. (Optional) Configure AI Enhancement:
```bash
sdat ai setup
# Choose: [1] Local, [2] Hosted/Free, [3] BYOK, or [4] Continue Without AI
```

Detailed installation, local model setup, and provider credential configuration are documented in [SETUP.md](file:///D:/system-design-tool/SETUP.md).

---

## Configuration

See `config/sdat.config.yaml`:

```yaml
# Which scanners to enable for your stack
scanners:
  enabled: [python, typescript, go, rust, c_cpp, php, java] # active; ruby, swift, dart in progress

# Classification
classifier:
  enabled: true
  use_llm_refinement: false

# Research Agent (requires network, optional)
research:
  enabled: true
  max_search_queries: 10
  max_peers_to_analyze: 5

# Swarm
swarm:
  always_on: [F-01, F-02, ..., F-20]   # all foundation agents
  force_agents: []                      # override: force specific agents
  skip_agents: []                       # override: skip specific agents
  max_concurrent_agents: 4

# Output
output:
  reports_dir: docs/audit/
  formats: [markdown, json]
```

---

## Output Reports

All reports are generated under `docs/audit/`:

```
docs/audit/
├── 00-research-report.md      # Peer comparison & literature context (optional AI/research)
├── 01-swarm-report.md         # Foundation & domain agent execution breakdown
├── 02-inventory.md            # Implemented concepts grounded in verified EvidenceFacts
├── 03-gaps.md                 # Missing concepts, priority-ranked with recommendations
└── 04-misconfigurations.md    # Fragile or broken implementations with remediation guidance
```

### Example gaps report excerpt:

```markdown
## 🚨 Critical Gaps

| Concept | Priority | Recommendation |
|---------|----------|----------------|
| Circuit Breaker (F-04) | CRITICAL | Add pybreaker or tenacity around all external HTTP calls. Set failure_threshold=5, recovery_timeout=30s. |
| Rate Limiting (F-13) | CRITICAL | No rate limiting on payment endpoints. Add token-bucket rate limiter (100 req/min per user). |
| Idempotency Keys (F-09) | HIGH | Payment webhook handler lacks idempotency. Add idempotency key header check to prevent double-charges. |
```

---

## Project Structure

```
sdav1/
├── PHASES.md              # Project rules (follow before any code)
├── README.md              # This file
├── PRD.md                 # Product Requirements
├── TRD.md                 # Technical Requirements (architecture)
├── AGENTS.md              # Agent contract (how agents work)
├── TODO.md                # Implementation checklist
├── CONTRIBUTING.md        # How to add concepts, scanners, agents
├── SECURITY.md            # Threat model, security rules
├── config/
│   ├── sdat.config.yaml   # User configuration
│   └── swarm_agent_map.yaml # Agent dispatch rules
├── concepts/              # Knowledge base (system-design concepts)
│   ├── foundation/        # 20 foundation concepts (Tier 1, always-on)
│   ├── backend-web/       # Domain concepts (Tier 2, classification-driven)
│   ├── ml/                # ML/AI domain concepts
│   └── ... (24 domains total)
├── scanners/              # Language-specific AST & static analyzers
├── evidence/              # Evidence Aggregator & bundle correlation
├── classifier/            # Project type classifier (28 categories)
├── research_agent/        # Peer analysis + literature research
├── swarm/                 # Two-tier agent swarm
│   ├── orchestrator.py    # Entry point: classify → research → dispatch → merge → render
│   ├── merger.py          # Deduplicate + resolve conflicts across agents
│   └── agents/            # 20 F-agents + 24 D-agents + F-99
└── renderer/              # Report generator
```

---

## Agent Architecture

### Tier 1 — Foundation Agents (20, always-on)

F-01 Caching, F-02 HLD, F-03 LLD, F-04 Circuit Breaker, F-05 Retries, F-06 Connection Pooling, F-07 Message Queues, F-08 Fault Tolerance, F-09 Idempotency, F-10 CAP Consistency, F-11 Database Scaling, F-12 Consistent Hashing, F-13 Rate Limiting, F-14 Load Balancers, F-15 Proxies, F-16 Protocols, F-17 Client-Server, F-18 Latency/Bandwidth, F-19 Observability, F-20 Security Fundamentals

### Tier 2 — Domain Agents (24, classification-driven)

D-01 API Design, D-02 Billing, D-03 Data Layer, D-04 AI/LLM, D-05 Computer Vision, D-06 GNN, D-07 Sequential Models, D-08 Mobile, D-09 Blockchain, D-10 Security/Pentest, D-11 OS/Embedded, D-12 Bots, D-13 Database Internals, D-14 Agentic Automation, D-15 DevOps, D-16 Game Dev, D-17 Sensor/IoT, D-18 Networking, D-19 Multi-Agent Orchestrator, D-20 Personal LLM, D-21 Frontend, D-22 Backend, D-23 Workflow Automation, D-24 Infrastructure

---

## Contributing

See `CONTRIBUTING.md`. We welcome:
- New system-design concepts (PRs to `concepts/`)
- New language scanners (PRs to `scanners/`)
- New domain agents (PRs to `swarm/agents/`)
- Bug reports and feature requests

---

## Why two tiers?

**Tier 1 (Foundation):** These 20 foundation agents audit the core architectural capabilities that apply to software systems regardless of domain. A FastAPI backend, a Flutter game, an OS kernel — all need resilience, all need security, all need observability. Running them always ensures baseline quality.

**Tier 2 (Domain):** Domain-specific concepts (e.g., reorg tolerance for Web3, ECS patterns for games, SCADA protocols for IoT) are only relevant when the project matches that domain. Dynamic dispatch driven by project profiling keeps audit time bounded.

---

*Built by Subhadip Paul. Designed for the system-design community.*
#
