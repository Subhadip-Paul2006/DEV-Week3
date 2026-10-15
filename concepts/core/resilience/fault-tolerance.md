---
id: foundation.fault-tolerance
category: foundation
owning_agent: F-08
maturity: stable
languages:
- any
tags:
- resilience
- timeout
- bulkhead
- graceful-degradation
related:
- foundation.circuit-breaker
- foundation.retries
- foundation.message-queues
domain: core
---

# Fault Tolerance

## 1. Overview

Fault tolerance is the set of engineering techniques that allow a distributed system to keep functioning correctly when individual components fail. Every piece of software involved in a production system will fail: network packets are dropped, services restart, disks fill, databases lock, downstream APIs return 500s, and garbage-collection pauses cause multi-second latencies. Fault tolerance does not prevent failures — it prevents failures from propagating, cascading, or becoming visible to end users. It exists because "it worked on my machine" is a necessary but insufficient condition for a system that serves real traffic across unreliable networks and unreliable hosts.

## 2. Core Principles

- **Failure is inevitable, not exceptional.** Plan for it. If a system works only when every component is healthy, it does not work in production.
- **Contain failures before they spread.** A timeout misconfiguration in one microservice should not trigger a thundering herd that takes down three other services. Isolation is a first-class design goal.
- **Fail fast, degrade gracefully.** Knowing a downstream is unavailable in 100 ms and returning a cached result is better than hanging for 30 seconds and timing out anyway.
- **Retry only idempotent operations.** Retrying a non-idempotent write multiplies the failure surface. `GET` and `PUT` to a known ID are idempotent; `POST /charge` is not.
- **Backpressure must be explicit.** A system that accepts unlimited work when it is already overloaded will eventually collapse. Signal overload to upstream systems so they can shed load.
- **Recovery should be automatic.** Human intervention at 3 AM is not a fault-tolerance strategy. Every failure mode should have an automatic path to recovery.
- **Observe before you fix.** You cannot tolerate failures you cannot see. Every tolerance mechanism must produce observable signals — metrics, logs, traces, and paging alerts.

## 3. Sub-Concepts

### 3.1 Timeouts (Connect, Read, Total, Strategy)

**Definition:** A timeout is the maximum duration a caller will wait for a response from a downstream call before aborting. Timeouts come in four flavors: connect (TCP handshake), read (waiting for response bytes), overall request (end-to-end including retries), and strategy-level (cumulative wall time before giving up entirely).

**Why it matters:** No timeout is the most common distributed-systems bug. Without timeouts, one slow thread per request can pin a thread pool, pin a connection pool, and propagate into an OOM. Default timeout values in libraries are almost always wrong for production environments (e.g., Python `requests` default timeout is `None` — no timeout at all).

**Implementation patterns:**
```python
import httpx
import tenacity

client = httpx.Client(
    timeout=httpx.Timeout(
        connect=2.0,    # TCP handshake must complete in 2 s
        read=5.0,       # wait at most 5 s for the first byte after connection
        write=2.0,      # send the full request body in 2 s
        pool=3.0,       # get a connection from the pool in 3 s
    ),
)

@retry.retry(
    retry=tenacity.retry_if_exception_type(httpx.TimeoutException)
    | tenacity.retry_if_exception_type(httpx.NetworkError),
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=0.5, min=0.5, max=4),
    reraise=True,
)
async def call_payment_api(order):
    resp = await client.post(
        'https://payments.example.com/charge',
        json=order,
        timeout=httpx.Timeout(read=10.0, connect=3.0),
    )
    resp.raise_for_status()
    return resp.json()
```
```typescript
// TypeScript / node-fetch
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 5000);

const res = await fetch('https://payments.example.com/charge', {
  method: 'POST',
  signal: controller.signal,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(order),
});

clearTimeout(timeout);
if (!res.ok) throw new Error(`HTTP ${res.status}`);
return res.json();
```
```go
// Go — standard net/http with context deadline
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
defer cancel()

req, _ := http.NewRequestWithContext(ctx, "POST", apiURL, bytes.NewReader(payload))
req.Header.Set("Content-Type", "application/json")

client := &http.Client{
    Timeout: 10 * time.Second,           // overall request ceiling
    Transport: &http.Transport{
        DialContext: (&net.Dialer{
            Timeout:   3 * time.Second,   // TCP connect
            KeepAlive: 30 * time.Second,
        }).DialContext,
        TLSHandshakeTimeout: 3 * time.Second,
        ResponseHeaderTimeout: 5 * time.Second,
    },
}
resp, err := client.Do(req)
```

