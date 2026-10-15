---
id: foundation.client-server
category: foundation
owning_agent: F-17
maturity: stable
languages:
- any
tags:
- request-response
- polling
- sse
- websocket
related:
- foundation.protocols
- foundation.latency-bandwidth
- foundation.load-balancers
domain: core
---

# Client-Server Communication

## 1. Overview

Client-server communication is the fundamental interaction pattern of distributed systems, where a client sends a request to a server and receives a response. This simple abstraction — formalized in the 1980s — underpins the entire internet: every web page load, API call, and database query is a client-server interaction. In modern systems, the pattern has evolved beyond simple request-response to include streaming (Server-Sent Events, WebSocket), long-polling, and bidirectional event-driven communication. The choice of communication pattern directly determines system latency, throughput, resource utilization, and user experience. An architecture that uses polling where SSE would suffice wastes compute and bandwidth; one that uses WebSocket where a simple REST call would do introduces unnecessary complexity.

## 2. Core Principles

- **Every communication pattern has a latency-throughput tradeoff** — synchronous request-response is simple but blocks; polling wastes resources; streaming is efficient but requires stateful connections.
- **The server should never hold client connections longer than necessary** — long-lived connections consume file descriptors and memory on the server. Connection limits are finite resources.
- **Communication patterns must match the data flow** — if data changes on the server and the client needs immediate notification, push patterns (SSE, WebSocket) are correct. If the client only needs data on demand, request-response is correct.
- **Timeouts must be set on both ends** — the client must have a deadline for expecting a response, and the server must have a timeout for idle connections. Without both, hung connections accumulate silently.
- **Backpressure must be handled** — if the server produces data faster than the client can consume it, the server must slow down or drop data. Ignoring backpressure causes memory exhaustion.
- **Idempotency is a client-server contract** — retrying a failed request must not cause duplicate side effects. Servers must be designed to handle at-least-once delivery semantics safely.

## 3. Sub-Concepts

### 3.1 Synchronous Request-Response

**Definition:** The client sends a request and blocks, waiting for the server to return a complete response before proceeding. This is the default pattern of HTTP and gRPC unary calls.

**Why it matters:** Synchronous request-response is the simplest and most widely understood communication pattern. It maps directly to function calls, is easy to debug, and integrates cleanly with most frameworks and libraries. However, it becomes problematic under high latency, when the client thread is blocked waiting for a slow response.

**Implementation patterns:**

```python
# Python — synchronous HTTP request with requests library
import requests
from requests.exceptions import Timeout, ConnectionError

def get_user(user_id: str) -> dict | None:
    try:
        response = requests.get(
            f"https://api.example.com/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {get_token()}"},
            timeout=(3.05, 27),  # (connect_timeout, read_timeout) in seconds
        )
        response.raise_for_status()
        return response.json()
    except Timeout:
        logging.warning(f"Timeout fetching user {user_id}")
        return None
    except ConnectionError:
        logging.error("Connection to API failed")
        return None
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise
```

```typescript
// TypeScript — synchronous-style fetch with async/await
async function createOrder(orderData: OrderInput): Promise<Order> {
    const response = await fetch('https://api.example.com/api/v1/orders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`,
            'Idempotency-Key': crypto.randomUUID(), // Safe to retry
        },
        body: JSON.stringify(orderData),
        signal: AbortSignal.timeout(10000), // 10s total timeout
    });

    if (!response.ok) {
        if (response.status === 409) {
            throw new ConflictError('Order already exists for this idempotency key');
        }
        throw new ApiError(response.status, await response.text());
    }

    return response.json() as Promise<Order>;
}
```

```go
// Go — synchronous gRPC call
func (s *Server) GetUser(ctx context.Context, req *pb.GetUserRequest) (*pb.UserResponse, error) {
    // Server-side: respect client deadline
    if deadline, ok := ctx.Deadline(); ok {
        log.Printf("Request deadline: %v", deadline)
    }

    user, err := s.db.GetUser(req.UserId)
    if err != nil {
        if errors.Is(err, sql.ErrNoRows) {
            return nil, status.Errorf(codes.NotFound, "user %s not found", req.UserId)
        }
        return nil, status.Errorf(codes.Internal, "database error: %v", err)
    }

    return &pb.UserResponse{
        UserId:    user.ID,
        Email:     user.Email,
        CreatedAt: user.CreatedAt.Unix(),
    }, nil
}
```

**Common mistakes:**
- No timeout set on requests, causing threads to hang indefinitely when the server is slow.
- Retrying POST requests without idempotency keys, creating duplicate records on retry.
- Blocking the main thread in GUI applications, freezing the UI.

**Scanner signals:**
- Presence: `requests.get`, `requests.post`, `fetch()`, `axios.get`, `grpc.*Call`, `client.GetUser`.
- Absence: No HTTP or RPC calls (application is purely computational).
- Misconfiguration: `timeout=None` or `timeout: 0`, no `Idempotency-Key` header on POST/PUT.

### 3.2 Polling

**Definition:** The client repeatedly sends requests to the server at fixed intervals to check for new data. There are two variants: short polling (fixed interval, e.g., every 5 seconds) and long polling (client sends request, server holds it open until data is available or timeout).

**Why it matters:** Polling is the simplest way to get near-real-time data without persistent connections. It works with any HTTP infrastructure and requires no server-side push support. However, it generates significant unnecessary traffic — most poll requests return empty responses.

**Implementation patterns:**

```python
# Python — short polling (every 5 seconds)
import asyncio
import httpx

