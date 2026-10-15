---
id: foundation.latency-bandwidth
category: foundation
owning_agent: F-18
maturity: stable
languages:
- any
tags:
- latency
- throughput
- p99
- cdn
- bandwidth
related:
- foundation.client-server
- foundation.protocols
- foundation.caching
domain: core
---

# Latency and Bandwidth

## 1. Overview

Latency and bandwidth are the two fundamental performance dimensions of distributed systems. Latency is the time taken for a single request to travel from client to server and back, measured in milliseconds. Bandwidth is the rate at which data can be transmitted across the network, measured in bits or bytes per second. Together, they determine the perceived performance of any distributed system. A high-bandwidth network with high latency (typical of satellite connections) feels sluggish even for small data transfers. A low-bandwidth network with low latency (typical of LANs) feels slow when transferring large files. Understanding and optimizing both dimensions is essential for designing systems that feel responsive to users and scale to handle millions of requests per second.

## 2. Core Principles

- **Latency is dominated by the slowest component** — a single database query at 500ms dominates a 50ms service response. Optimize the slowest link first.
- **Bandwidth is a finite resource shared across users** — bandwidth overbooked by 2x or more causes congestion, packet loss, and effectively infinite latency (until drops clear).
- **p99 latency matters more than average** — a 100ms average with 5-second tail means 1% of users have a terrible experience, and at 1M daily users, that is 10,000 frustrated customers.
- **Bandwidth and latency have diminishing returns together** — once latency is below 50ms and bandwidth is 10Mbps+ for most interactions, additional optimization has minimal user-visible impact.
- **Latency and bandwidth must be measured, not assumed** — every deployment has unique network characteristics. Use distributed tracing and continuous benchmarking to capture real values.
- **Edge placement reduces latency but adds cost** — deploying to 100 edge locations reduces average latency by 60-70ms but increases operational complexity and infrastructure cost by 3-5x.

## 3. Sub-Concepts

### 3.1 Latency Fundamentals

**Definition:** Latency is the round-trip time (RTT) for a request to travel from the client to the server and back. Components of latency include: transmission delay (time to push bits onto the wire), propagation delay (time for the signal to travel the distance), queuing delay (time waiting in network buffers), and processing delay (time spent in routers, switches, and the application).

**Why it matters:** Latency directly determines user experience. Amazon found that every 100ms of latency costs 1% of sales. Google found that adding 500ms to search page generation time reduced traffic by 20%. These results show that latency is not just a technical metric but a business metric.

**Latency components in a typical request:**
```
Client                        Network                       Server
[Browser] ──→[ISP]─→[CDN]─→[Backbone]─→[Datacenter]─→[Load Balancer]─→[App Server]─→[Database]
   5ms       10ms   2ms     20ms          15ms           5ms            30ms        20ms
                                                                                      TOTAL: 107ms
```

**Latency benchmarks for common operations (approximate, single-digit to hundreds of milliseconds):**

| Operation | Latency |
|-----------|---------|
| L1 cache reference | 1 ns |
| Branch mispredict | 5 ns |
| L2 cache reference | 7 ns |
| Mutex lock/unlock | 25 ns |
| Main memory reference | 100 ns |
| Compress 1KB with Zippy | 3 µs |
| Send 1KB over 1 Gbps network | 10 µs |
| Read 4KB from SSD | 150 µs |
| Round-trip in same datacenter | 0.5 ms |
| Round-trip US East ↔ US West | 70 ms |
| Round-trip US East ↔ Europe | 90 ms |
| Round-trip US ↔ Asia-Pacific | 200 ms |
| HDD seek | 10 ms |
| Network round-trip (TCP+TLS handshake) | 200 ms |
| Read 1MB sequentially from SSD | 1 ms |
| Read 1MB sequentially from HDD | 20 ms |
| Disk seek, rotational | 10 ms |
| Datacenter round-trip (TCP) | 0.5 ms |

**Implementation patterns:**

```python
# Python — measure end-to-end latency of an API call
import time
import statistics

def measure_endpoint_latency(url: str, num_requests: int = 100):
    latencies = []
    for _ in range(num_requests):
        start = time.perf_counter_ns()
        response = requests.get(url)
        end = time.perf_counter_ns()

        if response.status_code == 200:
            latencies.append((end - start) / 1_000_000)  # ns to ms

    if not latencies:
        return None

    # Compute percentiles
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    return {
        "min":    sorted_latencies[0],
        "p50":    sorted_latencies[n // 2],
        "p90":    sorted_latencies[int(n * 0.90)],
        "p95":    sorted_latencies[int(n * 0.95)],
        "p99":    sorted_latencies[int(n * 0.99)],
        "p999":   sorted_latencies[int(n * 0.999)] if n >= 1000 else None,
        "max":    sorted_latencies[-1],
        "mean":   statistics.mean(latencies),
        "stdev":  statistics.stdev(latencies) if n > 1 else 0,
    }

# Result for a healthy endpoint:
# { "min": 12, "p50": 18, "p90": 32, "p99": 95, "p999": 240, "max": 450, "mean": 22.5 }
```

