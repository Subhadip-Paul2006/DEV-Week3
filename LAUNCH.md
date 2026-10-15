# LAUNCH.md — From Concept to v0.1.0

**Goal:** Ship a working system-design audit tool on GitHub within 4 weeks.

---

## Week 1: Foundation (The Bedrock)

**Output:** 20 foundation concept files + directory structure

### Day 1–2: Setup
- Create the GitHub repo
- Write PHASES.md (project rules)
- Create directory structure
- Write first 3 concept files: F-01 caching, F-04 circuit breaker, F-20 security

### Day 3–5: Concept Marathon
- Write 5 concepts/day × 4 days = 20 concepts total
- Each concept = YAML frontmatter + definition + signals + smells + recommendations
- This is the most important work. Do it well.

### Day 6–7: First Agent Stubs
- Create directory structure for 20 F-agents
- Write agent.md templates (copy-paste, fill in specifics)
- Write basic orchestrator that dispatches all 20 agents and collects output

**Week 1 checkpoint:** All 20 foundation concepts written. 20 agent stubs exist. Orchestrator runs end-to-end on a simple test project.

---

## Week 2: First Vertical Slice

**Output:** Working audit on Python/FastAPI projects

### Day 8–9: Python Scanner
- Implement python_scanner.py
- Detect imports, function calls, decorators
- Emit structured signals JSON
- Write unit tests

### Day 10–11: Foundation Agents (Full Prompts)
- Write full agent.md for top 5 most important agents:
  - F-01 caching, F-04 circuit breaker, F-05 retries, F-13 rate limiting, F-20 security
- Each agent receives scanner signals, applies concept judgment, outputs JSON
- Test against 2 real FastAPI repos

### Day 12–13: Merger + Renderer
- Write merger.py (merge agent outputs, deduplicate, resolve conflicts)
- Write renderer.py (produce 3 markdown reports)
- Test: run full pipeline, verify output quality

### Day 14: Refine
- Find 2–3 real repos (FastAPI itself, a payment API, a ML service)
- Run the audit, inspect reports
- Fix false positives, add missing signals, tighten prompts
- Iterate until reports are genuinely useful

**Week 2 checkpoint:** `make audit` works. Three clean reports on real Python projects.

---

## Week 3: Classification + Research + Dynamic Dispatch

**Output:** Two-tier swarm with smart agent selection

### Day 15–16: Classifier
- Write classifier with 28 categories
- Test against repos of different types
- Verify correct category assignment

### Day 17: Research Agent
- Write peer analyzer + literature analyzer
- Set up trusted domain allowlist
- Implement content sanitization

### Day 18: Dynamic Dispatch
- Update orchestrator to read classification
- Implement agent map
- Wire F-01–F-20 as always-on
- Wire D-agents by classification

### Day 19: Domain Agents (First 5)
- D-01 API Design, D-02 Billing, D-03 Data Layer, D-21 Frontend, D-22 Backend

### Day 20–21: End-to-End Test + Polish
- Run full audit on diverse repos
- Verify correct agent dispatch
- Fix timing bugs
- Polish output formatting

**Week 3 checkpoint:** Two-tier swarm works. Research agent runs before swarm. Reports include peer analysis.

---

## Week 4: Scanner Expansion + Release Prep

**Output:** v0.1.0 ready to ship

### Day 22–23: More Scanners
- TypeScript scanner (React + Express)
- Go scanner
- That's enough for v0.1.0 — more languages in v0.2

