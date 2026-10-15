# Setup Guide — System Design Audit Tool (SDAT)

**v0.4.0 — Multi-Language Swarm + Archify Foundation + AI Gateway Edition**

This guide walks you through installing, configuring, and running SDAT.

> **Fundamental Principle:** SDAT core auditing is **100% functional without AI**. Scanners, swarm agents, evidence collection, and Archify-based reports run with zero external AI models or API keys. AI is strictly an **optional enhancement layer** for summaries, chat, and multimodal diagrams.

---

## 1. Prerequisites

### Core SDAT (Required for all runs)
| Dependency | Minimum Version | Check | Note |
|------------|-----------------|-------|------|
| Python | 3.10+ | `python --version` | Standard library + minimal dependencies |
| pip | Latest | `pip --version` | Package manager |
| Git | 2.30+ | `git --version` | Submodule management |
| Make | Any | `make --version` | Optional CLI shortcut |

### Optional AI Enhancement Layer (Only needed if enabling AI features)
| Component | Supported Options | Check / Command |
|-----------|-------------------|-----------------|
| **Local Runtime** | Ollama, llama.cpp, LocalAI | `ollama --version` |
| **Local Models** | Qwen Coder, DeepSeek, GPT-OSS, Devstral, Gemma (e.g. Gemma 4), Phi, GLM | `ollama list` |
| **Hosted / Free APIs** | Groq, NVIDIA endpoints | API Key in environment |
| **BYOK APIs** | Google Gemini, OpenAI, Anthropic, Kimi, custom endpoint | API Key in environment |

**If you're on Windows:** Native PowerShell, WSL2, or Git Bash are all fully supported.

---

## 2. Installation

### Option A — Git Submodule (Recommended)

```bash
# In the root of your target repository:
git submodule add https://github.com/<your-username>/system-design-tool.git .system-design-tool
git submodule update --init --recursive
```

Verify:
```bash
ls .system-design-tool/
# Expected: README.md, PRD.md, TRD.md, concepts/, scanners/, classifier/, research/, swarm/, renderer/
```

### Option B — pip install (Phase 11)

```bash
pip install sdat
```

---

## 3. Configuration Philosophy & Schema

```bash
cp .system-design-tool/config/sdat.config.yaml.example .system-design-tool/config/sdat.config.yaml
```

Key configuration layout:

```yaml
# Core Audit Configuration (Always Active)
scanners:
  enabled: [python, typescript, rust, go, c_cpp, swift, dart]

classifier:
  enabled: true                 # run project classification across 28 categories
  use_llm_refinement: false     # deterministic heuristics by default

research:
  enabled: true                 # set to false for offline mode
  trusted_domains_only: true    # strict allowlist for peer analysis

swarm:
  mode: auto                    # auto-selects agents based on classification
  always_on: [F-01, F-02, ..., F-20] # all 20 foundation agents run on every audit
  max_concurrent_agents: 4

# Optional AI Gateway Configuration
ai:
  enabled: false                # Master switch: false = pure deterministic core audit
  provider: local               # local | hosted | byok | none
  runtime: ollama               # ollama | llamacpp | generic (for local provider)
  model: qwen2.5-coder:7b       # e.g., deepseek-coder, gemma2, gpt-4o, gemini-2.0-flash
  endpoint: http://localhost:11434 # endpoint URL for local or custom providers
  capabilities:
    auto_detect: true           # dynamically probe vision, tools, reasoning support

# Reporting & Presentation (Powered by Archify)
renderer:
  engine: archify               # Archify-based structured reporting & diagrams
  output_dir: docs/audit/
```

> **Security Invariant:** Never store raw API keys in `sdat.config.yaml` or any version-controlled file. All credentials must resolve via environment variables.

---

## 4. AI Setup & Provider Strategy (Interactive Flow)

SDAT provides an interactive setup wizard that configures the AI Gateway:

```bash
sdat ai setup
```

On first run, you will be prompted:
```text
Choose how SDAT should use AI:

  [1] Local / Open-Source Models (Ollama, llama.cpp; Qwen Coder, DeepSeek, Gemma, Phi, etc.)
  [2] Hosted / Free-access AI Providers (Groq, NVIDIA, etc.)
  [3] Use My Own API Key / BYOK (Google Gemini, OpenAI, Anthropic, Kimi, etc.)
  [4] Continue Without AI (Core audit works 100% with deterministic rules & Archify reports)

Enter choice [1-4] (default: 4):
```

### Path 1: Local / Open-Source Models
Run open models completely on your own hardware with 100% data privacy.

1. **Distinction between Model Family and Runtime:**
   - **Model Families:** Qwen Coder, DeepSeek, GPT-OSS, Devstral, Gemma, Phi, GLM, etc.
   - **Runtimes:** Ollama, llama.cpp, LocalAI, vLLM.
   *(Gemma or Qwen are supported model options, never a mandatory dependency).*