**Common mistakes:** Using a single global timeout for all calls; setting the timeout longer than the upstream load balancer's timeout (hidden timeouts); forgetting to cancel the context on success; using `socket.setSoTimeout` instead of proper read/write timeouts.

**Scanner signals:** `httpx.Timeout(`, `requestTimeout`, `Timeout(\d*\.?\d*\s*(?:second\|s\|ms))`, `context.WithTimeout`, `AbortController`, `deadline` keyword in SQL or gRPC calls.

### 3.2 Retries (Policies, Exponential Backoff, Jitter)

**Definition:** A retry re-executes a failed call, optionally with a delay between attempts. The key policy decisions are: which failures to retry (network errors yes; 400 bad request no; 409 conflict maybe; 429 rate-limit yes), how long to wait, how many attempts, and what to do when retries are exhausted.

**Why it matters:** Transient failures (a 503 during a deploy, a TCP reset during a HA failover, a rate-limit 429) are normal. Retrying them makes them invisible. But retrying non-idempotent writes or crashing fast-fail paths creates data corruption and cascading load.

**Implementation patterns:**
```python
import tenacity
import httpx

# ✅ CORRECT — exponential backoff with full jitter, only retry network errors
@tenacity.retry(
    retry=(
        tenacity.retry_if_exception_type(httpx.TimeoutException)
        | tenacity.retry_if_exception_type(httpx.NetworkError)
        | tenacity.retry_if_result(lambda r: r.status_code == 429)
    ),
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=0.5, min=0.5, max=4)
           + tenacity.wait_random(0, 1),    # jitter
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def call_order_service(order_id):
    return client.get(f'https://orders.example.com/{order_id}')
```

**Backoff formulas:**
| Strategy | Formula | Notes |
|---|---|---|
| Fixed delay | `delay = constant` | Predictable but causes thundering herd. Never use without jitter. |
| Exponential | `delay = base × 2^(attempt-1)` | Standard. Add jitter. |
| Exponential + full jitter | `delay = random(0, base × 2^(attempt-1))` | Best practice from AWS Architecture Blog. |
| Decorrelated Jitter | `delay = min(cap, random(base, sleep × 3))` | Used by AWS SDK. |
| Fibonacci | `delay = fib(attempt) × base` | Slow escalation, safer for sensitive services. |

**Scanner signals:** Library imports (`tenacity`, `retry`, `go-retryablehttp`, `axios-retry`, `opossum`), retry configs (`maxRetries`, `max_attempts`, `RetryPolicy`), `maxRetries = 0` (intentionally none) — important positive signal.

### 3.3 Circuit Breaker (States, Transitions, Half-Open)

**Definition:** A circuit breaker wraps a call to a downstream and monitors for failures. It has three states: **Closed** (normal, calls pass through), **Open** (call fails immediately without hitting the downstream — it is "open"), and **Half-Open** (periodically lets one request through to check recovery). When the failure rate exceeds a threshold, the breaker trips open. After a cooldown, it goes half-open.

**Why it matters:** A circuit breaker is the primary defense against cascading failures. Without one, a downstream that is timing out at 100 % will cause every call to wait for the full timeout, consuming threads and connections. With a breaker, it fails fast in < 1 ms and lets the downstream recover.

**State diagram:**
```
Closed → Open     (failure rate > threshold for N consecutive failures)
Open    → Half-Open (cooldown timer expires)
Half-Open → Closed  (test request succeeds)
Half-Open → Open    (test request fails — reset cooldown)
```

