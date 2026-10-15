---
id: foundation.rate-limiting
category: foundation
owning_agent: F-13
maturity: stable
languages:
- any
tags:
- token-bucket
- sliding-window
- api-gateway
- throttling
related:
- foundation.load-balancers
- foundation.circuit-breaker
- foundation.proxies
domain: core
---

# Rate Limiting

## 1. Overview

Rate limiting restricts the number of requests, operations, or resource consumption a client can perform within a defined time window. Every system has finite capacity — database connections, CPU, network bandwidth, and third-party API quotas all have ceilings. Without rate limiting, a misbehaving client or traffic spike can exhaust these resources, causing cascading failures. Rate limiting converts an unbounded demand problem into a bounded, predictable one. It ensures fair resource allocation and protects the system from overload. The standard HTTP response is 429 Too Many Requests, accompanied by a `Retry-After` header so clients can back off intelligently.

## 2. Core Principles

- **Every system has a capacity.** Rate limiting makes that limit explicit and enforced.
- **Window size matters more than count.** 100 req/s with a 1s window behaves differently from 100 req/s with a 60s window. The latter allows bursts at window boundaries.
- **Different clients need different limits.** Free-tier, enterprise, and internal service clients each need distinct thresholds.
- **Distributed rate limiting requires consensus.** Without shared state, a client can exceed global limits by spreading requests across nodes.
- **Rate limiting should fail with a clear signal, never silently.** If the limiter crashes, the system should either fail open (with monitoring) or fail closed (reject all).
- **429 Too Many Requests is the standard signal.** Clients need `Retry-After` to back off rather than retry immediately.
- **Throttling complements rate limiting.** Rate limiting rejects excess; throttling delays excess. Some workloads (IoT, financial) cannot lose requests and need queues instead.

## 3. Sub-Concepts

### 3.1 Token Bucket Algorithm

**Definition:** Maintains a bucket of tokens that refills at a constant rate. Each request consumes tokens. If the bucket is empty, the request is denied. Bucket capacity allows controlled bursts.

**Why it matters:** Matches real-world traffic patterns where requests are unevenly distributed. Clients can burst up to the bucket capacity and then must wait for refill.

```python
import time, threading

class TokenBucket:
    def __init__(self, capacity, refill_rate):
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self.lock = threading.Lock()

    def _refill(self):
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now

    def consume(self, tokens=1.0):
        with self.lock:
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
```

```go
type TokenBucket struct {
    mu         sync.Mutex
    capacity   float64
    refillRate float64
    tokens     float64
    lastRefill time.Time
}

func (tb *TokenBucket) Allow() bool {
    tb.mu.Lock()
    defer tb.mu.Unlock()
    tb.refill()
    if tb.tokens >= 1 {
        tb.tokens--
        return true
    }
    return false
}
```

**Common mistakes:**
- No lock in multi-threaded code — concurrent `consume()` corrupts token count.
- Not handling floating-point drift — use fixed-point integers for production.

**Scanner signals:**
- `Positive`: Class named `TokenBucket` with `consume`/`refill` methods.
- `Positive`: 429 response + `Retry-After` header.
- `Negative`: No locking mechanism in multi-threaded implementation.

### 3.2 Sliding Window Algorithm

**Definition:** Tracks exact timestamps of recent requests and counts how many fall within the current time window. Prevents the "burst at boundary" problem of fixed windows.

**Why it matters:** A fixed 1-minute window allows 60 requests at second 0 and 60 more at second 1 (double rate). A sliding window prevents this by considering the trailing N seconds of history.

```python
class RedisSlidingWindow:
    def is_allowed(self, client_id, max_requests, window_seconds):
        key = f"sliding:{client_id}"
        now = time.time()
        window_start = now - window_seconds
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, window_seconds + 1)
        results = pipe.execute()
        current_count = results[1]
        if current_count >= max_requests:
            self.redis.zrem(key, str(now))
            return False
        return True
```

**Common mistakes:**
- Using `LIST` instead of `ZSET` for Redis — lists don't handle duplicate timestamps correctly.
- Not setting `EXPIRE` — old keys accumulate, causing memory exhaustion.