```go
// Go — latency histogram with HDR histogram for high-precision p99
import (
    hdrhistogram "github.com/HdrHistogram/hdrhistogram-go"
)

func measureLatencies() {
    histogram := hdrhistogram.New(1, 60_000_000, 3) // 1ns to 60s, 3 sig figs

    for i := 0; i < 10000; i++ {
        start := time.Now()
        doWork()
        elapsed := time.Since(start).Microseconds()
        histogram.RecordValue(elapsed)
    }

    p50 := histogram.ValueAtQuantile(50)
    p99 := histogram.ValueAtQuantile(99)
    p999 := histogram.ValueAtQuantile(99.9)
    max := histogram.Max()

    log.Printf("p50=%dµs p99=%dµs p999=%dµs max=%dµs", p50, p99, p999, max)
}
```

**Common mistakes:**
- Optimizing average latency instead of p99 — p99 can be 10-100x higher than the average.
- Measuring latency at the client only — server-side processing and database latency must be measured separately to identify bottlenecks.
- Failing to account for cold starts (Lambda, serverless) — first-request latency can be 10-100x higher than steady-state.

**Scanner signals:**
- Presence: Histogram metric types in Prometheus (`type: histogram`), OpenTelemetry span recording, latency measurement code.
- Absence: No percentile histograms — only averages or counters.
- Misconfiguration: Histogram buckets too coarse (e.g., only `0.1, 1, 10` buckets for ms-scale latency), missing high-resolution buckets.

### 3.2 Bandwidth Fundamentals

**Definition:** Bandwidth is the maximum rate at which data can be transmitted across a network connection, measured in bits per second (bps). It is determined by the slowest link in the path: client ISP, transit networks, server NIC, or load balancer.

**Why it matters:** Bandwidth determines how fast large payloads can be transferred. A 10MB image loads in 8 seconds on a 10 Mbps connection but in 0.8 seconds on a 100 Mbps connection. For data-heavy workloads (video streaming, large file downloads, API responses with embedded data), bandwidth is the primary constraint.

**Bandwidth across deployment tiers:**

| Connection | Typical Bandwidth |
|------------|-------------------|
| Datacenter internal (east-west) | 10–100 Gbps |
| Datacenter to internet (north-south) | 1–10 Gbps |
| Cloud instance-to-instance (same region) | 10–25 Gbps |
| Cloud instance-to-instance (cross-region) | 0.5–5 Gbps |
| Broadband home (US avg, 2024) | 100–500 Mbps |
| Mobile (4G LTE) | 10–50 Mbps |
| Mobile (5G) | 100–1000 Mbps |
| Public WiFi | 5–50 Mbps |
| Satellite (Starlink) | 50–200 Mbps |

**Implementation patterns:**

```go
// Go — measure bandwidth of a download
func measureBandwidth(url string) (float64, error) {
    resp, err := http.Get(url)
    if err != nil {
        return 0, err
    }
    defer resp.Body.Close()

    data := make([]byte, 0, 8*1024*1024)
    buf := make([]byte, 64*1024)
    start := time.Now()

    for {
        n, err := resp.Body.Read(buf)
        if n > 0 {
            data = append(data, buf[:n]...)
        }
        if err == io.EOF {
            break
        }
        if err != nil {
            return 0, err
        }
    }

    elapsed := time.Since(start).Seconds()
    bits := float64(len(data) * 8)
    return bits / elapsed, nil  // Returns bits per second
}

// Result: 94371840 bps = ~94 Mbps for a 10MB file on a 100Mbps link
```

```python
# Python — bandwidth-aware adaptive streaming
import time

def adaptive_quality_select(current_bandwidth_bps: float, available_qualities: list[int]) -> int:
    """Select the highest video quality that fits within current bandwidth."""
    # 80% utilization target — leaves headroom for network variability
    target_bps = current_bandwidth_bps * 0.8

    best_quality = available_qualities[0]
    for quality_bps in available_qualities:
        if quality_bps <= target_bps:
            best_quality = quality_bps
        else:
            break

    return best_quality

# Quality ladder (video bitrates in bps):
qualities = [200_000, 500_000, 1_000_000, 2_500_000, 5_000_000, 8_000_000]

# Example: on a 5 Mbps connection
# Target = 4 Mbps → select 2.5 Mbps quality
selected = adaptive_quality_select(5_000_000, qualities)
print(f"Selected quality: {selected/1_000_000} Mbps")
```

**Common mistakes:**
- Not compressing API responses (gzip, brotli) — sending uncompressed JSON doubles or triples bandwidth usage.
- Sending embedded binary blobs in API responses (base64-encoded) — base64 increases size by 33%.
- Optimizing for bandwidth while ignoring latency (or vice versa) — the right answer depends on workload.

**Scanner signals:**
- Presence: `Content-Encoding: gzip\|br` response header, response compression middleware (`gzipper`, `compression`).
- Absence: No response compression middleware, no `Content-Encoding` header.
- Misconfiguration: Compression not enabled for responses > 1KB, MIME types excluded that benefit from compression.

### 3.3 Latency Percentiles and Distributions

**Definition:** Latency percentiles describe the distribution of latencies across requests. p50 (median) is the latency where half of requests are faster. p99 is where 99% are faster. p99.9 ("three-nines") is where 99.9% are faster. The tail (p99+) often reveals bottlenecks invisible in averages.