**Implementation patterns:**
```python
# opossum (Python)
from opossum import (
    CircuitBreaker, CircuitBreakerError,
    CircuitBreakerStrategy,
    ThresholdOpenOnCount, IncrementOnFailure,
    OpenToClosedAfter, HalfOpenBuilder,
    CloseOnSuccess,
)

breaker = CircuitBreaker(
    name='payment-service',
    strategy=CircuitBreakerStrategy(
        failure_threshold=ThresholdOpenOnCount(5),
        increment_on_failure=IncrementOnFailure(),
        open_to_closed_after=OpenToClosedAfter(time=10_000),  # 10 s cooldown
        close_on_success=CloseOnSuccess(count=2),              # 2 success in half-open
    ),
)

try:
    with breaker:
        resp = client.post(api_url, json=payload)
except CircuitBreakerError:
    # fail fast — return fallback
    return fallback_response
```
```typescript
// TypeScript — opossum
import CircuitBreaker from 'opossum';

const breaker = new CircuitBreaker(
  callPaymentAPI,
  {
    timeout: 5000,
    errorThresholdPercentage: 50,
    resetTimeout: 15000,
    volumeThreshold: 10,        // min 10 calls before measuring error rate
    rollingCountTimeout: 5000,
    rollingCountBuckets: 10,
    fallback: () => ({ fallback: true }),
  }
);

const result = await breaker.fire(orderId);
```
```go
// Go — sony/gobreaker
import "github.com/sony/gobreaker"

var cb = gobreaker.NewCircuitBreaker(gobreaker.Settings{
    Name:        "PaymentAPI",
    MaxRequests: 3,           // max concurrent requests in half-open
    Interval:    time.Duration(30) * time.Second, // state change count reset window
    Timeout:     time.Duration(10) * time.Second, // open→half-open after this
    ReadyToTrip: func(counts gobreaker.Counts) bool {
        return counts.ConsecutiveFailures >= 5
           || float64(counts.TotalFailures)/float64(counts.Requests) > 0.6,
    },
    OnStateChange: func(name string, from gobreaker.State, to gobreaker.State) {
        metrics.inc(f'cb.state_change.{name}.{from}.{to}')
    },
})
```
```go
cb.Execute(func() (interface{}, error) {
    resp, err := httpClient.Do(req)
    if err != nil { return nil, err }
    return resp, nil
})
```

**Scanner signals:** Library imports (`opossum`, `sony/gobreaker`, `resilience4j`, `cbpython`, `netflix/hystrix`), circuit breaker config objects (`errorThresholdPercentage`, `ReadyToTrip`, `timeout` in CircuitBreaker config, not HTTP timeout), state-change callbacks (`onStateChange`, `OnStateChange`), fallback functions.

### 3.4 Bulkhead Pattern (Thread/Connection Pools, Isolation)

**Definition:** A bulkhead isolates distinct functional areas of a system so that a failure in one area does not exhaust resources needed by another. Named after watertight compartments in a ship — one compartment flooding does not sink the ship.

**Why it matters:** Without bulkheads, a single slow downstream can consume all connections from a shared pool, starving other unrelated services. A payment service using the same HTTP connection pool as the notification service means payment failures starve email sends.

**Implementation patterns:**
```python
# HTTP connection pools isolated per downstream
import httpx

# Pool for payment service (max 20 connections — won't starve others)
payment_client = httpx.Client(
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
    timeout=httpx.Timeout(connect=3, read=5),
)

# Pool for notification service (max 50 — expected higher volume)
notification_client = httpx.Client(
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
    timeout=httpx.Timeout(connect=3, read=10),
)
```
```typescript
// TypeScript — separate Agent pools
import { Agent } from 'https';

const paymentAgent = new Agent({ maxSockets: 20, keepAlive: true });
const notificationAgent = new Agent({ maxSockets: 50, keepAlive: true });

const paymentClient = axios.create({ httpsAgent: paymentAgent });
const notificationClient = axios.create({ httpsAgent: notificationAgent });
```
```go
// Go — separate transport pools per service
paymentTransport := &http.Transport{
    MaxIdleConns: 20,
    MaxIdleConnsPerHost: 10,
    IdleConnTimeout: 90 * time.Second,
    DisableKeepAlives: false,
}
paymentClient := &http.Client{Transport: paymentTransport, Timeout: 5 * time.Second}

notificationTransport := &http.Transport{
    MaxIdleConns: 50,
    MaxIdleConnsPerHost: 20,
}
notificationClient := &http.Client{Transport: notificationTransport, Timeout: 15 * time.Second}
```

**Scanner signals:** Separate `Limits` / `Transport` / `Agent` instances for different downstream hosts; named pool configs; absence of shared `global` connection pool.

### 3.5 Graceful Degradation and Fallbacks

**Definition:** When a component fails or is too slow, the system reduces functionality instead of failing entirely. Examples: returning cached data when the database is slow, showing a static rate-limit notice instead of a 500, displaying a pre-rendered HTML page when the CMS is down.

**Why it matters:** A system that returns a fast, partially-correct result is infinitely better than one that returns a 500. Users accept "your recommendation may be slightly stale" far more than "service unavailable."

