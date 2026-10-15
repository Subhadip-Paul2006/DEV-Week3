---
id: foundation.protocols
category: foundation
owning_agent: F-16
maturity: stable
languages:
- any
tags:
- http
- grpc
- websocket
- tcp-udp
related:
- foundation.client-server
- foundation.proxies
- foundation.load-balancers
domain: core
---

# Protocols

## 1. Overview

A network protocol is a formalized set of rules that defines how data is formatted, transmitted, and received between networked systems. In system design, the choice of protocol directly determines the communication patterns available: request-response semantics, streaming capability, multiplexing, and error handling. HTTP enables stateless REST APIs, gRPC enables efficient typed RPC with streaming, WebSocket enables full-duplex real-time communication, and raw TCP/UDP enable low-level transport control. Every distributed system must select and configure protocols deliberately, because protocol mismatch at the boundary between two services is one of the most common and costly integration failures.

## 2. Core Principles

- **Protocol choice is an architectural commitment** — the protocol selected for an API surface constrains the client libraries, infrastructure requirements, and operational tooling for the lifetime of that interface.
- **Every protocol has a well-defined port assignment** — HTTP uses 80/443, gRPC uses 443, WebSocket upgrades from 80/443, MQTT uses 1883/8883. Using the wrong port triggers firewall failures and client connection errors.
- **Protocols define their own error semantics** — HTTP has status codes, gRPC has status codes in trailers, WebSocket has close codes, and raw TCP has no standard error signaling. The receiving layer must translate errors correctly.
- **TLS is the universal security layer** — regardless of the application protocol, transport encryption should be the default. HTTP becomes HTTPS, gRPC runs over h2c or TLS, WebSocket upgrades to `wss://`.
- **Protocols have framing boundaries** — HTTP delimits messages by headers and body, gRPC uses length-prefixed frames within HTTP/2 streams, WebSocket uses opcode-framed messages, and TCP is a raw byte stream with no inherent message boundaries. Application code must handle framing for stream-oriented protocols.
- **HTTP semantics are the common denominator** — REST APIs, gRPC-Web, and GraphQL all ultimately map to HTTP. Understanding HTTP status codes, headers, and body semantics is prerequisite knowledge for any protocol work.

## 3. Sub-Concepts

### 3.1 HTTP/1.1

**Definition:** The Hypertext Transfer Protocol version 1.1 is the foundational application-layer protocol of the web. It is text-based, request-response oriented, and header-driven. HTTP/1.1 introduced persistent connections via `Connection: keep-alive` and chunked transfer encoding, but is limited to one outstanding request per TCP connection (head-of-line blocking).

**Why it matters:** HTTP/1.1 is the universal protocol. Every web browser, API client, and proxy supports it. Understanding its semantics — status codes, headers, caching directives — is essential for debugging any web-based system.

**Implementation patterns:**

```python
# Python — HTTP/1.1 server with FastAPI (Uvicorn)
from fastapi import FastAPI, HTTPException, Header

app = FastAPI()

@app.get("/api/v1/users/{user_id}", status_code=200)
async def get_user(user_id: str, if_none_match: str | None = Header(default=None)):
    user = db.fetch_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ETag-based conditional response
    user_etag = f'"user-{user_id}-v{user.version}"'
    if if_none_match == user_etag:
        return Response(status_code=304)

    return {
        "id": user.id,
        "email": user.email,
        "version": user.version,
    }

@app.post("/api/v1/users", status_code=201)
async def create_user(user_data: UserCreate):
    user = db.create_user(user_data)
    return Response(
        status_code=201,
        headers={"Location": f"/api/v1/users/{user.id}"},
        content=json.dumps({"id": user.id}),
    )
```

```typescript
// TypeScript — HTTP/1.1 client with axios
import axios, { AxiosError } from 'axios';

const api = axios.create({
    baseURL: 'https://api.example.com',
    headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    },
    timeout: 10000, // 10s request timeout
    http2: false,   // Explicitly HTTP/1.1
});

async function getUser(userId: string) {
    try {
        const response = await api.get(`/api/v1/users/${userId}`, {
            headers: { 'If-None-Match': `"user-${userId}"` },
        });
        return response.data;
    } catch (error) {
        const axiosError = error as AxiosError;
        if (axiosError.response?.status === 404) {
            return null; // Not found — caller handles absence
        }
        if (axiosError.response?.status === 304) {
            // Not Modified — return cached version
            return getCachedUser(userId);
        }
        throw new Error(`API error: ${axiosError.response?.status}`);
    }
}
```

**Key HTTP/1.1 headers:**
- `Host`: Required in every request (RFC 7230); enables virtual hosting
- `Content-Type`: Media type of the request/response body (`application/json`, `application/x-www-form-urlencoded`)
- `Accept`: Media types the client can process
- `Authorization`: Credentials for authentication (`Bearer <token>`, `Basic <credentials>`)
- `Cache-Control`: Directives for caching (`no-cache`, `max-age=3600`, `private`)
- `ETag` / `If-None-Match`: Entity tags for conditional requests
- `Connection: keep-alive` / `close`: Connection management

**Common mistakes:**
- Not setting `Content-Type: application/json`, causing clients to misinterpret the response body.
- Returning `200 OK` for POST requests instead of `201 Created` with a `Location` header.
- Not handling `304 Not Modified` responses, causing unnecessary data transfer.

