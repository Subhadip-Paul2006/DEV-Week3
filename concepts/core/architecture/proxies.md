---
id: foundation.proxies
category: foundation
owning_agent: F-15
maturity: stable
languages:
- any
tags:
- reverse-proxy
- api-gateway
- sidecar
- forward-proxy
related:
- foundation.load-balancers
- foundation.protocols
- foundation.rate-limiting
domain: core
---

# Proxies

## 1. Overview

A proxy is an intermediary server that sits between a client and one or more backend services, forwarding requests and responses on behalf of the client. Proxies exist to enforce cross-cutting concerns — security, routing, observability, and reliability — without modifying the services behind them. They are the architectural backbone of every production web system, from the edge proxy terminating TLS at the data-center perimeter to the sidecar proxy handling service-to-service calls inside a Kubernetes mesh. Understanding proxy types, placement, and configuration patterns is foundational to designing systems that are secure, scalable, and maintainable.

## 2. Core Principles

- **A proxy must be transparent to the client by default** — the client should not need to know whether a proxy is in the path, except when explicit proxy configuration is required (e.g., HTTP `CONNECT` for forward proxies).
- **A proxy must not mutate the semantics of the protocol it carries** — a reverse proxy for HTTP/1.1 must not silently downgrade a connection that the client expects to remain open, and a TCP proxy must not interpret application-layer data.
- **A proxy is a single point of failure unless it is redundant** — every production proxy deployment must run at least two instances behind a load balancer or in an active-active configuration.
- **Proxies should handle concerns orthogonal to business logic** — TLS termination, authentication, rate limiting, request logging, and retries belong at the proxy layer, not inside application code.
- **Proxy hop-by-hop headers must be managed according to RFC 7230** — headers like `Connection`, `Keep-Alive`, `Proxy-Authenticate`, and `Transfer-Encoding` must be consumed by the proxy and not forwarded.
- **The trust boundary of a proxy defines the security perimeter** — traffic arriving at a reverse proxy from the internet is untrusted; traffic between internal proxies in a service mesh may carry mTLS-authenticated identity.

## 3. Sub-Concepts

### 3.1 Reverse Proxy

**Definition:** A reverse proxy sits in front of one or more backend servers, accepting requests from clients and forwarding them to the appropriate backend. The client is unaware of the proxy; it believes it is communicating directly with the server.

**Why it matters:** Reverse proxies are the standard way to expose services to the internet. They centralize TLS termination, routing, and security enforcement. Without a reverse proxy, every backend service must independently manage certificates, authentication, and access control.

**Implementation patterns:**

```nginx
# Nginx reverse proxy — TLS termination and backend routing
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # Proxy headers must be stripped or set correctly
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Backend routing
    location /api/v1/ {
        proxy_pass http://api_v1_backend:8080/;
        proxy_read_timeout 30s;
        proxy_connect_timeout 10s;
    }

    location /api/v2/ {
        proxy_pass http://api_v2_backend:8080/;
        proxy_read_timeout 30s;
    }
}
```

```go
// Go reverse proxy using httputil.ReverseProxy
package main

import (
    "log"
    "net/http"
    "net/http/httputil"
    "net/url"
)

func main() {
    backend, _ := url.Parse("http://localhost:8080")
    proxy := httputil.NewSingleHostReverseProxy(backend)

    // Customize director to modify the request before forwarding
    originalDirector := proxy.Director
    proxy.Director = func(req *http.Request) {
        originalDirector(req)
        req.Header.Set("X-Forwarded-For", req.RemoteAddr)
        req.Header.Set("X-Forwarded-Proto", "https")
    }

    // Error handler for backend failures
    proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
        log.Printf("proxy error for %s %s: %v", r.Method, r.URL.Path, err)
        w.WriteHeader(http.StatusBadGateway)
        w.Write([]byte("backend unavailable"))
    }

    log.Fatal(http.ListenAndServe(":443", proxy))
}
```

**Common mistakes:**
- Not stripping hop-by-hop headers before forwarding, causing downstream servers to misinterpret `Connection: close` or `Transfer-Encoding: chunked`.
- Using `proxy_set_header Host $proxy_host` in Nginx, which passes the backend hostname instead of the original `Host` header, breaking virtual-host-based routing in the application.
- Forgetting to set `X-Forwarded-For`, which makes backend logging show only the proxy IP instead of the real client IP.

