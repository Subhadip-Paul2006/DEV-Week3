---
id: performance.connection-pool
category: performance
name: Connection Pooling
owning_agent: P-26
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- pgbouncer
- pool-size
- max-connections
- pooling
related:
- data.orm
- foundation.connection-pooling
domain: core
---

# Connection Pooling

## 1. Overview

Connection Pooling reuses TCP and database connections across requests, avoiding the overhead of creating a new connection per request. Pool sizing is critical: too small creates contention, too large exhausts backend capacity.

## 2. Core Principles

- Connection Pooling must be implemented with clear ownership and documented operational procedures.
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


**Skipping this concept** — The most common anti-pattern is simply not implementing the concept at all, trading short-term velocity for long-term technical debt.


## 6. Real-World Examples


- **Industry standard** — Connection Pooling is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Connection Pooling.

**Absence:** No evidence of this concept's implementation in the codebase.