2. **Runtime Detection:**
   SDAT checks if your runtime is running (default: `http://localhost:11434` for Ollama).
3. **Model Detection & Guidance if Missing:**
   If the runtime is missing or the model is not found, SDAT provides direct guidance:
   ```bash
   # Install Ollama (if missing):
   # macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh
   # Windows: Download from https://ollama.com/download

   # Pull your chosen model:
   ollama pull qwen2.5-coder:7b
   # or
   ollama pull gemma2:9b
   # or
   ollama pull deepseek-coder:6.7b
   ```
4. **Validation:**
   Verify reachability and model availability:
   ```bash
   sdat ai test
   ```

### Path 2: Hosted / Free-Access Providers
Use cloud inference endpoints that provide free, community, or developer-tier access.

1. **Groq:**
   - Obtain key: Sign up at `https://console.groq.com/keys`
   - Set environment variable:
     ```bash
     export GROQ_API_KEY=<your-groq-api-key>
     ```
   - Model: `llama-3.3-70b-versatile` or `qwen-2.5-coder-32b`
2. **NVIDIA Inference Endpoints:**
   - Obtain key: Generate API key at `https://build.nvidia.com`
   - Set environment variable:
     ```bash
     export NVIDIA_API_KEY=<your-nvidia-api-key>
     ```
3. **Test Connectivity:**
   ```bash
   sdat ai test
   ```

### Path 3: Bring Your Own Key (BYOK) / Paid APIs
Connect your commercial AI provider accounts directly:

1. **Google Gemini:**
   - Obtain key: Google AI Studio (`https://aistudio.google.com`)
   - Set environment variable:
     ```bash
     export GEMINI_API_KEY=<your-gemini-api-key>
     ```
   - Model: `gemini-2.0-flash`
2. **OpenAI:**
   - Obtain key: OpenAI Platform (`https://platform.openai.com`)
   - Set environment variable:
     ```bash
     export OPENAI_API_KEY=<your-openai-api-key>
     ```
   - Model: `gpt-4o` or `gpt-4o-mini`
3. **Anthropic:**
   - Obtain key: Anthropic Console (`https://console.anthropic.com`)
   - Set environment variable:
     ```bash
     export ANTHROPIC_API_KEY=<your-anthropic-api-key>
     ```
   - Model: `claude-3-5-sonnet`
4. **Moonshot Kimi:**
   - Obtain key: Moonshot Open Platform
   - Set environment variable:
     ```bash
     export MOONSHOT_API_KEY=<your-kimi-api-key>
     ```
5. **Custom OpenAI-Compatible Endpoint:**
   - Set endpoint and key:
     ```bash
     export CUSTOM_OPENAI_BASE_URL=https://your-custom-endpoint.com/v1
     export CUSTOM_OPENAI_API_KEY=<your-key>
     ```

### Path 4: Continue Without AI (Core Mode)
Selecting option `[4]` leaves `ai.enabled: false`. SDAT executes with complete deterministic precision, producing comprehensive Archify reports without any network calls, background runtimes, or API keys.

---

## 5. Model Capability Discovery & Verification

Different models support different feature subsets. You can inspect active capabilities using:

```bash
sdat ai capabilities
```

Output:
```text
Provider: local (Ollama)
Model: qwen2.5-coder:7b
Capabilities:
  [✓] Text Generation
  [✓] Code Reasoning
  [✓] Structured JSON Output
  [✓] Streaming
  [✗] Vision / Multimodal (Diagram understanding will be disabled)
  [✓] Tool / Function Calling
```

If a capability (such as `vision`) is unsupported by the active model:
- Core scanning continues normally.
- Multimodal diagram features are cleanly deactivated with an explanation.
- The user is never misled into expecting unsupported features.

---

## 6. Running an Audit (Core Mode & AI-Enhanced Mode)

### Make target

```bash
cd .system-design-tool
make audit TARGET=../
```

### Direct script

```bash
cd .system-design-tool
./run.sh audit ../
```

Both methods produce:
- `../docs/audit/01-swarm-report.md` — agent execution breakdown
- `../docs/audit/02-inventory.md` — implemented concepts grounded in `EvidenceFacts`
- `../docs/audit/03-gaps.md` — missing concepts with actionable recommendations
- `../docs/audit/04-misconfigurations.md` — fragile implementations requiring remediation
- `../docs/audit/00-research-report.md` — *(optional)* external peer and literature context if research is enabled
- `.sdat-cache/evidence_facts.json` — canonical typed structural facts
- `.sdat-cache/signals.json` — *(legacy compatibility view)*
- `.sdat-cache/decisions.json` — evaluated decisions
- `.sdat-cache/project_profile.json` — observed languages, ecosystems, workloads, and rule packs

### What happens under the hood