**Scanner signals:**
- Presence: `app.route`, `app.get`, `@app.get` (FastAPI/Flask), `express()`, `axios.create`, `fetch()`.
- Absence: No HTTP route definitions, no HTTP client configuration.
- Misconfiguration: `timeout: 0` (infinite), missing `Content-Type` header.

### 3.2 HTTP/2

**Definition:** HTTP/2 is a binary protocol that multiplexes multiple concurrent streams over a single TCP connection. It uses HPACK header compression to reduce overhead and introduces server push for proactive resource delivery.

**Why it matters:** HTTP/2 eliminates head-of-line blocking — if stream 3 is blocked, streams 1, 2, 4, 5, and 6 continue transmitting. This dramatically improves page load performance and is now required for HTTP/3 adoption.

**Implementation patterns:**

```go
// Go — HTTP/2 server with gRPC
// gRPC runs exclusively over HTTP/2
// Server must be configured with TLS (h2) or cleartext (h2c)
import (
    "crypto/tls"
    "net/http"
    "google.golang.org/grpc"
)

func main() {
    lis, _ := net.Listen("tcp", ":50051")

    // gRPC server — HTTP/2 over TLS
    s := grpc.NewServer(
        grpc.MaxConcurrentStreams(100),           // Limit concurrent streams
        grpc.KeepaliveParams(grpc.KeepaliveServerParams{
            MaxConnectionIdle:     5 * time.Minute,
            MaxConnectionAge:      30 * time.Minute,
            MaxConnectionAgeGrace: 5 * time.Minute,
            Time:                  2 * time.Minute,
            Timeout:               20 * time.Second,
        }),
    )
    pb.RegisterUserServiceServer(s, &userServer{})
    s.Serve(lis)
}
```

```nginx
# Nginx — HTTP/2 with TLS
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    # HTTP/2 specific: server push (push preload links)
    location / {
        proxy_pass http://backend:8080;
        http2_push_preload on;  # Push resources linked in Link headers
    }
}
```

```typescript
// TypeScript — HTTP/2 client with Node.js http2 module
import http2 from 'http2';
import { ClientHttp2Stream, ClientHttp2Session } from 'http2';

const session: ClientHttp2Session = http2.connect('https://api.example.com', {
    rejectUnauthorized: true,
});

// Multiple concurrent streams — no head-of-line blocking
const makeRequest = (path: string): Promise<http2.IncomingHttpHeaders> => {
    return new Promise((resolve, reject) => {
        const req = session.request({ ':path': path, ':method': 'GET' });

        req.on('response', (headers) => {
            resolve(headers);
            req.close();
        });

        req.on('error', reject);
        req.end();
    });
};

// Fire 10 concurrent requests — all share one TCP connection
const paths = Array.from({ length: 10 }, (_, i) => `/api/v1/users/${i}`);
const results = await Promise.all(paths.map(makeRequest));
```

**Common mistakes:**
- Serving HTTP/2 without TLS (`h2c`) to external clients — browsers require TLS for HTTP/2, and many proxies strip cleartext HTTP/2.
- Using HTTP/1.1-specific features like `Transfer-Encoding: chunked` with HTTP/2, which uses its own framing.
- Not configuring HPACK header table size, causing compression to be ineffective for large header sets.

**Scanner signals:**
- Presence: `http2: true` in Go `http.Server`, `listen 443 ssl http2` in Nginx, `ALPN` negotiation, `grpc` service definitions.
- Absence: No `http2` flag, only HTTP/1.1 configured.
- Misconfiguration: `http2` enabled without TLS for external traffic.

### 3.3 gRPC

**Definition:** gRPC is a high-performance, open-source universal RPC framework that uses Protocol Buffers as its interface definition language and HTTP/2 as its transport. It supports unary (request-response), server streaming, client streaming, and bidirectional streaming RPC patterns.

**Why it matters:** gRPC is the standard for internal service-to-service communication in microservices architectures. Its binary serialization (Protobuf) is significantly more compact than JSON, its code generation eliminates manual client/server boilerplate, and its streaming support enables real-time data flows.

**Implementation patterns:**

```protobuf
// proto/user_service.proto — Protocol Buffer definition
syntax = "proto3";

package user;

service UserService {
    // Unary RPC: request → single response
    rpc GetUser (GetUserRequest) returns (UserResponse);

    // Server streaming: request → stream of responses
    rpc ListUsers (ListUsersRequest) returns (stream UserResponse);

    // Bidirectional streaming
    rpc Chat (stream ChatMessage) returns (stream ChatMessage);
}

message GetUserRequest {
    string user_id = 1;
}

message UserResponse {
    string user_id = 1;
    string email = 2;
    string display_name = 3;
    int64 created_at = 4;
}
```

```python
# Python — gRPC server
import grpc
from concurrent import futures
import user_pb2
import user_pb2_grpc

class UserServiceServicer(user_pb2_grpc.UserServiceServicer):
    def GetUser(self, request, context):
        user = database.get_user(request.user_id)
        if not user:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"User {request.user_id} not found")
            return user_pb2.UserResponse()

        return user_pb2.UserResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            created_at=int(user.created_at.timestamp()),
        )

    def ListUsers(self, request, context):
        for user in database.list_users(limit=request.limit):
            yield user_pb2.UserResponse(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
            )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()
```

