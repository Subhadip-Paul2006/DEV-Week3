---
id: resilience.timeouts
category: resilience
name: Timeouts & Deadlines
owning_agent: R-19
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- connect-timeout
- read-timeout
- deadline
- context-timeout
related:
- resilience.circuit-breaker
- resilience.retries
domain: core
---

# Timeouts & Deadlines

## 1. Overview

Timeouts & Deadlines bounds the wall-clock time of every external call. A missing timeout can hold a thread or connection indefinitely during a downstream outage.

## 2. Core Principles

- Timeouts & Deadlines must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Timeouts & Deadlines is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Timeouts & Deadlines.

**Absence:** No evidence of this concept's implementation in the codebase.

