---
id: foundation.observability
category: foundation
owning_agent: F-19
maturity: stable
languages:
- any
tags:
- metrics
- logs
- traces
- slo
- prometheus
- opentelemetry
- apm
- alerting
- dashboards
related:
- foundation.fault-tolerance
- foundation.latency-bandwidth
- foundation.security-fundamentals
- foundation.scalability
domain: core
---

# Observability

## 1. Overview

Observability is the capability of a software system to expose sufficient internal state — through metrics, logs, and traces — that an engineer can answer arbitrary questions about its behavior without deploying additional instrumentation. In contrast to "monitoring," which answers pre-defined questions ("is the service up?"), observability allows you to explore novel or unexpected behavior after the fact ("why did p99 latency spike for POST requests on the orders endpoint in the last 30 minutes?"). Observability is built on three pillars: metrics (time-series signals about aggregates), logs (structured, context-rich event records), and distributed traces (a causal map of a request flowing through a system). A production-grade observability stack must include SLI/SLO definitions, dashboards, and alerting, all backed by instrumentation at every tier.

## 2. Core Principles

1. **Instrument at the boundary** — every process boundary (HTTP handler, message consumer, database query, cache lookup) should emit observability signals; instrument inside, not only at the top level.
2. **Correlate across the three pillars** — every trace carries a trace ID that must appear on every log line and every metric tag.
3. **Measure what matters to users** — SLIs must reflect user-perceived experience, not internal implementation.
4. **Alerts must be actionable** — every alert must have a clear "what's wrong" and a "what to do" runbook.
5. **High-cardinality tags are acceptable in logs** — metrics require caution with cardinality; logs are less constrained.
6. **Structured logging only** — every log line must be a structured JSON object with `timestamp`, `level`, `service`, `trace_id`, `span_id`.
7. **Redact sensitive data** — logs, traces, and metrics must never contain passwords, API keys, session tokens, or PII.

## 3. Sub-Concepts

### 3.1 Metrics

**Definition:** Time-series numeric signals measured at regular intervals. Metrics represent aggregations (sum, count, rate, histogram) over a population of events.

**Signal types:**
- **Gauge** — point-in-time value (queue_depth). Fluctuates up and down.
- **Counter** — monotonically increasing value (http_requests_total). Calculate rates with `rate(counter[5m])`.
- **Histogram** — bucketed distribution. Exposes p50/p95/p99 via buckets.
- **Summary** — client-side quantiles. NOT comparable across processes (use histograms for cross-instance aggregation).

**RED method** (per service): Rate (`rate(http_requests_total[5m])`), Errors (`rate(total{5xx})/rate(total)`), Duration (`histogram_quantile(0.99, rate(bucket[5m]))`).

**USE method** (per resource): Utilization (% capacity), Saturation (queue depth, pool size), Errors (connection failures).

**Golden Signals:** Latency, Traffic, Errors, Saturation.

```python
# Prometheus with prometheus_client (Python)
from prometheus_client import Counter, Histogram, Gauge

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests",
    ["service", "endpoint", "method", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds",
    "Request latency in seconds", ["service", "endpoint", "method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0))
INFLIGHT_REQUESTS = Gauge("http_requests_inflight", "Currently in-flight requests", ["service"])

@app.get("/users/{user_id}")
def get_user(user_id: str):
    INFLIGHT_REQUESTS.labels(service="api").inc()
    timer = REQUEST_LATENCY.labels(service="api", endpoint=f"/users/{user_id}", method="GET").time()
    try:
        user = repo.find(UserID(user_id))
        if not user:
            REQUEST_COUNT.labels(service="api", endpoint=f"/users/{user_id}", method="GET", status="404").inc()
            return JSONResponse(status_code=404, content={"error": "not found"})
        REQUEST_COUNT.labels(service="api", endpoint="/users/{user_id}", method="GET", status="200").inc()
        return user
    except Exception:
        REQUEST_COUNT.labels(service="api", endpoint="/users/{user_id}", method="GET", status="500").inc()
        raise
    finally:
        INFLIGHT_REQUESTS.labels(service="api").dec()
        timer()
```

**Common mistakes:** Infinite-cardinality labels (user_id as label = 1M time series); counter without status label; forgetting `dec` on inflight gauge; using summary for cross-instance aggregation.

### 3.2 Logging

**Definition:** Structured, time-stamped event records. Logs carry the richest signal — free-form context, stack traces, request bodies.