**Why it matters:** Average latency hides problems. A system with 100ms average latency could have p99 of 10 seconds (one in 100 requests is catastrophically slow) or p99 of 120ms (consistent performance). Percentiles expose this distinction. SLA compliance is typically defined in terms of p99 — e.g., "99% of requests must complete in under 200ms."

**Tail-latency causes:**
- GC pauses in JVM/Go (sub-millisecond to multiple seconds)
- Disk seeks (random I/O is 1000x slower than sequential)
- Network retransmissions (TCP lost packets, congestion)
- Cold caches (Redis cold start, JIT compilation)
- Lock contention (thread blocked on mutex)
- Cold connections (new TCP handshake, TLS negotiation)
- OS scheduling delays (process preempted)

**Implementation patterns:**

```python
# Python — comprehensive percentile reporting
import time
from typing import Callable
from collections import defaultdict

class LatencyTracker:
    def __init__(self, bucket_size_ms: int = 10):
        self.buckets: dict[int, int] = defaultdict(int)
        self.bucket_size = bucket_size_ms
        self.total_count = 0
        self.total_latency_ms = 0

    def record(self, latency_ms: float):
        bucket = int(latency_ms / self.bucket_size) * self.bucket_size
        self.buckets[bucket] += 1
        self.total_count += 1
        self.total_latency_ms += latency_ms

    def report(self) -> dict:
        sorted_buckets = sorted(self.buckets.items())
        cumulative = 0
        percentile_values = {}

        for threshold, count in self.buckets.items():
            cumulative += count
            percentile = (cumulative / self.total_count) * 100
            for p in (50, 90, 95, 99, 99.9):
                if p not in percentile_values and percentile >= p:
                    percentile_values[p] = threshold

        return {
            "p50":    percentile_values.get(50),
            "p90":    percentile_values.get(90),
            "p95":    percentile_values.get(95),
            "p99":    percentile_values.get(99),
            "p99.9":  percentile_values.get(99.9),
            "mean":   self.total_latency_ms / self.total_count,
            "count":  self.total_count,
            "max":    max(b for b, _ in sorted_buckets),
        }

# Usage in HTTP middleware:
tracker = LatencyTracker()

@app.middleware("http")
async def track_latency(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000
    tracker.record(latency_ms)
    return response
```

**Prometheus histogram configuration for accurate percentiles:**

```yaml
# Prometheus exposition — using histogram_quantile
# Histogram buckets must cover the full latency range
- name: http_request_duration_seconds
  type: histogram
  help: HTTP request duration in seconds
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
  label_names:
  - method
  - endpoint
  - status_code

# Query for p99 over 5-minute window:
# histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))
```

**Common mistakes:**
- Using summary metrics (pre-computed quantiles) instead of histograms — histograms enable aggregation across instances, summaries do not.
- Choosing histogram buckets that don't match your latency distribution (e.g., buckets of 0.1s for sub-millisecond endpoints).
- Tracking only one percentile — p50 alone misses tail latency issues.

**Scanner signals:**
- Presence: `type: histogram` in Prometheus config, `histogram_quantile` in PromQL queries.
- Absence: Only `summary` or `gauge` for latency tracking, no p99 queries.
- Misconfiguration: Histogram buckets missing high-range values (e.g., no bucket at 10s for endpoints that can take seconds).

### 3.4 Content Delivery Networks (CDNs)

**Definition:** A CDN is a globally distributed network of edge servers that cache and serve content close to end users. CDNs reduce latency by serving content from the nearest geographic location, and reduce bandwidth costs by offloading traffic from origin servers.

**Why it matters:** A page with assets served from a single origin server requires every user worldwide to traverse the internet to reach it. A CDN places copies of those assets at 100+ edge locations, so a user in Tokyo fetches the asset from a Tokyo edge instead of waiting for a trans-Pacific round trip. This reduces asset load time from 200ms to 20ms for that user.

**Implementation patterns:**

```yaml
# Cloudflare CDN configuration via Page Rules / Transform Rules
- name: Cache static assets aggressively
  match:
    url_pattern: "*.example.com/static/*"
  actions:
    edge_cache_ttl: 2592000  # 30 days
    browser_cache_ttl: 86400  # 1 day
    cache_level: cache_everything
    cache_key:
      include_query_string: false
      include_host: true

- name: Cache API GET responses with stale-while-revalidate
  match:
    url_pattern: "api.example.com/v1/products/*"
    methods: ["GET"]
  actions:
    edge_cache_ttl: 300        # 5 minutes
    browser_cache_ttl: 60      # 1 minute
    stale_while_revalidate: 86400  # 24 hours stale OK
    cache_level: cache_everything
```

```python
# Python — FastAPI with explicit Cache-Control for CDN
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/api/v1/products/{product_id}")
async def get_product(product_id: str, response: Response):
    product = db.get_product(product_id)
    if not product:
        return {"error": "not found"}

    # Cache at CDN for 5 minutes, browser for 1 minute
    response.headers["Cache-Control"] = (
        "public, max-age=60, s-maxage=300, stale-while-revalidate=86400"
    )
    response.headers["Vary"] = "Accept-Encoding"

    # Allow CDN to serve stale content for 24h while revalidating
    return product

@app.get("/api/v1/users/{user_id}/private")
async def get_private_data(user_id: str, response: Response):
    data = db.get_private_data(user_id)
    # Private data must NOT be cached at CDN
    response.headers["Cache-Control"] = "private, no-cache, no-store, must-revalidate"
    response.headers["Surrogate-Control"] = "no-store"  # For Fastly CDN
    return data
```