```go
// Go — gRPC client with retry and load balancing
package main

import (
    "google.golang.org/grpc"
    "google.golang.org/grpc/credentials/insecure"
    "google.golang.org/grpc/balancer/roundrobin"
    "google.golang.org/grpc/resolver"
    "google.golang.org/grpc/health"
    pb "example.com/proto/user"
)

func main() {
    // Round-robin load balancing via DNS
    resolver.SetDefaultScheme("dns")
    conn, err := grpc.Dial(
        "dns:///user-service:50051",
        grpc.WithTransportCredentials(insecure.NewCredentials()),
        grpc.WithDefaultServiceConfig(`{"loadBalancingConfig":[{"ROUND_ROBIN":{}}]}`),
    )
    if err != nil {
        log.Fatalf("failed to connect: %v", err)
    }
    defer conn.Close()

    client := pb.NewUserServiceClient(conn)

    // Unary call with retry
    resp, err := client.GetUser(ctx, &pb.GetUserRequest{UserId: "123"})
    if err != nil {
        log.Printf("GetUser failed: %v", err)
        return
    }
    log.Printf("User: %s <%s>", resp.DisplayName, resp.Email)
}
```

**gRPC status codes:** `OK` (0), `CANCELLED` (1), `INVALID_ARGUMENT` (3), `DEADLINE_EXCEEDED` (4), `NOT_FOUND` (5), `ALREADY_EXISTS` (6), `PERMISSION_DENIED` (7), `RESOURCE_EXHAUSTED` (8), `FAILED_PRECONDITION` (9), `ABORTED` (10), `UNIMPLEMENTED` (12), `INTERNAL` (13), `UNAVAILABLE` (14), `DATA_LOSS` (15), `UNAUTHENTICATED` (16).

**Common mistakes:**
- Mixing Protobuf versions between client and server without backward compatibility rules — field number reuse breaks deserialization.
- Using gRPC directly in browser applications — browsers cannot make raw gRPC calls; gRPC-Web is required with an Envoy transcoding proxy.
- Not setting gRPC deadlines, causing server resources to be held indefinitely by slow clients.

**Scanner signals:**
- Presence: `.proto` files, `protoc` generated imports, `grpc.Server()`, `add_*Servicer_to_server`, `pb.Register*`.
- Absence: No `.proto` files, no gRPC server/client code.
- Misconfiguration: `grpc.InsecureServerCredentials` in production, no `MaxRecvMsgSize` set (default 4MB, can be exhausted).

### 3.4 WebSocket

**Definition:** WebSocket is a full-duplex communication protocol that operates over a single TCP connection, initiated via an HTTP `Upgrade` handshake. Once established, both client and server can send messages at any time without the request-response overhead of HTTP.

**Why it matters:** WebSocket is the standard for real-time features: chat applications, live dashboards, collaborative editing, and notification systems. It eliminates the need for polling and reduces latency compared to Server-Sent Events for bidirectional communication.

**Implementation patterns:**

```typescript
// TypeScript — WebSocket server with ws library
import { WebSocketServer, WebSocket } from 'ws';

const wss = new WebSocketServer({ port: 8080, path: '/ws/v1/events' });

// Map of connected clients with their subscription channels
const subscriptions = new Map<string, Set<WebSocket>>();

wss.on('connection', (ws: WebSocket, req) => {
    const clientId = uuid();
    ws.send(JSON.stringify({ type: 'connected', clientId }));

    ws.on('message', (data: Buffer) => {
        try {
            const message = JSON.parse(data.toString());

            switch (message.type) {
                case 'subscribe':
                    const channel = message.channel;
                    if (!subscriptions.has(channel)) {
                        subscriptions.set(channel, new Set());
                    }
                    subscriptions.get(channel)!.add(ws);
                    ws.send(JSON.stringify({ type: 'subscribed', channel }));
                    break;

                case 'publish':
                    // Server-to-client broadcast within a channel
                    const subs = subscriptions.get(message.channel) || new Set();
                    subs.forEach(client => {
                        if (client.readyState === WebSocket.OPEN) {
                            client.send(JSON.stringify({
                                type: 'message',
                                channel: message.channel,
                                payload: message.payload,
                            }));
                        }
                    });
                    break;

                case 'unsubscribe':
                    subscriptions.get(message.channel)?.delete(ws);
                    break;
            }
        } catch (err) {
            ws.send(JSON.stringify({ type: 'error', message: 'Invalid message format' }));
        }
    });

    ws.on('close', () => {
        // Clean up subscriptions
        subscriptions.forEach((clients) => clients.delete(ws));
    });

    ws.on('error', (err) => {
        console.error(`WebSocket error for ${clientId}:`, err.message);
    });
});
```

```python
# Python — WebSocket client with websockets library
import asyncio
import websockets
import json

async def connect_and_subscribe():
    uri = "wss://api.example.com/ws/v1/events"
    async with websockets.connect(uri) as websocket:
        # Subscribe to price updates channel
        await websocket.send(json.dumps({
            "type": "subscribe",
            "channel": "price_updates",
            "symbols": ["BTC-USD", "ETH-USD"],
        }))

        # Receive messages continuously
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "message":
                print(f"Price: {data['symbol']} = {data['price']}")

asyncio.run(connect_and_subscribe())
```

