---
id: observability.tracing
category: observability
name: Distributed Tracing
owning_agent: O-15
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- opentelemetry
- jaeger
- zipkin
- trace-id
- span
related:
- observability.metrics
- streaming.event-streaming
domain: core
---

# Distributed Tracing

## 1. Overview

Distributed Tracing tracks a request across service boundaries using trace IDs and spans. Distributed tracing reveals latency hotspots in microservice architectures.

## 2. Core Principles

- Distributed Tracing must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Distributed Tracing is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Distributed Tracing.

**Absence:** No evidence of this concept's implementation in the codebase.

