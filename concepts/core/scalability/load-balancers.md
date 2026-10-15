---
id: foundation.load-balancers
category: foundation
owning_agent: F-14
maturity: stable
languages:
- any
tags:
- l4-l7
- health-checks
- session-affinity
- round-robin
related:
- foundation.rate-limiting
- foundation.proxies
- foundation.consistent-hashing
domain: core
---

# Load Balancers

## 1. Overview

A load balancer distributes incoming requests across multiple backend servers to achieve high availability, scalability, and fault tolerance. Without one, a single server becomes a single point of failure and a capacity bottleneck. The load balancer acts as a reverse proxy: clients connect to its address and the LB forwards each request to a healthy backend based on a distribution algorithm. It also performs active health checking, terminates encryption to offload cryptographic work, and provides a stable address that survives backend scaling events. It is the entry point for nearly every high-traffic production system.

## 2. Core Principles

- **A load balancer hides backend complexity.** Clients see a single endpoint; backend changes are invisible.
- **Health checks are non-negotiable.** Without active probing, the LB continues sending traffic to failed servers.
- **L4 vs L7 determines capability and performance.** L4 routes on IP/port (fast, protocol-agnostic). L7 inspects HTTP headers (slower, more flexible).
- **Distribution algorithms trade simplicity for optimality.** Round-robin is simple; least-connections adapts to variable duration; weighted handles heterogeneous fleets.
- **Session affinity breaks stateless design.** Sticky sessions force all requests from a client to one backend. Prefer stateless design with external session storage.
- **TLS termination centralizes certificate management.** Offloads CPU work from application servers and enables header inspection.
- **The LB itself is a single point of failure.** Use multiple LBs (active-active, VRRP, DNS-based, or cloud-managed).

## 3. Sub-Concepts

### 3.1 Layer 4 Load Balancing

**Definition:** Routes traffic based on IP address and port (transport-layer). Forwards TCP/UDP packets without inspecting application headers.

**Why it matters:** Significantly faster than L7 (no header parsing) and protocol-agnostic (works for HTTP, gRPC, PostgreSQL, Redis). Reduced flexibility — cannot route by URL or cookies.

```haproxy
defaults
    mode tcp
    timeout connect 5s
    timeout client 30s
    timeout server 30s

frontend api-lb
    bind *:80
    default_backend api-servers

backend api-servers
    balance roundrobin
    server api1 10.0.1.10:8080 check inter 2000
    server api2 10.0.1.11:8080 check inter 2000
```

```nginx
stream {
    upstream postgres_backend {
        server 10.0.1.10:5432;
        server 10.0.1.11:5432;
        least_conn;
    }
    server {
        listen 5432;
        proxy_pass postgres_backend;
        proxy_connect_timeout 5s;
    }
}
```

**Common mistakes:**
- Using L4 for HTTP with sticky session or routing needs.
- Timeout too short (breaks uploads, long-running DB queries).

### 3.2 Layer 7 Load Balancing

**Definition:** Parses application protocols (HTTP, gRPC) to make routing decisions based on URL path, host header, cookies, or content.

**Why it matters:** Enables path-based routing (`/api/users` to one service, `/api/orders` to another), header inspection, and protocol-aware features.

```haproxy
frontend api-gateway
    bind *:443 ssl crt /etc/haproxy/certs/api.pem
    mode http

    acl is_user_service path_beg /api/users
    acl is_order_service path_beg /api/orders
    use_backend user_service if is_user_service
    use_backend order_service if is_order_service
    default_backend default_app

backend user_service
    balance roundrobin
    option httpchk GET /healthz
    server user1 10.0.1.10:8080 check inter 2000
```

```nginx
upstream user_service {
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
    keepalive 32;
}

server {
    location /api/users/ {
        proxy_pass http://user_service;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        health_check uri=/healthz interval=5s fails=3 passes=2;
    }
}
```

**Common mistakes:**
- Forgetting to forward original protocol. Without `X-Forwarded-Proto`, redirect generation and HSTS break.
- Default 60s `proxy_read_timeout` breaks long-running requests.

### 3.3 Load Balancing Algorithms

