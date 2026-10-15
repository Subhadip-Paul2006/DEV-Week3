---
id: security.sanitization
category: security
name: Input Sanitization
owning_agent: F-09
maturity: stable
languages:
- python
- typescript
- go
- java
tags:
- xss
- sql-injection
- sanitize
- escape
related:
- security.dependency-scan
- foundation.validation
domain: core
---

# Input Sanitization

## 1. Overview

Input Sanitization ensures user-supplied input cannot alter application logic or corrupt stored data. It covers output encoding, SQL parameterization, XSS prevention, and template auto-escaping.

## 2. Core Principles

- Input Sanitization must be implemented with clear ownership and documented operational procedures.
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


**Client-side only sanitization** — Trusting JavaScript input validation as the sole defense, ignoring that client-side checks can be bypassed.

**String concatenation for SQL** — Building queries by concatenating user input, which is the #1 cause of SQL injection vulnerabilities.


## 6. Real-World Examples


- **Industry standard** — Input Sanitization is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Input Sanitization.

**Absence:** No evidence of this concept's implementation in the codebase.

