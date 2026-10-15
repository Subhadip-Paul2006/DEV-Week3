# System Design Audit Tool (SDAT) — TODO

**Based on:** `PRD.md`, `TRD.md`
**Owner:** Subhadip Paul
**Status:** 🔵 Not started

---

## Phase 0 — Bootstrap & Repo Setup

- [ ] 0.1 Create the GitHub repo (`subhadip-paul/system-design-audit-tool`)
- [ ] 0.2 Set up `PHASES.md` (project rules — follow them strictly before any code)
- [ ] 0.3 Create repo structure:
  ```
  sdav1/
  ├── PHASES.md
  ├── README.md
  ├── PRD.md
  ├── TRD.md
  ├── TODO.md
  ├── AGENTS.md
  ├── CONTRIBUTING.md
  ├── SECURITY.md
  ├── config/
  │   ├── sdat.config.yaml
  │   └── swarm_agent_map.yaml
  ├── concepts/
  │   ├── foundation/            # 20 foundation concepts
  │   ├── backend-web/
  │   ├── frontend-web/
  │   ├── devops/
  │   ├── game-development/
  │   ├── sensor-projects/
  │   ├── os-building/
  │   ├── ml/
  │   ├── ...
  ├── scanners/
  │   ├── registry.yaml
  │   ├── python_scanner.py
  │   ├── typescript_scanner.py
  │   ├── go_scanner.py
  │   ├── rust_scanner.py
  │   ├── c_cpp_scanner.py
  │   ├── swift_scanner.py
  │   ├── dart_scanner.py
  │   ├── react_scanner.py
  │   ├── svelte_scanner.py
  │   ├── angular_scanner.py
  ├── classifier/
  │   ├── classify.py
  │   ├── manifest_parser.py
  │   ├── heuristics.yaml
  │   ├── llm_refiner.py
  ├── research_agent/
  │   ├── research_agent.py
  │   ├── peer_analyzer.py
  │   ├── literature_analyzer.py
  │   ├── custom_kb_builder.py
  ├── swarm/
  │   ├── orchestrator.py
  │   ├── merger.py
  │   ├── agents/
  │   │   ├── f01_caching_agent/
  │   │   ├── f02_hld_agent/
  │   │   ├── f03_lld_agent/
  │   │   ├── f04_circuit_breaker_agent/
  │   │   ├── f05_retries_agent/
  │   │   ├── f06_connection_pooling_agent/
  │   │   ├── f07_message_queues_agent/
  │   │   ├── f08_fault_tolerance_agent/
  │   │   ├── f09_idempotency_agent/
  │   │   ├── f10_cap_consistency_agent/
  │   │   ├── f11_db_scaling_agent/
  │   │   ├── f12_consistent_hashing_agent/
  │   │   ├── f13_rate_limiting_agent/
  │   │   ├── f14_load_balancers_agent/
  │   │   ├── f15_proxies_agent/
  │   │   ├── f16_protocols_agent/
  │   │   ├── f17_client_server_agent/
  │   │   ├── f18_latency_bandwidth_agent/
  │   │   ├── f19_observability_agent/
  │   │   ├── f20_security_fundamentals_agent/
  │   │   ├── d01_api_design_agent/
  │   │   ├── d02_billing_agent/
  │   │   ├── d03_data_layer_agent/
  │   │   ├── d04_ai_llm_agent/
  │   │   ├── d05_computer_vision_agent/
  │   │   ├── d06_gnn_agent/
  │   │   ├── d07_sequential_agent/
  │   │   ├── d08_mobile_agent/
  │   │   ├── d09_blockchain_agent/
  │   │   ├── d10_security_pentest_agent/
  │   │   ├── d11_os_embedded_agent/
  │   │   ├── d12_bot_agent/
  │   │   ├── d13_database_internals_agent/
  │   │   ├── d14_agentic_automation_agent/
  │   │   ├── d15_devops_agent/
  │   │   ├── d16_game_dev_agent/
  │   │   ├── d17_sensor_iot_agent/
  │   │   ├── d18_networking_agent/
  │   │   ├── d19_multi_agent_agent/
  │   │   ├── d20_personal_llm_agent/
  │   │   ├── d21_frontend_agent/
  │   │   ├── d22_backend_agent/
  │   │   ├── d23_workflow_agent/
  │   │   ├── d24_infrastructure_agent/
  │   │   └── f99_general_agent/
  │   └── swarm_report_renderer.py
  ├── renderer/
  │   ├── renderer.py
  │   ├── templates/
  │   └── schemas/
  ├── tests/
  ├── examples/
  ├── scripts/
  │   ├── run_audit.sh
  │   ├── makefile
  └── .sdat-cache/             # gitignore
  ```

