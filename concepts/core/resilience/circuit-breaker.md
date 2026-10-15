---
id: resilience.circuit-breaker
category: resilience
name: Circuit Breaker
owning_agent: R-17
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- pybreaker
- resilience4j
- hystrix
- opossum
related:
- resilience.retries
- resilience.timeouts
domain: core
---

# Circuit Breaker

## 1. Overview

Circuit Breaker stops calling a failing downstream service after a threshold of failures, giving it time to recover. Without circuit breakers, cascading failures take down entire dependency chains.

## 2. Core Principles

- Circuit Breaker must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Circuit Breaker is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Circuit Breaker.

**Absence:** No evidence of this concept's implementation in the codebase.

