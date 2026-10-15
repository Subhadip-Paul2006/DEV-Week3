---
id: data.backup
category: data
name: Backup & Recovery
owning_agent: D-13
maturity: stable
languages:
- any
tags:
- snapshot
- replication
- pitr
- point-in-time
related:
- data.migrations
- compliance.audit-log
domain: database
---

# Backup & Recovery

## 1. Overview

Backup & Recovery ensures data durability through periodic snapshots, replication, and point-in-time recovery. Backup strategy defines RPO (Recovery Point Objective) and RTO (Recovery Time Objective).

## 2. Core Principles

- Backup & Recovery must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Backup & Recovery is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Backup & Recovery.

**Absence:** No evidence of this concept's implementation in the codebase.

