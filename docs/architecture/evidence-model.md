# SDAT Architecture — Evidence Model

**Status:** Implemented & Verified in Codebase  
**Core Source:** [sdat/models.py](../../sdat/models.py), [sdat/evidence/aggregator.py](../../sdat/evidence/aggregator.py)

---

## 1. The Common Evidence Model (CEM)

In legacy audit architectures, code scanners directly emitted opinions on concepts (e.g., flagging "caching missing"). This tightly coupled AST parsing to domain interpretations and made cross-language correlation brittle.

SDAT separates observation from judgment through the **Common Evidence Model (CEM)**:
```
AST Code Parsing ──► EvidenceFact (Objective observation, no concept bias)
                          │
                          ▼
                  EvidenceAggregator (Correlation, deduplication, bundling)
                          │
                          ▼
                  EvidenceBundle (Grouped observations for a concept)
                          │
                          ▼
                  Swarm Agents (Domain rules evaluation & smells analysis)
                          │
                          ▼
                  Decision (Architectural verdict with citations & priority)
```

> **Guiding Axiom:** *"Names are clues. Behavior is evidence."*  
> Filenames, class names, or comments alone are weak corroborating hints, never architectural proof.

---

## 2. Core Typed Schemas

### 2.1 `EvidenceKind` (Canonical Observation Types)
Defined in [sdat/models.py](../../sdat/models.py#L96):

```python
class EvidenceKind(str, Enum):
    # Structural AST Observations
    IMPORT = "import"                     # Module/library import (e.g., 'redis', 'pybreaker')
    CALL = "call"                         # Function or method invocation (e.g., 'client.set')
    DECORATOR = "decorator"               # Decorator pattern (e.g., '@cache', '@retry')
    INHERITANCE = "inheritance"           # Class hierarchy base classes
    INSTANTIATION = "instantiation"       # Object instantiation (e.g., 'redis.Redis()')
    ANNOTATION = "annotation"             # Type hint or structural marker

    # Behavioral & Control Flow
    CONTROL_FLOW = "control_flow"         # Loop, try/except/retry branch, fallback logic
    ASYNC_PATTERN = "async_pattern"       # Async/await, coroutine, event loop interaction
    CONCURRENCY = "concurrency"           # Thread pool, multiprocessing, worker channels

    # Configuration & Environment
    CONFIG_KEY = "config_key"             # Key-value declaration in settings files
    ENV_VAR = "env_var"                   # Environment variable access or definition

    # Data & Storage
    DB_QUERY = "db_query"                 # SQL statement, ORM query, transaction block
    SCHEMA_DEF = "schema_def"             # DB model, migration table, Pydantic schema
    MIGRATION = "migration"               # Schema migration step

    # Architecture & Manifest
    DEPENDENCY = "dependency"             # Manifest package dependency (pyproject, package.json)
    FRAMEWORK_MARKER = "framework_marker" # Sentinel file or framework boilerplate
    ARCHITECTURE_PATTERN = "architecture_pattern"

    # Explicit Absence
    ABSENT_PATTERN = "absent_pattern"     # Explicitly verified absence of required safeguard
```

### 2.2 `EvidenceFact` (The Atomic Observation)
An `EvidenceFact` is an immutable, frozen dataclass representing a verified structural observation in the target repository.

```python
@dataclass(frozen=True)
class EvidenceFact:
    kind: EvidenceKind
    subject: str                         # Symbol or key under observation (e.g. 'redis', 'retry')
    language: str                        # 'python', 'typescript', 'go', 'rust', etc.
    file_path: Path                      # Relative or absolute path to source file
    line_range: tuple[int, int] | None   # (start_line, end_line)
    snippet: str                         # Verbatim source code snippet (capped at <= 200 chars)
    scope: str | None = None             # Enclosing function or class name
    call_target: str | None = None       # Resolved/qualified call target
    call_args_schema: str | None = None  # Summary of arguments passed
    parent_symbol: str | None = None     # Base class or decorated symbol
    value_observed: str | None = None    # Config or constant value
    value_schema: str | None = None      # Type/format of observed value
    extraction_confidence: float = 1.0   # Scanner certainty of observation (0.0 to 1.0)
    identifier_hints: tuple[str, ...] = ()# Weak corroborating symbol hints
    framework: str | None = None         # 'fastapi', 'express', etc.
    library: str | None = None           # 'tenacity', 'redis-py', etc.
    ttl_observed: bool | None = None     # Specific parameter flag for cache checks
    retry_count_observed: int | None = None
    timeout_observed: bool | None = None
    circuit_breaker_threshold: int | None = None
```

### 2.3 `Evidence` (Citation) and `Decision` (Verdict)
When an agent evaluates a concept, it emits one or more `Decision` records with citations:

```python
class DecisionStatus(str, Enum):
    IMPLEMENTED = "implemented"       # Concept is correctly present and verified
    MISSING = "missing"               # Concept is absent where expected
    MISCONFIGURED = "misconfigured"   # Concept is present but exhibits dangerous smells
    UNKNOWN = "unknown"               # Insufficient evidence to determine status

class Priority(str, Enum):
    CRITICAL = "critical"             # High probability of system crash, outage, or data loss
    HIGH = "high"                     # Significant reliability, security, or performance risk
    MEDIUM = "medium"                 # Technical debt or suboptimal resiliency
    LOW = "low"                       # Minor improvement or hygiene item
    INFO = "info"                     # Informational pattern confirmation
    N_A = "n/a"

@dataclass(frozen=True)
class Evidence:
    """Citation proving a decision: file, line, verbatim snippet, and reviewer note."""
    file: str
    line: int
    snippet: str
    note: str = ""

@dataclass(frozen=True)
class Decision:
    concept_id: str                   # e.g., 'foundation.caching', 'resilience.circuit-breaker'
    concept_name: str                 # Readable concept title
    status: DecisionStatus
    confidence: float                 # Architectural certainty score (0.0 to 1.0)
    priority: Priority = Priority.INFO
    evidence: list[Evidence] = field(default_factory=list)
    misconfiguration: str | None = None
    gaps: list[str] = field(default_factory=list)
    recommendation: str | None = None
```

---

## 3. Confidence vs. Extraction Certainty

A critical distinction enforced in SDAT's evidence architecture:

1. **Scanner `extraction_confidence` (0.0 – 1.0):**
   * Represents the *syntactic certainty* that the scanner accurately identified the AST construct.
   * Direct AST visits (e.g. Python `ast.Import`) yield `1.0`.
   * Heuristic regex matches on raw text yield lower extraction confidence (`0.6 – 0.8`).
2. **Agent `confidence` (0.0 – 1.0):**
   * Represents the *architectural certainty* that the concept is properly implemented or absent.
   * High confidence (`> 0.8`) requires structural evidence (e.g., both connection instantiation and query execution with error handlers).
   * Identifier name matches alone (e.g. a variable named `cache = True`) result in low confidence or rejection.

---

## 4. Evidence Aggregation and Correlation

The `EvidenceAggregator` class in [sdat/evidence/aggregator.py](../../sdat/evidence/aggregator.py) provides multi-pass consolidation:
1. **Deduplication:** Normalizes snippets and deduplicates identical observations in the same file and line range.
2. **Cross-File Linkage:** Links imported client libraries (e.g. `import redis` in `app/config.py`) to downstream usage (e.g. `client.get()` in `app/services/user.py`).
3. **Absence Correlation:** Verifies whether a call site is missing required defensive arguments (such as HTTP calls made without an explicit `timeout` argument).
4. **Bundling:** Emits `EvidenceBundle` records keyed by target concept to provide focused context for swarm agents.

---

## 5. Backward Compatibility (`SignalBridge`)

To maintain interoperability with legacy rules during the v0.4.0 evolution:
* `SignalBridge.facts_to_signals(facts)` translates modern `EvidenceFact` structures into legacy `Signal` objects.
* `SignalBridge.signals_to_facts(signals)` converts legacy signals back into typed facts with kind `EvidenceKind.LEGACY_SIGNAL`.
* Both representations are supported in agent execution contexts without data loss.
