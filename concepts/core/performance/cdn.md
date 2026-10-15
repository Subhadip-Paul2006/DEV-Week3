---
id: performance.cdn
category: performance
name: CDN & Edge Caching
owning_agent: P-29
maturity: stable
languages:
- any
tags:
- cloudflare
- cloudfront
- fastly
- edge
related:
- performance.async
- foundation.caching
domain: core
---

# CDN & Edge Caching

## 1. Overview

CDN & Edge Caching caches static and dynamic content at geographically distributed edge locations. CDNs reduce latency for global users and absorb traffic spikes.

## 2. Core Principles

- CDN & Edge Caching must be implemented with clear ownership and documented operational procedures.
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


- **Industry standard** — CDN & Edge Caching is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to CDN & Edge Caching.

**Absence:** No evidence of this concept's implementation in the codebase.