**Scanner signals:**
- Presence: Nginx `proxy_pass` directive, Envoy `static_resources` clusters, `httputil.ReverseProxy`, `@Proxy` middleware (Laravel), `app.Use(proxy())` (Express).
- Absence: No reverse proxy configuration in infrastructure-as-code (Terraform, Helm charts), no `X-Forwarded-For` handling in application code.
- Misconfiguration: `proxy_set_header Host $proxy_host` (wrong host header), missing `ssl_protocols` restriction allowing TLS 1.0/1.1.

### 3.2 Forward Proxy

**Definition:** A forward proxy sits between a client and the internet. The client is aware of the proxy and explicitly routes requests through it (e.g., corporate HTTP proxy, VPN gateway).

**Why it matters:** Forward proxies enforce organizational policies: content filtering, egress control, audit logging, and caching for bandwidth reduction. Unlike reverse proxies, forward proxies require explicit client configuration.

**Implementation patterns:**

```python
# Python forward proxy using aiohttp
import asyncio
from aiohttp import web

async def handle(request):
    # Extract target URL from the request
    target_url = str(request.url.with_scheme('http').with_host(''))

    async with request.session.request(
        method=request.method,
        url=target_url,
        headers=dict(request.headers),
        data=await request.read(),
        allow_redirects=False,
    ) as resp:
        body = await resp.read()
        return web.Response(
            status=resp.status,
            headers=resp.headers,
            body=body,
        )

app = web.Application()
app.router.add_route('*', '/{tail:.*}', handle)
web.run_app(app, port=8888)
```

```typescript
// TypeScript forward proxy with Express
import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();

// Forward proxy — client sends absolute URL
app.use('/proxy', createProxyMiddleware({
    target: 'http://',
    changeOrigin: true,
    router: (req) => req.url, // dynamic target from request URL
    onProxyReq: (proxyReq, req) => {
        console.log(`FORWARD ${req.method} ${req.url}`);
    },
    onError: (err, req, res) => {
        console.error('Forward proxy error:', err);
        res.writeHead(502);
        res.end('Proxy error');
    },
}));

app.listen(3128);
```

**Common mistakes:**
- Allowing unauthenticated access to the forward proxy, turning it into an open relay for spam or attack traffic.
- Not validating the target URL scheme, allowing `file://` or `gopher://` requests that can access internal services (SSRF).
- Forwarding all headers including `Authorization` cookies, leaking user credentials to arbitrary destinations.

**Scanner signals:**
- Presence: `http-proxy-middleware`, `proxy.py`, Squid configuration (`http_port 3128`), `ProxySQL` setup.
- Absence: No `http_proxy` / `https_proxy` environment variable configuration, no proxy middleware.
- Misconfiguration: Open proxy (no ACL), missing `Proxy-Authorization` check, forwarding internal URLs.

### 3.3 API Gateway

**Definition:** An API gateway is a specialized reverse proxy that operates at the edge of a microservices architecture, providing a single entry point for all client requests. It adds protocol translation, request aggregation, authentication, rate limiting, and monitoring.

**Why it matters:** API gateways decouple the client-facing API surface from the internal service topology. They allow teams to refactor backend services without breaking clients, enforce security policies consistently, and reduce client-side complexity.

**Implementation patterns:**

```go
// Kong gateway configuration via declarative YAML
// (served via Admin API at :8001)
//
// _: Format
// _format_version: "2.1"
// services:
// - name: user-service
//   url: http://user-service:8080
//   routes:
//   - name: user-routes
//     paths:
//     - /api/v1/users
//   plugins:
//   - name: rate-limiting
//     config:
//       minute: 120
//       policy: local
//   - name: jwt
//     config:
//       secret_is_base64: false
//       claims_to_verify:
//       - exp
```

```python
# AWS API Gateway — Lambda integration (Python handler)
import json

def lambda_handler(event, context):
    # API Gateway passes the request through the event object
    http_method = event['httpMethod']
    path = event['path']
    headers = event.get('headers', {})

    # Authorization at the gateway level via JWT authorizer
    # If unauthenticated, request never reaches this handler
    claims = event.get('requestContext', {}).get('authorizer', {}).get('claims', {})

    # Business logic
    if http_method == 'GET' and path == '/api/v1/users':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'users': []}),
        }

    return {'statusCode': 404, 'body': json.dumps({'error': 'not found'})}
```

