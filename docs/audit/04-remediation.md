# 04 — Architectural Remediation Guide

> **तन्त्रविन्यास-निरीक्षा (निरीक्षा)** — System Design Audit Tool
> *Target:* `fastapi_project` | *Path:* `D:\SDAT\tests\fixtures\fastapi_project`
> **AI Reasoning Engine:** `qwen/qwen3-coder:free` (Offline Cached Artifact)

---

## Executive Architectural Summary

The FastAPI project establishes a mature production baseline with distributed caching (Redis), resilience boundaries (pybreaker circuit breaker, tenacity retries), structured database connectivity (SQLAlchemy), and observability (OpenTelemetry). However, the primary architectural gap is the absence of an idempotency key protocol on state-mutating endpoints, exposing the system to duplicate processing and race-condition mutations during client retry storms.

---

## Prioritized Architectural Action Plans

### 1. [HIGH] Idempotency For Mutating Operations

**Concept ID:** `backend.idempotency` | **Status:** `missing` | **Confidence:** `0.92`

#### Finding
State-mutating endpoints lack idempotency key validation and distributed response deduplication.

#### Evidence
- Location: `app/main.py:42`
  ```text
  @app.post('/items')
def create_item(item: ItemSchema):
  ```

#### Why It Matters
Network blips and client-side retries over distributed links cause duplicate operations, phantom record creation, and inconsistent financial or inventory records without deterministic request deduplication.

#### Architectural Impact
Resource duplication, data drift between distributed caches and primary databases, and potential double-charging under high concurrency.

#### Architectural Reasoning (qwen/qwen3-coder:free)
> Qwen3-Coder analyzed the repository AST facts and endpoint declarations. Downstream dependencies feature circuit breakers and retries, but upstream ingress does not validate Idempotency-Key headers, violating at-most-once delivery guarantees.

#### Recommended Solution
Introduce an IdempotencyMiddleware or dependency in FastAPI utilizing Redis SETNX with TTL. Validate and store computed responses keyed by Idempotency-Key header.

#### Architectural Transformation
```text
BEFORE: Client ──► [Unbounded POST /items] ──► Flaky Network Retry ──► [Duplicate Database Record Created]
AFTER:  Client (Idempotency-Key) ──► Redis Token Lock (SETNX) ──► [First Request: 201 Created | Retries: 201 From Cache]
```

#### Concrete Implementation Steps
- 1. Create app/idempotency.py defining IdempotencyKeyHeader dependency and Redis storage backend
- 2. Parse 'Idempotency-Key' from incoming request headers for mutating HTTP verbs (POST, PUT, PATCH)
- 3. Atomically check and reserve the idempotency key in Redis using `SET key IN_PROGRESS NX EX 120`
- 4. Return previously cached response (HTTP status, headers, body) if key is already resolved
- 5. Upon successful execution, persist response in Redis with a 24-hour expiration (`EX 86400`)

#### Validation Criteria
Run an asynchronous integration test using pytest-asyncio and httpx sending 5 concurrent requests with identical Idempotency-Key headers. Verify exactly 1 execution reaches the service handler and all 5 receive identical HTTP 201 responses.

---


### Note on Verification
SDAT remediation guidance is generated to assist architectural evolution. All recommended steps 
should be tested in staging environments before production deployment.

*Developed by shubh06 — तन्त्रविन्यास-निरीक्षा*