---

## Phase 1 — Foundation (Vertical Slice)

### Prerequisites
- Phase 0 complete
- PHASES.md written and reviewed
- Read PRD.md and TRD.md in full

### 1.1 Knowledge Base — Foundation Concepts & Canonical Knowledge Architecture (Complete)

**Goal:** Establish the canonical Knowledge Architecture and write foundation & domain concepts.

- [x] 1.1.1 F-01 — caching: strategies, eviction policies, consistency patterns, TTL tradeoffs, common misconfigurations
- [x] 1.1.2 F-02 — HLD: architecture patterns, separation of concerns, module boundaries, when to microservice vs monolith
- [x] 1.1.3 F-03 — LLD: class design, SOLID, interface segregation, tight coupling signals
- [x] 1.1.4 F-04 — circuit breaker: Hystrix/Resilience4j patterns, half-open state, fallback design
- [x] 1.1.5 F-05 — retries: exponential backoff, jitter, max attempts, retry storm prevention
- [x] 1.1.6 F-06 — connection pooling: DB pool sizing, HTTP client pools, connection exhaustion detection
- [x] 1.1.7 F-07 — message queues: pub/sub, at-least-once vs at-most-once, dead-letter queues, consumer groups
- [x] 1.1.8 F-08 — fault tolerance: bulkhead, graceful degradation, timeout patterns, failover design
- [x] 1.1.9 F-09 — idempotency: keys, deduplication, idempotent APIs, idempotency vs safety
- [x] 1.1.10 F-10 — CAP: availability vs consistency tradeoffs, eventual consistency implications
- [x] 1.1.11 F-11 — database scaling: sharding strategies, read replicas, connection pooling, indexing
- [x] 1.1.12 F-12 — consistent hashing: virtual nodes, ring topology, load distribution
- [x] 1.1.13 F-13 — rate limiting: token bucket, sliding window, leaky bucket, API gateway vs app-level
- [x] 1.1.14 F-14 — load balancers: L4 vs L7, health checks, session affinity, least-connections vs round-robin
- [x] 1.1.15 F-15 — proxies: forward, reverse, API gateway, sidecar patterns
- [x] 1.1.16 F-16 — protocols: HTTP/1.1 vs HTTP/2 vs gRPC, WebSocket, TCP vs UDP tradeoffs
- [x] 1.1.17 F-17 — client-server: request-response, long-polling, server-sent events, WebSocket, patterns
- [x] 1.1.18 F-18 — latency/bandwidth: p99 vs p50, bandwidth bottleneck detection, CDN placement
- [x] 1.1.19 F-19 — observability: metrics, logs, traces (three pillars), SLI/SLO/SLA, alerting thresholds
- [x] 1.1.20 F-20 — security fundamentals: OWASP top 10, least privilege, input validation, auth patterns
- [x] 1.1.21 Canonical Concept Hierarchy (`concepts/core/`, `concepts/domains/`, `concepts/cross-domain/`, `concepts/INDEX.yaml` with 78 cataloged concepts)
- [x] 1.1.22 Canonical contracts implemented (`sdat/knowledge/models.py`, `registry.py`, `scoring.py`)
- [x] 1.1.23 Universal concepts separated from domain specializations (e.g. `core.caching` vs `frontend.client-caching`)
- [x] 1.1.24 Negative verification rules enforced ("Names are clues. Behavior is evidence.")
- [x] 1.1.25 ML, NLP, and Web3 specs defined (`status: spec_only`) without shallow fake rules
- [x] 1.1.26 Backend Domain System-Design Module (`sdat/backend/`, 25 concepts, `kp.backend`, D-01 `BackendAgent`, 32 tests)

For each concept file:
- [x] Write YAML frontmatter (id, category, owning_agent, maturity, languages, tags, related)
- [x] Write definition + why-it-matters
- [x] Write signals (scanner signals that indicate presence/absence)
- [x] Write smells (what misconfigurations look like)
- [x] Write recommendations (how to fix)

### 1.2 Scanner — Python/FastAPI (Vertical Slice Scanner)

- [ ] 1.2.1 Implement basic Python scanner: import detection, function call detection
- [ ] 1.2.2 Add FastAPI-specific signals: route decorators, middleware, dependency injection
- [ ] 1.2.3 Add Flask-specific signals: Blueprint patterns, before_request
- [ ] 1.2.4 Emit structured signals JSON: `[{signal, file, line, snippet}]`
- [ ] 1.2.5 Write unit tests for scanner

### 1.3 Foundation Agent Stubs (Tier 1)