**Common mistakes:**
- Using the API gateway as a business-logic layer (fat gateway antipattern), which turns it into a distributed monolith.
- Not implementing request timeouts at the gateway, causing backend services to hold connections open indefinitely.
- Placing non-edge concerns like complex data transformation inside the gateway instead of in backend services.

**Scanner signals:**
- Presence: Kong/APISIX/Express Gateway config, AWS API Gateway `AWS::ApiGateway::RestApi`, GCP API Gateway, Envoy route configuration.
- Absence: No API gateway in infrastructure, direct backend exposure from load balancer.
- Misconfiguration: Gateway timeout > 30s without backend timeout alignment, no authentication plugin configured.

### 3.4 Sidecar Proxy

**Definition:** A sidecar proxy is a proxy instance deployed alongside each service instance in a containerized environment. It intercepts all inbound and outbound network traffic, enabling transparent handling of service discovery, mTLS, retries, and telemetry without modifying the service code.

**Why it matters:** Sidecars are the cornerstone of service meshes (Istio, Linkerd). They move networking concerns out of application code, enabling polyglot environments where services can be written in any language.

**Implementation patterns:**

```yaml
# Istio sidecar injection — Kubernetes deployment annotation
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
  annotations:
    sidecar.istio.io/inject: "true"  # Enables automatic sidecar injection
spec:
  replicas: 3
  selector:
    matchLabels:
      app: payment-service
  template:
    metadata:
      labels:
        app: payment-service
        sidecar.istio.io/inject: "true"
    spec:
      containers:
      - name: payment-service
        image: payment-service:v3.2.1
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
---
# Istio configures iptables rules to redirect all traffic through Envoy sidecar
# The sidecar listens on 15001 (outbound) and 15006 (inbound)
# VirtualService defines routing rules
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: payment-service
spec:
  hosts:
  - payment-service
  http:
  - route:
    - destination:
        host: payment-service
        port:
          number: 8080
    timeout: 10s
    retries:
      attempts: 3
      perTryTimeout: 3s
      retryOn: 5xx,reset,connect-failure
```

```go
// Envoy sidecar filter — CDS (Cluster Discovery Service) response structure
// The sidecar dynamically discovers backends via xDS APIs
type Cluster struct {
    Name                 string            `json:"name"`
    ConnectTimeout       float64           `json:"connect_timeout"`
    Type                 string            `json:"type"` // STRICT_DNS, LOGICAL_DNS
    LbPolicy             string            `json:"lb_policy"` // ROUND_ROBIN, LEAST_REQUEST
    LoadAssignment       LoadAssignment    `json:"load_assignment"`
    HealthChecks         []HealthCheck     `json:"health_checks,omitempty"`
    CircuitBreakers     *CircuitBreakers  `json:"circuit_breakers,omitempty"`
}
```

**Common mistakes:**
- Allowing sidecars to consume excessive CPU/memory with no resource limits, causing node-level resource contention.
- Disabling mTLS at the mesh level while assuming it is active, leaving service-to-service communication unencrypted.
- Not configuring sidecar resource requests/limits, leading to unpredictable performance during traffic spikes.

**Scanner signals:**
- Presence: `istio-sidecar-injector` webhook, `sidecar.istio.io/inject` annotation, `envoy` binary in container, Linkerd `linkerd-proxy` container.
- Absence: No sidecar injection, no service mesh control plane in cluster.
- Misconfiguration: Sidecar resource limits missing, mTLS `PERMISSIVE` mode in production.

### 3.5 Protocol Translation Proxy

**Definition:** A proxy that transcodes between different protocols, enabling clients using one protocol to communicate with backends using another (e.g., gRPC-to-REST, WebSocket-to-TCP).

**Why it matters:** Protocol translation is essential during incremental migrations. A service may need to expose a REST API while its internals communicate via gRPC, or a legacy TCP service may need a modern HTTP gateway.

**Implementation patterns:**