```typescript
// CloudFront distribution config (AWS CDK)
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';

new cloudfront.Distribution(this, 'ApiCDN', {
    defaultBehavior: {
        origin: new origins.HttpOrigin('api.example.com'),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        compress: true,  // Enable automatic gzip/brotli compression
        allowedMethods: cloudfront.AllowedMethods.ALLOW_GET_HEAD,
    },
    additionalBehaviors: {
        '/api/v1/private/*': {
            origin: new origins.HttpOrigin('api.example.com'),
            cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
            compress: true,
        },
    },
    priceClass: cloudfront.PriceClass.PRICE_CLASS_100,  // US/EU edge only
    httpVersion: cloudfront.HttpVersion.HTTP2_AND_3,    // HTTP/2 + HTTP/3
});
```

**Common mistakes:**
- Caching authenticated content at CDN without `Cache-Control: private` — leaks user data.
- Not setting `Vary: Accept-Encoding` — compressed and uncompressed responses get mixed, causing client decoding errors.
- Caching responses with `Set-Cookie` headers — same cookie sent to all CDN users.
- Not purging CDN cache after deployments — users see stale code or assets for hours/days.

**Scanner signals:**
- Presence: CDN provider configuration (CloudFront, Fastly, Cloudflare), `Cache-Control` headers in API responses, `s-maxage` directive.
- Absence: No CDN configuration for static assets, no `Cache-Control` headers on API responses.
- Misconfiguration: `Cache-Control: public` on authenticated endpoints, `Vary` header missing for compressed responses.

### 3.5 Bandwidth Optimization Techniques

**Definition:** Bandwidth optimization reduces the amount of data transmitted across the network, improving transfer speed and reducing infrastructure costs. Techniques include compression, minification, pagination, partial responses, delta sync, and binary serialization.

**Why it matters:** Sending 100KB of JSON when 10KB would suffice wastes bandwidth, increases latency (more time to transfer), and costs money (egress fees from cloud providers). Optimization at every layer — transport (gzip), protocol (Protobuf instead of JSON), and application (pagination) — compounds.

**Implementation patterns:**

```python
# Python — gzip middleware for FastAPI
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
# Responses > 1024 bytes are compressed with gzip level 6

# OR explicit compression with brotli (better compression, slower)
from brotli_middleware import BrotliMiddleware
app.add_middleware(BrotliMiddleware, quality=4)
```

```go
// Go — gzip response compression in net/http
import (
    "compress/gzip"
    "net/http"
)

type gzipResponseWriter struct {
    http.ResponseWriter
    gzWriter *gzip.Writer
}

func (gzw *gzipResponseWriter) Write(b []byte) (int, error) {
    return gzw.gzWriter.Write(b)
}

func GzipMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        if !strings.Contains(r.Header.Get("Accept-Encoding"), "gzip") {
            next.ServeHTTP(w, r)
            return
        }

        w.Header().Set("Content-Encoding", "gzip")
        w.Header().Set("Vary", "Accept-Encoding")

        gz := gzip.NewWriter(w)
        defer gz.Close()
        gzw := &gzipResponseWriter{ResponseWriter: w, gzWriter: gz}
        next.ServeHTTP(gzw, r)
    })
}
```

```typescript
// TypeScript — pagination with cursor-based queries
async function listProducts(req: Request, res: Response) {
    const limit = Math.min(parseInt(req.query.limit as string) || 50, 200);
    const cursor = req.query.cursor as string | undefined;

    const { products, nextCursor } = await db.products.findMany({
        take: limit + 1,  // Take one extra to detect more pages
        cursor: cursor ? { id: cursor } : undefined,
        orderBy: { id: 'asc' },
    });

    const hasMore = products.length > limit;
    const results = hasMore ? products.slice(0, -1) : products;

    res.json({
        data: results,
        pagination: {
            next_cursor: hasMore ? results[results.length - 1].id : null,
            has_more: hasMore,
            limit,
        },
    });
}

// Client receives ~50 products per request instead of all 10,000
```

**Common mistakes:**
- No pagination on list endpoints, returning thousands of records in a single response.
- No compression on API responses, sending uncompressed JSON.
- Sending full objects when only a few fields are needed (no `?fields=` parameter or GraphQL `select`).

**Scanner signals:**
- Presence: `gzip` middleware, `Content-Encoding: gzip\|br` response headers, pagination logic, GraphQL queries.
- Absence: List endpoints without `limit` / `cursor` parameters, no compression.
- Misconfiguration: Compression disabled on responses > 1MB, pagination limit > 200.

### 3.6 Latency Optimization Techniques

**Definition:** Latency optimization reduces the time taken for a single request, improving perceived performance and enabling higher throughput. Techniques include connection reuse (HTTP keep-alive), request parallelism, pre-fetching, lazy loading, and server-side computation caching.

**Why it matters:** A 500ms reduction in latency can dramatically improve conversion rates and user satisfaction. For API consumers, latency directly determines how many requests they can make in parallel and how much parallelism their code can have.

**Latency reduction techniques:**