| Algorithm | Pros | Cons | Use Case |
|-----------|------|------|----------|
| Round-robin | Simple, predictable | Ignores server capacity | Homogeneous backends, equal-duration requests |
| Weighted round-robin | Heterogeneous capacity | Manual weight tuning | Mixed instance sizes |
| Least connections | Adapts to variable duration | Tracking overhead | Long-lived connections, websockets |
| Source IP hash | Session affinity | Skewed distribution for uneven IPs | Stateful legacy apps |
| URL hash | Cache affinity | Only for URL-keyed data | Cache-optimized workloads |
| Power-of-2-choices | Low overhead, near-optimal | Harder to reason about | Large fleets (100+ servers) |
| Consistent hashing | Minimal disruption on scale | More complex | Caches, sharded storage |

**NGINX:**
```nginx
upstream backend {
    server 10.0.1.10:8080 weight=3;
    server 10.0.1.11:8080 weight=2;
    server 10.0.1.12:8080 weight=1;
    least_conn;
}
```

### 3.4 Health Checks

**Definition:** Periodic probes sent by the LB to backend servers to determine readiness. Active checks are sent by the LB; passive checks observe real traffic for errors.

**Why it matters:** Without health checks, traffic flows to crashed or hung servers. Active checks with proper thresholds remove unhealthy servers within seconds.

**Envoy:**
```yaml
clusters:
- name: api_service
  health_checks:
  - timeout: 1s
    interval: 5s
    interval_jitter: 1s
    unhealthy_threshold: 3
    healthy_threshold: 1
    http_health_check:
      path: /healthz
```

**Backend health endpoint:**
```python
@app.route('/healthz')
def healthz():
    checks = {"status": "ok"}
    try:
        db.execute("SELECT 1")
    except Exception as e:
        checks["status"] = "degraded"
        return jsonify(checks), 503
    try:
        redis_client.ping()
    except Exception as e:
        return jsonify(checks), 503
    return jsonify(checks), 200
```

**Common mistakes:**
- Single health check with no threshold — one transient blip removes the server.
- Health checks too lightweight — passing 200 OK when DB is dead.

### 3.5 TLS Termination

**Definition:** The LB decrypts incoming HTTPS connections and forwards plain HTTP to backends. Centralizes certificate management.

**NGINX:**
```nginx
http {
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:50m;
    ssl_session_timeout 1d;

    server {
        listen 443 ssl http2;
        ssl_certificate /etc/ssl/certs/api.crt;
        ssl_certificate_key /etc/ssl/private/api.key;
        ssl_stapling on;
        ssl_stapling_verify on;

        location / {
            proxy_pass http://backend;
            proxy_set_header X-Forwarded-Proto https;
        }
    }
}
```

**End-to-end TLS (re-encrypt to backend):**
```nginx
location / {
    proxy_pass https://backend;
    proxy_ssl_protocols TLSv1.2 TLSv1.3;
    proxy_ssl_name backend.internal;
}
```

**Common mistakes:**
- TLS 1.0/1.1 enabled (deprecated, vulnerable).
- TLS termination without re-encryption for sensitive traffic in shared networks.

### 3.6 Session Affinity (Sticky Sessions)

**Definition:** All requests from a client go to the same backend, achieved via cookie or source-IP hash.

**Why it matters:** Required for legacy apps with in-memory session state. Modern stateless apps should use shared session storage (Redis, DynamoDB) instead.

```haproxy
backend api
    cookie SERVERID insert indirect nocache httponly secure
    server s1 10.0.1.10:8080 check cookie s1
    server s2 10.0.1.11:8080 check cookie s2
```

```nginx
upstream api { ip_hash; server 10.0.1.10:8080; server 10.0.1.11:8080; }
```

**Modern alternative:**
```python
class SessionStore:
    def __init__(self, redis_client):
        self.redis = redis_client
    def get(self, session_id):
        return json.loads(self.redis.get(f"session:{session_id}") or "{}")
```

**Common mistakes:**
- No fallback — losing the sticky server means losing all sessions on it.
- IP hash with mobile clients — IPs change frequently.

### 3.7 High Availability of LBs

Production uses multiple LB instances: active-passive with VRRP/keepalived, DNS-based, or cloud-managed (AWS ALB/NLB with anycast).

```bash
# keepalived
vrrp_script check_haproxy {
    script "killall -0 haproxy"
    interval 2
    weight 2
}
vrrp_instance VI_1 {
    state MASTER
    priority 101
    virtual_ipaddress { 192.168.1.100/24 }
    track_script { check_haproxy }
}
```

**Common mistakes:**
- Single LB instance in production.
- No LB-level health check / failover mechanism.