POLL_INTERVAL = 5  # seconds

async def poll_for_updates(last_timestamp: float):
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(
                    "https://api.example.com/api/v1/events",
                    params={"since": str(last_timestamp)},
                    timeout=5,
                )
                if response.status_code == 200:
                    events = response.json()
                    for event in events:
                        process_event(event)
                        last_timestamp = max(last_timestamp, event["timestamp"])
                elif response.status_code == 304:
                    pass  # No new events
            except httpx.TimeoutException:
                pass  # Server is slow, retry next interval
            except httpx.HTTPError as e:
                logging.error(f"Poll error: {e}")

            await asyncio.sleep(POLL_INTERVAL)
```

```typescript
// TypeScript — long polling (server holds connection open)
async function longPoll(since: string): Promise<void> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 30000); // 30s max hold

    try {
        const response = await fetch(
            `https://api.example.com/api/v1/events?since=${since}`,
            { signal: controller.signal },
        );

        if (response.ok) {
            const events = await response.json();
            processEvents(events);
            // Immediately start next long poll
            longPoll(getLatestTimestamp());
        } else if (response.status === 503) {
            // Server overloaded — back off exponentially
            await sleep(min(backoff * 2, 60000));
            longPoll(since);
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            // Timeout — restart long poll
            longPoll(since);
        }
    } finally {
        clearTimeout(timeout);
    }
}
```

```go
// Go — server-side long poll implementation
func (s *Server) handleEvents(w http.ResponseWriter, r *http.Request) {
    since := r.URL.Query().Get("since")
    if since == "" {
        since = "0"
    }

    sinceTime, _ := strconv.ParseInt(since, 10, 64)

    // Set long-poll timeout headers
    w.Header().Set("Content-Type", "application/json")
    w.Header().Set("Cache-Control", "no-cache")
    w.WriteHeader(http.StatusOK)

    flusher, ok := w.(http.Flusher)
    if !ok {
        http.Error(w, "streaming unsupported", http.StatusInternalServerError)
        return
    }

    // Hold connection open for up to 30 seconds
    timeout := time.After(30 * time.Second)
    ticker := time.NewTicker(500 * time.Millisecond)
    defer ticker.Stop()

    for {
        select {
        case <-timeout:
            // Return empty array — client will re-poll
            fmt.Fprint(w, "[]")
            flusher.Flush()
            return

        case <-ticker.C:
            events := s.eventStore.GetSince(sinceTime)
            if len(events) > 0 {
                json.NewEncoder(w).Encode(events)
                flusher.Flush()
                return
            }
        }
    }
}
```

**Common mistakes:**
- Polling interval too short (e.g., every 1 second), generating excessive load without perceptible benefit.
- Polling interval too long (e.g., every 60 seconds), making the UI feel stale for time-sensitive data.
- Not using conditional requests (`If-Modified-Since`, `ETag`) with polling, so every request returns the full payload even when unchanged.

**Scanner signals:**
- Presence: `setInterval`, `setTimeout` with HTTP calls in loop, cron jobs hitting an API endpoint, Celery beat tasks.
- Absence: No polling for data that requires freshness (config changes, notifications).
- Misconfiguration: Polling interval < 1s for high-traffic endpoints, no conditional headers on poll requests.

### 3.3 Server-Sent Events (SSE)

**Definition:** SSE is a server-push technology where the server sends a continuous stream of events to the client over a single HTTP connection. The server can push text-based event messages at any time, and the client receives them as they arrive. SSE is unidirectional (server to client only) and uses standard HTTP, making it compatible with existing infrastructure.

**Why it matters:** SSE is the simplest and most efficient way to implement real-time updates from server to client. It works over standard HTTP/1.1, is supported natively in browsers via `EventSource`, and requires no special protocol negotiation. It is ideal for notifications, live feeds, and progress updates where only the server needs to push data.

**Implementation patterns:**

```python
# Python — SSE endpoint with FastAPI
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import asyncio
import json
import time

