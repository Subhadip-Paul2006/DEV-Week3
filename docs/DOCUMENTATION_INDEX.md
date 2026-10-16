# SDAT Documentation Pack — Navigation Index

Welcome to the comprehensive, modular documentation suite for the **System Design Audit Tool (SDAT)** (internal codename: *NIRĪKṢĀ* / *तन्त्रविन्यास-निरीक्षा*).

This index organizes SDAT's documentation into distinct areas of concern: high-level architecture, verifiable evidence models, agent swarm coordination, multi-provider AI gateways, end-to-end execution workflows, day-to-day operations, diagrams, and release protocols.

---

## 1. Documentation Structure & Map

```
docs/
├── DOCUMENTATION_INDEX.md               # [You are here] Central entrypoint and navigation map
├── contributing-documentation.md        # Conventions, standards, and non-destructive guidelines
├── HACKATHON_STATUS_REPORT.md           # [Protected] Historical milestone & test coverage report
│
├── architecture/                        # Architectural specifications and design contracts
│   ├── system-overview.md              # High-level pipeline, subsystems, and scanner ecosystem
│   ├── evidence-model.md               # Common Evidence Model (CEM), schemas, and facts
│   ├── swarm-execution.md              # Two-tier swarm orchestrator, resilience, and agent lifecycle
│   └── ai-provider-gateway.md          # Multi-provider AI Gateway, fail-open semantics, zero-leakage
│
├── workflows/                           # Step-by-step lifecycle documentation
│   ├── audit-lifecycle.md              # CLI invocation to multi-language scanning and report generation
│   └── report-lifecycle.md             # Inventory, gaps, misconfigurations, and remediation reports
│
├── operations/                          # Operational, testing, and maintenance runbooks
│   ├── testing-and-validation.md       # Regression suite, fixture validation, and CLI verification
│   └── documentation-maintenance.md    # Strict non-destructive documentation update protocol
│
├── releases/                            # Release notes, changelog, and governance
│   ├── SDAT-DOCUMENTATION-CHANGELOG.md  # Detailed record of the documentation pack delivery
│   └── documentation-release-process.md # Safe promotion, tag alignment, and publication checklist
│
├── diagrams/                            # Editable Mermaid architectural diagrams
│   ├── README.md                       # Diagram catalog, viewing guidelines, and conventions
│   ├── system-architecture.mmd         # End-to-end subsystem layout
│   ├── audit-workflow.mmd              # Pipeline sequence diagram (Discovery to Reports)
│   ├── swarm-execution.mmd             # Concurrent swarm dispatch and conflict resolution
│   └── ai-provider-flow.mmd            # Gateway provider fallback and grounding engine
│
└── audit/                               # [Protected] Historical audit runs and outputs
    ├── 01-inventory.md                 # Baseline scanner evidence catalog
    ├── 02-gaps.md                      # Documented architectural gaps
    ├── 03-misconfigurations.md         # Documented pattern misconfigurations
    ├── 04-remediation.md              # Actionable remediation guidance cards
    ├── cached_gemma_enrichment.json    # Cached Gemma 4 offline reasoning output
    ├── cached_qwen_enrichment.json     # Cached Qwen offline reasoning output
    └── telemetry.json                  # Audit telemetry metrics and execution timings
```

---

## 2. Navigation by Area of Concern

### Architecture
* [System Overview](architecture/system-overview.md): Architectural boundaries, scanner discovery registry, core rules engine, and reporting subsystem.
* [Evidence Model](architecture/evidence-model.md): Detailed specifications of `EvidenceFact`, `EvidenceKind`, typed AST observations, and `SignalBridge`.
* [Swarm Execution](architecture/swarm-execution.md): `SwarmOrchestrator`, bounded thread pools, per-agent timeouts, failure isolation, and deterministic result merging.
* [AI Provider Gateway](architecture/ai-provider-gateway.md): Abstraction layer (`sdat/ai/gateway.py`), plug-and-play provider switching, credential hygiene, and deterministic fallbacks.

### Workflows
* [Audit Lifecycle](workflows/audit-lifecycle.md): End-to-end walk-through of an audit execution run from `sdat audit` CLI dispatch to final completion.
* [Report Lifecycle](workflows/report-lifecycle.md): How markdown reports (`01-inventory.md`, `02-gaps.md`, `03-misconfigurations.md`, `04-remediation.md`) and telemetry are generated and preserved.

### Operations & Maintenance
* [Testing and Validation](operations/testing-and-validation.md): Running the 468-test regression suite, AST scanner fixtures, and integration verification.
* [Documentation Maintenance](operations/documentation-maintenance.md): Rules for ensuring zero regressions and preserving historical records during documentation updates.
* [Contributing Documentation](contributing-documentation.md): Style guide, markdown rules, and review safeguards for new contributors.

### Releases & Evolution
* [Documentation Changelog](releases/SDAT-DOCUMENTATION-CHANGELOG.md): Scope, rationale, and catalog of all files introduced in this pack.
* [Documentation Release Process](releases/documentation-release-process.md): Checklist for aligning documentation with codebase tags and PyPI releases.

### Editable Mermaid Diagrams
* [Diagrams Directory](diagrams/README.md): High-fidelity architectural diagrams in raw `.mmd` format for rendering in GitHub, IDEs, or Mermaid CLI.

---

## 3. Preserved Root References

The following core root documents serve as the authoritative baseline for project rules, technical specifications, and development contracts. They remain strictly preserved:

* [README.md](../README.md): Root project summary, quick-start guide, and core design philosophy.
* [AGENTS.md](../AGENTS.md): Strict contract for Foundation (`F-01..F-20`) and Domain (`D-01..D-24`) agents, schemas, and Graphify navigation.
* [AI_INSTRUCTIONS.md](../AI_INSTRUCTIONS.md): Swarm execution rules, knowledge pack evaluation, and AST signal constraints.
* [PRD.md](../PRD.md): Product Requirements Document defining target personas, capabilities, and system boundaries.
* [TRD.md](../TRD.md): Technical Requirements Document specifying scanner architectures, rules, and telemetry.
* [SETUP.md](../SETUP.md): Environment setup, prerequisites, and developer tooling instructions.
* [SECURITY.md](../SECURITY.md): Vulnerability disclosures, secret handling policies, and scanning safety invariants.
* [TODO.md](../TODO.md): Multi-phase implementation roadmap and task tracking.
* [LAUNCH.md](../LAUNCH.md): Milestone delivery plan and launch schedules.
