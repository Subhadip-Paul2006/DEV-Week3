---
id: data.indexing
category: data
name: Database Indexing
owning_agent: D-12
maturity: stable
languages:
- any
tags:
- b-tree
- composite-index
- covering-index
- query-optimization
related:
- data.orm
- performance.pagination
domain: database
---

# Database Indexing

## 1. Overview

Database Indexing uses B-tree, hash, and composite indexes to accelerate query performance. Index design directly affects read throughput and write latency.

## 2. Core Principles

- Database Indexing must be implemented with clear ownership and documented operational procedures.
- The implementation must be testable, observable, and recoverable in failure scenarios.
- Configuration must be externalised and never hardcoded in source control.
- Failure modes must be explicitly handled with appropriate fallbacks and timeouts.
- The concept's effectiveness must be measurable through metrics, logs, or traces.

## 3. Sub-Concepts


### 3.1 Core Components

Each concept can be decomposed into its primary components, each with distinct responsibilities, failure modes, and scaling characteristics.


## 4. Implementation Patterns

```python
# Implementation pattern
# Refer to the scanner rules in config/rules/signals/ for detection patterns.
```

## 5. Anti-Patterns


**Over-indexing** — Adding indexes to every column without considering write overhead. Each index slows INSERT/UPDATE/DELETE operations.

**Missing composite indexes** — Using separate single-column indexes instead of composite indexes for multi-column WHERE clauses.


## 6. Real-World Examples


- **Industry standard** — Database Indexing is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Database Indexing.

**Absence:** No evidence of this concept's implementation in the codebase.