**Structured logging rules:**
```python
import structlog
logger = structlog.get_logger()

# WRONG: unstructured
logger.info("User logged in")   # no user_id, trace_id

# CORRECT: structured, key-value
logger.info(
    "user.login",
    user_id=str(user.id),
    trace_id=span.get_span_context().trace_id,
    ip=request.client.host,
    result="success",
)
```

**Log levels:** TRACE (debug-only), DEBUG (dev investigation), INFO (normal operation), WARN (unexpected but functioning), ERROR (operation failed), CRITICAL (system degraded).

**Correlation IDs on every log line:** `trace_id`, `span_id`, `request_id`, `user_id`. Format: JSON, always.

```go
// Go with logrus + trace context
import "github.com/sirupsen/logrus"
func handleRequest(ctx context.Context, r *http.Request) {
    span := trace.SpanFromContext(ctx)
    log := logrus.WithFields(logrus.Fields{
        "trace_id": span.SpanContext().TraceID().String(),
        "span_id":  span.SpanContext().SpanID().String(),
        "user_id":  r.Header.Get("X-User-ID"),
    })
    log.Info("request_started")
}
```

### 3.3 Distributed Tracing

**Definition:** Tracking a request as it flows through multiple services. A trace is a tree of spans; each span represents one unit of work.

**OpenTelemetry (OTel):** CNCF standard replacing OpenTracing and OpenCensus.

```python
# Python OpenTelemetry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="otel-collector:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("query_database")
def get_user(user_id: str):
    with tracer.start_as_current_span("SELECT users",
            attributes={"db.table": "users", "db.statement": "SELECT * FROM users WHERE id = %s"}):
        return repo.find(user_id)
```

**Context propagation:** HTTP→HTTP inject `traceparent` header, HTTP→gRPC (automatic in OTel SDK), HTTP→Kafka (inject into message headers).

**Key spans to instrument:** External HTTP/gRPC calls, database queries, cache lookups, message publish/consume, business operations.

### 3.4 SLIs, SLOs, and Error Budgets

**Definition:**
- **SLI** — a quantitative measure (request latency at p99 is 200ms).
- **SLO** — a target value for an SLI ("99% of requests < 200ms over 30 days").
- **Error Budget** — `1 - SLO target` (0.1% downtime/month ≈ 43 min for 99.9% SLO).

```yaml
# SLO recording rules
groups:
  - name: api-slos
    rules:
      - record: slo:request_availability:ratio
        expr: |
          sum(rate(http_requests_total{service="api",status!~"5.."}[28d]))
          /
          sum(rate(http_requests_total{service="api"}[28d]))

      - record: slo:request_latency:ratio
        expr: |
          histogram_quantile(0.99,
            rate(http_request_duration_seconds_bucket{service="api"}[28d])) < 0.2

      - alert: HighErrorBudgetBurnRate
        expr: |
          (sum(rate(http_requests_total{service="api",status=~"5.."}[1h]))
           / sum(rate(http_requests_total{service="api"}[1h])) > 0.014 * (1 - 0.999))
          AND
          (sum(rate(http_requests_total{service="api",status=~"5.."}[5m]))
           / sum(rate(http_requests_total{service="api"}[5m])) > 0.02)
        for: 2m
        labels: { severity: page }
```

**Common mistakes:** SLO at 100% (error budget = 0 → ship nothing); measuring at wrong layer; SLO without alerting.

### 3.5 Alerting Design

**Definition:** Converting raw signals into human action.

**Severity model:**
| Severity | Meaning | Response time | Notification |
|----------|---------|--------------|--------------|
| P1 — Page | System degraded/down, revenue impacted | Immediate (5m) | Phone/SMS/PagerDuty |
| P2 — Inform | Real failure but no revenue impact | 15m | Slack, email |
| P3 — Track | Warning sign | 1h | Slack, ticket |
| P4 — FYI | Informational | None | Dashboard |

**Principles:** Every P1 alert must have a runbook; alert on duration not events; pages must be rare (fix root cause, not symptom).

```yaml
groups:
  - name: api.rules
    rules:
      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{service="api",status=~"5.."}[5m])
          / rate(http_requests_total{service="api"}[5m]) > 0.05
        for: 5m
        labels: { severity: "page" }
        annotations:
          summary: "API error rate > 5%"
          runbook_url: "https://wiki.internal/runbooks/api-error-rate"
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            rate(http_request_duration_seconds_bucket{service="api"}[5m])) > 1.0
        for: 5m
        labels: { severity: "page" }
```

