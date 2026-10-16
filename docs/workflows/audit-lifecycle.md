# SDAT Workflows — Audit Lifecycle

**Status:** Implemented & Verified in Codebase  
**Execution Entrypoint:** `sdat audit [target_path]` via [sdat/cli.py](../../sdat/cli.py)

---

## 1. Lifecycle Overview

An SDAT audit executes in a 6-stage sequential pipeline managed by `run_audit_pipeline()` in [sdat/orchestrator.py](../../sdat/orchestrator.py). Each stage is instrumented with execution timers and error boundaries recorded in structured telemetry.

```
[CLI Invocation]
       │
       ▼
[Stage 1: Discovery & Path Sanitization] ──► Prunes secrets & build artifacts
       │
       ▼
[Stage 2: Multi-Language AST Scanning]   ──► Emits typed EvidenceFacts (cached)
       │
       ▼
[Stage 3: Evidence Aggregation]          ──► Correlates cross-file AST facts
       │
       ▼
[Stage 4: Swarm Rule Evaluation]         ──► Evaluates Foundation & Domain rules
       │
       ▼
[Stage 5: AI Enrichment (Optional)]      ──► Generates remediation narratives (fail-open)
       │
       ▼
[Stage 6: Report & Telemetry Rendering]  ──► Writes markdown reports to docs/audit/
```

---

## 2. Step-by-Step Execution Stages

### Stage 1: Discovery and Path Sanitization
1. **Target Path Resolution:** `_resolve_target()` converts relative paths to absolute paths, rejecting dangerous root directories (`/` or drive roots).
2. **Configuration Loading:** Loads settings from `config/sdat.config.yaml` or a user-specified config file.
3. **Secret File Exclusion:** `is_secret_file()` inspects discovered paths and immediately filters out:
   * Known secret file names: `.env`, `.env.production`, `id_rsa`, `id_ed25519`.
   * Cryptographic extensions: `.key`, `.pem`, `.p12`, `.pfx`, `.keystore`.
4. **Exclusion Filters:** Omits common build directories (`node_modules`, `venv`, `dist`, `__pycache__`, `.git`).

### Stage 2: Multi-Language AST Scanning
1. **Registry Lookup:** SDAT iterates through language scanners registered in `sdat/scanners/registry.py` (Python, TypeScript, Go, Rust, C/C++, PHP, Java).
2. **Content-Hashed Cache Check:** Computes a SHA-256 hash of each source file. If a file has not changed since the last run, cached `EvidenceFact` records are replayed from disk (`.sdat_cache/`), skipping AST parsing.
3. **AST Fact Extraction:** For modified or uncached files, the scanner visits AST nodes and extracts structural observations (`kind`, `subject`, `file_path`, `line_range`, `snippet`, `call_target`, `extraction_confidence`).

### Stage 3: Evidence Aggregation and Correlation
1. **Aggregation:** `EvidenceAggregator` gathers facts across all scanned files.
2. **Correlation:** Connects library imports with downstream invocations (e.g. associating `import redis` with `client.set()`).
3. **Defensive Parameter Checks:** Evaluates whether critical resiliency parameters (e.g. `timeout`, `retry`, `ttl`) are explicitly declared or absent.
4. **Bundle Generation:** Generates `EvidenceBundle` instances grouped by concept.

### Stage 4: Swarm Rule Evaluation
1. **Agent Context Assembly:** Builds `project_context` with correlated facts, bundles, and backward-compatible signals.
2. **Concurrent Dispatch:** `SwarmOrchestrator` schedules agents on a bounded worker pool (`ThreadPoolExecutor`).
3. **Foundation Evaluation:** `FoundationAgent` runs rules for universal system design tenets (`foundation.caching`, `resilience.circuit-breaker`, etc.).
4. **Workload Evaluation:** Active domain agents (`BackendAgent`, `FrontendAgent`) and knowledge pack adapters (`KnowledgePackAgent` for ML/NLP) evaluate domain-specific rules.
5. **Conflict Resolution:** `merge_decisions()` consolidates verdicts into a single list of deduplicated `Decision` objects.

### Stage 5: AI Enrichment (Optional Pass)
1. **Bypass Check:** If `--no-ai` is passed, this stage is skipped and deterministic guidance is used.
2. **Gateway Dispatch:** The AI Gateway passes decisions and evidence facts to the active provider (e.g. OpenRouter, Gemma).
3. **Grounding Verification:** The gateway validates that any code or files mentioned by the AI are grounded in verified scanner evidence.
4. **Fail-Open Fallback:** If the AI provider times out or returns an error, the pipeline catches the condition and falls back to deterministic markdown templates.

### Stage 6: Report Generation & Completion
1. **Jinja2 Rendering:**
   * Writes `01-inventory.md` (all implemented patterns).
   * Writes `02-gaps.md` (missing architectural safeguards).
   * Writes `03-misconfigurations.md` (antipatterns and dangerous settings).
   * Writes `04-remediation.md` (step-by-step fix cards).
2. **Telemetry Export:** Writes execution timings, memory metrics, and cache statistics to `telemetry.json`.
3. **Console Summary:** Renders a Rich-formatted audit overview with severity counts and exit code 0.

---

## 3. CLI Options and Overrides

| Flag | Description | Default |
| :--- | :--- | :--- |
| `target` | Target directory to audit | `.` (Current directory) |
| `--config PATH` | Custom YAML configuration file | `config/sdat.config.yaml` |
| `--output-dir PATH` | Directory to output markdown reports | `docs/audit` |
| `--no-ai` | Disable AI enrichment and run 100% deterministically | `False` (AI enabled if keys exist) |
| `--model MODEL_ID` | Override AI model identifier | Resolved from environment |
| `--project-type TYPE` | Explicit workload classification (`backend`, `frontend`, etc.) | Auto-detected |
