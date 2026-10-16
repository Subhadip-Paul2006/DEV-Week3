# SDAT Operations — Documentation Maintenance Protocol

**Status:** Enforced Operational Policy  
**Scope:** All Documentation Updates, Guides, Diagrams, and Reports

---

## 1. The Non-Destructive Documentation Invariant

Existing project documentation, workflow files, agent behavioral instructions, and audit artifacts represent the historical record and operational foundation of SDAT.

### The Golden Rule
> **All documentation enhancements must be strictly additive. Existing documents must never be deleted, truncated, overwritten, or degraded.**

---

## 2. Forbidden Operations

Contributors and automated coding agents are strictly forbidden from performing the following actions:

1. **No Deletions:** Never delete existing markdown files in the repository root, `docs/`, or `concepts/`.
2. **No Monolithic Overwrites:** Never overwrite an existing conceptual guide, requirements document, or status report with a newly generated version.
3. **No File Moves or Renames:** Never move or rename core files such as `README.md`, `AGENTS.md`, `AI_INSTRUCTIONS.md`, `PRD.md`, `TRD.md`, `SETUP.md`, `SECURITY.md`, `TODO.md`, or `LAUNCH.md`.
4. **No Historical Report Deletions:** Never delete or wipe historical audit outputs (e.g. `docs/HACKATHON_STATUS_REPORT.md` or files under `docs/audit/`).
5. **No Destructive Git Commands:** Never run `git reset --hard`, `git clean -fd`, or `git checkout -- .` to clear uncommitted changes.

---

## 3. Required Additive-Only Strategy

When adding new documentation or expanding on existing concepts:

### Step 1: Create Dedicated Modular Files
Place new deep-dives into structured subdirectories:
* Architectural specifications $\rightarrow$ `docs/architecture/<feature>.md`
* Execution runbooks $\rightarrow$ `docs/workflows/<workflow>.md`
* Operational guides $\rightarrow$ `docs/operations/<operation>.md`
* Release records $\rightarrow$ `docs/releases/<release>.md`
* Visual models $\rightarrow$ `docs/diagrams/<diagram>.mmd`

### Step 2: Register in Documentation Index
Link new files into [docs/DOCUMENTATION_INDEX.md](../DOCUMENTATION_INDEX.md) under the relevant category.

### Step 3: Minimal Targeted Edits (When Modifying Existing Docs)
If an existing file requires an update (e.g., fixing a broken link or correcting a syntax error):
1. Preserve all existing headings, sections, links, and text.
2. Apply the smallest necessary contiguous patch.
3. Validate that existing references remain valid.

---

## 4. Verification & Validation Checklist

Before submitting any documentation pull request or commit:

- [ ] Run `git status --short` to verify that only expected new files were added.
- [ ] Confirm that no tracked existing files were modified or deleted unintentionally.
- [ ] Verify that all internal relative markdown links resolve to existing files.
- [ ] Validate that Mermaid diagram syntax is correct.
- [ ] Run `pytest` to confirm that documentation changes have not broken any doc-dependent tests.
