---
id: compliance.audit-log
category: compliance
name: Audit Logging
owning_agent: C-44
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- audit
- soc2
- hipaa
- immutable-log
- tamper-proof
related:
- compliance.pii
- observability.tracing
- core.observability
domain: cross_domain
specializes: core.observability
---

# Audit Logging

## 1. Overview

Audit Logging creates tamper-evident, time-ordered records of security-relevant events. Audit logs are required for SOC 2, HIPAA, PCI-DSS, and internal incident investigation.

## 2. Core Principles

- Audit Logging must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Audit Logging is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Audit Logging.

**Absence:** No evidence of this concept's implementation in the codebase.