**Scanner signals:**
- `Positive`: `ZADD`/`ZRANGEBYSCORE`/`ZREMRANGEBYSCORE` in Redis code.
- `Positive`: Sorted timestamp list with window cleanup.
- `Negative`: Fixed-window implementation for security-sensitive endpoints.

### 3.3 Fixed Window Counter

**Definition:** Divides time into discrete windows. A counter tracks requests within the current window and resets at window boundaries.

**Why it matters:** Simplest algorithm with lowest memory footprint. Appropriate when the boundary burst is acceptable or for infrastructure-level enforcement.

```python
class FixedWindowRateLimiter:
    def is_allowed(self, client_id, limit, window_seconds):
        key = f"ratelimit:{client_id}:{int(time.time() / window_seconds)}"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, window_seconds + 1)
        return count <= limit
```

**Standard response headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 73
X-RateLimit-Reset: 42
Retry-After: 42
```

**Common mistakes:**
- Not setting `EXPIRE` on counter keys.
- Using client time for window calculation — clock skew causes inconsistent boundaries.

**Scanner signals:**
- `Positive`: `INCR` + `EXPIRE` pattern; `X-RateLimit-*` headers; 429 status code.
- `Negative`: Counter without expiration mechanism.

### 3.4 Distributed Rate Limiting

**Definition:** In a multi-server cluster, all nodes share rate limit state so that the global limit applies across the entire fleet, not per-node.

**Why it matters:** A 10-server cluster with per-node limits of 100/min achieves 1000/min globally — 10x violation. Distributed rate limiting enforces the true global limit.

**Cell-based (Google approach):**
```python
class CellRateLimiter:
    """Divide limit across N cells for high-throughput."""
    def __init__(self, redis_client, limit, num_cells=10):
        self.limit_per_cell = limit // num_cells
        self.num_cells = num_cells
        self.redis = redis_client

    def is_allowed(self, client_id):
        cell = random.randint(0, self.num_cells - 1)
        key = f"cell:{client_id}:{cell}"
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, 60)
        return count <= self.limit_per_cell
```

**Common mistakes:**
- In-memory counters in multi-instance deployments — each node only counts its own requests.
- No fallback when Redis is unavailable — rate limiter crashes, either accepting all or rejecting all traffic.

**Scanner signals:**
- `Positive`: Shared Redis for counters; cell-based or sharded rate limiting.
- `Negative`: In-memory counter in a >1 instance deployment.

### 3.5 API Gateway Rate Limiting

**Definition:** Rate limiting at the gateway layer (NGINX, Envoy, AWS API Gateway) rather than in application code. Centralized enforcement across all services.

**NGINX:**
```nginx
http {
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req_zone $http_x_api_key zone=authenticated:10m rate=100r/s;

    server {
        location /api/public/ {
            limit_req zone=general burst=20 nodelay;
            limit_req_status 429;
        }
        location /api/authenticated/ {
            limit_req zone=authenticated burst=50 nodelay;
            limit_req_status 429;
        }
    }
}
```

**Envoy:**
```yaml
http_filters:
- name: envoy.filters.http.ratelimit
  typed_config:
    "@type": type.googleapis.com/envoy.extensions.filters.http.ratelimit.v3.RateLimit
    domain: api
    failure_mode_deny: true