**WebSocket close codes (standard):**
- `1000` — Normal closure
- `1001` — Going away (server shutting down)
- `1006` — Abnormal closure (connection lost)
- `1008` — Policy violation
- `1011` — Internal server error
- `1012` — Service restart
- `1015` — TLS handshake failure

**Common mistakes:**
- Using WebSocket for unidirectional server-to-client communication where Server-Sent Events would be simpler and more bandwidth-efficient.
- Not handling connection drops and reconnection, causing client applications to lose data during brief network interruptions.
- Storing WebSocket state in a single-process memory, making it impossible to scale horizontally across multiple server instances.

**Scanner signals:**
- Presence: `ws.Server`, `WebSocketServer`, `socket.io`, `aiohttp.web.WebSocketResponse`, `use(ws())` (FastAPI).
- Absence: No WebSocket upgrade handling, no `Upgrade: websocket` header processing.
- Misconfiguration: No `ping_interval` / `ping_timeout` configured (connections die silently), no message size limit.

### 3.5 TCP and UDP

**Definition:** TCP (Transmission Control Protocol) is a connection-oriented, reliable, ordered byte-stream transport protocol. UDP (User Datagram Protocol) is a connectionless, unreliable, unordered datagram protocol. Both operate at the transport layer (OSI Layer 4) and provide the foundation for all application-layer protocols.

**Why it matters:** TCP and UDP are the building blocks beneath HTTP, gRPC, and WebSocket. Understanding their characteristics — TCP's three-way handshake, congestion control, and retransmission vs. UDP's zero-overhead, no-delivery-guarantee model — is essential for designing systems that require fine-grained control over delivery semantics.

**Implementation patterns:**

```go
// Go — TCP server with custom protocol framing
package main

import (
    "bufio"
    "fmt"
    "net"
    "strings"
)

func main() {
    ln, _ := net.Listen("tcp", ":9090")
    fmt.Println("TCP server listening on :9090")

    for {
        conn, _ := ln.Accept()
        go handleConnection(conn)
    }
}

func handleConnection(conn net.Conn) {
    defer conn.Close()

    // Custom line-delimited protocol
    scanner := bufio.NewScanner(conn)
    scanner.Split(bufio.ScanLines)

    for scanner.Scan() {
        line := scanner.Text()
        parts := strings.SplitN(line, " ", 2)

        switch parts[0] {
        case "PING":
            conn.Write([]byte("PONG\n"))
        case "ECHO":
            conn.Write([]byte(fmt.Sprintf("ECHO:%s\n", parts[1])))
        default:
            conn.Write([]byte("ERR unknown command\n"))
        }
    }
}
```

```python
# Python — UDP server for low-latency metrics collection
import socket
import struct
import time

# Custom binary protocol: 4-byte sequence + 8-byte timestamp + N-byte payload
PROTO_MAGIC = b'\xde\xad\xbe\xef'

def handle_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 5140))

    while True:
        data, addr = sock.recvfrom(65535)  # Max UDP payload
        if len(data) < 16:
            continue  # Too short

        magic = data[:4]
        if magic != PROTO_MAGIC:
            continue  # Invalid packet

        seq = struct.unpack('!I', data[4:8])[0]
        ts = struct.unpack('!Q', data[8:16])[0]
        payload = data[16:]

        # Process metric without acknowledging (UDP is unidirectional)
        process_metric(seq, ts, payload)
```

```go
// Go — QUIC (UDP-based, reliable) client using quic-go
import (
    "github.com/quic-go/quic-go"
)

func main() {
    session, _ := quic.DialAddr(context.Background(), "server.example.com:4433",
        &tls.Config{InsecureSkipVerify: false},
        &quic.Config{},
    )

    // Open a bidirectional stream
    stream, _ := session.OpenStreamSync(context.Background())
    stream.Write([]byte("HELLO"))
    buf := make([]byte, 1024)
    stream.Read(buf)
    stream.Close()
    session.CloseWithError(0, "")
}
```

**TCP vs. UDP comparison:**

| Characteristic | TCP | UDP |
|---------------|-----|-----|
| Connection | Three-way handshake (SYN, SYN-ACK, ACK) | None — send datagrams directly |
| Reliability | Guaranteed delivery via retransmission | Best-effort, no retransmission |
| Ordering | Guaranteed in-order delivery | No ordering guarantee |
| Flow control | Sliding window, congestion control | None |
| Latency | Higher (handshake + retransmission overhead) | Lower (no connection state) |
| Use cases | HTTP, gRPC, SSH, databases | DNS, gaming, live video, QUIC |
| Port range | 0–65535 (well-known: 0–1023) | Same |

**Common mistakes:**
- Using TCP for latency-sensitive real-time applications where UDP would eliminate retransmission delay.
- Implementing custom TCP framing without length prefixes, causing message boundary ambiguity.
- Setting `SO_REUSEADDR` on UDP sockets without `SO_REUSEPORT`, causing unexpected packet routing in multi-process deployments.