**Implementation patterns:**
```python
# ✅ CORRECT — circuit breaker fallback
def get_product_recommendations(user_id: int) -> list:
    try:
        return recommendation_service.get_for(user_id)
    except CircuitBreakerOpenError:
        log.warning('rec service open, falling back to popular')
        return product_repo.popular(limit=10)

# ✅ CORRECT — stale-while-revalidate cache fallback
def get_user_profile(user_id: int) -> dict:
    cached = cache.get(f'profile:{user_id}')
    if cached:
        # trigger async refresh if > 5 min old
        if cached.get('age_seconds', 0) > 300:
            refresh_profile.delay(user_id)
        return cached
    try:
        profile = db.query("SELECT * FROM users WHERE id=%s", user_id)
        cache.setex(f'profile:{user_id}', 600, profile)
        return profile
    except DatabaseError:
        if cached:
            return cached  # degraded but functional
        raise
```

**Scanner signals:** `try/except` blocks with fallback returns, cache-as-fallback patterns, feature flag libraries (`flipper`, `flagsmith`, `launchdarkly`, `@unleash/client`), static fallback content files.

### 3.6 Bulkhead via Rate Limiting and Concurrency Guards

**Definition:** Rate limits cap the number of requests per time window to a service or endpoint. They complement circuit breakers: rate limits prevent hitting the downstream hard enough to trip the breaker; circuit breakers stop the bleeding once the breaker trips.

**Why it matters:** Rate limiting is the upstream bulkhead. It prevents the worst-case scenario (a buggy deploy sends 10k req/s to a 100 req/s service) before the circuit breaker even fires.

**Scanner signals:** Rate-limit middleware (`ratelimit`, `express-rate-limit`, `throttler`, `bottleneck`), Redis-based sliding window configs, nginx/Envoy rate-limit header configs.

### 3.7 Shed Load and Admission Control

**Definition:** When a system is overloaded, it must reject some requests rather than accept all and degrade all. This is "load shedding." Admission control is the pre-filter that decides which requests get through.

**Why it matters:** A system that accepts everything when at 100 % CPU returns responses at 10× their SLO, making every user miserable. The same system that rejects 30 % of requests when at capacity ensures the 70 % that pass through get acceptable latency. Overloaded systems must become selective, not slower.

**Implementation patterns:**
- **HTTP 429 Too Many Requests** with `Retry-After` header.
- **HTTP 503 Service Unavailable** with `Retry-After` when the system itself is overloaded (as opposed to per-client rate limiting).
- **TCP connection drop** (reset) when the worker pool is full — faster than a slow 503.
- **Layered:** rate-limit per user → queue depth gate → thread pool full → TCP reset. Each layer catches a different failure mode.

**Scanner signals:** HTTP 429 / 503 response codes, `Retry-After` header, thread pool max sizes, `max_connections` configs, admission-control gate decorators.

### 3.8 Watchdog and Health-Check Patterns

**Definition:** A health check is a synthetic probe (HTTP endpoint, TCP port) that tells an orchestrator (Kubernetes, ELB) whether a process is alive. A deeper "readiness" probe tells the LB whether the process should receive traffic. A "liveness" probe tells Kubernetes whether to kill and restart it.

**Why it matters:** A process that can accept TCP connections but is wedged in a deadlock (e.g., waiting for a downstream that will never respond) looks healthy to a TCP check. Liveness probes that only check "is the process running" miss this entirely. Readiness probes that check downstream health are the right tool.

**Scanner signals:** `/healthz`, `/ready`, `/live` endpoint definitions, k8s `livenessProbe` / `readinessProbe` config, load-balancer health-check URL config.

### 3.9 Retry Budgets and Hedged Requests

**Definition:** A retry budget caps the total number of retries allowed per time window as a fraction of the primary call count. Hedged requests send the same request to two backends simultaneously and return whichever answers first — a last-resort tolerance for jitter.

**Why it matters:** Unbounded retries amplify load by 3× or more during outages, turning a slow downstream into an overwhelmed one. Retry budgets keep the retry "blast radius" bounded. Hedged requests work well for expensive read queries from replicated datasets.

**Scanner signals:** Retry budget config (`max_retry_ratio`, `budget_percent`), hedged request patterns (`race` with multiple RPCs, `Spanner` hedged reads, `google-cloud-go` `experimental.UseGRPCQuorum`).

### 3.10 Observability

