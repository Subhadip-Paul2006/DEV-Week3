---
id: deployment.iaac
category: deployment
name: Infrastructure as Code
owning_agent: D-24
maturity: stable
languages:
- any
tags:
- terraform
- cloudformation
- pulumi
- bicep
related:
- deployment.orchestration
- cloud.cost-optimization
domain: devops
---

# Infrastructure as Code

## 1. Overview

Infrastructure as Code declaratively defines infrastructure in version-controlled files. IaC enables peer-reviewed infrastructure changes, drift detection, and reproducible environments.

## 2. Core Principles

- Infrastructure as Code must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Infrastructure as Code is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Infrastructure as Code.

**Absence:** No evidence of this concept's implementation in the codebase.

