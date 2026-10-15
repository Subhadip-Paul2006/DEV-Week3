---
id: observability.alerting
category: observability
name: Alerting & Paging
owning_agent: O-16
maturity: stable
languages:
- any
tags:
- alertmanager
- pagerduty
- opsgenie
- slo
- error-budget
related:
- observability.metrics
- resilience.timeouts
domain: core
---

# Alerting & Paging

## 1. Overview

Alerting & Paging converts metric thresholds and log patterns into human-actionable notifications. Alerting design must balance signal-to-noise ratio against detection latency.

## 2. Core Principles

- Alerting & Paging must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Alerting & Paging is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Alerting & Paging.

**Absence:** No evidence of this concept's implementation in the codebase.