**Key metrics:**
- `http_request_duration_seconds` (p50, p95, p99) per endpoint
- `timeout_total` — count of timeout-triggered failures
- `retry_total` — count per retry attempt
- `circuit_breaker_state` — gauge: 0=closed, 1=open, 2=half-open
- `circuit_breaker_rejected_total` — requests rejected because breaker is open
- `pool_active_connections` — in-use connections per pool
- `pool_available_connections` — idle connections per pool
- `pool_pending_requests` — waiting for a pool slot (backpressure indicator)
- `health_check_failure_total` — failing health checks

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Timeout config on HTTP client | Python, TypeScript, Go | regex: `Timeout\(|requestTimeout|Timeout\(|context\.WithTimeout` | High |
| Retry decorator or library usage | Python, TypeScript, Go | regex: `@retry\|tenacity\|retry\(|retryablehttp\|resilience4j\|axios-retry` | High |
| Circuit breaker library import | Python, TypeScript, Go | regex: `opossum\|gobreaker\|resilience4j\|hystrix\|cbpython` | High |
| Separate connection pool per downstream | Python, TypeScript, Go | AST: distinct `Client(` / `Transport(` / `Agent(` instances per hostname | High |
| Circuit breaker fallback function | All | regex: `fallback\|default\|onStateChange` in breaker config | High |
| Graceful degradation (try/except with fallback) | Python | AST: `try` → `except` block contains a return or default value | Medium |
| Feature flag library import | All | regex: `flipper\|flagsmith\|launchdarkly\|unleash\|@unleash` | Medium |
| Liveness / readiness health endpoint | Python, TypeScript, Go | regex: `(?:/healthz\|/ready\|/live\|/liveness\|/readiness)` | High |
| Rate-limit middleware | All | regex: `rate.limit\|rateLimit\|throttler\|bottleneck` | Medium |
| Retry budget config | All | regex: `retry_budget\|max_retry_ratio\|budget` | Medium |
| Hedged request / parallel RPC | Go, TypeScript | regex: `HedgedRequest\|grpc\.DefaultStrategy\.(SingleUse\|UseCounter)\|parallel.*RPC` | Medium |
| Health check config in k8s/deployment | YAML, JSON | regex: `livenessProbe\|readinessProbe\|startupProbe` | High |
| Circuit breaker state gauge metric | All | regex: `cb\.state\|circuit_breaker_state\|breaker_state` | Medium |
| Thread pool max size configured | All | regex: `max_workers\|maxWorkers\|GOMAXPROCS\|maxConcurrent` | Medium |
| Pool metrics exposed (active/idle connections) | All | regex: `active_connections\|idle_connections\|pool\.Available` | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| HTTP call without timeout | All | AST: `httpx.Client()` / `fetch()` / `http.NewRequest` with no `Timeout(` / `context.WithTimeout` in 10 lines of scope | High |
| No retry on HTTP call to external service | All | heuristic: external `https?://` URL used but no retry library imported | Medium |
| No circuit breaker on calls to critical downstream | All | heuristic: `httpx.Client` / `http.Client` used to call service hostnames but no breaker import | Low |
| Shared connection pool across all downstreams | All | regex: single `httpx.Client()` / `http.Client` instance used for > 2 distinct hostname patterns | Medium |
| No 429 / 503 handling in HTTP handler | All | AST: HTTP handler function with no `except (RateLimit\|TooManyRequests\|503)` | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| HTTP timeout = 0 or `None` (no timeout) | All | regex: `Timeout\(0\|Timeout\(None\|timeout=None` | High |
| Timeout longer than upstream load balancer | All | heuristic: timeout > 55 s on a known AWS ALB (default idle 60 s) | Low |
| Retry limit = 0 on idempotent external call | All | regex: `stop=stop_after_attempt\(1\)\|max_retries\s*[:=]\s*0\|maxRetries\s*[:=]\s*0` | Medium |
| Exponential backoff without jitter | All | regex: `wait_exponential` without `wait_random\|wait_full_jitter\|jitter` | Medium |
| Circuit breaker volume threshold > 99th percentile throughput | All | heuristic: volume threshold > expected 95th pct traffic per minute | Low |
| Circuit breaker timeouts > 10× timeout of wrapped call | All | heuristic: breaker `timeout` > 10× call `timeout` | Medium |
| Max in-flight = 0 (disabled) in half-open | All | regex: `maxRequests.*=.*0\|MaxRequests.*=.*0` | High |
| Health check that only probes the process, not downstreams | All | AST: liveness probe handler does not call downstream or check DB | Medium |
| Prefetch / pool size = 0 (unbounded) | All | regex: `max_connections\s*[:=]\s*0\|maxSockets\s*[:=]\s*0` | High |
| No retry jitter | All | regex: `multiplier=` without any `random\|jitter\|plus` | Medium |
| Circuit breaker fallback raises | All | AST: fallback function body contains a `raise` or throws | Medium |