#### A. Core Mode (Deterministic Baseline — Zero AI Required)
```text
make audit TARGET=../
  │
  ├── 1. Repository Discovery & Language Profiling
  │       Identify languages and package manifests across the repository
  ├── 2. Structural Scanning (AST, calls, configs)
  │       Language scanners extract typed EvidenceFact records
  │       Emits .sdat-cache/evidence_facts.json
  ├── 3. Project Classification & ProjectProfile Synthesis
  │       Multi-workload categorization (28 categories)
  │       Emits .sdat-cache/project_profile.json
  ├── 4. Evidence Aggregation & Correlation
  │       Evidence Aggregator links cross-file facts into concept EvidenceBundles
  ├── 5. Deterministic Audit & Swarm Dispatch
  │       20 Foundation Agents (always-on) + matched Domain Agents
  │       Evaluates Core System Design & active Domain Knowledge Packs
  ├── 6. Decision Merge & Conflict Resolution
  │       Deduplicates by concept_id; resolves ties by structural confidence
  │       Emits .sdat-cache/decisions.json
  └── 7. Archify Rendering
          Generates 01-swarm, 02-inventory, 03-gaps, 04-misconfigurations markdown reports
          Renders interactive HTML & Mermaid architecture diagrams
```

#### B. Optional AI-Enhanced Flow (With AI Gateway Enabled)
```text
sdat audit --ai TARGET=../
  │
  ├── (Runs Steps 1–7 of the Core Deterministic Baseline above)
  │
  ├── 8. Pre-Audit Research (Optional, network-enabled)
  │       Searches GitHub & literature for peer patterns and chain-specific parameters
  │       Renders 00-research-report.md (contextual only; never target proof)
  ├── 9. Domain & Chain-Specific Analysis
  │       Examines network constraints (e.g. Polygon gas dynamics, reorg depth)
  │       Synthesizes structured DesignDelta architecture improvement plan
  │       Emits .sdat-cache/design_delta.json
  └── 10. AI Report Enhancer & Interactive Tools
          Enriches reports with executive summaries & "Why This Matters" impact
          Unlocks interactive SDAT Chatbot (`sdat chat`) and Multimodal Diagram Inspection
```

### Selective agent runs

```bash
# Only run billing + auth agents (skip classification-driven selection)
make audit TARGET=../ AGENTS="A-02,A-03"

# Force all 20 agents (skip classifier)
make audit TARGET=../ SWARM_MODE=all

# Skip research phase (offline mode)
make audit TARGET=../ RESEARCH_ENABLED=false
```

---

## 7. Reading the Reports (Archify Presentation Foundation)

All reports are generated under `docs/audit/` using the **Archify** presentation format:

```
docs/audit/
├── 00-research-report.md      # Classification, peer comparison, best-practice references
├── 01-swarm-report.md         # Foundation & domain agent dispatch, coverage map
├── 02-inventory.md            # Implemented concepts with verified code citations
├── 03-gaps.md                 # Missing concepts, priority-ranked with recommendations
└── 04-misconfigurations.md    # Fragile or broken implementations with remediation guidance
```

### Deterministic Baseline (Without AI)
Every finding is backed by structural evidence facts (`file`, `line`, verbatim `snippet`, `note`). Diagrams and findings are traceable and 100% reproducible.

### AI-Enhanced Layer (When AI is Enabled)
When an AI model is configured, Archify reports are enriched with:
- **Executive Summary:** Top architecture risks and systemic strengths at the top of the report.
- **"Why This Matters":** Real-world impact explanations (e.g. why missing jitter causes a thundering herd).
- **Simplified Explanations:** Non-jargon translations for junior engineers or non-technical stakeholders.

---

## 8. Project Categories Supported

SDAT recognizes 28 project categories:

