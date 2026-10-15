---
id: networking.load-balancer
category: networking
name: Load Balancer
owning_agent: N-40
maturity: stable
languages:
- any
tags:
- alb
- elb
- lb
- round-robin
- least-connections
related:
- networking.proxy
- foundation.load-balancers
domain: networking
---

# Load Balancer

## 1. Overview

Load Balancer distributes incoming traffic across multiple backend instances. Load balancers operate at L4 (TCP/UDP) or L7 (HTTP/HTTPS) and provide health-checked routing.

## 2. Core Principles

- Load Balancer must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — Load Balancer is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Load Balancer.

**Absence:** No evidence of this concept's implementation in the codebase.

