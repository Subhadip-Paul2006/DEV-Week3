# SDAT Releases — Documentation Release Process

**Status:** Process Runbook  
**Applies To:** Documentation Pack Promotions & Release Versioning  

---

## 1. Scope & Objective

This process defines the safe, standardized workflow for releasing documentation updates, architecture guides, and technical runbooks in SDAT. It guarantees that documentation releases do not inadvertently overwrite user code, break tests, or introduce unverified claims.

---

## 2. Pre-Release Verification Checklist

Before tagging or publishing any documentation release:

### 2.1 Non-Destructive Integrity Check
Run `git status` to ensure that only intended documentation additions are present:
```bash
git status --short
```
* **Rule:** If any pre-existing tracked file outside `docs/` is modified, stop and review before proceeding.

### 2.2 Relative Link Validation
* Ensure all links in `docs/DOCUMENTATION_INDEX.md` and child documents resolve to valid local files.
* Ensure all links to root files (e.g., `../README.md`, `../../AGENTS.md`) use accurate relative paths.

### 2.3 Syntax & Test Regression Suite
Documentation updates must not break tests or syntax checkers:
```bash
# Run complete test suite
pytest

# Verify code and config formatting
ruff check .
```

---

## 3. Version Alignment & Release Promotion

### 3.1 Version Mapping
Documentation versions align directly with core SDAT releases:
* `v0.4.0` — Two-Tier Swarm, AI Gateway, and Multi-Language AST Scanners.
* Documentation changelogs must be documented in [SDAT-DOCUMENTATION-CHANGELOG.md](SDAT-DOCUMENTATION-CHANGELOG.md).

### 3.2 Git Tagging Protocol
Once approved on a documentation branch, merge cleanly and tag the release:
```bash
# Example release tag for documentation update
git tag -a v0.4.0-docs -m "Release: Modular Documentation Pack v1.0.0"
git push origin v0.4.0-docs
```

---

## 4. Current Automation Status

| Capability | Current State | Notes |
| :--- | :--- | :--- |
| Documentation Linting | **Manual (`ruff`, markdown checks)** | CI integration planned |
| Relative Link Checking | **Manual Inspection** | Automated link-checker workflow planned |
| GitHub Pages / MkDocs | **Planned** | Static site generation under evaluation |
| GitHub Release Automation | **Manual** | Releases currently created via GitHub Web or Git tags |
| PyPI Package Publication | **Manual / Blocked on Name** | Package renaming required before CI/CD setup |
