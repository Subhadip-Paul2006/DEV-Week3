---
id: security.secrets-management
category: security
name: Secrets Management
owning_agent: F-09
maturity: stable
languages:
- any
tags:
- vault
- secrets
- credentials
- rotation
related:
- foundation.config
- security.https
domain: core
---

# Secrets Management

## 1. Overview

Secrets Management covers how API keys, database passwords, and certificates are stored, distributed, and rotated. Hardcoded secrets in repositories are the leading cause of credential-related breaches.

## 2. Core Principles

- Secrets Management must be implemented with clear ownership and documented operational procedures.
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


**Secrets in .env committed to git** — Even with .gitignore, a single committed .env file exposes secrets permanently in git history.

**Secrets in plaintext configmaps** — Storing secrets in Kubernetes ConfigMaps instead of Secrets, making them visible to anyone with cluster read access.


## 6. Real-World Examples


- **Industry standard** — Secrets Management is widely adopted across production systems at scale.


## 7. Detection Signals


**Presence signals:**
- `security.secrets-management.presence.vault` — HashiCorp Vault integration.
- `security.secrets-management.presence.aws-secrets-manager` — AWS Secrets Manager client.
- `security.secrets-management.presence.sops` — SOPS encrypted files.

**Misconfiguration signals:**
- `security.secrets-management.misconfig.hardcoded-secret` — Secrets embedded in source code.

**Anti-pattern:**
- `security.secrets-management.anti.secret-in-code` — API keys, passwords, or tokens in plaintext.

