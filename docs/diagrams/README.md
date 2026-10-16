# SDAT Architectural Diagrams

This directory contains editable text-based Mermaid source files (`.mmd`) representing the architecture, execution workflows, and data pipelines of the **System Design Audit Tool (SDAT)**.

---

## 1. Diagram Catalog

| Diagram File | Description | Source Type |
| :--- | :--- | :--- |
| [`system-architecture.mmd`](system-architecture.mmd) | High-level subsystem architecture, scanner registry, evidence models, swarm orchestrator, and report generation. | Mermaid Flowchart (`flowchart TD`) |
| [`audit-workflow.mmd`](audit-workflow.mmd) | Sequence diagram tracking an audit run from CLI invocation to disk report output. | Mermaid Sequence (`sequenceDiagram`) |
| [`swarm-execution.mmd`](swarm-execution.mmd) | Multi-agent concurrency, task-level caching, failure isolation, and deterministic merger conflict resolution. | Mermaid Flowchart (`flowchart TD`) |
| [`ai-provider-flow.mmd`](ai-provider-flow.mmd) | Provider resolution, context budget enforcement, grounding checks, and fail-open deterministic fallback. | Mermaid Flowchart (`flowchart LR`) |

---

## 2. Viewing and Rendering Instructions

### In GitHub / Git Web Viewers
GitHub automatically renders `.mmd` files as interactive vector diagrams in the web interface.

### In VS Code / IDEs
Install any Mermaid preview extension (e.g. *Markdown Preview Mermaid Support* or *Mermaid Chart*) to view and edit diagrams with live reload.

### Exporting to SVG / PNG via CLI
If you have `@mermaid-js/mermaid-cli` installed:
```bash
# Export system architecture diagram to SVG
mmdc -i system-architecture.mmd -o system-architecture.svg

# Export audit workflow diagram to PNG
mmdc -i audit-workflow.mmd -o audit-workflow.png
```

---

## 3. Authoring Conventions

1. **Text Editable:** Keep all diagrams as raw `.mmd` source files. Do not commit binary image assets unless explicitly required.
2. **Quoted Node Labels:** Always quote node labels containing punctuation, parentheses, or brackets:
   ```mermaid
   A["CLI (sdat/cli.py)"] --> B["Orchestrator [run_audit_pipeline]"]
   ```
3. **Factual Representation:** Label planned, optional, or unavailable subsystems clearly (e.g. `[OPTIONAL]` or `[PLANNED]`).