app = FastAPI()

async def event_generator(user_id: str):
    """Yield SSE-formatted events as they occur."""
    last_event_id = 0
    while True:
        # Wait for new events (poll internal event store)
        events = await get_events_for_user(user_id, since=last_event_id)

        if events:
            for event in events:
                last_event_id = event["id"]
                yield f"id: {event['id']}\n"
                yield f"event: {event['type']}\n"
                yield f"data: {json.dumps(event['payload'])}\n\n"

        await asyncio.sleep(1)  # Poll interval

@app.get("/api/v1/stream/events")
async def stream_events(user_id: str):
    return StreamingResponse(
        event_generator(user_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
```

```typescript
// TypeScript — SSE client using EventSource
function connectSSE(userId: string): EventSource {
    const source = new EventSource(`/api/v1/stream/events?user_id=${userId}`);

    source.addEventListener('notification', (event: MessageEvent) => {
        const notification = JSON.parse(event.data);
        showNotification(notification.title, notification.body);
    });

    source.addEventListener('progress', (event: MessageEvent) => {
        const progress = JSON.parse(event.data);
        updateProgressBar(progress.percent);
    });

    source.addEventListener('error', (err: Event) => {
        if (source.readyState === EventSource.CLOSED) {
            console.log('SSE connection closed permanently');
            source.close();
        } else if (source.readyState === EventSource.CONNECTING) {
            console.log('SSE reconnecting...');
        }
    });

    return source;
}

// Clean up on component unmount
function cleanup(source: EventSource) {
    source.close();
    if (source.readyState === EventSource.CONNECTING) {
        // Force close by replacing with a closed source
        const closedSource = new EventSource('/api/v1/stream/events');
        closedSource.close();
    }
}
```

**SSE event format:**
```
id: 42
event: notification
data: {"title":"New message","body":"Alice sent you a message"}
retry: 5000

id: 43
event: progress
data: {"percent":75,"status":"processing"}
```

**Common mistakes:**
- Using SSE for bidirectional communication — SSE is server-to-client only. For client-to-server messages, use a separate HTTP POST endpoint.
- Not setting `Cache-Control: no-cache` — intermediate proxies may buffer and cache SSE responses, breaking the streaming behavior.
- Not setting `X-Accel-Buffering: no` behind Nginx — Nginx buffers SSE responses by default, introducing up to 1 second of delay.

**Scanner signals:**
- Presence: `EventSource`, `text/event-stream` media type, `StreamingResponse` with `text/event-stream`, `@app.get` returning `EventSourceResponse` (FastAPI SSE).
- Absence: No real-time server push despite real-time UI requirements.
- Misconfiguration: Missing `X-Accel-Buffering: no` behind Nginx, missing `retry` field in SSE events.

### 3.4 Long-Polling and Comet

**Definition:** Long-polling is a variation of polling where the client sends a request and the server holds it open until new data is available or a timeout expires. The client immediately re-establishes the connection after receiving a response. The server-side pattern is called Comet.

**Why it matters:** Long-polling approximates real-time push while remaining compatible with legacy HTTP infrastructure that does not support WebSocket or SSE. It was the standard approach before WebSocket (RFC 6455, 2011) and SSE gained browser support.

**Implementation patterns:**

```go
// Go — Comet-style long polling server
func (s *Server) LongPollHandler(w http.ResponseWriter, r *http.Request) {
    topic := r.URL.Query().Get("topic")
    lastID := r.URL.Query().Get("last_id")

    // Channel to wait for new messages
    msgChan := s.broker.Subscribe(topic, lastID)
    defer s.broker.Unsubscribe(topic, msgChan)

    // 30-second timeout
    timer := time.NewTimer(30 * time.Second)
    defer timer.Stop()

    select {
    case msg := <-msgChan:
        w.Header().Set("Content-Type", "application/json")
        json.NewEncoder(w).Encode(msg)
    case <-timer.C:
        // Return empty — client will re-poll
        w.WriteHeader(http.StatusNoContent)
    }
}
```

**Common mistakes:**
- Not closing the long-poll response on server shutdown, leaving client connections hanging until they time out.
- Using long-polling with a very short hold time (e.g., 5 seconds), which degenerates into expensive short polling.
- Not batching multiple events into one response, causing the client to make rapid successive long-poll requests.

**Scanner signals:**
- Presence: HTTP handler with long timeout (> 10s), `select` with timeout + channel receive pattern.
- Absence: No long-poll implementation for real-time features.
- Misconfiguration: Hold time < 10s (too short to be efficient), no reconnection after response.

### 3.5 Connection Lifecycle and Keep-Alive

**Definition:** Connection lifecycle management covers the full lifecycle of a client-server connection: establishment (TCP handshake, TLS negotiation), active use (request-response cycles, keep-alive probes), and teardown (FIN/ACK, connection pool return).

**Why it matters:** Connection management is where most network-related bugs and performance issues originate. Incorrect keep-alive settings cause connection storms. Missing connection pool limits cause resource exhaustion. Incorrect teardown causes half-open connections that hold resources indefinitely.

**Implementation patterns:**

```go
// Go — HTTP client with connection pool and keep-alive
import (
    "crypto/tls"
    "net"
    "time"
)

func createHTTPClient() *http.Client {
    transport := &http.Transport{
        // Connection pool limits
        MaxIdleConns:        100,
        MaxIdleConnsPerHost: 20,
        MaxConnsPerHost:     50,
        IdleConnTimeout:     90 * time.Second,

        // TCP keep-alive
        DialContext: (&net.Dialer{
            Timeout:   5 * time.Second,
            KeepAlive: 30 * time.Second,
        }).DialContext,

        // TLS configuration
        TLSClientConfig: &tls.Config{
            MinVersion: tls.VersionTLS12,
            CipherSuites: []uint16{
                tls.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
                tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
                tls.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305,
            },
        },

        // Response header timeout — prevents slow-read attacks
        ResponseHeaderTimeout: 10 * time.Second,
    }

    return &http.Client{
        Transport: transport,
        Timeout:   30 * time.Second, // Total request timeout
    }
}
```

```python
# Python — SQLAlchemy connection pool (database connection lifecycle)
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@db-host:5432/mydb",
    poolclass=QueuePool,
    pool_size=10,            # Persistent connections in pool
    max_overflow=5,          # Additional connections when pool is full
    pool_timeout=30,         # Time to wait for a free connection
    pool_recycle=1800,       # Recycle connections after 30 min (prevents stale)
    pool_pre_ping=True,      # Test connection health before use
)
```

**Connection states:**
1. **Idle** — Connection in pool, waiting to be used.
2. **Active** — Connection in use, processing a request.
3. **Closing** — FIN sent, waiting for ACK.
4. **Half-closed** — One side has closed, the other has not.
5. **Time-wait** — TCP state after close, waiting for delayed packets to expire.

**Common mistakes:**
- Setting `pool_size` too large, exhausting database connection limits.
- Not enabling `pool_pre_ping`, causing "connection already closed" errors when the DB server kills idle connections.
- Disabling TCP keep-alive, causing firewalls and NAT gateways to silently drop idle connections.

**Scanner signals:**
- Presence: `http.Transport` with pool config, `QueuePool` / `ConnectionPool`, `MaxIdleConns`, `pool_pre_ping`.
- Absence: No connection pool configuration for database or HTTP clients.
- Misconfiguration: `pool_size=0`, `pool_pre_ping=False` without `pool_recycle`, `IdleConnTimeout: 0`.

### 3.6 Idempotency and Safe Retry

**Definition:** Idempotency is the property that applying an operation multiple times produces the same result as applying it once. In client-server communication, idempotent requests can be safely retried without causing duplicate side effects.

**Why it matters:** Networks fail. Timeouts happen. Without idempotency, a client that retries a timed-out POST request creates duplicate records, charges a customer twice, or sends a notification twice. HTTP's idempotent methods are GET, PUT, DELETE, HEAD, OPTIONS, and TRACE. POST is not idempotent by default.

**Implementation patterns:**

```typescript
// TypeScript — idempotency key pattern for POST requests
async function createOrderWithIdempotency(order: OrderInput): Promise<Order> {
    const idempotencyKey = crypto.randomUUID();

    const response = await fetch('https://api.example.com/api/v1/orders', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': idempotencyKey,
        },
        body: JSON.stringify(order),
    });

    if (response.status === 409) {
        // Request with this idempotency key was already processed
        // Return the original result
        const existingOrder = await getOrderByIdempotencyKey(idempotencyKey);
        if (existingOrder) return existingOrder;
    }

    return response.json() as Promise<Order>;
}
```

```go
// Go — server-side idempotency enforcement
func (s *Server) CreateOrder(w http.ResponseWriter, r *http.Request) {
    idempotencyKey := r.Header.Get("Idempotency-Key")
    if idempotencyKey == "" {
        http.Error(w, "Idempotency-Key header required", http.StatusBadRequest)
        return
    }

    // Check if this key was already processed
    existing, err := s.idempotencyStore.Get(idempotencyKey)
    if err == nil && existing != nil {
        // Return cached response — no duplicate processing
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(existing)
        return
    }

    var req CreateOrderRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, "Invalid request body", http.StatusBadRequest)
        return
    }

    // Process the order
    order := s.processOrder(req)

    // Cache result for future retries
    s.idempotencyStore.Set(idempotencyKey, order, 24*time.Hour)

    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(http.StatusCreated)
    json.NewEncoder(w).Encode(order)
}
```

**Common mistakes:**
- Retrying POST requests without idempotency keys, creating duplicates.
- Using auto-increment IDs as idempotency keys — if the first request succeeds but the response is lost, the retry creates a new record with a new ID.
- Not clearing idempotency keys after successful processing, causing the system to return stale data forever.

**Scanner signals:**
- Presence: `Idempotency-Key` header, idempotency store/table, `PUT` / `DELETE` methods for mutations.
- Absence: No idempotency mechanism for POST/PATCH endpoints.
- Misconfiguration: Idempotency key derived from request body (changes if body changes), key TTL too short.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| HTTP server definition | Any | AST: `app.run\|app.listen\|createServer\|FastAPI()` | High |
| HTTP client call | Python, TypeScript, Go | AST: `requests\.\|fetch(\|axios\.\|http\.Get\|http\.Do` | High |
| gRPC client/server | Go, Python | regex: `grpc\.\|user_pb2_grpc\.` | High |
| WebSocket server | TypeScript, Python | AST: `new WebSocketServer\|ws\.Server` | High |
| SSE media type | Any | regex: `text/event-stream` | High |
| EventSource client | TypeScript, Python | AST: `new EventSource` | High |
| Connection pool config | Any | regex: `pool_size\|MaxIdleConns\|QueuePool\|pool_pre_ping` | Medium |
| Idempotency-Key header | Any | regex: `Idempotency-Key\|idempotency_key` | Medium |
| HTTP timeout config | Any | regex: `timeout=\|Timeout: \|AbortSignal\.timeout\|context\.WithTimeout` | High |
| Long-poll handler | Go, Python | regex: `time\.After.*30.*time\.Second` with HTTP handler | Medium |
| Keep-alive configuration | Any | regex: `KeepAlive\|keepalive\|pool_recycle` | Medium |
| Retry logic | Any | regex: `retry\|Retryable\|backoff\|max_retries` | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No HTTP client timeout | Python, TypeScript | `requests.get` without `timeout=` parameter; `fetch` without `signal` or timeout | High |
| No connection pool for database | Any | Database connection string without pool config | Medium |
| No retry logic for external calls | Any | HTTP/gRPC calls without try/catch + retry | Medium |
| No idempotency for mutation endpoints | Any | POST/PATCH without `Idempotency-Key` header | Medium |
| No keepalive configuration | Any | No TCP keepalive, no HTTP keepalive timeout | Medium |
| No SSE/WebSocket for real-time UI | Any | UI uses `setInterval` polling for updates > 5s intervals | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| `timeout=None` or `timeout: 0` | Python | regex: `timeout\s*=\s*None\|timeout\s*:\s*0` | High |
| `AbortSignal.timeout(0)` | TypeScript | regex: `AbortSignal\.timeout\(0\)` | High |
| `grpc.WithTimeout(0)` | Go | regex: `grpc\.WithTimeout\(0` | High |
| No `Idempotency-Key` on POST | Any | POST handler without idempotency mechanism | Medium |
| `context.Background()` for external calls | Go | regex: `context\.Background\(\)` without timeout in RPC/HTTP call | High |
| SSE without `X-Accel-Buffering: no` | Any | `text/event-stream` response without `X-Accel-Buffering: no` header | Medium |
| SSE without `Cache-Control: no-cache` | Any | `text/event-stream` without `Cache-Control: no-cache` | Medium |
| `pool_pre_ping=False` without `pool_recycle` | Python | `pool_pre_ping` absent and `pool_recycle` absent | Medium |
| Polling interval < 1s | Any | `setInterval.*[0-9]{1,3}` with HTTP call | Medium |
| Long-poll timeout < 10s | Any | Long-poll handler timeout < 10s | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Polling for Real-Time Data

**Description:**
```typescript
// Frontend — polling every 1 second for chat messages
useEffect(() => {
    const interval = setInterval(async () => {
        const messages = await fetch(`/api/messages?room=${roomId}`);
        setMessages(await messages.json());
    }, 1000); // Poll every 1 second

    return () => clearInterval(interval);
}, [roomId]);
```

**Why it's dangerous:** Polling every second generates 3,600 requests per hour per client. For a chat app with 10,000 active users, that is 36 million requests per hour, almost all returning empty responses. This wastes server CPU, database queries, and network bandwidth.

**Detection:** Scanner looks for `setInterval` with HTTP calls in UI code, interval < 5 seconds, or high-frequency cron jobs hitting an API that returns mostly empty responses.

**Fix:** Use WebSocket or SSE for server-push real-time updates. Fall back to long-polling only if push infrastructure is unavailable.

```typescript
// SSE-based real-time updates — one persistent connection
useEffect(() => {
    const source = new EventSource(`/api/v1/stream/chat?room=${roomId}`);
    source.onmessage = (event) => {
        setMessages(prev => [...prev, JSON.parse(event.data)]);
    };
    return () => source.close();
}, [roomId]);
```

### Anti-Pattern: No Timeout on External Requests

**Description:**
```python
# Python requests — no timeout
response = requests.get("https://slow-service.internal/api/data")
data = response.json()  # This line is reached minutes later if server is slow
```

**Why it's dangerous:** Without a timeout, a slow or unresponsive server causes the client thread to hang indefinitely. In a web server context, this blocks a worker thread. In a serverless function context, it causes the function to time out and be retried, wasting compute and potentially causing duplicate effects.

**Detection:** Scanner looks for HTTP/gRPC calls without explicit timeout parameters.

**Fix:**
```python
response = requests.get(
    "https://slow-service.internal/api/data",
    timeout=(3.05, 27),  # (connect_timeout, read_timeout)
)
```

### Anti-Pattern: Fire-and-Forget Without Delivery Guarantee

**Description:**
```go
// Go — sending a UDP message and hoping it arrives
func sendMetric(name string, value float64) {
    conn, _ := net.Dial("udp", metrics-collector:5140)
    conn.Write([]byte(fmt.Sprintf("%s:%f", name, value)))
    conn.Close()
    // If the packet is lost, it is lost forever
    // No acknowledgment, no retry, no ordering guarantee
}
```

**Why it's dangerous:** UDP provides no delivery guarantee. For non-critical metrics this is acceptable, but for any data where loss is unacceptable (financial transactions, audit logs, security events), fire-and-forget without acknowledgment is dangerous.

**Detection:** Scanner looks for UDP sends without acknowledgment/receipt handling, or HTTP POSTs without response body processing.

**Fix:**
```go
func sendMetricWithACK(name string, value float64) error {
    conn, _ := net.Dial("udp", "metrics-collector:5140")
    _, err := conn.Write([]byte(fmt.Sprintf("%s:%f", name, value)))
    conn.Close()
    return err // At least detect local send errors
}

// For critical data, use TCP or HTTP with retry
func sendCriticalEvent(event Event) error {
    return retry.Do(func() error {
        resp, err := http.Post("https://events.internal/api/v1/ingest",
            "application/json", bytes.NewReader(event.JSON()))
        if err != nil {
            return err
        }
        resp.Body.Close()
        if resp.StatusCode != 202 {
            return fmt.Errorf("server rejected: %d", resp.StatusCode)
        }
        return nil
    }, retry.Attempts(3), retry.Delay(time.Second))
}
```

### Anti-Pattern: Blocking Event Loop in Async Server

**Description:**
```python
# FastAPI — blocking call in async handler
@app.get("/api/slow")
async def slow():
    time.sleep(10)  # Blocks ALL concurrent requests for 10 seconds
    return {"status": "done"}
```

**Why it's dangerous:** Async frameworks use a single-threaded event loop. A blocking call freezes the entire server — no other request can be processed until the blocking call completes. Under concurrent load, this causes a cascading timeout storm.

**Detection:** Scanner looks for known-blocking functions (`time.sleep`, `socket.gethostbyname`, synchronous DB calls) inside `async def` routes.

**Fix:**
```python
@app.get("/api/slow")
async def slow():
    # Offload to thread pool
    result = await asyncio.get_event_loop().run_in_executor(
        None, blocking_database_call
    )
    return {"status": "done", "data": result}

# Better: use async-native libraries (asyncpg, aiohttp)
```

### Anti-Pattern: WebSocket State in Single Process

**Description:**
```go
// Go — WebSocket hub that only works on a single process
var clients = make(map[*websocket.Conn]bool)

func broadcast(message string) {
    for client := range clients {
        client.WriteMessage(websocket.TextMessage, []byte(message))
    }
}
```

**Why it's dangerous:** This hub works only when a single Go process handles all WebSocket connections. In production with multiple replicas behind a load balancer, each replica has its own `clients` map. A message broadcast from one replica reaches only that replica's clients. Horizontal scaling breaks the system.

**Detection:** Scanner looks for in-memory WebSocket client maps without a pub/sub or external message broker.

**Fix:**
```go
// Use Redis Pub/Sub for cross-instance WebSocket broadcast
func broadcast(channel string, message []byte) {
    redisClient.Publish(ctx, channel, message)
}

// Each instance subscribes to Redis and broadcasts to local clients
func listenForBroadcasts() {
    sub := redisClient.Subscribe(ctx, "websocket:broadcast")
    for msg := range sub.Channel() {
        for client := range localClients {
            client.WriteMessage(websocket.TextMessage, []byte(msg.Payload))
        }
    }
}
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `request_timeout` | duration | 0 (none) | 30s | Maximum time to wait for server response |
| `connect_timeout` | duration | 0 (none) | 5s | Maximum time for TCP connection establishment |
| `read_timeout` | duration | 0 (none) | 30s | Maximum time to wait for server to send response headers |
| `write_timeout` | duration | 0 (none) | 30s | Maximum time to send request body |
| `max_retries` | int | 0 | 3 | Number of retry attempts for failed requests |
| `retry_backoff` | string | none | exponential | Backoff strategy: exponential, linear, fixed |
| `retry_max_delay` | duration | none | 30s | Maximum delay between retries |
| `retry_on` | list | none | 5xx, timeout, connection-error | HTTP status codes / error types to retry on |
| `idempotency_key_ttl` | duration | none | 24h | TTL for stored idempotency keys |
| `keepalive_time` | duration | 2m (HTTP/2) | 30s | Interval for TCP keep-alive probes |
| `keepalive_timeout` | duration | 20s (HTTP/2) | 10s | Time to wait for keep-alive ACK |
| `max_idle_conns` | int | 100 | 100 | Max idle connections in pool |
| `max_idle_conns_per_host` | int | 2 | 10 | Max idle connections per host |
| `pool_timeout` | duration | 90s | 30s | Time to wait for a free connection from pool |
| `pool_recycle` | duration | 0 (none) | 1800s | Recycle connections after this age |
| `poll_interval` | duration | none | 5s | Interval for short-polling requests |
| `long_poll_timeout` | duration | none | 30s | Server hold time for long-poll requests |
| `sse_retry` | duration | none | 3000ms | SSE reconnect delay sent by server |
| `websocket_ping_interval` | duration | 0 (disabled) | 30s | WebSocket ping interval |
| `websocket_ping_timeout` | duration | 0 (disabled) | 10s | Timeout for pong response |
| `websocket_max_message_size` | int | 100MB | 10MB | Maximum WebSocket message size |

## 7. Integration Points

- **Depends on:** Every client-server communication depends on the network layer (TCP/UDP, TLS). HTTP-based patterns depend on an HTTP server or client library. WebSocket depends on an HTTP server capable of handling the `Upgrade` handshake. SSE depends on an HTTP server that supports streaming responses without buffering.

- **Used by:** Every application feature is delivered through client-server communication. API handlers serve HTTP clients. Background job systems use HTTP/gRPC to dispatch work. CI/CD pipelines use HTTP to communicate with deployment targets. Monitoring agents use various protocols (SNMP, HTTP, gRPC) to collect metrics from services.

- **Related to `foundation.protocols`:** The communication pattern (request-response, polling, SSE, WebSocket) is implemented over a specific protocol. SSE requires HTTP, WebSocket requires HTTP Upgrade, gRPC requires HTTP/2, and raw TCP enables custom protocols.

- **Related to `foundation.latency-bandwidth`:** Communication pattern choice directly determines observable latency and throughput. Request-response adds round-trip latency per interaction. SSE and WebSocket amortize connection establishment over many messages. Polling multiplies latency by the poll interval.

- **Related to `foundation.load-balancers`:** Load balancers distribute client-server connections across backend instances. They must understand the protocol to make intelligent routing decisions (e.g., sticky sessions for WebSocket, path-based routing for HTTP, health checks at the application layer).

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Request latency (p50, p99) | Prometheus | p99 > 1s → warn, p99 > 3s → page | Profile slow endpoints |
| Request rate (RPS) | Prometheus | > 2x baseline → warn | Traffic anomaly |
| Error rate (4xx + 5xx) | Prometheus | > 1% → warn, > 5% → page | Check for client errors or backend failures |
| Active connections | Prometheus gauge | > 80% of limit → warn | Increase connection pool or add capacity |
| Connection pool wait time | Prometheus histogram | p99 > 100ms → warn | Increase pool size |
| Timeout rate | Prometheus counter | > 0.5% → warn | Fix slow backends, increase timeout |
| Retry rate | Prometheus counter | > 10% → warn | Upstream service degradation |
| SSE connection duration | Prometheus histogram | > 1 hour → warn | Check for leaked connections |
| WebSocket connection count | Prometheus gauge | > 80% of max → warn | Scale horizontally |
| Idempotency key collision rate | Custom metric | > 0 → warn | Check for client retry storms |
| Poll request count | Prometheus | Unusual spike → warn | Polling interval may be too aggressive |

Key log messages:
- `request timeout after 30s` — server or client exceeded deadline
- `connection pool exhausted` — all connections in use, new requests are queuing
- `idempotency key collision: <key>` — retry detected, returning cached result
- `WebSocket connection closed abnormally` — network issue, triggering reconnection
- `SSE client disconnected` — browser tab closed or network lost

## 9. Evolution / Version Tracking

The client-server model was formally described in the 1980s by the X Window System and later popularized by the web in the 1990s. Early web applications used synchronous HTTP exclusively — every page load was a full request-response cycle.

AJAX (1998, popularized 2005) enabled partial page updates by making HTTP requests from JavaScript without a full page reload. This created the first need for polling patterns, as there was no server-push mechanism in HTTP/1.1.

Comet (2006) introduced long-polling as a server-push approximation. Libraries like Atmosphere (Java) and Socket.IO (Node.js) implemented long-polling with automatic fallback to WebSocket when available.

WebSocket (RFC 6455, 2011) provided a standard, full-duplex, low-overhead protocol for real-time communication. It replaced Comet for most real-time use cases but required server infrastructure changes.

SSE (WHATWG Living Standard, ongoing) emerged as a simpler alternative to WebSocket for unidirectional server-push. It works over standard HTTP/1.1, requires no special proxy configuration, and is natively supported in all major browsers. It is now the recommended approach for server-to-client real-time updates (notifications, feeds, progress bars) unless bidirectional communication is needed.

gRPC (2015) introduced typed, streaming RPC over HTTP/2, enabling efficient bidirectional streaming for service-to-service communication with schema enforcement via Protocol Buffers.

The current frontier is WebTransport (draft standard, 2022), which combines QUIC transport with WebSocket-like streaming, enabling low-latency bidirectional communication with built-in reliability and unordered message delivery. It is supported in Chrome and Edge as of 2023 and is the future of browser-server real-time communication.

## 10. References

1. RFC 7231 — HTTP/1.1 Semantics and Content — https://datatracker.ietf.org/doc/html/rfc7231
2. RFC 6455 — The WebSocket Protocol — https://datatracker.ietf.org/doc/html/rfc6455
3. Server-Sent Events — WHATWG Living Standard — https://html.spec.whatwg.org/multipage/server-sent-events.html
4. RFC 9114 — HTTP/3 — https://datatracker.ietf.org/doc/html/rfc9114
5. gRPC Documentation — https://grpc.io/docs/
6. WebTransport — W3C Draft — https://www.w3.org/TR/webtransport/
7. High Performance Browser Networking — Ilya Grigorik — https://hpbn.co/
8. HTTP Socket.IO Documentation — https://socket.io/docs/v4/