### 3.6 OpenTelemetry Architecture

**Definition:** OTel standardizes instrumentation across languages and eliminates vendor lock-in.

**Architecture:**
```
[Application] --instrumented with--> [OTel SDK]
                                          v
[OTel Collector] -- OTLP/gRPC --> [Jaeger] [Prometheus] [Elasticsearch] [Grafana Tempo]
```

- **SDK** — inside the application. Instruments code, collects signals.
- **Collector** — standalone daemon. Receives, processes (tails, redacts, samples), exports.
- **Resource** — service name, environment, region, version. Must be set in SDK.

```yaml
# otel-collector.yaml
receivers:
  otlp:
    protocols: { grpc: {}, http: {} }
  prometheus:
    config:
      scrape_configs:
        - job_name: "otel-collector"
          scrape_interval: "15s"
          static_configs:
            - targets: ["localhost:9464"]
processors:
  batch:
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
exporters:
  jaeger:   { endpoint: "jaeger:14250" }
  prometheus:{ endpoint: "0.0.0.0:9469" }
service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [jaeger]
    metrics:
      receivers: [otlp, prometheus]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Prometheus client imported | Python/TS/Go | regex: `from prometheus_client\|import 'prom-client'\|prometheus_client\|github.com/prometheus/client_golang` | High |
| Metrics endpoint exposed | Python/TS/Go | regex: `start_http_server\|/metrics\|promhttp.Handler` | High |
| Structured logger imported | Python/TS/Go | regex: `import structlog\|import pino\|import zap\|import slog\|logrus` | High |
| OpenTelemetry SDK imported | Python/TS/Go | regex: `from opentelemetry\|import "@opentelemetry"\|go.opentelemetry` | High |
| OTLP exporter configured | Python/TS/Go | regex: `OTLPSpanExporter\|OTLPExporter` | High |
| Trace context propagation | Python/TS/Go | regex: `traceparent\|inject\|W3CTraceContextPropagator` | High |
| Histogram with custom buckets | Python/TS/Go | regex: `buckets=\|buckets: \` | High |
| Alerting rules defined | YAML | regex: `- alert:` | High |
| SLO recording rules | YAML | regex: `record: slo:` | Medium |
| Grafana dashboard JSON | JSON | glob: `**/grafana-dashboards/*.json` | Medium |
| Runbook link in alert annotation | YAML | regex: `runbook_url\|runbook` | Medium |
| `trace_id` field in log calls | Python/TS/Go | regex: `trace_id` in log calls | Medium |
| `histogram_quantile` in PromQL | PromQL | regex: `histogram_quantile` | High |
| `rate()` / `increase()` in PromQL | PromQL | regex: `rate(\|increase(` | High |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No metrics endpoint (`/metrics`) in service | any | absence of `promhttp\|/metrics\|start_http_server` | High |
| No structured logger; uses `print`/`console.log` | any | regex: `print(\|console.log(` outside tests | High |
| No trace ID in log format | any | log lines lacking `trace_id` field | High |
| No alerting rules for a "production" service | YAML | absence of `- alert:` | High |
| No SLOs defined | YAML | absence of `record: slo:` | High |
| No runbooks linked in alerts | YAML | absence of `runbook_url` | Medium |
| No dashboard definitions | JSON/YAML | absence of `**/grafana-dashboards/*.json` | Medium |
| Counter without status/error label | Python/TS/Go | `Counter\(` without `status`/`status_code` in label_names | High |
| No `rate`/`increase` in PromQL | PromQL | absence of rate functions | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Counter defined without status label | Python/TS/Go | `Counter\(` without `status` in `label_names` | High |
| Gauge inflight without `dec` in finally | Python/TS/Go | `inc\(` without `dec\(` in `finally` | Medium |
| `print()` or `console.log()` in production | any | regex: `print(\|console.log(` | High |
| Histogram with < 5 buckets | Python/TS/Go | `buckets:` with < 5 entries | High |
| `summary` used for cross-instance quantile | PromQL | `_summary` in comparison across jobs | Medium |
| Alert with no `for:` clause | YAML | `- alert:` without `for:` | High |
| Alert without severity label | YAML | `- alert:` without `severity:` | Medium |
| Alert without runbook URL | YAML | `- alert:` without `runbook_url` | Medium |
| PII or secret logged | Python/TS/Go | regex: `logger.*password\|log.*api_key\|log.*secret` | High |
| Sensitive header logged without redaction | Python/TS/Go | `Authorization\|Cookie` in log fields without masking | High |
| SLO set to 100% | YAML | `target.*100` or `slo: 1` | High |
| P1 alert with no runbook URL | YAML | `severity: "page"` without `runbook_url` | High |

## 5. Anti-Patterns

#### Anti-Pattern: High-Cardinality Metric Labels

**Description:**
```python
http_requests_total = Counter("http_requests_total", "Total HTTP requests",
    ["service", "endpoint", "method", "user_id", "request_id"])
```

**Why it's dangerous:** 1M unique user_id values = 1M time series. Prometheus OOMs.

**Detection:** Metric labels that could take on unbounded values: `user_id`, `session_id`, `request_id`.

**Fix:** Use bounded labels. Normalize path patterns. Aggregate at the edge.

#### Anti-Pattern: Unstructured Logging

**Description:**
```python
print(f"User {user_id} logged in from {ip_address}")
```

**Why it's dangerous:** Cannot be filtered, aggregated, or correlated with traces.

**Fix:**
```python
logger.info("user.login", user_id=user_id, ip=ip_address, trace_id=trace_id, result="success")
```

#### Anti-Pattern: Logging PII and Secrets

**Description:**
```python
logger.info("payment_processed", card_number=card.last4, cvv=card.cvv)
```

**Why it's dangerous:** Logs stored unencrypted for months. PCI DSS/GDPR/SOC 2 require redaction. Breach notifications follow.

**Detection:** Regex for `cvv`, `card_number`, `password`, `secret`, `api_key`, `authorization` in log calls.

**Fix:** Maintain a PII/secrets denylist. Strip values before logging.

#### Anti-Pattern: Alert Without `for` Clause (Noise)

**Description:**
```yaml
- alert: Any500Error
  expr: rate(http_requests_total{status="500"}[1m]) > 0
  for: 0m            # fires immediately
  labels: { severity: "page" }
```

**Why it's dangerous:** Transient 500s from retries are normal. Pages that fire every 5 minutes get ignored within a day.

**Fix:** Add `for: 5m` to require sustained elevation.

#### Anti-Pattern: SLO at 100%

**Description:**
```yaml
slo: { target: "100%" }
```

**Why it's dangerous:** Error budget = 0. Engineers stop shipping. Most production systems use 99.9%–99.99%.

**Fix:** SLO = 99.9% (allows ~43 min downtime/month).

#### Anti-Pattern: No Trace Correlation Between Logs and Traces

**Description:**
```
Log line: {"event":"user.login","user_id":"u-123"}
Trace span: trace_id=abc123, span_id=def456
# No connection.
```

**Why it's dangerous:** During an incident, you can't jump from log to trace. Manual grepping across services.

**Fix:** Inject `trace_id` and `span_id` into every log line via structured logging processors.

#### Anti-Pattern: Monitoring the Wrong Layer

**Description:**
```
# Monitoring the load balancer but not the actual service
# Error rate on LB = 0%, but the service has 30% errors
```

**Why it's dangerous:** SLI measured at the LB layer misses service-level failures.

**Fix:** Measure at the service layer and the edge. SLI must reflect what the user experienced.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `metrics.port` | int | 8000 | 9090 | Port for `/metrics` endpoint |
| `metrics.path` | string | `/metrics` | `/metrics` | Path for metrics endpoint |
| `metrics.collection_interval_seconds` | int | 60 | 15 | How often Prometheus scrapes |
| `traces.export_timeout_seconds` | int | 30 | 30 | OTLP export timeout |
| `traces.sampling.rate` | float | 1.0 | 0.01–1.0 | Fraction of traces to sample (0.01 = 1%) |
| `traces.sampling.strategy` | string | "always_on" | "parentbased_always_on" in prod | Sampling strategy |
| `logs.format` | string | "text" | "json" | Log output format |
| `logs.level` | string | "info" | "info" (prod), "debug" (dev) | Minimum log level |
| `logs.rotation_max_size_mb` | int | 100 | 100 | Max log file size before rotation |
| `alerts.evaluation_interval_seconds` | int | 15 | 15 | How often Prometheus evaluates rules |
| `alerts.for_minimum` | int | 1 | 5 | Minimum `for:` clause in alerts |
| `alerts.group_wait_seconds` | int | 30 | 30 | Alertmanager: time to wait before first notification |
| `alerts.repeat_interval_hours` | float | 4 | 4 | Alertmanager: time before re-firing same alert |
| `alertmanager.receivers` | list | [] | pagerduty, slack, email | Alert notification channels |
| `slo.target_availability` | float | 0.999 | 0.999 | SLO target (99.9%) |
| `slo.window_days` | int | 7 | 28 | Rolling window for SLO calculation |
| `slo.alert_burn_rate_threshold` | float | 1 | 14 | Alert when burn rate > 14x |

## 7. Integration Points

- **Circuit Breaker** — breaker state transitions (closed→open) emit `circuit_breaker_state` gauge (0=closed, 1=open, 2=halfopen).
- **Connection Pooling** — pool saturation is a key USE metric. `connection_pool_active_connections`, `connection_pool_wait_seconds` must be instrumented.
- **Security Fundamentals** — audit logs feed compliance. Failed auth attempts, privilege escalations must be logged with alerting.
- **Rate Limiting** — rate limiters must expose `rate_limit_remaining` and `rate_limit_reset` metrics.
- **HLD** — observability is cross-cutting; retrofitting costs 10x compared to planning at HLD.

## 8. Observability

Meta-observability of the observability stack:

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Prometheus scrape duration | Prometheus | > scrape interval → warn | Reduce cardinality |
| Prometheus query duration (p99) | Prometheus | > 5s → warn | Optimize PromQL, add recording rules |
| OTel Collector dropped spans | OTel Collector | > 5% → warn | Scale collector, increase memory |
| Log ingestion lag | Loki / Elasticsearch | > 5m → warn | Scale indexing |
| Alertmanager delivery latency | Alertmanager | > 30s → warn | Check receiver config |
| Active alert count | Alertmanager | > 200 → warn | Noise reduction |
| SLO error budget remaining | Prometheus | < 10% → warn, < 0% → page | Freeze deploys; investigate |
| Card base rate | Prometheus | > 10k unique label values → warn | Fix hot cardinality label |
| Dashboard load time | Grafana | > 5s → warn | Simplify queries |

## 9. Evolution / Version Tracking

**1990s–2000s — Logs only:** Systems logged to flat files. `tail -f`, `grep`, `awk`. Nagios (2002) introduced external health checks.

**2005–2010 — Metrics emerge:** Graphite (2006) introduced time-series storage. But metrics were coarse — no histograms, no labels.

**2012 — Prometheus:** SoundCloud built Prometheus with pull-based model, PromQL, native histograms. Introduced RED/USE methods and golden signals.

**2015 — Distributed tracing:** Google's Dapper paper (2010) inspired Jaeger (Uber) and Zipkin (Twitter). OpenTracing (2016) and OpenCensus (2018) merged into OpenTelemetry (2019).

**2017–2020 — Observability as a platform:** Vendors (Datadog, New Relic, Honeycomb) unify the three pillars. OpenTelemetry becomes de-facto standard (GA 2022). SRE movement takes hold.

**2021–present — eBPF and continuous profiling:** Pixie, Parca, Pyroscope demonstrate agentless profiling and always-on CPU/memory profiling.

**Emerging patterns:** OTel as universal standard; eBPF-based zero-code instrumentation; SLO-as-code; alerting correlation with root-cause inference.

**Deprecated patterns:** StatsD + Graphite; manual instrumentation; Elastic APM (proprietary); Nagios checks.

## 10. References

- [Google SRE Book — Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/naming/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Jaeger Tracing Documentation](https://www.jaegertracing.io/docs/)
- [Cindy Sridharan — Distributed Systems Observability (O'Reilly)](https://www.oreilly.com/library/view/distributed-systems-observability/9781492033431/)
- [The RED Method — Tom Wilkie](https://www.weave.works/blog/the-red-method-key-metrics-for-microservices-architecture/)
- [USE Method — Brendan Gregg](http://www.brendangregg.com/usemethod.html)
- [Alerting Design — SRE Book Chapter 21](https://sre.google/sre-book/alerting-on-slos/)
- [OpenTelemetry Collector Config Reference](https://opentelemetry.io/docs/collector/configuration/)
- [Pyroscope — Continuous Profiling](https://pyroscope.io/)