| Technique | Latency Reduction | Implementation |
|-----------|-------------------|----------------|
| HTTP keep-alive | -20ms per request | Connection reuse, no TCP handshake |
| Pre-fetching | -100ms (parallel work) | Load next page before user requests |
| Browser caching | -200ms (no network) | Cache-Control, ETag |
| CDN edge serving | -150ms (cross-region) | Global edge servers |
| Compression | -50ms (faster transfer) | gzip/brotli on responses |
| Database indexing | -500ms (10s → ms) | Proper indexes on query columns |
| Connection pooling | -100ms per query | Reuse DB connections |
| Query optimization | -200ms | Select only needed columns, avoid N+1 |
| Caching (Redis) | -300ms (DB query → cache) | Cache hot keys |
| Streaming responses | -50ms TTFB | Don't buffer full response |

**Implementation patterns:**

```python
# Python — connection pooling with httpx for HTTP keep-alive
import httpx

# Shared connection pool across requests
client = httpx.Client(
    http2=True,                    # Multiplexed HTTP/2
    timeout=httpx.Timeout(10.0),
    limits=httpx.Limits(
        max_keepalive_connections=20,
        max_connections=100,
        keepalive_expiry=30,       # Keep connections alive for 30s
    ),
)

# All requests share the same connection pool
def get_users_parallel(user_ids: list[str]) -> list[dict]:
    with httpx.Client(http2=True) as client:
        # Issue all requests in parallel — HTTP/2 multiplexes over one connection
        responses = [
            client.get(f"https://api.example.com/users/{uid}")
            for uid in user_ids
        ]
        return [r.json() for r in responses]

# Total time: ~100ms for 10 requests (vs. 1s sequentially without keep-alive)
```

```go
// Go — pre-fetching with goroutines and channels
func (s *Server) GetDashboardData(ctx context.Context, userID string) (*Dashboard, error) {
    // Use errgroup to parallelize independent calls
    g, ctx := errgroup.WithContext(ctx)

    var user *User
    var orders []Order
    var recommendations []Recommendation

    g.Go(func() error {
        var err error
        user, err = s.userService.Get(ctx, userID)
        return err
    })

    g.Go(func() error {
        var err error
        orders, err = s.orderService.List(ctx, userID, 10)
        return err
    })

    g.Go(func() error {
        var err error
        recommendations, err = s.recommendationService.Get(ctx, userID, 5)
        return err
    })

    if err := g.Wait(); err != nil {
        return nil, err
    }

    // Total time = max(individual calls) instead of sum
    return &Dashboard{User: user, Orders: orders, Recommendations: recommendations}, nil
}
```

```typescript
// TypeScript — pre-fetch next page when current page loads
async function loadProductsPage(page: number) {
    const currentPage = await fetch(`/api/v1/products?page=${page}`);
    const products = await currentPage.json();

    // Pre-fetch next page immediately for instant navigation
    const nextPagePromise = fetch(`/api/v1/products?page=${page + 1}`);

    return { products, nextPagePromise };
}

// When user clicks "Next":
const { products, nextPagePromise } = await loadProductsPage(currentPage);
// nextPagePromise is already resolved — instant response
const nextPage = await nextPagePromise;
```

**Common mistakes:**
- Sequential calls when parallel calls would suffice — adds 2-5x latency unnecessarily.
- Reusing HTTP clients without keep-alive — every request re-establishes TCP connection.
- Loading all data upfront when only a subset is needed.

**Scanner signals:**
- Presence: `Promise.all`, `errgroup`, connection pool config, pre-fetch hooks.
- Absence: Sequential `await` calls for independent operations, no connection pooling.
- Misconfiguration: `max_connections=1` (no parallelism), no `keepalive_expiry` configured.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Prometheus histogram for HTTP latency | YAML | regex: `type:\s*histogram.*name:\s*http_request_duration` | High |
| `histogram_quantile` in PromQL | YAML | regex: `histogram_quantile\(` in dashboards | High |
| CDN configuration (CloudFront, Fastly, Cloudflare) | YAML | regex: `aws_cloudfront\|fastly\|cloudflare` | High |
| `Cache-Control` header setting | Any | regex: `Cache-Control\|s-maxage\|max-age` | High |
| Response compression middleware | Any | regex: `GZipMiddleware\|gzip\.\|BrotliMiddleware\|compress\(\)` | High |
| HTTP/2 enabled | Any | regex: `http2.*true\|HTTP/2\|alpn h2` | Medium |
| Connection pool config | Any | regex: `pool_size\|MaxIdleConns\|QueuePool\|MaxKeepAlive` | High |
| Parallel request execution | Any | regex: `Promise\.all\|errgroup\|asyncio\.gather` | Medium |
| Pagination on list endpoints | Any | regex: `limit\|cursor\|offset\|page` | High |
| HTTP keep-alive timeout | Any | regex: `keepalive.*timeout\|KeepAlive.*time` | Medium |
| CDN cache purge on deploy | YAML | regex: `cache_purge\|invalidate.*cache\|purge_cache` | Medium |
| Brotli or gzip compression | Any | regex: `Content-Encoding.*gzip\|Content-Encoding.*br` | High |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No histogram metric for API latency | YAML | No `type: histogram` for HTTP request latency | High |
| No CDN for static assets | Config | Static asset serving without CDN config | Medium |
| No response compression | Any | No compression middleware or `Content-Encoding` header | Medium |
| No pagination on list endpoints | Any | List endpoints returning unbounded result sets | High |
| No connection pooling | Any | Database/HTTP client without pool config | Medium |
| No keep-alive configuration | Any | No `KeepAlive` or `IdleConnTimeout` settings | Medium |
| No Cache-Control headers | Any | API responses without `Cache-Control` header | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Histogram buckets too coarse for latency range | YAML | Buckets only `0.1, 1, 10` for sub-millisecond endpoints | High |
| `Cache-Control: public` on authenticated endpoints | Any | regex: `Cache-Control.*public` with `Authorization` header | High |
| `Vary` header missing for compressed responses | Any | `Content-Encoding` without `Vary: Accept-Encoding` | Medium |
| Compression disabled on large responses | Any | `GZipMiddleware` with `minimum_size=1048576` (1MB threshold) | Medium |
| `Content-Encoding: gzip` on already-compressed assets | Any | `Content-Encoding: gzip` for `image/png`, `image/jpeg`, `video/mp4` | Medium |
| Pagination limit > 200 | Any | `limit > 200` in pagination defaults | Medium |
| Missing connection pool max size | Any | `pool_size` absent or 0 | High |
| HTTP/1.1 only (no HTTP/2) for external APIs | Any | `http2: false` or no HTTP/2 configuration | Medium |
| CDN cache TTL > 1 day for dynamic content | Any | `s-maxage=86400` on API responses with user-specific data | Medium |
| TCP keep-alive disabled | Any | `KeepAlive: 0` or `-1` | High |