```

**Common mistakes:**
- No `burst` parameter — false 429s on normal traffic.
- No `429` status configured — NGINX returns 503, confusing clients.
- Same rate limit for authenticated and unauthenticated endpoints.

**Scanner signals:**
- `Positive`: `limit_req_zone`, `envoy.filters.http.ratelimit`.
- `Negative`: Rate limiting only in app code, not at gateway.

### 3.6 Throttling vs. Rate Limiting

Rate limiting rejects excess requests (429). Throttling delays excess requests via a queue. Throttling is for workloads that cannot afford data loss.

```python
class LeakyBucketThrottler:
    def __init__(self, rate, queue_size):
        self.rate = rate
        self.queue = asyncio.Queue(queue_size)

    async def submit(self, item):
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            raise RateLimitExceeded()
```

**Scanner signals:**
- `Positive`: Queue with max size for backpressure.
- `Negative`: Unbounded queue for backpressure (`maxsize=None`).

## 4. Scanner Signals

### 4.1 Presence

| Signal | Scanner Pattern | Confidence |
|---------|-----------------|------------|
| TokenBucket / RateLimiter class | AST: `consume`, `allow`, `refill` methods | High |
| Redis INCR + EXPIRE | Regex: `INCR.*EXPIRE\|incr.*expire` | High |
| NGINX limit_req_zone | Regex: `limit_req_zone` | High |
| Envoy ratelimit filter | Regex: `envoy.filters.http.ratelimit` | High |
| HTTP 429 response | Regex: `status_code.*429\|429\|Too Many Requests` | High |
| Retry-After header | Regex: `Retry-After\|retry_after` | High |
| X-RateLimit-Limit header | Regex: `X-RateLimit-Limit` | High |
| Sliding window with Redis ZADD | Regex: `ZADD.*ZRANGEBYSCORE` | Medium |
| Distributed counter in Redis | Regex: `incr.*ratelimit` | Medium |

### 4.2 Absence

| Signal | Scanner Pattern | Confidence |
|---------|-----------------|------------|
| No rate limit on public APIs | Public routes without rate limiter middleware | High |
| No rate limit on auth endpoints | Auth routes without rate limiter | High |
| No 429 handling in clients | Absence of 429 retry logic | Medium |

### 4.3 Misconfiguration

| Signal | Scanner Pattern | Confidence |
|---------|-----------------|------------|
| Rate limit = 0 (unlimited) | Regex: `limit.*=.*0\|rate.*=.*-1` | High |
| No EXPIRE on counters | `INCR` without `EXPIRE` in same block | High |
| No Retry-After on 429 | 429 response without `Retry-After` | Medium |
| In-memory counter in multi-instance | Counter without shared backend | High |
| IP-based for authenticated users | `remote_addr` for authenticated endpoints | Medium |
| Window = 0 | Regex: `window.*=.*0\|period.*=.*0` | High |

## 5. Anti-Patterns

### Anti-Pattern: Client-Side Only

```typescript
// WRONG: Client-side limiter (trivially bypassed)
class ClientRateLimiter {
    lastRequest = 0;
    canMakeRequest() {
        const now = Date.now();
        if (now - this.lastRequest < 100) return false;
        this.lastRequest = now;
        return true;
    }
}
```

**Why:** Trivially bypassed. Server-side enforcement is mandatory.

**Fix:**
```python
from flask_limiter import Limiter
limiter = Limiter(get_remote_address, app=app, storage_uri="redis://localhost:6379")
@app.route('/api/query')
@limiter.limit("10 per second")
def api_query(): pass
```

### Anti-Pattern: Per-Node Limits in a Cluster

```python
# WRONG: Each server counts independently
class LocalRateLimiter:
    def __init__(self, limit=100):
        self.limit = limit; self.counter = 0
    def is_allowed(self):
        if self.counter < self.limit:
            self.counter += 1; return True
        return False
```

**Why:** 10 servers × 100/min = 1000/min achievable.

**Fix:** Use centralized Redis counter shared by all servers.

### Anti-Pattern: No Retry-After Header

```python
# WRONG: 429 without timing information
return Response("Rate limit exceeded", status_code=429)
```

**Why:** Clients retry immediately, causing thundering herd at window reset.

**Fix:**
```python
retry_after = window_seconds - (now % window_seconds)
return Response(jsonify({"retry_after": retry_after}), status_code=429,
                headers={"Retry-After": str(math.ceil(retry_after))})
