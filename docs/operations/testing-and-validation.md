# SDAT Operations — Testing and Validation

**Status:** Implemented & Verified in Codebase  
**Test Suite:** 468 Passing Tests (Pytest 9.x / Python 3.10+)  

---

## 1. Test Architecture Overview

SDAT maintains a comprehensive test suite across unit, scanner fixture, rule engine, swarm coordination, and AI layer tests:

```
tests/
├── ai/                # AI Gateway, provider resolution, and fail-open fallbacks
├── backend/           # Backend knowledge pack and scoring tests
├── cache/             # Content-hashed caching, invalidation, and hashing tests
├── evidence/          # CEM models, aggregator, and fixture validation
├── frontend/          # Frontend knowledge pack and page analyzer tests
├── knowledge/         # Architecture concepts and registry integrity tests
├── ml/                # ML rule validation and tensor contracts
├── nlp/               # NLP rule validation and attention mask checks
├── orchestrator/      # End-to-end pipeline execution and CLI runner tests
├── scanners/          # Multi-language AST fixture validation (Python, TS, Go, Rust, C/C++, PHP, Java)
├── swarm/             # Swarm concurrency, timeout cancellation, and merger tests
└── telemetry/         # AuditTelemetry tracking and metric export tests
```

---

## 2. Running Test Commands

### 2.1 Complete Regression Suite
Run all 468 automated tests:
```bash
pytest
```
*Expected Output:*
```text
======================= 468 passed in 64.25s ========================
```

### 2.2 Subsystem-Specific Suites
To run tests for specific subsystems during targeted development:

```bash
# AST Scanners (Python, TypeScript, Go, Rust, C/C++, PHP, Java)
pytest tests/scanners/

# Common Evidence Model & Aggregator
pytest tests/evidence/

# Agent Swarm & Concurrency Orchestrator
pytest tests/swarm/

# AI Provider Gateway & Fallback Semantics
pytest tests/ai/

# Domain Knowledge Packs (ML, NLP, Backend, Frontend)
pytest tests/knowledge/ tests/ml/ tests/nlp/ tests/backend/ tests/frontend/
```

### 2.3 Code Formatting & Linting
SDAT uses `ruff` configured in [pyproject.toml](../../pyproject.toml#L51):
```bash
# Lint checks
ruff check .

# Automated fix application
ruff check --fix .
```

---

## 3. End-to-End CLI Smoke Testing

To validate the CLI in deterministic mode without consuming network calls or external AI tokens:

```bash
# Run deterministic audit against current repository
python -m sdat.cli audit . --no-ai --output-dir docs/audit/smoke_test
```

### Smoke Test Validation Checklist:
1. Console outputs NIRĪKṢĀ header and multi-stage progress `[1/6]` through `[6/6]`.
2. Execution finishes with exit code `0`.
3. Output directory `docs/audit/smoke_test/` contains:
   * `01-inventory.md`
   * `02-gaps.md`
   * `03-misconfigurations.md`
   * `04-remediation.md`
   * `telemetry.json`

---

## 4. Known Testing Limitations & Constraints

1. **Python Version Requirement:** Tests require Python `3.10` or newer due to `type | None` union syntax and modern AST features.
2. **AI Provider Isolation:** Unit tests in `tests/ai/` mock external HTTP calls. Running live AI evaluations requires valid environment credentials (`OPENROUTER_API_KEY` or `GEMINI_API_KEY`).
3. **Secret Hygiene Test:** Tests assert that files matching `.env` or `*.pem` are never ingested into `all_facts`.