## 5. Anti-Patterns

### Anti-Pattern: Optimizing Average Latency Instead of p99

**Description:**
```python
# Engineer reports: "Our average latency is 50ms, which is great!"
import time

def measure_average():
    total = 0
    count = 0
    for i in range(1000):
        start = time.perf_counter()
        result = slow_database_query()
        elapsed = time.perf_counter() - start
        total += elapsed
        count += 1
    avg = (total / count) * 1000  # Average in ms
    print(f"Average: {avg}ms")  # Prints: Average: 50ms
```

**Why it's dangerous:** Average latency hides catastrophic tail latency. In the example, 999 requests are 5ms but 1 request is 50,000ms (50 seconds). The average is 50ms, but 0.1% of users wait 50 seconds. For a real system, this means some users see page-load times measured in tens of seconds, while the dashboards show green.

**Detection:** Scanner looks for code that measures latency with mean() instead of percentile tracking (no sorted-based p99 calculation, no histogram_quantile in PromQL).

**Fix:**
```python
def measure_percentiles():
    latencies = []
    for _ in range(1000):
        start = time.perf_counter()
        slow_database_query()
        elapsed = time.perf_counter() - start
        latencies.append(elapsed * 1000)

    latencies.sort()
    print(f"p50: {latencies[500]:.1f}ms")
    print(f"p99: {latencies[990]:.1f}ms")
    print(f"p99.9: {latencies[999]:.1f}ms")
    # Likely output: p50: 5ms, p99: 50ms, p99.9: 50000ms — reveals the truth
```

### Anti-Pattern: Sending Uncompressed JSON

**Description:**
```python
# Python FastAPI — sending uncompressed JSON responses
from fastapi import FastAPI

app = FastAPI()

@app.get("/api/v1/users")
async def list_users():
    users = db.get_all_users()
    # Returns ~5MB of uncompressed JSON
    # Without compression, this takes 5 seconds on a 10Mbps connection
    return {"users": users}
```

**Why it's dangerous:** JSON is highly compressible — typical compression ratio is 5-10x. Sending 5MB when 500KB would suffice wastes 9x the bandwidth and takes 9x longer to transfer. For users on slow connections (mobile, rural), this is the difference between a responsive app and an unusable one.

**Detection:** Scanner looks for FastAPI/Flask/Express apps without compression middleware, or response handlers that don't set `Content-Encoding`.

**Fix:**
```python
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1024)

# Now responses > 1KB are gzip-compressed automatically
# 5MB JSON becomes ~500KB — 10x reduction
```

### Anti-Pattern: Sequential Network Calls

**Description:**
```python
# Python — sequential calls that could be parallel
async def get_dashboard_data(user_id: str) -> dict:
    # Each call takes 100ms — total 300ms
    user = await fetch(f"/users/{user_id}")         # 100ms
    orders = await fetch(f"/users/{user_id}/orders") # 100ms
    recommendations = await fetch(f"/users/{user_id}/recommendations")  # 100ms
    return {"user": user, "orders": orders, "recommendations": recommendations}
```

**Why it's dangerous:** Sequential calls serialize latency. Three independent calls at 100ms each take 300ms total when they could take 100ms in parallel. This wastes 200ms of user-perceived latency on every request.

**Detection:** Scanner looks for sequential `await` or `.then()` chains on independent network calls without `Promise.all` or `asyncio.gather`.

**Fix:**
```python
import asyncio

async def get_dashboard_data(user_id: str) -> dict:
    # Run all three in parallel — total 100ms (max of three)
    user, orders, recommendations = await asyncio.gather(
        fetch(f"/users/{user_id}"),
        fetch(f"/users/{user_id}/orders"),
        fetch(f"/users/{user_id}/recommendations"),
    )
    return {"user": user, "orders": orders, "recommendations": recommendations}
```

