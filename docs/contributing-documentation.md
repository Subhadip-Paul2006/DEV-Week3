# Contributing to SDAT Documentation

Thank you for helping improve the documentation for the **System Design Audit Tool (SDAT)**. Clear, accurate, and non-destructive documentation is essential for maintainers, contributors, and users.

---

## 1. Documentation Principles

1. **Accuracy Over Aspiration:**
   * Distinguish between **Implemented & Verified** (proven by working code/tests), **Partially Implemented**, and **Planned** features.
   * Never state a feature exists merely because it is described in an architectural proposal.
2. **Strict Non-Destructive Policy:**
   * Always follow the [Documentation Maintenance Protocol](operations/documentation-maintenance.md).
   * Create new modular files rather than rewriting existing documents.
3. **Traceability:**
   * When documenting architectural patterns or scanner capabilities, reference the exact source files and line ranges where they are implemented.

---

## 2. Style and Formatting Guidelines

### 2.1 File Naming & Placement
* Use lowercase kebab-case for documentation files: `e.g. system-overview.md`, `audit-lifecycle.md`.
* Place documents in the appropriate category under `docs/`:
  * `docs/architecture/` — Structural models, schemas, and subsystem boundaries.
  * `docs/workflows/` — Execution lifecycles and step-by-step procedures.
  * `docs/operations/` — Testing, CI/CD, runbooks, and maintenance guides.
  * `docs/releases/` — Release notes, documentation changelogs, and version governance.
  * `docs/diagrams/` — Raw Mermaid source files (`.mmd`).

### 2.2 Relative Markdown Links
* Always use clean relative links that work on GitHub and local markdown viewers:
  ```markdown
  <!-- Linking to architecture guide from within docs/ -->
  [System Overview](architecture/system-overview.md)

  <!-- Linking to root file from within docs/ -->
  [Root README](../README.md)
  ```
* Test all relative links before submitting.

### 2.3 Code and Config Blocks
Always specify the syntax highlighter for fenced code blocks:
```python
def example_function() -> None:
    pass
```

### 2.4 Mermaid Diagrams
* Store reusable diagrams as raw `.mmd` files under `docs/diagrams/`.
* When embedding diagrams in markdown, use fenced `mermaid` blocks with quoted node labels:
  ```mermaid
  flowchart TD
      A["Scanner (AST)"] --> B["Evidence Aggregator"]
  ```

---

## 3. Contribution Workflow

1. **Branching:** Create a dedicated documentation branch:
   ```bash
   git checkout -b docs/add-new-guide
   ```
2. **Drafting:** Author the new guide under `docs/<category>/`.
3. **Index Registration:** Add a link to the new guide in [docs/DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md).
4. **Pre-flight Checks:**
   ```bash
   git status --short
   pytest
   ```
5. **Review:** Verify that no existing files were inadvertently deleted or rewritten.
