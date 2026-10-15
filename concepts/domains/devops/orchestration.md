---
id: deployment.orchestration
category: deployment
name: Container Orchestration
owning_agent: D-22
maturity: stable
languages:
- any
tags:
- kubernetes
- k8s
- helm
- argo-cd
- ecs
related:
- deployment.containers
- networking.service-mesh
domain: devops
---

# Container Orchestration

## 1. Overview

Container Orchestration automates container scheduling, networking, scaling, and self-healing across a cluster of machines. Kubernetes is the de facto standard.

## 2. Core Principles

- Container Orchestration must be implemented with clear ownership and documented operational procedures.
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


- **Spotify** — Allegedly runs the world's largest Kubernetes cluster (10,000+ nodes).

- **Lyft** — Migrated from Mesos to Kubernetes, reducing deploy time from hours to minutes.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Container Orchestration.

**Absence:** No evidence of this concept's implementation in the codebase.