```typescript
// gRPC-to-REST transcoding proxy using Envoy filter
import { GrpcWeb, Transport } from '@improbable-eng/grpc-web';

// Envoy HTTP filter for gRPC transcoding
const httpFilter = {
    name: 'envoy.filters.http.grpc_json_transcoder',
    typed_config: {
        '@type': 'type.googleapis.com/envoy.extensions.filters.http.grpc_json_transcoder.v3.GrpcJsonTranscoder',
        proto_descriptor: '/etc/envoy/proto/descriptor.pb',
        services: ['user.UserService'],
        print_options: {
            add_whitespace: true,
            always_print_primitive_fields: true,
        },
    },
};

// Client-side: TypeScript gRPC-Web calling through transcoding proxy
const userService = new UserServiceClient('https://api.example.com');
const response = await userService.GetUser({ userId: '123' });
console.log(response.user.email);
```

**Common mistakes:**
- Translating between protocols without preserving request metadata (headers, tracing context), breaking observability.
- Lossy transcoding where types that exist in one protocol (e.g., gRPC `bytes` for binary) cannot be represented in the other (REST JSON), causing data corruption.

**Scanner signals:**
- Presence: Envoy `grpc_json_transcoder` filter, AWS AppSync, GraphQL gateway, `grpc-web` client library.
- Absence: No protocol translation layer where services use different protocols.
- Misconfiguration: Missing proto descriptor path, unhandled binary field types in JSON mapping.

### 3.6 Load Distribution and Health Checking

**Definition:** Proxies distribute traffic across multiple backend instances and continuously check backend health to remove unhealthy instances from the pool.

**Why it matters:** Without load distribution, traffic hits only one backend. Without health checking, traffic is routed to crashed or unresponsive backends, causing cascading failures.

**Implementation patterns:**

```python
# HAProxy configuration — round-robin with health checks
defaults
    log     global
    mode    http
    option  httplog
    timeout connect 5s
    timeout client  30s
    timeout server  30s

frontend api_frontend
    bind *:443 ssl crt /etc/haproxy/cert.pem alpn h2,http/1.1
    default_backend api_backends

backend api_backends
    balance roundrobin
    option httpchk GET /health
    http-check expect status 200

    server api-01 api-01.internal:8080 check inter 5s rise 2 fall 3
    server api-02 api-02.internal:8080 check inter 5s rise 2 fall 3
    server api-03 api-03.internal:8080 check inter 5s rise 2 fall 3
```

```go
// Go — custom round-robin with active health checking
type ServerPool struct {
    mu        sync.RWMutex
    servers   []*Server
    current   uint32
    alive     []bool
}

func (p *ServerPool) Next() *Server {
    p.mu.RLock()
    defer p.mu.RUnlock()

    n := uint32(len(p.servers))
    if n == 0 {
        return nil
    }

    attempts := n
    for attempts > 0 {
        idx := atomic.AddUint32(&p.current, 1) % n
        if p.alive[idx] {
            return p.servers[idx]
        }
        attempts--
    }
    return nil // no healthy servers
}

func (p *ServerPool) healthCheckLoop() {
    ticker := time.NewTicker(5 * time.Second)
    for range ticker.C {
        for i, srv := range p.servers {
            alive := ping(srv.Addr)
            p.mu.Lock()
            p.alive[i] = alive
            p.mu.Unlock()
        }
    }
}
```