```

### Anti-Pattern: Fixed Window for Security Endpoints

```python
# WRONG: Fixed window allows double-rate burst at boundary
window_key = f"ratelimit:{user_id}:{int(now / 60)}"
```

**Why:** Client can send 60 requests at 12:00:00 and 60 more at 12:01:00 (120 in 2 seconds). Use sliding windows for login/OTP endpoints.

### Anti-Pattern: Rate Limiting Authenticated Users by IP

```python
# WRONG: IP-based limits for authenticated endpoints
client_id = request.remote_addr
```

**Why:** NAT/Corporate proxies share IPs. One malicious user behind a proxy throttles all legitimate users.

**Fix:**
```python
user_id = request.headers.get("X-User-ID")
client_id = f"user:{user_id}" if user_id else f"ip:{request.remote_addr}"
```

### Anti-Pattern: Same Limit for All Endpoint Types

**Why:** A POST that writes to the database costs 10x more than a GET. Uniform limits over-restrict cheap endpoints or under-protect expensive ones.

**Fix:**
```python
RATE_LIMITS = {
    "GET:/api/health": {"limit": 1000, "window": 60},
    "POST:/api/orders": {"limit": 20, "window": 60},
    "POST:/api/upload": {"limit": 5, "window": 60},
}
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `rate_limit_per_minute` | int | 60 | Varies by endpoint | Max requests per minute per client |
| `burst_size` | int | 0 | 5–20x sustained rate | Max burst requests |
| `window_seconds` | int | 60 | 1–3600 | Time window for counting |
| `algorithm` | enum | token_bucket | token_bucket / sliding_window / fixed | Limiting algorithm |
| `redis_url` | string | localhost:6379 | Redis Cluster | Backend for distributed state |
| `rate_limit_key_template` | string | `{client_id}` | `user:{id}` or `ip:{ip}` | Key construction template |
| `failure_mode` | enum | open | open (proxies) / closed (APIs) | Behavior when backend is down |
| `token_refill_rate` | float | 10.0 | Sustained throughput target | Tokens/second for token bucket |
| `token_bucket_capacity` | float | 50.0 | Expected burst size | Max tokens in bucket |
| `envoy_failure_mode_deny` | bool | true | true | Reject if rate limit service unreachable |
| `ngx_zone_size` | string | 10m | Scale with client count | Shared memory for NGINX rate state |

## 7. Integration Points

- **Depends on:** Redis or shared KV store for distributed rate limit state.
- **Depends on:** API gateway to inspect request metadata (IP, API key, user ID).
- **Used by:** API handlers to gate expensive operations (DB writes, external calls).
- **Used by:** API gateways (NGINX, Envoy, Kong) for centralized enforcement.
- **Related to:** Circuit breakers — rate limiter prevents overload; circuit breaker detects already-overloaded downstream services.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Rejection rate (429/total) | Prometheus | > 5% → warn, > 20% → page | Increase limit or investigate abuse |
| Rate limit hit per client | Prometheus | Single client > 50% of limit → warn | Check for abuse |
| Backend latency | Prometheus | > 10ms → warn, > 50ms → page | Redis slow or partitioned |
| Error rate | Prometheus | Any → warn | Backend down |
| Active rate limit keys | Prometheus | Rapidly growing → warn | Memory leak, missing TTL |

## 9. Evolution

**Early web:** Simple in-memory counters in web server modules. Per-server only. **2010s:** Redis shared counters, fixed window standard. **Current:** Token bucket and sliding window at API gateways (NGINX, Envoy) with Redis for distributed state. Managed services (AWS API Gateway, Cloudflare) handle distributed state transparently. **Emerging:** Adaptive rate limiting (adjusts based on system health); quota-based (monthly budgets with per-second smoothing); AI-driven anomaly detection to reduce false positives.

## 10. References

- RFC 6585 (429 Too Many Requests): https://datatracker.ietf.org/doc/html/rfc6585
- RFC 7231 (Retry-After header): https://datatracker.ietf.org/doc/html/rfc7231
- NGINX Rate Limiting: https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
- Envoy Rate Limit Filter: https://www.envoyproxy.io/docs/envoy/latest/configuration/http/http_filters/rate_limit_filter
- AWS API Gateway Throttling: https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html
- Google SRE Book — Handling Overload: https://sre.google/sre-book/handling-overload/
- Kleppmann — "Designing Data-Intensive Applications": https://dataintensive.net/
