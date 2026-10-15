---
id: security.dependency-scan
category: security
name: Dependency Scanning
owning_agent: F-09
maturity: emerging
languages:
- any
tags:
- snyk
- dependabot
- pip-audit
- trivy
related:
- deployment.ci-cd
- security.sanitization
domain: core
---

# Dependency Scanning

## 1. Overview

Dependency Scanning detects known vulnerabilities in third-party libraries before they reach production. Automated scanning in CI/CD is the primary defense against supply-chain attacks.

## 2. Core Principles

- Dependency Scanning must be implemented with clear ownership and documented operational procedures.
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


**Scanning only in development** — Running dependency scans manually instead of in CI/CD, allowing vulnerable dependencies to reach production.


## 6. Real-World Examples


- **Industry standard** — Dependency Scanning is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Dependency Scanning.

**Absence:** No evidence of this concept's implementation in the codebase.