**Scanner signals:**
- Presence: HAProxy `backend` / `server` / `check` directives, Envoy `load_assignment` clusters, AWS ALB target groups, Kubernetes `readinessProbe`.
- Absence: No health check configuration, no load balancing configuration.
- Misconfiguration: Health check hitting `/` instead of `/health` (may return 200 for error pages), `fall 1` (too aggressive removal).

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Nginx `proxy_pass` directive | Config | regex: `proxy_pass\s+https?://` | High |
| HAProxy `backend` and `server` blocks | Config | regex: `backend\s+\w+[\s\S]*?server\s+` | High |
| Envoy `static_resources` cluster list | YAML/JSON | AST: `static_resources.clusters` exists | High |
| Envoy `route_config` or `http_connection_manager` | YAML/JSON | regex: `http_connection_manager` | High |
| Kong plugin configuration (rate-limiting, jwt) | YAML | regex: `name:\s*(rate-limiting\|jwt\|oauth2)` | High |
| `httputil.ReverseProxy` usage | Go | AST: `httputil.ReverseProxy` instantiation | High |
| `@Proxy` middleware in Laravel routes | PHP | AST: `@Proxy` decorator on route or controller | High |
| `createProxyMiddleware` or `http-proxy` in Node.js | TypeScript | regex: `require\('http-proxy'\)\|createProxyMiddleware` | Medium |
| Istio `sidecar.istio.io/inject` annotation | YAML | regex: `sidecar\.istio\.io/inject:\s*"true"` | High |
| Istio `VirtualService` or `DestinationRule` | YAML | regex: `kind:\s*(VirtualService\|DestinationRule)` | High |
| AWS `AWS::ApiGateway::RestApi` in CloudFormation | JSON/YAML | regex: `AWS::ApiGateway::RestApi` | High |
| `X-Forwarded-For` header construction | Any | regex: `X-Forwarded-For\|X-Real-IP\|Forwarded` | High |
| TLS termination config (ssl_certificate, ssl_protocols) | Nginx config | regex: `ssl_certificate\|ssl_protocols` | Medium |
| Envoy `tls_context` or `transport_socket` | YAML/JSON | regex: `tls_context\|transport_socket` | High |
| Linkerd `linkerd-proxy` container in pod spec | YAML | regex: `linkerd-proxy` in `image:` field | High |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No reverse proxy config for externally-facing service | Any | No `proxy_pass`, `backend`, `VirtualService` found; service exposed directly on load balancer | High |
| No TLS termination configuration | Config | No `ssl_certificate`, `tls_context`, or ACM certificate reference | High |
| No `X-Forwarded-For` / `Forwarded` header handling | Any | No regex match for `X-Forwarded-For` in backend code | Medium |
| No rate-limiting plugin at gateway level | YAML | No `rate-limiting` in gateway plugin config | Medium |
| No health check endpoint in service | Any | No `/health`, `/healthz`, `/ready`, `/live` route definition | Medium |
| Direct internet exposure of backend port | Config | Security group / firewall allows 0.0.0.0/0 to app port (not just 80/443) | High |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| `proxy_set_header Host $proxy_host` (wrong Host header) | Nginx | regex: `proxy_set_header\s+Host\s+\$proxy_host` | High |
| TLS 1.0 or 1.1 enabled | Nginx/HAProxy | regex: `ssl_protocols.*TLSv1[^\.]` or `ssl_protocols\s+TLSv1\.?` | High |
| Proxy timeout set to 0 (infinite) | Nginx/HAProxy/Envoy | regex: `proxy_read_timeout\s+0\|timeout server\s+0\|route.timeout\s+0s` | High |
| No `ssl_ciphers` restriction (allows weak ciphers) | Nginx | `ssl_ciphers` absent while `ssl_protocols` present | Medium |
| Open forward proxy (no ACL / authentication) | HAProxy/Squid | regex: `acl\s+localnet` absent; `http_port` without `acl` restriction | High |
| `X-Forwarded-For` not stripped before client-facing response | Any | Backend code returns `X-Forwarded-For` header value to client | Medium |
| Health check hitting `/` instead of dedicated endpoint | Any | health check URL is `/` or empty | Medium |
| Missing `proxy_set_header X-Forwarded-Proto` | Nginx | `X-Forwarded-Proto` header not set in proxy block | Medium |
| Envoy retry policy without `retry_on` specification | YAML/JSON | `retries:` block exists but `retry_on` is absent | Medium |
| Sidecar injected without resource limits | YAML | `resources:` missing from injected container spec | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Open Forward Proxy

**Description:**
```nginx
# Squid — no ACL restriction, any internet client can use this proxy
http_port 3128
# No acl localnet src ... 
# No http_access allow localnet
# No http_access deny all
```

```typescript
// Express forward proxy with no authentication
import { createProxyMiddleware } from 'http-proxy-middleware';
app.use('/', createProxyMiddleware({ target: 'http://', changeOrigin: true }));
```

**Why it's dangerous:** An open proxy allows any internet user to route arbitrary traffic through your infrastructure. This is immediately flagged by abuse databases, leads to IP blacklisting, and can expose internal services to external attackers via DNS rebinding or URL manipulation.

**Detection:** Scanner checks for proxy middleware without authentication middleware, Squid config without `http_access deny all`, or absence of `Proxy-Authorization` header validation.

