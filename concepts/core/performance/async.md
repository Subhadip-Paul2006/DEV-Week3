---
id: performance.async
category: performance
name: Async Processing
owning_agent: P-27
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- async-await
- asyncio
- event-loop
- non-blocking
related:
- streaming.message-broker
- performance.connection-pool
domain: core
---

# Async Processing

## 1. Overview

Async Processing uses non-blocking I/O to handle concurrent operations without dedicating a thread per operation. Async patterns are essential for I/O-bound workloads.

## 2. Core Principles

- Async Processing must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Async Processing is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Async Processing.

**Absence:** No evidence of this concept's implementation in the codebase.