## 5. Anti-Patterns

### Anti-Pattern: No Timeout on HTTP Call

**Description:** An HTTP client call with no timeout — infinite wait.

```python
# ❌ WRONG
client = httpx.Client()  # default: no timeout at all
resp = client.get('https://slow-api.example.com/data')  # hangs forever
```

**Why it's dangerous:** A slow downstream hangs the calling thread. The thread never returns. The thread pool fills. No new requests are processed. Total outage for that service.

**Detection:** `httpx.Client()` with no Timeout, `requests.get` without timeout, `http.NewRequest` without `context.WithTimeout`.

**Fix:**
```python
# ✅ CORRECT
client = httpx.Client(
    timeout=httpx.Timeout(connect=3, read=5, write=2, pool=3),
)
```

### Anti-Pattern: Blind Exponential Retry Without Jitter

**Description:** All clients retry at the same intervals, amplifying a slow downstream into an unavailable one.

```python
# ❌ WRONG
@retry.retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
def call_api():
    ...
# At attempt 1: 1 s. At attempt 2: 2 s. At attempt 3: 4 s.
# If the downstream is recovering, all 100 services retry at 1s/2s/4s.
# The 1s pile-up alone is enough to push the recovering service over again.
```

**Why it's dangerous:** This is the thundering herd. Every client retries in lockstep, creating a wave of requests that is often larger than the original failure load.

**Detection:** Regex for `wait_exponential` without any `random` or `jitter` in the same retry config.

**Fix:**
```python
# ✅ CORRECT
@retry.retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4) + wait_random(0, 1),
)
```

### Anti-Pattern: Retry Non-Idempotent Writes

**Description:** Retrying a `POST` that creates a charge or a user account.

```python
# ❌ WRONG — POST is not idempotent
@retry.retry(stop=stop_after_attempt(3))
def create_charge(amount_cents: int):
    return client.post('/charge', json={'amount': amount_cents})
# If the request times out but the charge was created, retry charges the card twice.
```

**Why it's dangerous:** Double-charged users. Duplicate accounts. The entire point of idempotency keys is to prevent this.

**Detection:** Retry decorator on a function that makes a `POST` / `PUT` (non-GET) without an `idempotency_key` or `Idempotency-Key` header.

**Fix:**
```python
# ✅ CORRECT — idempotency key in header
@retry.retry(stop=stop_after_attempt(3), retry=retry_if_exception_type(NetworkError))
def create_charge(amount_cents: int, idempotency_key: str):
    return client.post(
        '/charge',
        json={'amount': amount_cents},
        headers={'Idempotency-Key': idempotency_key},
    )
```

### Anti-Pattern: Circuit Breaker Without Fallback

**Description:** The breaker opens but the application returns a raw error to the user instead of a degraded result.

**Why it's dangerous:** "Circuit breaker opened" means the downstream is down. Returning a 500 to the user is the same as no circuit breaker. The fallback is the whole point.

**Detection:** Circuit breaker configured but no `fallback` function / `on_fallback` handler in the same scope.

**Fix:**
```typescript
const breaker = new CircuitBreaker(callAPI, {
  timeout: 5000,
  errorThresholdPercentage: 50,
  fallback: () => ({ items: [], source: 'cache' }),  // degrade gracefully
});
```

### Anti-Pattern: Shared Connection Pool Across All Downstreams

**Description:** A single HTTP client / connection pool used for every external call.

**Why it's dangerous:** One slow downstream can consume all connections. The payment service hogs 10 connections out of 10 → notification service cannot send emails. Total failure of an unrelated feature.

**Detection:** Single `httpx.Client()` / `http.Client` instance used for ≥ 3 distinct hostnames.

**Fix:** One pool per downstream service. The isolation is the bulkhead.

### Anti-Pattern: Health Check Only Checks the Process

**Description:** `/health` returns 200 because the handler doesn't touch the database or downstream.

```go
// ❌ WRONG
func healthHandler(w http.ResponseWriter, r *http.Request) {
    w.WriteHeader(http.StatusOK)  // always 200
}
```

**Why it's dangerous:** Kubernetes will not restart a process that is wedged in a deadlock because the liveness probe always returns 200. The pod looks healthy while serving zero requests correctly.

**Detection:** Liveness / readiness probe handler with no downstream calls.