**Scanner signals:**
- Presence: `net.Listen("tcp"`, `socket(AF_INET, SOCK_STREAM)`, `net.Listen("udp"`, `socket(AF_INET, SOCK_DGRAM)`, `quic-go`, `SOCK_DGRAM`.
- Absence: No socket creation code (application is purely HTTP-based).
- Misconfiguration: TCP `keepalive` disabled, UDP socket buffer too small (causes packet loss).

### 3.6 Protocol Version Negotiation

**Definition:** The mechanism by which client and server agree on which protocol version to use. Methods include ALPN (Application-Layer Protocol Negotiation) for TLS, the `Upgrade` header for HTTP/1.1-to-WebSocket, and API versioning in gRPC via package naming.

**Why it matters:** Version negotiation enables rolling upgrades where old and new versions of services coexist during deployment. Without it, protocol mismatches cause connection failures or silent data corruption.

**Implementation patterns:**

```nginx
# Nginx — ALPN negotiation for HTTP/2 and HTTP/1.1
server {
    listen 443 ssl http2;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # ALPN: advertise supported application protocols
    ssl_prefer_server_ciphers on;
    # Nginx handles ALPN automatically with http2 directive
    # Chrome/Firefox will negotiate h2 over TLS 1.2+
    # Older clients fall back to HTTP/1.1
}
```

```go
// Go — ALPN in custom TLS configuration
import "crypto/tls"

config := &tls.Config{
    MinVersion: tls.VersionTLS12,
    NextProtos: []string{"h2", "http/1.1"}, // Advertise HTTP/2 first
}

// Server ALPN callback — select protocol based on client preference
config.NextProtos = []string{"h2", "http/1.1"}
// When client supports both h2 and http/1.1, server selects h2 (first in list)
```

```python
# API versioning via Accept header (REST)
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

@app.get("/api/{version}/users/{user_id}")
async def get_user(version: str, user_id: str, accept: str = Header(default="application/json")):
    if version not in ("v1", "v2"):
        raise HTTPException(status_code=400, detail=f"Unsupported API version: {version}")

    if version == "v1":
        return {"id": user_id, "email": get_v1_user(user_id)}
    elif version == "v2":
        return {"id": user_id, "email": get_v2_user(user_id), "preferences": get_prefs(user_id)}
```

**Scanner signals:**
- Presence: ALPN configuration, `Upgrade` header handling, version-prefixed API paths (`/api/v1/`, `/api/v2/`), gRPC service package versioning.
- Absence: No version negotiation mechanism for evolving APIs.
- Misconfiguration: Hardcoded protocol version without fallback, removing old API versions without deprecation period.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| HTTP route definition (FastAPI, Flask, Express) | Python, TypeScript | AST: `@app.get\|@app.post\|app.get\|app.post` | High |
| Nginx `listen` directive with `ssl http2` | Config | regex: `listen\s+\d+\s+ssl\s+http2` | High |
| gRPC `.proto` file in project | Any | glob: `**/*.proto` | High |
| gRPC server registration (`add_*Servicer_to_server`) | Python, Go | AST: `add_.*Servicer_to_server\|grpc\.Server` | High |
| WebSocket server creation (`WebSocketServer`, `ws.Server`) | TypeScript, Python | AST: `new WebSocketServer\|ws\.Server\|websockets\.serve` | High |
| Raw TCP socket creation | Go, Python | regex: `net\.Listen\("tcp"\|socket\.AF_INET.*SOCK_STREAM` | High |
| UDP socket creation | Go, Python | regex: `net\.Listen\("udp"\|socket\.AF_INET.*SOCK_DGRAM` | Medium |
| `Upgrade: websocket` header handling | Any | regex: `Upgrade.*websocket\|upgrade.*websocket` | High |
| ALPN protocol advertisement | Config, Go | regex: `NextProtos\|alpn\|ssl_prefer_server_ciphers` | Medium |
| gRPC-Web or transcoding proxy config | YAML/TypeScript | regex: `grpc_json_transcoder\|grpc-web` | Medium |
| QUIC/HTTP3 configuration | Any | regex: `quic\|http3\|h3` | Medium |
| `grpc.Dial` or `grpc.NewClient` | Go | AST: `grpc\.Dial` | High |
| `grpc.insecure_channel` (Python) | Python | AST: `grpc\.insecure_channel` | Medium |
| WebSocket client creation | TypeScript | AST: `new WebSocket\|ws\.connect\|websockets\.connect` | High |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No network communication at all | Any | No socket creation, no HTTP client/server, no `grpc` imports | High |
| No TLS configuration for external services | Any | No `ssl_certificate`, `tls.Config`, or `https://` URLs | High |
| No protocol versioning for public APIs | Any | API paths lack version prefix (`/api/vN/`), no `Accept` version negotiation | Medium |
| No WebSocket upgrade handling for real-time features | Any | Real-time requirements detected in requirements doc but no WebSocket/SSE code | Medium |
| No health check endpoint | Any | No `/health`, `/healthz`, `/ready`, `/live` route | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| `grpc.insecure_channel` or `InsecureSkipVerify: true` | Python, Go | regex: `insecure_channel\|InsecureSkipVerify.*true` | High |
| HTTP/2 without TLS for external traffic | Nginx/Go | `http2` directive without `ssl` on external-facing server | High |
| WebSocket without `ping_interval` / `ping_timeout` | TypeScript, Python | `WebSocketServer` without `heartbeat` config | Medium |
| TCP `keepalive` disabled | Go | `KeepAlive: -1` on `net.TCPConn` | Medium |
| gRPC no deadline set (infinite timeout) | Go, Python | `context.Background()` used without timeout for gRPC calls | High |
| API version in path is `v0` or missing | Any | Path pattern `/api/[^v]` or `/api/v0/` | Medium |
| TLS 1.0/1.1 enabled | Config | `ssl_protocols` includes TLSv1 or TLSv1.1 | High |
| UDPhardcoded to MTU-unsafe size | Any | `recvfrom(65535)` is fine, but `send()` with > 1500 bytes on path MTU-sensitive network | Low |
| WebSocket message size unlimited | TypeScript | `maxPayload` not set in `WebSocketServer` options | Medium |

