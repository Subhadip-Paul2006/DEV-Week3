---
id: resilience.retries
category: resilience
name: Retry Strategy
owning_agent: R-18
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- tenacity
- backoff
- exponential
- jitter
related:
- resilience.circuit-breaker
- foundation.idempotency
domain: core
---

# Retry Strategy

## 1. Overview

Retry Strategy re-attempts transient failures using strategies like exponential backoff with jitter. Retries must be idempotent-safe to prevent duplicate side effects.

## 2. Core Principles

- Retry Strategy must be implemented with clear ownership and documented operational procedures.
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


**Retries without backoff** — Immediate retries amplify load on a failing service, turning a brief blip into an extended outage.

**Retrying non-idempotent operations** — Retrying a POST that creates resources can produce duplicates.


## 6. Real-World Examples


- **Industry standard** — Retry Strategy is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Retry Strategy.

**Absence:** No evidence of this concept's implementation in the codebase.