**Fix:**
```go
// ✅ CORRECT — readiness checks downstream health
func readinessHandler(w http.ResponseWriter, r *http.Request) {
    ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
    defer cancel()
    if err := db.PingContext(ctx); err != nil {
        http.Error(w, "db down: "+err.Error(), http.StatusServiceUnavailable)
        return
    }
    w.WriteHeader(http.StatusOK)
}
```

### Anti-Pattern: Retry Without Backoff

**Description:** Immediate retry with zero delay.

```python
# ❌ WRONG
@retry.retry(wait=wait_fixed(0))
def call():
    ...
```

**Why it's dangerous:** Immediate retry consumes CPU and network for no benefit. The downstream is still down. This converts a transient failure into a self-inflicted DDoS on the recovering service.

**Detection:** `wait_fixed(0)` or `delay=0`.

**Fix:** Minimum 500 ms with exponential backoff + jitter.

### Anti-Pattern: Catching All Exceptions in Retry Handler

**Description:** Retry decorator catches `Exception`, including `TypeError`, `NameError`, `KeyboardInterrupt`.

**Why it's dangerous:** Bugs in the code itself (null pointer, wrong type) are retried. The same bug retries 3 times before surfacing, wasting time and adding noise to metrics.

**Detection:** `retry_if_exception_type(Exception)` with no filter.

**Fix:** Only retry specific, transient exceptions: `httpx.TimeoutException`, `httpx.NetworkError`, `grpc.RpcError` with `UNAVAILABLE` status. Let everything else propagate.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `HTTP_CONNECT_TIMEOUT` | float (s) | — | 2–3 | TCP handshake timeout |
| `HTTP_READ_TIMEOUT` | float (s) | — | 5–10 | Time to first byte |
| `HTTP_WRITE_TIMEOUT` | float (s) | — | 2–5 | Request body upload timeout |
| `HTTP_POOL_TIMEOUT` | float (s) | — | 3–5 | Wait for a connection from pool |
| `HTTP_MAX_CONNECTIONS` | int | — | 20–100 per downstream | Connection pool limit (bulkhead) |
| `HTTP_KEEPALIVE` | bool | true | true | Reuse connections |
| `RETRY_MAX_ATTEMPTS` | int | 1 (no retry) | 3–4 | Maximum retry attempts |
| `RETRY_BASE_DELAY` | float (s) | 1 | 0.5–1 | Base delay for exponential backoff |
| `RETRY_MAX_DELAY` | float (s) | 60 | 4–60 | Cap on retry delay |
| `RETRY_JITTER` | bool | false | true | Add random jitter to backoff |
| `CB_FAILURE_THRESHOLD` | int | 5 | 3–10 | Consecutive failures to trip breaker |
| `CB_ERROR_RATE_THRESHOLD` | float (0–1) | 0.5 | 0.5 | Failure rate % to trip breaker |
| `CB_RESET_TIMEOUT` | int (s) | 30 | 10–60 | Seconds before half-open probe |
| `CB_HALF_OPEN_MAX_REQUESTS` | int | 1 | 2–5 | Max test requests in half-open |
| `CB_VOLUME_THRESHOLD` | int | 20 | 20–100 | Min requests before measuring failure rate |
| `RATE_LIMIT_MAX_REQUESTS` | int | 100 | depends on SLO | Requests allowed per window |
| `RATE_LIMIT_WINDOW` | int (s) | 60 | 60 | Rate limit window in seconds |
| `HEALTHCHECK_TIMEOUT` | int (s) | 5 | 2 | Timeout for health check probe |
| `DEADLINE_PROPAGATION` | bool | false | true | Propagate timeout to downstream services |

## 7. Integration Points

- **Depends on:** Network infrastructure (TCP keep-alive, DNS TTL, load-balancer timeouts); logging/monitoring (metrics for all tolerance mechanisms); configuration management (tunable timeouts); idempotency keys from `foundation.idempotency`.
- **Used by:** Every API handler (timeouts on HTTP clients), every downstream call (retry + circuit breaker + pool), health-check endpoints (orchestrator integration), rate-limit middleware (API gateway).
- **Related concepts:**
  - **`foundation.circuit-breaker`:** Circuit breakers are the canonical fault-tolerance mechanism. Combine with rate limits as the upstream guard and timeouts as the floor.
  - **`foundation.retries`:** Retries are useless without timeout protection and jitter. Together they form the "retry with backoff" pattern.
  - **`foundation.message-queues`:** A dead-letter queue is the fault-tolerance boundary for async work. A poison-pill message trapped in a DLQ is a tolerated failure.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| `http_request_duration_seconds` p50/p95/p99 | Prometheus | p99 > SLO → warn; p99 > 2×SLO → page | Check downstream latency, timeouts |