**Fix:**
```typescript
app.use('/proxy', requireAuth, createProxyMiddleware({
    target: 'http://',
    changeOrigin: true,
    router: (req) => validateAndResolveTarget(req.url),
    onProxyReq: (proxyReq, req) => {
        const auth = req.headers['proxy-authorization'];
        if (!isValidProxyAuth(auth)) {
            throw new Error('Unauthorized');
        }
    },
}));
```

### Anti-Pattern: Proxy as Business Logic Layer

**Description:**
```yaml
# Kong plugin — performing database queries at the proxy layer
plugins:
- name: pre-function
  config:
    header_filter:
    - |
      -- Lua code hitting PostgreSQL inside the proxy
      local result = pg.query("SELECT * FROM orders WHERE user_id = " .. ngx.var.arg_user_id)
      ngx.var.upstream_response_body = cjson.encode(result)
```

**Why it's dangerous:** Embedding business logic in the proxy creates a distributed monolith at the edge. Business logic changes require proxy redeployments, proxy Lua/DSL code is harder to test and debug than application code, and rate limiting / logging concerns get tangled with domain logic.

**Detection:** Scanner looks for database queries, complex transformations, or conditional branching inside proxy plugin configuration or filter chains.

**Fix:** Keep the proxy layer focused on cross-cutting concerns (auth, routing, rate limiting). Business logic belongs in backend services.

### Anti-Pattern: Missing Connection Timeout

**Description:**
```nginx
server {
    location / {
        proxy_pass http://backend:8080;
        # proxy_connect_timeout is not set — defaults to 60s
        # If backend is unreachable, Nginx holds the client connection for 60s
    }
}
```

```go
// Go reverse proxy — no timeout on backend response
proxy := httputil.NewSingleHostReverseProxy(backend)
// proxy.ErrorHandler handles errors but there is no proxy.Timeout
http.ListenAndServe(":443", proxy)
// Client can hang indefinitely if backend accepts connection but never responds
```

**Why it's dangerous:** A backend that accepts TCP connections but never sends a response causes the proxy to hold client connections open indefinitely. Under load, this exhausts the proxy's file descriptor limit and causes a cascading failure.

**Detection:** Scanner looks for proxy configuration blocks without explicit `proxy_connect_timeout`, `proxy_read_timeout`, or context deadline settings.

**Fix:**
```go
proxy := httputil.NewSingleHostReverseProxy(backend)
proxy.Transport = &http.Transport{
    TLSHandshakeTimeout: 5 * time.Second,
    IdleConnTimeout:     90 * time.Second,
    ResponseHeaderTimeout: 10 * time.Second,
}
http.ListenAndServe(":443", proxy)
```

### Anti-Pattern: Header Forwarding Without Sanitization

**Description:**
```python
# Python Flask API receiving proxy-forwarded headers without validation
from flask import Flask, request
app = Flask(__name__)

@app.route('/api/users')
def get_users():
    # Trusting X-Forwarded-For without checking if it came from the actual proxy
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # An attacker can set X-Forwarded-For to an arbitrary value
    # and bypass IP-based access controls
```

**Why it's dangerous:** Any client can set `X-Forwarded-For` to an arbitrary IP address. If the application trusts this header for access control, IP allowlisting, or audit logging, an attacker can spoof their identity.

**Detection:** Scanner looks for `X-Forwarded-For` being used for authorization or IP-based decisions without validation against a trusted proxy list.

**Fix:**
```python
TRUSTED_PROXIES = {'10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'}

def get_client_ip(request):
    xff = request.headers.get('X-Forwarded-For', '')
    if not xff:
        return request.remote_addr

    # Rightmost IP is the closest proxy; verify it is trusted
    ips = xff.split(',')
    closest_ip = ips[-1].strip()
    if not any(ipaddress.ip_address(closest_ip) in ipaddress.ip_network(net)
               for net in TRUSTED_PROXIES):
        raise SecurityError("Untrusted X-Forwarded-For header")

    return ips[0].strip()  # Original client IP
```

### Anti-Pattern: Single Proxy Instance

**Description:**
```bash
# Production deployment: one nginx instance, no redundancy
docker run -d -p 443:443 nginx:latest
```

**Why it's dangerous:** A single proxy instance is a single point of failure. When the process crashes or the host fails, all traffic is lost. There is no graceful degradation.