## 5. Anti-Patterns

### Anti-Pattern: HTTP API Without Content-Type

**Description:**
```python
# Flask — returning data without Content-Type header
@app.route('/api/users')
def get_users():
    users = db.query(User).all()
    return json.dumps([u.to_dict() for u in users])
    # Flask auto-sets Content-Type, but if using raw Response:
    # return Response(json.dumps(users))  # Content-Type defaults to text/html
```

**Why it's dangerous:** Clients that receive a response without `Content-Type: application/json` may interpret the body as HTML, triggering XSS when the response is rendered in a browser context, or may fail to deserialize the body entirely.

**Detection:** Scanner looks for HTTP response creation without explicit `Content-Type` header setting, or returns of raw strings/bytes where JSON is expected.

**Fix:**
```python
from flask import Response, json

@app.route('/api/users')
def get_users():
    users = db.query(User).all()
    return Response(
        json.dumps([u.to_dict() for u in users]),
        content_type='application/json',
    )
```

### Anti-Pattern: Blocking Event Loop in Async HTTP Handler

**Description:**
```python
# FastAPI — blocking the event loop with synchronous database call
from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/api/slow")
async def slow_endpoint():
    time.sleep(5)  # Blocks the entire event loop for 5 seconds
    # All other concurrent requests wait for this to complete
```

**Why it's dangerous:** An async framework like FastAPI runs on a single-threaded event loop. Any blocking call (synchronous I/O, CPU-bound computation, `time.sleep`) freezes the entire server. Under concurrent load, all requests queue behind the blocking call, causing latency spikes and connection timeouts.

**Detection:** Scanner looks for `time.sleep`, synchronous DB calls (`db.query` without `await` or `run_in_executor`), or CPU-intensive operations inside `async def` routes.

**Fix:**
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

@app.get("/api/slow")
async def slow_endpoint():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(executor, blocking_db_call)
    return {"status": "done"}

# Better: use an async database driver (asyncpg, asyncmy, motor)
```

### Anti-Pattern: WebSocket Without Reconnection Logic

**Description:**
```typescript
// Client — WebSocket that dies permanently on disconnect
const ws = new WebSocket('wss://api.example.com/ws/events');
ws.onmessage = (event) => console.log(JSON.parse(event.data));
// When the connection drops, the client never reconnects
// User loses all real-time updates until page refresh
```

**Why it's dangerous:** WebSocket connections are fragile — they drop on network interruptions, server restarts, and mobile handoffs. Without reconnection logic, the client permanently loses real-time data. In financial or operational systems, this can mean missing critical events.

**Detection:** Scanner looks for `WebSocket` client creation without a `close` or `error` handler that implements reconnection.

**Fix:**
```typescript
class ReconnectingWebSocket {
    private ws: WebSocket | null = null;
    private reconnectDelay = 1000;
    private maxReconnectDelay = 30000;
    private reconnectTimer: number | null = null;

    connect(url: string) {
        this.ws = new WebSocket(url);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectDelay = 1000; // Reset backoff
        };

        this.ws.onclose = (event) => {
            if (!event.wasClean) {
                console.log(`WebSocket disconnected (code ${event.code}), reconnecting in ${this.reconnectDelay}ms`);
                this.scheduleReconnect(url);
            }
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.ws?.close();
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(JSON.parse(event.data));
        };
    }

    private scheduleReconnect(url: string) {
        this.reconnectTimer = setTimeout(() => {
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
            this.connect(url);
        }, this.reconnectDelay);
    }
}
```

### Anti-Pattern: gRPC Without Deadline

**Description:**
```python
# gRPC client — no deadline on the RPC call
def get_user(user_id: str) -> UserResponse:
    stub = user_pb2_grpc.UserServiceStub(channel)
    # No context deadline — if server hangs, client hangs forever
    response = stub.GetUser(user_pb2.GetUserRequest(user_id=user_id))
    return response
```

**Why it's dangerous:** Without a deadline, a slow or unresponsive server holds the gRPC client connection indefinitely. This exhausts client resources (connection slots, thread pool) and can cascade into a full system stall.

**Detection:** Scanner looks for gRPC RPC calls where the context is created without a timeout (`context.Background()` or `context.TODO()` instead of `context.WithTimeout`).

**Fix:**
```python
import grpc
from concurrent import futures

def get_user(user_id: str, timeout: float = 5.0) -> UserResponse | None:
    stub = user_pb2_grpc.UserServiceStub(channel)
    try:
        response, call = stub.GetUser.with_call(
            user_pb2.GetUserRequest(user_id=user_id),
            timeout=timeout,
        )
        return response
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
            logging.warning(f"GetUser deadline exceeded for {user_id}")
            return None
        raise
