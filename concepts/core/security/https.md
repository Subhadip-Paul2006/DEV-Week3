---
id: security.https
category: security
name: HTTPS / TLS
owning_agent: F-09
maturity: stable
languages:
- any
tags:
- tls
- ssl
- encryption
- certificates
related:
- security.cors
- security.headers
domain: core
---

# HTTPS / TLS

## 1. Overview

HTTPS / TLS encrypts HTTP traffic using TLS, preventing eavesdropping and man-in-the-middle attacks. Every production service must terminate TLS at the edge and enforce HTTPS-only access. Certificate management (rotation, renewal, stapling) is part of this concept's operational burden.

## 2. Core Principles

- HTTPS / TLS must be implemented with clear ownership and documented operational procedures.
- The implementation must be testable, observable, and recoverable in failure scenarios.
- Configuration must be externalised and never hardcoded in source control.
- Failure modes must be explicitly handled with appropriate fallbacks and timeouts.
- The concept's effectiveness must be measurable through metrics, logs, or traces.

## 3. Sub-Concepts


### 3.1 TLS Termination

**Definition:** The point at which encrypted HTTPS traffic is decrypted and passed as HTTP to backend services. Typically occurs at a load balancer, CDN, or reverse proxy.

**Why it matters:** TLS termination at the edge centralises certificate management and offloads CPU-intensive encryption from application servers.

**Implementation patterns:**
- Cloud provider ALB/NLB with ACM certificate
- Nginx with Let's Encrypt (certbot)
- Envoy with SDS (Secret Discovery Service)


## 4. Implementation Patterns

```python
# Python — Enforce HTTPS with FastAPI
from fastapi import FastAPI, Request
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

app = FastAPI()
app.add_middleware(HTTPSRedirectMiddleware)
```

```yaml
# Nginx — TLS termination
server {
    listen 443 ssl http2;
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

## 5. Anti-Patterns


**Hardcoded certificates** — Embedding certificate content in source code or environment variables without rotation.

**Mixed content** — Serving HTTPS pages that load HTTP resources (scripts, images, APIs), which browsers block and which man-in-the-middle attacks exploit.


## 6. Real-World Examples


- **GitHub** — Enforces HTTPS for all traffic, uses HSTS with max-age of 1 year.

- **Stripe** — TLS 1.3 only, with certificate pinning for their dashboard.


## 7. Detection Signals


**Presence signals:**
- `security.https.presence.force-ssl` — HTTPS redirect middleware or forced-SSL configuration.
- `security.https.presence.tls-config` — TLS version/cipher configuration files.

**Absence signal:**
- `security.https.absence` — No TLS configuration, no HTTPS redirect, plain HTTP only.