- [ ] 1.3.1 Create stub for each of the 20 F-agents: directory, README, `agent.yaml`
- [ ] 1.3.2 Write agent  for each F-agent (template: concept list + signal schema + output schema)
- [ ] 1.3.3 Each agent prompt: "You are the [concept] auditor. Given these signals, decide: implemented/missing/misconfigured. Output JSON with evidence."

### 1.4 Orchestrator + Merger + Renderer (Minimal)

- [ ] 1.4.1 Orchestrator: load scanner output, dispatch all 20 F-agents (no classification yet — dispatch all)
- [ ] 1.4.2 Merger: merge agent outputs, deduplicate, resolve conflicts
- [ ] 1.4.3 Renderer: produce the three reports from merged JSON

### 1.5 Integration Test

- [ ] 1.5.1 Find 2–3 real Python/FastAPI repos to audit (e.g., FastAPI itself, a Flask app)
- [ ] 1.5.2 Run full pipeline, examine output
- [ ] 1.5.3 Refine: fix false positives, add missing signals, tighten agent prompts
- [ ] 1.5.4 Iterate until reports are useful

---

## Phase 2 — Classification + Research + Dynamic Dispatch

### 2.1 Profiling & Classifier

- [ ] 2.1.1 Implement `manifest_parser.py`: detect package.json, pyproject.toml, Cargo.toml, go.mod, etc.
- [ ] 2.1.2 Implement `heuristics.yaml`: all 28 classification rules
- [ ] 2.1.3 Implement layered profiling:
  - Language / Ecosystem discovery ("how it is written")
  - Project / Workload classification ("what it is doing")
  - Multi-workload assignment (e.g., Python + FastAPI + Web3 maps to both `backend-web` and `blockchain-web3`)
- [ ] 2.1.4 Implement `ProjectProfile` synthesizer: emits `project_profile.json` (languages, frameworks, ecosystems, project_types, capabilities, deployment_model, blockchain context, applicable_rule_packs)
- [ ] 2.1.5 Implement Web3 detection & Chain identification: distinct states (Ethereum, Polygon, Arbitrum, multi-chain, or unknown chain)
- [ ] 2.1.6 Implement `classify.py`: entry point, outputs `project_profile.json` and `classification.json`
- [ ] 2.1.7 (Optional) Implement LLM refinement pass
- [ ] 2.1.8 Test classifier against repos of each category

### 2.2 Research Agent (Peer & Chain-Specific Research)

- [ ] 2.2.1 Implement `research_agent.py`: orchestrate searches + analysis
- [ ] 2.2.2 Implement `peer_analyzer.py`: find GitHub peers, fetch, analyze signals
- [ ] 2.2.3 Implement `literature_analyzer.py`: search academic sources
- [ ] 2.2.4 Implement Chain-Specific AI Research:
  - Deep-dive into network constraints (Polygon gas spikes, finality block counts, custom RPC quirks)
  - Strict evidence rule: research provides context, NEVER target proof
- [ ] 2.2.5 Implement `custom_kb_builder.py`: synthesize custom KB when no peers found
- [ ] 2.2.6 Trusted domain allowlist enforcement (github.com, arxiv.org, official docs)
- [ ] 2.2.7 Content sanitization (strip scripts, limit excerpt length)
- [ ] 2.2.8 Implement `DesignDelta` Architecture Plan generator: reconciles baseline findings with chain/domain research into actionable plans

### 2.3 Dynamic Agent Dispatch & Knowledge Packs

- [ ] 2.3.1 Implement Domain Knowledge Packs (`KnowledgePack` abstraction): modular domain rules decoupled from generic system design
- [ ] 2.3.2 Implement Tier 1 Chain-Neutral Web3 Baseline audit rules (wallet lifecycle, transaction signing/submission, nonce tracking, RPC error handling, retries, idempotency, event processing, reorg tolerance, key protection, queues, observability)
- [ ] 2.3.3 Update orchestrator to read `ProjectProfile` and activate corresponding KnowledgePacks and agents
- [ ] 2.3.4 Implement `swarm_agent_map.yaml` with all 24 domain agents
- [ ] 2.3.5 Implement dispatch logic: always-on (F-01–F-20) + classification-driven (D-agents)
- [ ] 2.3.6 Implement user overrides: `force_agents`, `skip_agents` in config

### 2.4 Tier 2 Domain Agents (Stubs First, Then Full)

**Priority order (implement based on your most common project types):**

