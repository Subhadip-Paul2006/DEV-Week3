---
id: security.headers
category: security
name: Security Headers
owning_agent: F-09
maturity: stable
languages:
- any
tags:
- helmet
- csp
- hsts
- x-frame-options
related:
- security.https
- security.cors
domain: core
---

# Security Headers

## 1. Overview

Security Headers are HTTP response headers that instruct browsers to enforce security policies. They mitigate XSS, clickjacking, MIME sniffing, and data exfiltration without changing application code.

## 2. Core Principles

- Security Headers must be implemented with clear ownership and documented operational procedures.
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


**Helmet-only illusion** — Adding Helmet.js with default settings without reviewing and tightening individual headers (CSP, HSTS max-age).


## 6. Real-World Examples


- **Industry standard** — Security Headers is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Security Headers.

**Absence:** No evidence of this concept's implementation in the codebase.