### Day 24: Remaining Foundation Agents
- Complete the remaining F-agents (F-06 through F-03 that weren't done in Week 2)

### Day 25: Documentation
- Write CONTRIBUTING.md
- Write SECURITY.md
- Polish README with examples and screenshots

### Day 26: CI + Testing
- Set up GitHub Actions
- Run SDAT on itself (meta-audit!)
- Verify all tests pass

### Day 27: Community Prep
- Write announcement post (LinkedIn + Twitter)
- Prepare demo GIF/screenshots
- Add "How to Contribute" section

### Day 28: Tag v0.1.0 + Launch
- Tag the release
- Push to GitHub
- Announce

**Week 4 checkpoint:** v0.1.0 live on GitHub. Working audit on at least 3 language stacks.

---

## After v0.1.0 — Architecture Evolution Roadmap

- **v0.2.0:** Common Evidence Model (`EvidenceFact`), Evidence Aggregator, extended language scanners (TypeScript, Go, Rust, C/C++, PHP, Java/Kotlin)
- **v0.3.0:** Profiling & Project Classification (`ProjectProfile`, multi-workload support across 28 categories), Tier 1 Chain-Neutral Web3 Baseline audit
- **v0.4.0:** AI Gateway abstraction (Local runtimes, Hosted/Free endpoints, BYOK APIs), Archify-based structured reports, Chain-Specific AI Research & `DesignDelta` architectural planning
- **v0.5.0:** Optional SDAT Chatbot (grounded audit Q&A + general concepts) and Multimodal visual inspection (architecture diagrams & screenshot explanations)
- **v1.0.0:** Production-ready CI/CD integration, and the Final Guided Solution Phase (interactive human-in-the-loop remediation)

---

## User First-Run Experience: Getting Started with SDAT

SDAT is designed as an open-source, portable tool that can be invoked directly inside any target project by developers, students, or engineering auditors.

### 1. Initialize SDAT in Target Project
The user adds SDAT (e.g. as a submodule or installs the CLI) and runs the initial command:
```bash
sdat init
```

### 2. First-Run AI Setup Prompt
On initial execution or when configuring AI capabilities, SDAT presents an interactive choice:

```text
============================================================
              SDAT System Design Audit Tool
                     AI Configuration
============================================================

Choose how SDAT should use AI:

  [1] Local / Open-Source Models (Ollama, llama.cpp; Qwen Coder, DeepSeek, Gemma, Phi, etc.)
  [2] Hosted / Free-access AI Providers (Groq, NVIDIA, etc.)
  [3] Use My Own API Key / BYOK (Google Gemini, OpenAI, Anthropic, Kimi, etc.)
  [4] Continue Without AI (Core audit works 100% with deterministic rules & Archify reports)

Enter choice [1-4] (default: 4):
```

> **The No-AI Guarantee:** Option `[4]` is a first-class citizen. SDAT will never block or degrade core auditing capabilities if AI is declined or unavailable.

### 3. Local Model / Runtime Detection & Guidance
If the user selects `[1]` (Local / Open-Source):
1. **Runtime Check:** SDAT checks if the configured local runtime (e.g., Ollama, llama.cpp) is running and reachable on localhost.
2. **Model Check:** If the runtime is active, SDAT queries available models to verify if the requested model family (e.g., `qwen2.5-coder`, `deepseek-coder`, `gemma2`) is installed.
3. **Missing Runtime/Model Guidance:** If either is missing, SDAT outputs clear, non-blocking guidance explaining:
   - What runtime or model needs to be installed.
   - Example download/pull commands.
   - Pointers to centralized installation steps in [SETUP.md](file:///D:/system-design-tool/SETUP.md).
   - An option to retry detection or fall back to No-AI mode.
4. **Validation:** SDAT tests a minimal ping to verify connectivity before activating AI-assisted features.

### 4. Running the Audit
Once configured (or running in No-AI mode), the user triggers the audit:
```bash
make audit TARGET=./
# or
sdat audit .
```
- **Without AI:** Scanners extract structural facts, the swarm audits concepts, and Archify generates structured, evidence-cited markdown reports.
- **With AI:** The same factual reports are augmented with executive summaries, "why this matters" explanations, simplified terminology, and optional chatbot access.

---

## The Golden Rule

> **Don't ship a feature that you haven't tested on at least 2 real repos.**

If you can't run it on real code and get useful output, it's not done.