```

### Anti-Pattern: TCP Protocol Without Length-Prefixed Framing

**Description:**
```go
// Go TCP server — sending variable-length messages without length prefix
func handleConnection(conn net.Conn) {
    scanner := bufio.NewScanner(conn)
    scanner.Split(bufio.ScanLines) // Delimits by newline

    for scanner.Scan() {
        line := scanner.Text()
        // What if the message contains a newline character?
        // Data corruption, message truncation, or concatenation
        processMessage(line)
    }
}
```

**Why it's dangerous:** Without explicit framing, the receiver cannot distinguish message boundaries. A message containing the delimiter character gets split or merged with adjacent messages. This causes silent data corruption that is extremely difficult to debug.

**Detection:** Scanner looks for TCP message handling without length-prefix framing (4-byte length header) or fixed-size message protocol.

**Fix:**
```go
func sendMessage(conn net.Conn, data []byte) error {
    // 4-byte big-endian length prefix
    length := uint32(len(data))
    if err := binary.Write(conn, binary.BigEndian, length); err != nil {
        return err
    }
    _, err := conn.Write(data)
    return err
}

func readMessage(conn net.Conn) ([]byte, error) {
    var length uint32
    if err := binary.Read(conn, binary.BigEndian, &length); err != nil {
        return nil, err
    }
    if length > 10*1024*1024 { // 10MB sanity limit
        return nil, fmt.Errorf("message too large: %d", length)
    }
    data := make([]byte, length)
    _, err := io.ReadFull(conn, data)
    return data, err
}
```

### Anti-Pattern: Protocol Version Mixing Without Compatibility Layer

**Description:**
```yaml
# Kubernetes — Service A (v1) calls Service B (v2) directly
# Service B removed the v1 API endpoint
# Service A sends requests to /api/v1/users
# B returns 404 or unexpected response shape
```

**Why it's dangerous:** Removing a protocol version without a deprecation period breaks all clients still on the old version. This causes cascading failures across the service graph.

**Detection:** Scanner checks for API version removal (endpoint deleted without version-prefixed dual-support), gRPC service field removal (breaking Protobuf changes), or WebSocket message format changes without version handshake.

**Fix:**
```python
# Graceful API version deprecation
@app.route("/api/v1/users/<user_id>", methods=["GET"])
@deprecated(reason="Use /api/v2/users/<user_id> instead. Deprecated: 2025-01-01, Removal: 2025-07-01")
def get_user_v1(user_id):
    # Return v1 format with deprecation warning header
    return jsonify({
        "id": user_id,
        "email": get_email_v1(user_id),
    }), 200, {"Sunset": "2025-07-01", "Deprecation": "true"}
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `ssl_protocols` | list | TLSv1 TLSv1.1 TLSv1.2 | TLSv1.2 TLSv1.3 | Enabled TLS versions (Nginx) |
| `ssl_ciphers` | string | (system default) | ECDHE+AESGCM:!aNULL:!MD5 | TLS cipher suite whitelist |
| `proxy_read_timeout` | duration | 60s | 30s | Backend read timeout (Nginx) |
| `keepalive_timeout` | duration | 75s | 60s | HTTP keep-alive timeout (Nginx) |
| `keepalive_requests` | int | 100 | 1000 | Max requests per keep-alive connection (Nginx) |
| `grpc.max_recv_msg_size` | int | 4194304 (4MB) | 10485760 (10MB) | Max gRPC receive message size |
| `grpc.max_send_msg_size` | int | Infinity | 10485760 (10MB) | Max gRPC send message size |
| `grpc.keepalive_time_ms` | duration | 2 hours | 120000 (2 minutes) | Client keep-alive ping interval (gRPC) |
| `grpc.keepalive_timeout_ms` | duration | 20s | 20000 (20s) | Keep-alive ping timeout (gRPC) |
| `grpc.max_concurrent_streams` | int | 100 | 100 | Max concurrent streams per HTTP/2 connection (Envoy) |
| `websocket.ping_interval` | duration | 0 (disabled) | 30s | WebSocket ping interval |
| `websocket.ping_timeout` | duration | 0 (disabled) | 10s | WebSocket ping response timeout |
| `websocket.max_payload` | int | 100MB | 10MB | Max WebSocket message size (ws library) |
| `tcp.keepalive` | bool | true | true | TCP keep-alive probes |
| `tcp.keepidle` | duration | 7200s | 300s | Idle time before TCP keep-alive probes |
| `tcp.keepintvl` | duration | 75s | 75s | Interval between TCP keep-alive probes |
| `tcp.user_timeout` | duration | 0 (system default) | 30000 (30s) | Max data queued in TCP before connection is closed |
| `udp.buffer_size` | int | system default | 425984 (416KB) | UDP socket receive buffer size |
| `alpn_protocols` | list | h2, http/1.1 | h2, http/1.1 | Application-Layer Protocol Negotiation list |
| `http2.max_concurrent_streams` | int | 128 | 100 | Max concurrent HTTP/2 streams per connection |

## 7. Integration Points