| # | Category | Example Projects |
|---|----------|------------------|
| 1 | Networking | TCP servers, protocol implementations, proxies |
| 2 | Cybersecurity | Auth flows, encryption, pentest tools |
| 3 | Blockchain / Web3 | Solidity contracts, wallets, DeFi |
| 4 | Hardware / IoT | Firmware, embedded, sensors, MQTT |
| 5 | Sensor Projects | Telemetry, time-series ingestion, industrial IoT, SCADA |
| 6 | Machine Learning | Training pipelines, PyTorch, model serving |
| 7 | NLP | Tokenization, embeddings, transformers |
| 8 | Computer Vision | CNN, R-CNN, YOLO, OpenCV |
| 9 | Graph Neural Networks | PyG, DGL, GAT, GCN |
| 10 | Sequential Models | RNN, LSTM, GRU, forecasting |
| 11 | Transformers | Attention, HuggingFace, vLLM |
| 12 | Frontend (Web) | React, Vue, Svelte, Next.js |
| 13 | Backend (Web) | FastAPI, Express, Gin, NestJS |
| 14 | RAG / LangChain | Retrieval pipelines, vector DBs |
| 15 | CLI Tools | Click, Typer, Clap, terminal UI |
| 16 | Workflow / Automation | CI/CD, Airflow, Prefect |
| 17 | Plugins | Plugin architectures, hooks |
| 18 | Packages / Libraries | SDKs, public APIs |
| 19 | Personal LLM / Fine-tuning | LoRA, GGUF, Ollama |
| 20 | Multi-Agent Orchestration | A2A, agent swarms |
| 21 | Bots (Telegram/Discord) | Bot APIs, message handlers |
| 22 | Security / Hacking Tools | Pentest frameworks, fuzzers |
| 23 | Mobile (Android / iOS) | Swift, Kotlin, Flutter |
| 24 | Database Projects | Query engines, migrations, ORMs |
| 25 | Agentic Automation | Browser automation, RPA |
| 26 | DevOps | IaC, Terraform, Ansible, deployment pipelines |
| 27 | Game Development | Unity, Godot, ECS, physics, game networking |
| 28 | OS Building | Kernel modules, bootloaders, drivers |

---

## 9. Languages Supported

| Language | Extensions | Common Use Cases |
|----------|-----------|------------------|
| Python | `.py` | Backend, ML/AI, scripting |
| TypeScript / JS | `.ts`, `.tsx`, `.js`, `.jsx` | Frontend, Node.js backend |
| Go | `.go` | Backend, CLI tools, infrastructure |
| Rust | `.rs` | Systems software, embedded, Web3 |
| C / C++ | `.c`, `.cpp`, `.h`, `.hpp` | OS kernels, embedded, drivers |
| PHP | `.php` | Laravel, WordPress |
| Java / Kotlin | `.java`, `.kt` | Spring Boot, Android |
| Ruby | `.rb` | Rails |
| Swift | `.swift` | iOS, macOS, SwiftUI, Vapor |
| Dart / Flutter | `.dart` | Flutter apps, mobile |
| React | `.jsx`, `.tsx` | Frontend |
| Vue | `.vue` | Frontend |
| Svelte | `.svelte` | Frontend |
| Angular | `.ts` + templates | Frontend |

---

## 10. Updating SDAT

```bash
cd .system-design-tool
git submodule update --remote
cd ../
git add .system-design-tool
git commit -m "chore: update sdat submodule"
```

---

## 11. Troubleshooting

### "Classifier couldn't determine project type"
The manifest files are missing or non-standard. The tool will fall back to language-only classification. Check `classification.json` in `.sdat-cache/run-<ts>/`.

### "Research Agent skipped: no network access"
`research.enabled: true` but the system has no internet. The audit proceeds without the research phase. The swarm report notes this.

### "Research Agent found 0 peers"
The project is in a novel or niche domain. The self-improvement mode triggers automatically and synthesizes a custom KB slice. Review `.sdat-cache/run-<ts>/research/custom-kb-slice/`.

### "Local model unreachable at localhost:11434"
Ensure your local runtime (e.g. Ollama) is started via `ollama serve`. Run `sdat ai test` to diagnose the connection.

### "Vision features disabled"
The configured AI model lacks image understanding. Text features and core auditing continue without interruption. To enable diagram understanding, configure a multimodal model.

---

## 12. Using SDAT with AI Coding Agents & Assistants

### Claude Code
```bash
claude -p "Run the system-design audit in .system-design-tool/ against ../ and produce the Archify reports in docs/audit/"
```

### Cursor
```
In .system-design-tool/:
Run the system-design audit against this project. Classify the repo, run the swarm audit, and render the reports.
```

### Google Anti-gravity
```
In .system-design-tool/:
Run the full system-design audit pipeline with Archify report generation.
```

---

## 13. FAQ

**Q: Do I need an API key or an AI model to run SDAT?**  
**No.** Core auditing is 100% deterministic and runs without any AI model or API key. AI is strictly an optional enhancement layer for executive summaries, conversational Q&A, and multimodal diagram analysis.

**Q: Does SDAT modify my source code?**  
**No.** SDAT is strictly read-only. It scans your files and writes markdown reports to `docs/audit/`. Even the future Solution Phase is an interactive proposal assistant requiring explicit human confirmation before any file modification.

**Q: Can the Research Agent leak my code?**  
**No.** The Research Agent receives only classification metadata and manifest summaries — never your source code. See SECURITY.md INV-8.

**Q: How do I run completely offline?**  
Set `research.enabled: false` and `ai.enabled: false` in `sdat.config.yaml` or run:
```bash
make audit RESEARCH_ENABLED=false AI_ENABLED=false
```

**Q: How do I switch AI models?**  
Run `sdat ai setup` or update `ai.model` and `ai.provider` in `sdat.config.yaml`. The rest of SDAT requires no rebuild or code changes.