### Anti-Pattern: Caching Private Data at CDN

**Description:**
```python
# Python — caching user-specific data with public cache directive
@app.get("/api/v1/users/me")
async def get_current_user(response: Response):
    user_id = get_current_user_id()  # From session/JWT
    user = db.get_user(user_id)
    # BUG: 'public' allows CDN to cache this response
    # Now all users receive the first user's data
    response.headers["Cache-Control"] = "public, max-age=300"
    return user
```

**Why it's dangerous:** `Cache-Control: public` instructs CDNs and shared caches to store the response. If the response is user-specific (contains authentication, personal data, session info), the CDN serves one user's data to every other user. This is a critical security vulnerability and a privacy breach.

**Detection:** Scanner looks for `Cache-Control: public` on endpoints that return user-specific data, or on endpoints that read from `Authorization` / `Cookie` headers.

**Fix:**
```python
@app.get("/api/v1/users/me")
async def get_current_user(response: Response):
    user_id = get_current_user_id()
    user = db.get_user(user_id)
    # Use 'private' to prevent CDN caching — only browser may cache
    # Use 'no-store' for highly sensitive data
    response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"
    response.headers["Vary"] = "Authorization"  # Vary by auth header
    return user
```

### Anti-Pattern: No Pagination on List Endpoints

**Description:**
```python
# Python — returning all records without pagination
@app.get("/api/v1/transactions")
async def list_transactions():
    # Returns 100,000 records — 50MB JSON response
    transactions = db.query(Transaction).all()
    return {"transactions": transactions}
```

**Why it's dangerous:** Returning unbounded result sets causes memory exhaustion at the server, network bandwidth exhaustion, and client-side rendering failures. A single request can DoS the server by triggering massive response serialization. On mobile clients, parsing 50MB JSON blocks the UI thread for seconds.

**Detection:** Scanner looks for list endpoints (GET handlers returning arrays or "list" patterns) without `limit` / `offset` / `cursor` parameters.

**Fix:**
```python
@app.get("/api/v1/transactions")
async def list_transactions(
    limit: int = Query(50, ge=1, le=200),  # Cap at 200
    cursor: str | None = Query(None),
):
    query = db.query(Transaction).order_by(Transaction.id)
    if cursor:
        query = query.filter(Transaction.id > cursor)
    transactions = query.limit(limit + 1).all()

    has_more = len(transactions) > limit
    results = transactions[:limit]
    next_cursor = results[-1].id if has_more else None

    return {
        "data": results,
        "pagination": {
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }
```

### Anti-Pattern: Disabling TCP Keep-Alive

**Description:**
```go
// Go — disabling keep-alive
transport := &http.Transport{
    DisableKeepAlives: true,  // Forbids connection reuse
}
```

**Why it's dangerous:** Without keep-alive, every HTTP request re-establishes a TCP connection (and TLS handshake if HTTPS). A 50ms TLS handshake on every request means 5x slowdown. Mobile clients on high-latency networks see this most acutely.

**Detection:** Scanner looks for `DisableKeepAlives: true` in Go `http.Transport`, `keepalive: false` in Node.js, or `MaxKeepAliveRequests: 0`.