- **Depends on:** All application-layer protocols depend on the transport layer (TCP/UDP) and TLS for encryption. gRPC depends on Protobuf code generation at build time. WebSocket depends on an HTTP server capable of handling `Upgrade` requests.

- **Used by:** The API layer uses HTTP/1.1 or HTTP/2 for REST endpoints. Internal microservice communication typically uses gRPC. Real-time features (chat, notifications) use WebSocket. Metrics collection and gaming backends use UDP. Protocol translation proxies use multiple protocols simultaneously.

- **Related to `foundation.client-server`:** Protocols are the communication channel in client-server architectures. The choice of protocol (HTTP vs. gRPC vs. WebSocket) determines whether the architecture is request-response, streaming, or event-driven.

- **Related to `foundation.proxies`:** Proxies must be configured to correctly handle each protocol. An HTTP/1.1 proxy cannot transparently proxy gRPC without HTTP/2 support. A WebSocket proxy must handle the `Upgrade` handshake and then pass raw TCP frames without buffering.

- **Related to `foundation.load-balancers`:** Load balancers inspect protocol-specific fields (HTTP headers, gRPC service name, TLS SNI) to make routing decisions. Layer 4 load balancers distribute at the transport level regardless of protocol, while Layer 7 load balancers need protocol awareness.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| HTTP request rate | Prometheus | > 2x baseline → warn | Investigate traffic anomaly |
| HTTP error rate (4xx + 5xx) | Prometheus | > 1% → warn, > 5% → page | Check for bad requests or backend failures |
| HTTP p99 latency | Prometheus histogram | p99 > 1s → warn, > 3s → page | Check slow queries, backend saturation |
| gRPC error rate by status code | Prometheus | `UNAVAILABLE` > 1% → warn | Check backend health |
| gRPC p99 latency | Prometheus | > 500ms → warn | Profile gRPC handler |
| WebSocket connection count | Prometheus gauge | > 80% of limit → warn | Scale WebSocket servers |
| WebSocket message rate (msg/sec) | Prometheus | > capacity → warn | Add WebSocket instances |
| TLS handshake failures | Prometheus | Any → warn | Check certificate expiry |
| TLS version distribution | Prometheus | TLS 1.0/1.1 usage → warn | Enforce TLS 1.2+ |
| TCP connection backlog | Netdata / Prometheus | > 128 pending → warn | Tune `somaxconn` |
| UDP packet loss rate | Prometheus | > 0.1% → warn | Check network capacity |
| ALPN negotiation success rate | Prometheus | < 99% → warn | Check client protocol support |

Key log messages:
- `TLS handshake error: certificate verify failed` — certificate chain issue
- `HTTP/2 stream closed with error code 1 (CANCEL)` — client cancelled the request
- `gRPC error: UNAVAILABLE: connection closed` — backend connection lost
- `WebSocket closed abnormally (code 1006)` — connection dropped without close frame
- `TCP reset by peer` — backend actively rejected connection

## 9. Evolution / Version Tracking

HTTP/1.1, standardized in 1997 (RFC 2616), defined the request-response model that powers the internet. Its text-based format and head-of-line blocking became bottlenecks as web applications grew richer, leading to HTTP/2 in 2015 (RFC 7540), which introduced binary framing, multiplexing, and header compression. HTTP/2 dramatically improved performance but still relies on TCP, inheriting TCP's head-of-line blocking at the transport layer.

HTTP/3 (RFC 9114, 2022) replaces TCP with QUIC (UDP-based), eliminating transport-layer head-of-line blocking entirely. Major platforms (Cloudflare, Google, Facebook) have already adopted HTTP/3, and browser support is now universal.

gRPC, released by Google in 2015, popularized binary RPC with Protobuf and HTTP/2. It has become the de facto standard for internal service communication in Kubernetes-native architectures. gRPC-Web (2018) bridged the gap for browser clients by adding an intermediary transcoding layer.

WebSocket (RFC 6455, 2011) filled the real-time communication gap in browsers. While SSE (Server-Sent Events) offers a simpler unidirectional alternative, WebSocket's bidirectional nature remains essential for chat, gaming, and collaborative tools.

QUIC (standardized by IETF in 2021) is the emerging transport layer protocol. It combines TCP's reliability with UDP's low latency, adds built-in TLS 1.3, and enables fast connection migration (seamless handoff between WiFi and cellular). It is the foundation of HTTP/3 and is being adopted for VPNs (WireGuard) and database protocols (MySQL 8.0 over QUIC).

## 10. References

1. RFC 9110 — HTTP Semantics (2022) — https://datatracker.ietf.org/doc/html/rfc9110
2. RFC 7540 — HTTP/2 — https://datatracker.ietf.org/doc/html/rfc7540
3. RFC 9114 — HTTP/3 — https://datatracker.ietf.org/doc/html/rfc9114
4. gRPC Documentation — https://grpc.io/docs/
5. Protocol Buffers Documentation — https://protobuf.dev/
6. RFC 6455 — The WebSocket Protocol — https://datatracker.ietf.org/doc/html/rfc6455
7. RFC 9000 — QUIC: A UDP-Based Multiplexed and Secure Transport — https://datatracker.ietf.org/doc/html/rfc9000
8. WebSocket API — MDN — https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
9. High Performance Browser Networking (book) — Ilya Grigorik — https://hpbn.co/
