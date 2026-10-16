# SDAT Workflows — Report Lifecycle

**Status:** Implemented & Verified in Codebase  
**Core Source:** [sdat/renderer/renderer.py](../../sdat/renderer/renderer.py), [sdat/ai/enrichment.py](../../sdat/ai/enrichment.py), [sdat/telemetry/tracker.py](../../sdat/telemetry/tracker.py)

---

## 1. Overview of Audit Artifacts

Every SDAT audit run generates a standardized set of markdown reports and structured telemetry inside the designated output directory (default: `docs/audit/`).

```
docs/audit/
├── 01-inventory.md           # Implemented patterns with verbatim code citations
├── 02-gaps.md                # Missing architectural safeguards grouped by severity
├── 03-misconfigurations.md   # Detected antipatterns and smell explanations
├── 04-remediation.md         # Actionable remediation cards with code guidance
└── telemetry.json            # Machine-readable performance and execution metrics
```

---

## 2. Artifact Breakdown & Specifications

### 2.1 `01-inventory.md` (Implemented Patterns)
* **Purpose:** Provides a comprehensive catalog of all system-design patterns confirmed to be implemented in the target repository.
* **Organization:** Grouped by category (Architecture, Caching, Concurrency, Concurrency/Resilience, Observability, Performance, Scalability, Security).
* **Traceability Invariant:** Every entry includes:
  * Pattern title and concept identifier (e.g. `foundation.caching`).
  * Architectural certainty score (e.g. `Confidence: 0.95`).
  * Concrete evidence table citing exact file path, line numbers, verbatim code snippet, and reviewer notes.

### 2.2 `02-gaps.md` (Architectural Gaps)
* **Purpose:** Identifies missing safeguards where system resilience or security requires defensive patterns.
* **Organization:** Sorted strictly by severity (`CRITICAL` $\rightarrow$ `HIGH` $\rightarrow$ `MEDIUM` $\rightarrow$ `LOW` $\rightarrow$ `INFO`).
* **Content:**
  * Specific concept identified as missing.
  * Bulleted list of verified gaps (e.g., *"No circuit breaker library imported around external payment calls"*).
  * High-level architectural recommendation.

### 2.3 `03-misconfigurations.md` (Detected Antipatterns)
* **Purpose:** Details implemented patterns that exhibit known architectural smells or dangerous parameters.
* **Organization:** Sorted by severity priority.
* **Content:**
  * Concept name and location where the smell was observed.
  * Concrete explanation of the misconfiguration (e.g., *"Redis cache client initialized without a default TTL or eviction policy, leading to unbounded memory growth"*).
  * Cited code snippet demonstrating the antipattern.

### 2.4 `04-remediation.md` (Actionable Fix Guidance)
* **Purpose:** Provides step-by-step developer remediation instructions.
* **Structure per Concept Card:**
  * **Severity & Concept ID:** Standard priority badge.
  * **Finding Summary:** Verifiable statement of the issue.
  * **Why It Matters:** Business and operational rationale.
  * **Architectural Impact:** Outage, latency, or data integrity risks if unaddressed.
  * **Recommended Solution:** Recommended library or architectural pattern.
  * **Implementation Steps:** Numbered, concrete instructions for the developer.
  * **Validation Check:** Command or test method to verify the fix.
  * **Trade-Offs:** Complexity, memory, or operational trade-offs of the proposed solution.

### 2.5 `telemetry.json` (Structured Telemetry)
* **Schema:** Produced by `AuditTelemetry.to_dict()`:
  ```json
  {
    "run_id": "audit_1710000000",
    "timestamp": "2026-10-16T08:00:00Z",
    "total_duration_seconds": 1.42,
    "memory_delta_mb": 4.15,
    "scanner_timings": {
      "python": 0.32,
      "typescript": 0.45
    },
    "cache_metrics": {
      "hits": 18,
      "misses": 4,
      "hit_ratio": 0.818
    },
    "agent_metrics": {
      "active_agents": 4,
      "failed_agents": 0
    }
  }
  ```

---

## 3. Reproducibility & Traceability Guarantees

### Byte-Identical Output
When invoked with `--no-ai`, report generation is 100% deterministic:
* Jinja2 templates use `trim_blocks=True`, `lstrip_blocks=True`, and `keep_trailing_newline=True`.
* Findings are sorted by deterministic keys (Priority $\rightarrow$ Concept ID $\rightarrow$ File Path).
* Running SDAT twice against the same repository without code changes produces byte-identical `01-inventory.md`, `02-gaps.md`, and `03-misconfigurations.md` files.

### Verifiable Code Citations
SDAT prohibits vague statements like *"caching should be improved"*. Every finding in every report must cite:
1. Relative file path from target root.
2. 1-indexed line number or line range `(start, end)`.
3. Verbatim source snippet bounded to $\le 200$ characters.
