---
id: networking.dns
category: networking
name: DNS & Service Discovery
owning_agent: N-42
maturity: stable
languages:
- any
tags:
- dns
- consul
- core-dns
- service-discovery
related:
- networking.proxy
- deployment.orchestration
domain: core
---

# DNS & Service Discovery

## 1. Overview

DNS & Service Discovery translates human-readable domain names to IP addresses. In modern infrastructure, DNS also enables service discovery, load balancing, and failover.

## 2. Core Principles

- DNS & Service Discovery must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — DNS & Service Discovery is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to DNS & Service Discovery.

**Absence:** No evidence of this concept's implementation in the codebase.

