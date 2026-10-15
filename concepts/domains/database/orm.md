---
id: data.orm
category: data
name: ORM / Data Mapper
owning_agent: D-10
maturity: stable
languages:
- python
- typescript
- go
- java
- kotlin
- php
- ruby
tags:
- sqlalchemy
- prisma
- typeorm
- eloquent
- gorm
related:
- data.migrations
- data.indexing
domain: database
---

# ORM / Data Mapper

## 1. Overview

ORM / Data Mapper abstracts SQL database access through an object-oriented interface, eliminating hand-written SQL for most operations while providing query builders, migrations, and connection management.

## 2. Core Principles

- ORM / Data Mapper must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — ORM / Data Mapper is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to ORM / Data Mapper.

**Absence:** No evidence of this concept's implementation in the codebase.