## 4. Scanner Signals

### 4.1 Presence

| Signal | Scanner Pattern | Confidence |
|---------|-----------------|------------|
| HAProxy config | File: `haproxy.cfg` with frontend/backend | High |
| NGINX upstream block | Regex: `upstream\s+\w+\s*\{` | High |
| Envoy listener/cluster | Regex: `listeners:\|clusters:\|routes:` | High |
| Health check endpoint | Regex: `@app.route\(['\"]\/(healthz\|readyz\|livez)` | High |
| Active health check | Regex: `check inter\|health_check interval\|http_health_check` | High |
| TLS termination at LB | Regex: `ssl_certificate\|bind.*ssl\|tls_certificates` | High |
| LB algorithm specified | Regex: `balance\s+(roundrobin\|leastconn\|source)` | Medium |
| X-Forwarded-For header | Regex: `X-Forwarded-For\|proxy_add_x_forwarded_for` | Medium |
| WebSocket upgrade | Regex: `Upgrade\s+\$http_upgrade` | Medium |

### 4.2 Absence

| Signal | Scanner Pattern | Confidence |
|---------|-----------------|------------|
| No load balancer in deployment | Single backend exposed to clients | High |
| No health check configured | Backend servers without `check` directive | High |
| No health endpoint in backend | Absence of `/healthz`, `/readyz` | Medium |
| No TLS termination at LB | Plain HTTP listener with sensitive endpoints | High |
| Single LB instance | Single LB IP/hostname | Medium |

### 4.3 Misconfiguration

| Signal | Scanner Pattern | Confidence |
|---------|-----------------|------------|
| Health check interval > 30s | Regex: `inter\s+[3-9]\d{4,}` | Medium |
| No `fall` threshold | Health check without `fall \d+` | Medium |
| TLS 1.0/1.1 enabled | Regex: `ssl_protocols.*TLSv1[.01]` (no 1.2+) | High |
| Default round-robin with WebSockets | WebSocket without `least_conn`/`source` | Medium |
| No X-Forwarded-Proto | `proxy_pass` without `X-Forwarded-Proto` | Low |
| Connect timeout < 5s | Regex: `timeout connect\s+[1-4]\b` | High |
| Admin port publicly bound | Stats port on public interface | High |

## 5. Anti-Patterns

### Anti-Pattern: Single Load Balancer

```yaml
# WRONG: Single LB
kind: Service
spec:
  selector: { app: api }
  ports: [{ port: 80, targetPort: 8080 }]
```

**Why:** Single point of failure. At 99.9% reliability, LB is down for 8.7 hours/year.

**Fix:** Use cloud-managed LB (AWS ALB) or multiple LB instances with VRRP.

### Anti-Pattern: Health Check That Always Returns 200

```python
# WRONG: Doesn't verify dependencies
@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok"}), 200
```

**Why:** LB sends traffic to a server with broken DB. Every request fails with 500.

**Fix:** Verify database, Redis, and external dependencies in health check.

### Anti-Pattern: No Connection Draining

```yaml
# WRONG: No terminationGracePeriodSeconds
spec:
  containers:
  - name: api
    # No preStop hook
```

**Why:** Long-lived WebSocket connections abruptly terminate on deploy.

**Fix:**
```yaml
spec:
  containers:
  - name: api
    lifecycle:
      preStop:
        exec:
          command: ["sh", "-c", "sleep 15"]
  terminationGracePeriodSeconds: 30
```

### Anti-Pattern: TLS Without Re-Encryption

```nginx
# WRONG: Plain HTTP between LB and backend
location / {
    proxy_pass http://backend;
}
```

**Why:** Network attackers in shared clusters can read all traffic. PCI-DSS and HIPAA require encryption in transit.

**Fix:**
```nginx
location / { proxy_pass https://backend; proxy_ssl_name backend.internal; }
```

### Anti-Pattern: Round-Robin for WebSockets

```nginx
# WRONG: WebSocket with round-robin
upstream websocket {
    server 10.0.1.10:8080;
    server 10.0.1.11:8080;
    # No least_conn
}
```

**Why:** WebSocket connections last hours — first server loads up while others idle.

**Fix:**
```nginx
upstream websocket { least_conn; server 10.0.1.10:8080; server 10.0.1.11:8080; }
```

### Anti-Pattern: No Backend Timeouts