| `timeout_total` | Prometheus | > 1% of requests → warn; > 5% → page | Tune timeout up or fix downstream |
| `retry_total` | Prometheus | > 10% → warn; > 30% → page | Upstream is degraded; may need circuit breaker |
| `circuit_breaker_state` (0=closed, 1=open, 2=half-open) | Prometheus | = 1 → page | Downstream is down; check root cause |
| `circuit_breaker_rejected_total` | Prometheus | > 0 → warn | Requests are being short-circuited |
| `circuit_breaker_fallback_total` | Prometheus | > 0 → warn | Fallback path is active |
| `pool_active_connections` | Prometheus | > 80% of max → warn; 100% → page | Connection pool exhaustion |
| `pool_pending_requests` | Prometheus | > 0 → warn | Pool is saturated; request queuing |
| `http_error_429_total` | Prometheus | > 0 → warn | Rate limiting active |
| `http_error_503_total` | Prometheus | > 0 → warn | Load shedding active |
| `health_check_failure_total` | Prometheus | = 1 → page | Service is unhealthy |
| `retry_jitter_absent_total` | Prometheus | count > 0 → warn | Thundering-herd risk |

## 9. Evolution / Version Tracking

**Early era (1990s–2000s):** Monolithic applications running on a single machine. Fault tolerance meant `try/catch` blocks, process-level restarts via cron, and RAID. The concept of "distributed failure" did not exist because there was no distribution.

**SOA era (2000s–2010s):** As services were split across machines, engineers discovered that network calls fail silently. Patterns like the **staged event-driven architecture** (SEDA) formalized thread-pool isolation. **Bulkheads** and **circuit breakakers** were popularized by Michael Nygard's 2007 book "Release It!" and adopted by Netflix (Hystrix, 2012), which built the first production-grade Java library and documented the *fail fast* philosophy.

**Cloud-native era (2010s+):** Kubernetes liveness/readiness probes standardized health checks. Service meshes (Istio, Linkerd) moved circuit breaking to the proxy layer (Envoy), making it language-agnostic. AWS/GCP retries became configurable per API call. Resilience4j became the Java standard (lightweight, lambda-based, no annotation magic). **Retry budgets** emerged as the answer to "my service retries 100× the original load."

**Emerging patterns (2020s):**
- **Resilience4j, Polly, opossum** — modern circuit-breaker libraries in every language (Java, .NET, Python, Node).
- **Service mesh auto-retries** — Istio and Linkerd retry on the data plane. This is convenient but dangerous: the mesh retries without knowing whether the call is idempotent.
- **Chaos engineering** — proactively injecting failures (Chaos Monkey, Gremlin, Toxiproxy) to validate that fault-tolerance mechanisms actually work, not just that they exist.
- **Adaptive timeout** — dynamically adjusting timeouts based on observed latency distributions (Google's *Canary* and Netflix's *adaptive* timeout) rather than static values.
- **SLO-based alerting** — treating error budget burn as a failure signal for tolerance mechanisms.

**Deprecated patterns:** Retry-after without jitter; circuit breakers without fallbacks; "infinite retry" retry policies; catching `Exception` to retry (should be specific exception types only); process-level restart only as fault tolerance (without circuit breakers and retries, a restart just resets the clock on the same cascading failure).

## 10. References

- Michael Nygard, "Release It!" (2nd ed.) — pragmatic guide to production patterns including circuit breakers, bulkheads, and timeouts
- Netflix Hystrix wiki (archived) — https://github.com/Netflix/Hystrix/wiki
- Resilience4j documentation — https://resilience4j.readme.io/
- AWS Architecture Blog: "Exponential Backoff And Jitter" — https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Google Cloud: "Load Shedding and Graceful Degradation" — https://cloud.google.com/solutions/load-shedding
- opossum circuit breaker — https://nodeshift.dev/opossum/
- sony/gobreaker — https://github.com/sony/gobreaker
- tenacity — https://tenacity.readthedocs.io/
- "The Tail at Scale" (Jeff Dean & Luiz Barroso, CACM 2013) — https://research.google/pubs/pub43438/
- Kubernetes Probes — https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Chaos Monkey — https://github.com/Netflix/chaosmonkey
- "Designing Distributed Systems" by Brendan Burns (O'Reilly, 2018)