**Detection:** Scanner checks for single-replica deployments of proxy processes without a load balancer in front.

**Fix:**
```bash
# Deploy at least 2 nginx replicas behind a cloud load balancer
# In Kubernetes:
# replicas: 2
# With a Service of type LoadBalancer providing the entry point
```

### Anti-Pattern: Proxy with No Request Size Limits

**Description:**
```nginx
location / {
    proxy_pass http://backend:8080;
    # No client_max_body_size — defaults to 1MB
    # But also no proxy buffering limits — backend can be flooded
}
```

**Why it's dangerous:** Without request size limits, an attacker can send arbitrarily large request bodies, consuming proxy and backend memory. Without response size limits, a malicious backend can send an infinite response body, exhausting proxy resources.

**Detection:** Scanner looks for `client_max_body_size` in Nginx, `body_size_limit` in Envoy, or equivalent request body size configuration.

**Fix:**
```nginx
location / {
    proxy_pass http://backend:8080;
    client_max_body_size 10m;       # Limit upload size
    proxy_buffering on;
    proxy_buffer_size 4k;
    proxy_buffers 8 4k;
    proxy_busy_buffers_size 8k;
}
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `proxy_connect_timeout` | duration | 60s | 5s | Timeout for establishing connection to backend (Nginx) |
| `proxy_read_timeout` | duration | 60s | 30s | Timeout for reading backend response (Nginx) |
| `proxy_send_timeout` | duration | 60s | 30s | Timeout for sending request to backend (Nginx) |
| `client_max_body_size` | size | 1m | 10m | Maximum allowed size of the client request body (Nginx) |
| `proxy_buffering` | bool | on | on | Whether proxy buffers backend response (Nginx) |
| `ssl_protocols` | list | TLSv1 TLSv1.1 TLSv1.2 | TLSv1.2 TLSv1.3 | Enabled TLS protocol versions (Nginx) |
| `ssl_ciphers` | string | (system default) | ECDHE+AESGCM:ECDHE+CHACHA20 | Cipher suite whitelist (Nginx) |
| `proxy_set_header Host` | string | `$proxy_host` | `$host` | Host header sent to backend (Nginx) |
| `balance` | string | roundrobin | roundrobin | Load balancing algorithm (HAProxy) |
| `httpchk` | string | (none) | `GET /health` | HTTP health check method and URL (HAProxy) |
| `inter` | duration | 2s | 5s | Interval between health checks (HAProxy) |
| `rise` | int | 2 | 2 | Number of successful checks to mark server UP (HAProxy) |
| `fall` | int | 3 | 3 | Number of failed checks to mark server DOWN (HAProxy) |
| `max_connections` | int | 1024 | 512 per backend | Maximum concurrent connections to a backend (Envoy) |
| `circuit_breakers` | object | (none) | thresholds per service | Circuit breaker config for upstream calls (Envoy) |
| `retry_policy` | object | (none) | 3 retries, 5s timeout | Retry policy for failed upstream calls (Envoy) |
| `sidecar.istio.io/inject` | string | "false" | "true" | Enable automatic Envoy sidecar injection (Kubernetes/Istio) |
| `traffic.sidecar.istio.io/includeOutboundIPRanges` | string | "0.0.0.0/0" | specific CIDRs | IP ranges captured by sidecar outbound listener (Istio) |

## 7. Integration Points

- **Depends on:** A reverse proxy depends on at least one reachable backend service. It depends on the network layer (TCP/IP) and TLS certificate management (Let's Encrypt, internal CA, or cloud provider). An API gateway depends on service discovery (DNS, Consul, Istio) to route requests to the correct backend.

- **Used by:** Every externally-facing service uses a reverse proxy. API handlers use `X-Forwarded-For` for logging and rate limiting. Kubernetes Ingress controllers use reverse proxies (Nginx, Envoy) to route cluster-internal traffic. Service meshes use sidecar proxies to transparently manage all inter-service communication.

- **Related to `foundation.load-balancers`:** Proxies and load balancers are closely related — a reverse proxy performs load balancing across backends, and a dedicated load balancer often fronts multiple proxy instances. Layer 4 load balancers (L4) distribute TCP connections while Layer 7 load balancers (L7) distribute HTTP requests based on headers, paths, and cookies.

- **Related to `foundation.protocols`:** The proxy must correctly handle the protocol it terminates. An HTTP/2 proxy must support frame multiplexing. A WebSocket proxy must not buffer messages. A gRPC proxy must handle HTTP/2 trailers correctly.

- **Related to `foundation.rate-limiting`:** Proxies are the primary location for rate limiting enforcement. Nginx `limit_req_zone`, Envoy `local_ratelimit`, and Kong rate-limiting plugins implement token-bucket or leaky-bucket algorithms at the proxy layer, protecting backends from traffic spikes.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Proxy request rate (RPS) | Prometheus (nginx_vts, envoy_cluster) | Spike > 2x baseline → warn | Investigate traffic anomaly |
| Backend response time p99 | Prometheus histogram | p99 > 1s → warn, > 3s → page | Check backend health, increase timeout |
| Proxy error rate (5xx) | Prometheus counter | > 1% → warn, > 5% → page | Check upstream service health |
| Active connections to each backend | Prometheus gauge | Near `max_connections` → warn | Scale backend or increase pool size |
| TLS handshake failures | Prometheus counter | Any → warn | Check certificate expiry, TLS version mismatch |
| Health check failures | HAProxy/Envoy metrics | > 0 → warn | Investigate backend health endpoint |
| Circuit breaker open count | Prometheus counter | Any → page | Upstream service is down, trigger incident |
| Timeout rate | Prometheus counter | > 0.5% → warn | Increase timeout or fix backend latency |
| Proxy CPU utilization | Prometheus gauge | > 70% → warn, > 90% → page | Scale proxy horizontally |
| Proxy memory utilization | Prometheus gauge | > 80% → warn | Check for connection leak, increase memory |
| `X-Forwarded-For` spoofing attempts | Custom log alert | Any → warn | Block source IP |

Key log messages to emit:
- `proxy upstream connection refused` — backend is down or overloaded
- `proxy header too large` — client sent oversized headers, possible attack
- `TLS handshake error` — certificate or protocol mismatch
- `proxy read timeout` — backend is slow to respond
- `circuit breaker opened for <service>` — backend health degraded

## 9. Evolution / Version Tracking

The proxy concept has evolved dramatically over the past two decades. Early reverse proxies like Squid (1996) and Apache mod_proxy were simple HTTP forwarders primarily designed for caching. Nginx (2004) introduced an event-driven, non-blocking architecture that could handle tens of thousands of concurrent connections on a single core — making it the dominant reverse proxy for production systems.

The rise of microservices in the 2010s created demand for API gateways (Kong, 2015; AWS API Gateway, 2015) that added protocol translation, authentication, and request aggregation at the edge. Simultaneously, the service mesh pattern (Linkerd, 2016; Istio, 2017) moved proxy functionality into sidecar containers, enabling transparent service-to-service communication without application-level changes.

Envoy (2016) unified these patterns with a high-performance, extensible proxy designed explicitly for service mesh use cases. It introduced xDS APIs for dynamic configuration, eliminating the need to reload configuration files. The current trend is toward "ambient mesh" (Istio ambient mode, 2022) which uses per-namespace gateway proxies instead of per-pod sidecars, reducing resource overhead.

Emerging patterns include eBPF-based proxies (Cilium, 2019) that bypass the network stack entirely for improved performance, and zero-trust networking models (BeyondCorp, 2010, now widely adopted) where every proxy enforces identity-based authentication via mTLS.

## 10. References

1. Nginx Reverse Proxy Documentation — https://nginx.org/en/docs/http/ngx_http_proxy_module.html
2. HAProxy Configuration Guide — https://www.haproxy.org/#config
3. Envoy Proxy Documentation — https://www.envoyproxy.io/docs/envoy/latest/
4. Istio Service Mesh Architecture — https://istio.io/latest/docs/ops/deployment/architecture/
5. Kong Gateway Documentation — https://docs.konghq.com/gateway/latest/
6. RFC 7230 — HTTP/1.1 Message Syntax and Routing (hop-by-hop headers) — https://datatracker.ietf.org/doc/html/rfc7230#section-6.1
7. AWS API Gateway Developer Guide — https://docs.aws.amazon.com/apigateway/latest/developerguide/
8. Cilium eBPF-based Networking — https://docs.cilium.io/en/stable/