```nginx
# WRONG: Default 60s, no explicit timeouts
location / {
    proxy_pass http://backend;
}
```

**Why:** Hung backends accumulate connections in the LB, eventually exhausting its pool.

**Fix:**
```nginx
location / {
    proxy_pass http://backend;
    proxy_connect_timeout 5s;
    proxy_read_timeout 30s;
    proxy_send_timeout 30s;
}
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `balance` | enum | roundrobin | leastconn for variable workloads | Load balancing algorithm |
| `check inter` | int | 2000ms | 2000–5000ms | Health check interval |
| `fall` | int | 3 | 3–5 | Failed checks before marking unhealthy |
| `rise` | int | 2 | 1–3 | Successful checks before healthy |
| `timeout connect` | int | 5000ms | 3000–5000ms | TCP connection establishment timeout |
| `timeout server` | int | 5000ms | 30000–60000ms | Inactive server connection timeout |
| `maxconn` | int | 2000 | Tuned per LB capacity | Max concurrent connections |
| `ssl_protocols` | enum | TLSv1 TLSv1.1 TLSv1.2 | TLSv1.2 TLSv1.3 | TLS protocol versions |
| `ssl_ciphers` | string | Default | Modern ECDHE+AEAD only | TLS cipher suites |
| `keepalive` | int | 0 | 32–128 | Persistent connections to backends |
| `slow_start` | int | 0 | 30s–5min | Gradual ramp-up for new servers |
| `weight` | int | 1 | Tuned per capacity | Relative traffic share |
| `proxy_http_version` | enum | 1.0 | 1.1 | HTTP protocol version to backend |

## 7. Integration Points

- **Depends on:** Stable backend pool with network connectivity to LB.
- **Depends on:** Health check endpoint implemented by the backend.
- **Used by:** Every external client in a multi-server architecture. The LB is the entry point for nearly all production traffic.
- **Used by:** Internal services via service mesh sidecars (Envoy in Istio).
- **Related to:** Consistent hashing for cache-friendly routing; rate limiting typically implemented at the gateway layer.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Backend up/down count | Prometheus | < N-1 healthy → page | Fleet reduced |
| Response time P99 | Prometheus | > 500ms → warn, > 2s → page | Backend slow |
| Health check failure rate | Prometheus | > 5% → warn | Backend flapping |
| LB connection count | Prometheus | > 80% of maxconn → warn | Scale LB or backends |
| New connections/sec | Prometheus | Spikes beyond baseline → warn | DDoS or load spike |
| TLS handshake time | Prometheus | > 100ms → page | TLS CPU saturation |
| 5xx rate | Prometheus | > 1% → warn, > 5% → page | App errors |
| Bytes in/out | Prometheus | > 80% of capacity → warn | Scale LB bandwidth |

**Log examples:**
```
[WARNING] Server api/s1 is DOWN, reason: Layer4 connection problem
[NOTICE] Server api/s1 is UP
[error] connect() failed (111: Connection refused) while connecting to upstream
```

## 9. Evolution

**1990s–2000s:** Hardware LBs (F5, Citrix). Expensive but reliable. **2000s:** Linux Virtual Server and HAProxy emerged as software alternatives. **2010s:** NGINX, HAProxy, and Envoy became standard for L7. Cloud-managed LBs (AWS ELB, GCP) handled HA automatically. **2020s:** Cloud-managed is default. Kubernetes Ingress controllers (NGINX, Envoy, Traefik) for cluster ingress. Service mesh (Istio, Linkerd) handles east-west with sidecar proxies. **Emerging:** Service mesh sidecars; Envoy as universal data plane; Gateway API for Kubernetes-native routing. **Deprecated:** Hardware LBs for general workloads; static LB configuration.

## 10. References

- HAProxy Documentation: https://www.haproxy.org/documentation.html
- NGINX Load Balancing: https://nginx.org/en/docs/http/load_balancing.html
- Envoy Load Balancing: https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/overview
- AWS ELB Documentation: https://docs.aws.amazon.com/elasticloadbalancing/
- Google Cloud Load Balancing: https://cloud.google.com/load-balancing/docs
- Kubernetes Services: https://kubernetes.io/docs/concepts/services-networking/service/
- Google SRE Book — Load Balancing: https://sre.google/sre-book/load-balancing/
- Linux Virtual Server: http://www.linuxvirtualserver.org/
- Kleppmann — "Designing Data-Intensive Applications": https://dataintensive.net/