**Fix:**
```go
transport := &http.Transport{
    DisableKeepAlives: false,
    MaxIdleConns: 100,
    IdleConnTimeout: 90 * time.Second,
    TLSHandshakeTimeout: 5 * time.Second,
}
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `http_request_duration_seconds` | histogram | (none) | buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10] | Latency histogram buckets (seconds) |
| `cache-control.max_age` | int | 0 | 300 | Browser cache TTL in seconds |
| `cache-control.s_maxage` | int | 0 | 3600 | CDN edge cache TTL in seconds |
| `cache-control.stale_while_revalidate` | int | 0 | 86400 | Serve stale for N seconds while revalidating |
| `cdn.edge_cache_ttl` | int | 0 | 3600 | CDN edge cache lifetime |
| `cdn.browser_cache_ttl` | int | 0 | 300 | Browser cache lifetime |
| `compression.minimum_size` | int | 200 | 1024 | Minimum response size for compression (bytes) |
| `compression.level` | int | 6 | 6 | Compression level (gzip 1-9, brotli 0-11) |
| `pool.max_connections` | int | system default | 100 | Max concurrent connections in pool |
| `pool.idle_timeout` | duration | 0 (none) | 90s | Idle connection timeout before close |
| `keepalive.timeout` | duration | 0 (disabled) | 30s | TCP keep-alive interval |
| `keepalive.probes` | int | 0 (disabled) | 3 | TCP keep-alive probes before close |
| `pagination.default_limit` | int | none | 50 | Default pagination limit |
| `pagination.max_limit` | int | none | 200 | Maximum pagination limit |
| `http.max_connections_per_host` | int | system default | 100 | Max concurrent connections to single host |
| `http.idle_conn_timeout` | duration | 0 | 90s | Idle HTTP connection timeout |
| `tls.handshake_timeout` | duration | 0 | 5s | TLS handshake timeout |
| `response.header_timeout` | duration | 0 | 10s | Timeout for server response headers |
| `connection.request_timeout` | duration | 0 | 30s | Total request timeout |
| `connection.connect_timeout` | duration | 0 | 5s | TCP connect timeout |

## 7. Integration Points

- **Depends on:** Latency and bandwidth measurements depend on instrumentation libraries (Prometheus client, OpenTelemetry SDK). CDN configuration depends on DNS routing and certificate management. HTTP keep-alive depends on connection pooling libraries (`httpx`, `requests` with `Session`, `http.Transport`).

- **Used by:** Every component of the system contributes to overall latency and consumes bandwidth. API servers report latency histograms. Frontend applications consume bandwidth via assets. CDN serves cached content. Load balancers add 1-5ms latency per hop.

- **Related to `foundation.caching`:** Caching is the primary technique for reducing latency and bandwidth. Cache hits eliminate the database query (latency) and the network transfer (bandwidth). Cache invalidation is what makes caches correct.

- **Related to `foundation.client-server`:** The communication pattern chosen directly determines latency characteristics. Request-response adds round-trip latency per interaction. SSE and WebSocket amortize connection cost. Pagination limits bandwidth per response.

- **Related to `foundation.protocols`:** Different protocols have different bandwidth characteristics. HTTP/1.1 with TLS adds 7-9% overhead from headers. HTTP/2 with HPACK compresses headers to 1-2%. gRPC with Protobuf is 5-10x more compact than JSON.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| API p99 latency | Prometheus (histogram) | p99 > 1s → warn, p99 > 3s → page | Profile slow endpoints |
| API p999 latency | Prometheus | p999 > 5s → page | Tail latency investigation |
| Network bandwidth utilization (per instance) | Prometheus (gauge) | > 80% → warn, > 95% → page | Increase instance size or scale out |
| Egress bandwidth (cloud provider) | CloudWatch/GCP Monitoring | > 80% of quota → warn | Optimize payloads, add CDN |
| CDN cache hit rate | CloudFront metrics | < 80% → warn, < 60% → page | Increase TTL, review cache keys |
| CDN response time | CloudFront metrics | > 50ms → warn | Check edge location performance |
| Origin server request rate | Prometheus | Spike > 3x baseline → warn | Check CDN cache hit rate dropped |
| Connection pool wait time | Prometheus | p99 > 50ms → warn | Increase pool size |
| TLS handshake time | Prometheus | p99 > 200ms → warn | Network issue or TLS overhead |
| DNS resolution time | Prometheus | p99 > 50ms → warn | Use IP-based health checks |
| Response payload size | Prometheus (histogram) | p99 > 1MB → warn | Implement pagination |
| Compression ratio | Custom metric | < 2x → warn | Check if assets are already compressed |

Key log messages:
- `request latency exceeded budget: 500ms` — performance regression
- `cache miss for key: <key>` — high miss rate, investigate cache strategy
- `connection pool exhausted` — pool sizing issue
- `TLS handshake timeout` — network connectivity issue
- `origin server unreachable` — CDN cannot reach backend, routing problem
- `response size exceeded 10MB limit` — pagination missing

## 9. Evolution / Version Tracking

Latency and bandwidth optimization has been central to networking since the 1970s. Early networks (ARPANET) operated at 50 Kbps, where every byte mattered. The invention of HTTP/1.1 in 1997 introduced keep-alive connections, reducing connection establishment overhead. HTTP/2 (2015) with HPACK header compression reduced bandwidth usage by 30-50% for typical web traffic.

CDNs emerged in the late 1990s (Akamai, 1999) to solve the latency problem of geographically distributed users. The initial model was static asset caching; modern CDNs handle dynamic content, video streaming, and edge computing (Lambda@Edge, Cloudflare Workers).

The move to HTTP/3 with QUIC (2022) further reduces latency by eliminating TCP's head-of-line blocking. Connection migration (seamless handoff between WiFi and cellular) eliminates the 200-500ms reconnect cost on mobile devices.

Brotli compression (Google, 2015) achieves 20-30% better compression than gzip for web content, now supported by all major browsers. Zstandard (Facebook, 2016) offers similar compression with much faster decompression, increasingly used for API payloads.

Edge computing (Cloudflare Workers, AWS Lambda@Edge, Fastly Compute@Edge) pushes computation closer to users, reducing round-trip latency for personalized content. This is the current frontier of latency optimization — instead of serving cached content at the edge, edge functions execute logic at the edge.

## 10. References

1. High Performance Browser Networking — Ilya Grigorik — https://hpbn.co/
2. Designing Data-Intensive Applications — Martin Kleppmann — https://dataintensive.net/
3. Google Web Fundamentals — Performance — https://developers.google.com/web/fundamentals/performance
4. Prometheus Histograms and Summaries — https://prometheus.io/docs/practices/histograms/
5. Cloudflare Learning Center — CDN — https://www.cloudflare.com/learning/cdn/what-is-a-cdn/
6. HTTP Caching — MDN — https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching
7. RFC 7931 — HPACK Header Compression for HTTP/2 — https://datatracker.ietf.org/doc/html/rfc7541
8. Brendan's Blog — Latency Numbers Every Programmer Should Know — https://gist.github.com/jboner/2841832
9. CloudFront Developer Guide — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/