- [ ] D-01 api_design_agent (backend-web, cli-tools)
- [ ] D-02 billing_agent (backend-web, rag-langchain)
- [ ] D-03 data_layer_agent (backend-web, database, ml)
- [ ] D-04 ai_llm_agent (ml, nlp, transformers, rag)
- [ ] D-09 blockchain_agent (blockchain-web3)
- [ ] D-18 networking_agent (networking)
- [ ] D-15 devops_agent (devops)
- [ ] D-16 game_dev_agent (game-development)
- [ ] D-17 sensor_iot_agent (sensor-projects, hardware-iot)
- [ ] D-11 os_embedded_agent (os-building)
- [ ] D-05 through D-08, D-10, D-12 through D-14, D-19 through D-24 (remaining agents)

---

## Phase 3 — Scanner Expansion

- [ ] 3.1 TypeScript scanner (React, Next.js, Express, NestJS)
- [ ] 3.2 Go scanner (Gin, Echo, standard library)
- [ ] 3.3 Rust scanner (Actix, Axum, Tokio)
- [ ] 3.4 C/C++ scanner (system calls, networking)
- [ ] 3.5 PHP scanner (Laravel, Symfony)
- [ ] 3.6 Java scanner (Spring Boot)
- [ ] 3.7 Swift scanner (Vapor, iOS patterns)
- [ ] 3.8 Dart scanner (Flutter)
- [x] 3.9 Frontend System-Design Auditing Architecture (Framework-agnostic KnowledgePack, 15 rule categories, Page Analyzer, Explainable Scoring, Browser Runtime Layer, D-21 Agent)

---

## Phase 4 — Concept Library Expansion

**Goal:** Reach 99–100% coverage of system-design concepts.

- [ ] 4.1 Expand foundation concepts: add depth (signals, smells, recommendations)
- [ ] 4.2 Write domain concepts for each of the 24 domain categories
- [ ] 4.3 Add version tracking to concepts (evolution tracking)
- [ ] 4.4 Set up community contribution pipeline (PR template, review process)

---

## Phase 5 — Quality + Hardening

- [ ] 5.1 False-positive reduction: audit 20+ repos, tune prompts
- [ ] 5.2 Confidence scoring: add confidence field to every finding
- [ ] 5.3 Human feedback loop: allow users to dismiss findings, log for retraining
- [ ] 5.4 CI/CD test: run SDAT on itself, verify reports are sensible
- [ ] 5.5 Performance optimization: parallel agent dispatch, context window management
- [ ] 5.6 Error handling: graceful degradation when agent fails, when network is down
- [ ] 5.7 Security review: SECURITY.md, threat model walkthrough
- [ ] 5.8 Documentation: README, usage guide, examples, FAQ

---

## Phase 6 — Polish + Release

- [ ] 6.1 Write `AGENTS.md` (detailed agent contract, prompt template)
- [ ] 6.2 Write `CONTRIBUTING.md` (how to add concepts, how to add scanners, how to add agents)
- [ ] 6.3 Write `CHANGELOG.md`
- [ ] 6.4 Add GitHub Actions CI (lint, test, concept schema validation)
- [ ] 6.5 Write blog post / LinkedIn post announcing the tool
- [ ] 6.6 Tag v0.1.0 and publish

---

## Ongoing (Never Done)

- [ ] Weekly: add new concepts as system-design field evolves
- [ ] Weekly: scan 3+ repos, tune false positives
- [ ] Monthly: add new language scanner if a major language emerges
- [ ] Community: review PRs, accept contributions

---

## Current Sprint (Start Here)

**Focus: Phase 1.1 — Foundation Concepts (Tier 1)**

Pick one concept per day. Write the full YAML + content. Do all 20.
This is the backbone of the entire tool. Quality here > everything else.

Suggested order (most impactful first):
1. F-01 caching (every project has or should have caching)
2. F-19 observability (universally missing, high crash-prevention value)
3. F-04 circuit breaker (every external call should have this)
4. F-20 security fundamentals (OWASP catches are always valuable)
5. F-10 CAP consistency (database-related, high impact)
6. F-13 rate limiting (API projects, high crash-prevention)
7. F-05 retries (every network call needs this)
8. F-06 connection pooling (database + HTTP, prevents exhaustion)
9. F-11 database scaling (sharding, replicas, indexes)
10. F-03 LLD (coupling and cohesion signals)
11. F-02 HLD (architecture patterns)
12. F-07 message queues (async patterns)
13. F-08 fault tolerance (timeout, bulkhead, graceful degradation)
14. F-09 idempotency (payment and webhook handling)
15. F-14 load balancers (L4/L7, health checks)
16. F-15 proxies (API gateway, sidecar)
17. F-17 client-server (protocol choices)
18. F-18 latency/bandwidth (CDN, p99)
19. F-12 consistent hashing (distributed systems)
20. F-16 protocols (HTTP/2, gRPC, WebSocket)

After all 20 are done → move to Phase 1.2 (Python scanner).
