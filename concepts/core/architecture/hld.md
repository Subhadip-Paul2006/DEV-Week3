---
id: foundation.hld
category: foundation
owning_agent: F-02
maturity: stable
languages:
- any
tags:
- architecture
- microservices
- monolith
- layers
- deployment
- system-design
- distributed-systems
related:
- foundation.lld
- foundation.load-balancers
- foundation.proxies
- foundation.client-server
- foundation.scalability
domain: core
---

# High-Level Design (HLD)

## 1. Overview

High-Level Design (HLD) is the decomposition of an entire software system into its major components, the responsibilities of each component, the protocols they use to communicate, the data stores they share, and the deployment topology that runs them in production. It sits between product requirements (the "what") and Low-Level Design (the "how") and answers the question: *what are the boxes, what goes inside each box, and how do the boxes talk to each other?* HLD is the architectural artifact that determines whether a system can scale, whether it can be deployed independently, whether it survives the failure of a single node, and whether a team of 50 engineers can ship changes without colliding on every commit. A good HLD is technology-agnostic enough to outlive a single framework choice but specific enough that a new engineer can draw the diagram and find every component on day one.

## 2. Core Principles

1. **Components own one bounded context** — each service, module, or tier must have a single, well-defined responsibility; a component that does two unrelated things is a candidate to be split.
2. **Communication contracts are explicit and versioned** — every interface between components is a published contract with a schema, a version, and a backward-compatibility policy.
3. **Failure domains are scoped, not global** — the failure of one component must not cascade into a system-wide outage; isolation is a first-class design concern, not an afterthought.
4. **The data model is the architecture** — components are defined by the data they own; if two services can mutate the same row, the architecture is wrong, not the code.
5. **Deployment topology reflects the design** — if the production diagram does not match the design diagram, the design is fiction.
6. **No shared mutable state across services** — shared mutable state forces coupling; replicas of state must be eventual, not synchronous.
7. **Every cross-network call has a timeout, a retry policy, and a circuit breaker** — distributed calls fail in ways local calls never do, and the failure mode must be designed, not discovered.

## 3. Sub-Concepts

### 3.1 Architectural Styles

**Definition:** A named, recurring decomposition strategy for an entire system. Each style prescribes how components are organized, how they communicate, and how state is shared.

**Why it matters:** Picking the wrong style is the single most expensive mistake in system design — it costs more to migrate from a monolith to microservices than to build the system twice.

**Implementation patterns:**

- **Layered (N-tier)** — presentation → application/business → persistence → database. Synchronous, in-memory function calls between layers. Each layer depends only on the layer below it.
- **Microservices** — many small services, each owning one bounded context and one data store, communicating over the network via REST/gRPC/async events. Independently deployable.
- **Modular Monolith** — single deployable unit, but the code is organized into modules with strict internal boundaries, enforced by package managers (Java modules, Go internal/, Python namespace packages). Migration path to microservices if modules outgrow the monolith.
- **Event-Driven** — services publish events to a broker (Kafka, RabbitMQ, NATS); consumers subscribe and react asynchronously. Decouples producers from consumers.
- **CQRS (Command-Query Responsibility Segregation)** — separate write model from read model. Writes go through a command handler that updates a normalized store; reads hit a denormalized projection.
- **Event Sourcing** — store every state change as an immutable event; current state is derived by replaying events. Powerful audit trail and time-travel debugging.
- **Pipe-and-Filter (Pipeline)** — data flows through a chain of independent transforms (Unix pipes, AWS Step Functions, Apache Beam). Each filter does one thing.
- **Microkernel (Plugin)** — a minimal core provides the lifecycle; features are plugins loaded at runtime (Eclipse IDE, VS Code, OSGi).
- **Serverless / Function-as-a-Service** — functions triggered by events, managed by a cloud provider. Stateless, short-lived, billed per invocation.
- **Space-Based (GigaSpaces, Hazelcast)** — processing happens in-memory on a grid of nodes; avoids the database as a bottleneck at extreme scale.

**Common mistakes:**

- Choosing microservices for a 3-person team with 10 users — operational overhead exceeds the scaling benefit.
- Choosing a modular monolith but allowing modules to import each other's internal packages freely.
- Choosing event-driven without an idempotency strategy — duplicate events corrupt state.
- Mixing styles inside one component (a "microservice" that publishes events and writes directly to another service's database).

**Scanner signals:**

- Presence: existence of multiple deployable artifacts (Dockerfiles per service, Helm values per service, serverless.yml, multiple `package.json` with distinct names).
- Presence: service mesh sidecar (Linkerd/Consul service mesh), message brokers in `package.json`/`requirements.txt`/`go.mod`.
- Absence: single deployable artifact for a system described as "microservices" — the design and reality are misaligned.

**Tradeoffs:**

| Style | Strengths | Weaknesses | Best for |
|-------|-----------|------------|----------|
| Layered | Simple, easy to reason about | Single point of failure, scales as a unit | Small CRUD apps, admin tools |
| Microservices | Independent deployment, fault isolation, team autonomy | Operational complexity, distributed-system bugs, eventual consistency | Large teams, high-availability products |
| Modular Monolith | Easy deployment, can split later | Single deploy unit, can become a big-ball-of-mud | Early-stage startups, small teams |
| Event-Driven | Loose coupling, replayability, audit trail | Hard to debug, eventual consistency, broker becomes SPOF | Integrations, analytics, IoT |
| Serverless | Zero ops, scales to your unit, pay-per-use | Cold starts, vendor lock-in, limited runtime | Sporadic workloads, webhooks, glue code |

### 3.2 Component Decomposition and Bounded Contexts

**Definition:** The act of drawing the lines between components. Each component owns one bounded context (a term from Domain-Driven Design) — a consistent vocabulary and a consistent model of one slice of the business domain.

**Why it matters:** Without bounded contexts, two teams end up with two different meanings of "customer" — marketing's customer (a lead) vs. billing's customer (a paying account). The clash becomes a bug at the integration boundary.

**Implementation patterns:**

- **Domain-Driven Design (DDD) bounded contexts** — identify subdomains (core, supporting, generic) and draw context maps between them. Each context has its own ubiquitous language.
- **Business Capability Decomposition** — components mirror business capabilities (Order Management, Inventory, Shipping), not technical layers (DB Layer, API Layer).
- **Strangler Fig Pattern** — gradually replace a legacy system by placing new components alongside it and routing traffic incrementally.
- **Bulkhead Pattern** — isolate resources (thread pools, connection pools) per component so one failing component cannot exhaust shared resources.

**Common mistakes:**

- Decomposing by technical layer (one service for "all REST APIs", one for "all databases") — this is a distributed monolith and is worse than a real monolith.
- Two services writing to the same database table — neither owns the data, both can corrupt it.
- Contexts that are too small ("UserService with one method") — operational cost exceeds the benefit.

**Scanner signals:**

- Positive: distinct top-level directories per bounded context with their own `Dockerfile`, `package.json`, deployment manifest.
- Negative: a service that imports models from another service's internal directory (not from a shared library) — bounded context violation.

### 3.3 Communication Styles Between Components

**Definition:** The mechanism by which components exchange data. Each style has a different latency, reliability, and coupling profile.

**Why it matters:** Communication choice determines the failure modes of the system. Synchronous calls form failure cascades; asynchronous messaging trades latency for isolation.

**Implementation patterns:**

- **Synchronous request-response (REST, gRPC, SOAP, GraphQL)** — caller blocks waiting for reply. Tight temporal coupling. Use for read paths where latency matters and failure must surface to the caller.
- **Asynchronous messaging (Kafka, RabbitMQ, NATS, SQS)** — caller publishes, returns immediately; consumer processes later. Loose coupling. Use for write paths, fan-out, integration between teams.
- **Event streaming (Kafka, Kinesis, Pulsar)** — durable, ordered, replayable log of events. Use when consumers need to reprocess history or join multiple event streams.
- **Pub/Sub (Redis Pub/Sub, Google Pub/Sub, SNS)** — fire-and-forget broadcasts. Use for notifications, cache invalidation hints.
- **Shared database** — two services read/write the same tables. Avoid — this is the most common distributed-monolith smell.
- **Remote procedure call (RPC) over long-lived connections (gRPC, Thrift, Apache Avro)** — typed, binary, supports streaming. Use for internal service-to-service where performance matters.

**Common mistakes:**

- Synchronous chains (`A → B → C → D`) — a single slow link stalls the entire request and the failure domain is the whole chain.
- Async messaging without idempotency — duplicate messages corrupt state.
- Synchronous calls inside a request that does not need an immediate reply — wastes latency, increases failure surface.

**Scanner signals:**

- Presence: `requests.post`, `fetch(`, `grpc.Dial`, `channel.queue_declare`, `kafka.producer`, `@Async` annotation, `produce`/`consume` keywords.
- Absence of timeouts on synchronous calls — almost always a bug.
- Negative: a service that imports a database client pointing to another service's database — the "shared database" anti-pattern.

**Tradeoffs:**

| Style | Latency | Coupling | Reliability | When to use |
|-------|---------|----------|-------------|-------------|
| Sync REST | Low | Tight | Caller sees failure | Reads, user-facing requests |
| gRPC | Very low | Tight | Caller sees failure | Internal service mesh |
| Async message | Higher | Loose | Decoupled | Writes, cross-team, fan-out |
| Event stream | Higher | Very loose | Replayable | Analytics, audit, integration |

### 3.4 Data Architecture

**Definition:** Where data lives, who owns it, how it is replicated, and how it flows between components.

**Why it matters:** Data ownership conflicts are the #1 source of cross-service bugs. Two services writing to the same row is the database equivalent of a race condition; the entire team feels the consequences.

**Implementation patterns:**

- **Database per Service** — every service has its own private database. No cross-service joins; if you need it, use an event-driven replica or an API call.
- **Shared Database** — multiple services share a database. Smells like a distributed monolith. Avoid except for read-only reference data.
- **Saga Pattern** — a long-running business transaction is decomposed into a sequence of local transactions; compensating transactions roll back failures. Two variants: orchestration (central coordinator) and choreography (event-driven).
- **Outbox Pattern** — a service writes its database change and an outbound message in the same local transaction; a separate poller publishes the message to the broker. Guarantees at-least-once delivery without 2PC.
- **CQRS** — separate write and read models. Writes through one model, reads through another (often denormalized for query speed).
- **Event Sourcing** — store events, derive current state by folding.

**Common mistakes:**

- Cross-service joins via shared database — coupling is hidden in the schema.
- Two-phase commit (2PC) across services — coordinator failures cause indefinite locks. Use sagas instead.
- Missing outbox → lost messages on broker failure.

**Scanner signals:**

- Positive: each service has its own database connection string from a distinct secret; multiple `DATABASE_URL` env vars.
- Negative: one service connects to another's database by name — context leak.

### 3.5 Deployment Topology

**Definition:** The mapping of logical components to runtime instances — containers, pods, servers, regions.

**Why it matters:** Topology determines blast radius. A topology that co-locates critical and non-critical components in the same process fails together.

**Implementation patterns:**

- **Single instance** — one process running all components. Simplest, lowest cost, highest blast radius.
- **N replicas behind a load balancer** — stateless services scale horizontally.
- **Blue/Green** — two identical environments, switch traffic atomically. Zero-downtime deploys.
- **Canary** — new version receives 1–10% of traffic; promote or rollback based on metrics.
- **Rolling update** — replace instances one at a time.
- **Multi-region active/active** — multiple regions serve traffic simultaneously. Maximum availability, complex consistency.
- **Multi-region active/passive** — primary region serves, secondary is hot standby.
- **Edge deployment** — code runs at CDN edge nodes (Cloudflare Workers, Lambda@Edge) close to users.

**Common mistakes:**

- Single instance for a production system — no fault tolerance.
- Canary without automated rollback — manual rollback is too slow when metrics tank.
- Multi-region without conflict resolution — write conflicts silently corrupt data.

**Scanner signals:**

- Presence: `replicas:` field in Kubernetes manifests, `count:` in docker-compose, auto-scaling groups in Terraform.
- Absence: a system labeled "production" running with `replicas: 1` and no PDB.

### 3.7 Cross-Cutting Concerns

**Definition:** Capabilities that every component needs but that are not specific to any one component. They are either implemented once and reused, or duplicated everywhere (the wrong choice).

**Why it matters:** Cross-cutting concerns done badly — auth duplicated in every service with three different implementations — are how you end up with a security audit that takes six months.

**Examples:**

- Authentication / Authorization
- Logging / Tracing / Metrics
- Configuration management
- Secret management
- Service mesh sidecars (mTLS, retries, circuit breaking)
- API gateway (rate limiting, routing, auth)
- CI/CD pipeline
- Observability stack

**Implementation patterns:**

- **Sidecar pattern** — a helper container (Envoy, Istio) attaches to each service and handles auth, retries, metrics. Decouples cross-cutting from business logic.
- **Service mesh** — full sidecar network (Istio, Linkerd, Consul Connect) handling mTLS, traffic shaping, observability.
- **API Gateway** — single entry point for all clients; handles auth, rate limiting, routing, aggregation.
- **Shared library** — common code in a versioned library imported by all services. Risk: tight coupling to library releases.

**Scanner signals:**

- Presence: Istio sidecar injection annotations, Envoy filters, API Gateway config (`kong.yml`, `oas.yaml`).
- Absence: every service implementing its own JWT validation in three different ways — useless.

### 3.8 Quality Attributes and Tradeoffs

**Definition:** Non-functional requirements that the architecture must satisfy — availability, scalability, performance, security, maintainability, observability.

**Why it matters:** Architecture is the art of trading off one quality attribute against another. CAP theorem forces the choice between consistency and availability during a partition. Latency vs throughput vs cost is a three-way tradeoff that must be made consciously.

**Examples:**

- **Availability vs Consistency** — choose AP (eventual consistency) when downtime is unacceptable; choose CP (rejected writes) when stale reads are dangerous.
- **Latency vs Cost** — single-region is cheap and fast; multi-region is fast globally but operationally expensive.
- **Scalability vs Simplicity** — microservices scale better but cost more to operate.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Multiple service directories with independent `Dockerfile` | any | glob: `**/Dockerfile`, distinct `package.json`/`go.mod`/`requirements.txt` per dir | High |
| Kubernetes manifests referencing multiple `Deployment` / `StatefulSet` | any | regex: `kind:\s*Deployment`, `kind:\s*StatefulSet` | High |
| docker-compose with multiple `services:` entries | any | yaml: `services:` count > 1 | Medium |
| Service mesh sidecar injection annotation | any | regex: `sidecar.istio.io/inject:\s*"true"` | High |
| API gateway config file | any | filename: `kong.yml`, `oas.yaml`, `apisix.yaml`, `traefik.yml` | Medium |
| Message broker client imported | Python/TS/Go | regex: `from kafka import|import 'kafkajs'|github.com/segmentio/kafka-go|github.com/rabbitmq/amqp091-go` | High |
| gRPC service definition | any | file pattern: `**/*.proto` with `service` keyword | High |
| GraphQL schema file | any | file pattern: `**/*.graphql` with `type Query` | Medium |
| Outbox table in DB schema | SQL | regex: `CREATE TABLE.*outbox` | High |
| Saga orchestrator class/function | Python/TS/Go | regex: `class.*Saga|orchestrator|saga_step` | Medium |
| Helm chart per service | any | glob: `charts/*/Chart.yaml`, multiple `values.yaml` per chart | Medium |
| Terraform module per service | any | glob: `modules/*/main.tf` with distinct resources | Low |
| Independent CI workflow per service | any | glob: `.github/workflows/*.yml` > 1, each scoped to one service dir | Medium |
| Distributed tracing instrumentation | Python/TS/Go | regex: `opentelemetry|@opentelemetry|jaeger_client|otelgin` | High |
| Circuit breaker library imported | any | regex: `pybreaker\|polly\|sony/gobreaker\|resilience4j` | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Single `package.json` / `go.mod` / `pom.xml` for a "microservices" project | any | count: deployable manifests = 1 in a multi-service repo | High |
| No Dockerfile in repository | any | glob: no `**/Dockerfile` found | High |
| No deployment manifest (k8s, helm, terraform) | any | glob: no `**/*.yaml` under `k8s/`, `deploy/`, `infra/` | Medium |
| No message broker config but claim of "event-driven" | any | absence of `kafka`, `rabbitmq`, `nats` in deps combined with event-driven claim | High |
| No API gateway but multiple client-facing services exposed directly | any | absence of `kong`, `apisix`, `traefik`, `envoy` config with public ingress | Medium |
| Single shared `DATABASE_URL` env var imported by multiple services | any | env var used in > 1 service manifest | High |
| No tracing/metrics SDK imported in any service | any | absence of `prometheus_client`, `prom-client`, `promhttp`, `opentelemetry` | High |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Service has no `replicas:` field or `replicas: 1` in production | yaml | regex: `replicas:\s*1` in production manifests | High |
| No `readinessProbe` / `livenessProbe` defined | yaml | absence of `readinessProbe:` in Deployment | High |
| No `resources.requests` / `resources.limits` set | yaml | absence of `resources:` block | Medium |
| No `PodDisruptionBudget` for stateful or critical services | yaml | absence of `PodDisruptionBudget` for prod | Medium |
| Synchronous HTTP client with no `timeout` parameter | Python/TS/Go | regex: `requests.(get\|post)\([^)]*\)` without `timeout=` within args | High |
| Database connection without pool size limits | any | regex: `create_engine\|pool_size` missing or set to `None`/0 | High |
| No retry policy on inter-service calls | any | regex: `requests.(get\|post)\|`fetch(` without `retry` wrapper | Medium |
| Missing mTLS or auth between internal services | any | absence of `istio`, linkerd, JWT validation in mesh | Medium |
| Event handlers without idempotency key check | Python/TS/Go | regex: handler function without `idempotency_key` or `processed_event_id` | High |
| Shared database user across services with write permission | SQL/ORM | regex: same DB user in > 1 service config | High |
| Health endpoint returns 200 unconditionally | any | regex: `/health` returning `200` without dependency check | Medium |
| No circuit breaker on calls to remote services | any | absence of `pybreaker`, `gobreaker`, `polly` wrapping remote calls | Medium |

## 5. Anti-Patterns

#### Anti-Pattern: Distributed Monolith

**Description:**
```yaml
# Two services, but they share a database and call each other synchronously
# service-A/deployment.yaml
env:
  - name: DATABASE_URL
    value: "postgres://shared-db.example.com/orders"
# service-B/deployment.yaml
env:
  - name: DATABASE_URL
    value: "postgres://shared-db.example.com/orders"
```

**Why it's dangerous:** You get all the operational cost of microservices (network calls, distributed tracing, deployment coordination) with none of the benefits (independent scaling, fault isolation, team autonomy). A deploy of one service breaks the other. Worse than a monolith — at least a monolith has clear boundaries.

**Detection:** Multiple deployable units that share a database, or that import each other's internal code paths directly.

**Fix:** Give each service its own database. Communicate via events or API contracts. If you can't split the database, you're not really running microservices — collapse back to one service until you can.

#### Anti-Pattern: Sync Chain (a.k.a. Death by a Thousand Cuts)

**Description:**
```python
def handle_request(req):
    user = user_service.get_user(req.user_id)        # 50ms
    cart = cart_service.get_cart(user.id)            # 80ms
    inventory = inventory_service.check(cart.items)  # 120ms
    price = pricing_service.calculate(cart, user)    # 200ms
    return order_service.create(cart, price)         # 150ms
# 600ms p50, 3000ms p99, ANY link failure = full failure
```

**Why it's dangerous:** Latency is additive. Availability is multiplicative — five 99.9% services in series give you 95% end-to-end availability. One slow link stalls every request. One crashed link takes the system down.

**Detection:** Call graphs with depth > 3 synchronous hops. p99 latency dominated by sum of downstream p99s.

**Fix:** Shorten the chain (cache, merge services, denormalize). Make some hops asynchronous. Use bulkheads so one slow service can't exhaust shared threads. Add timeouts and circuit breakers at every hop.

#### Anti-Pattern: Single Point of Failure in a "Highly Available" System

**Description:**
```yaml
# Single replica in production with the comment "TODO: scale later"
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  replicas: 1   # <-- SPOF
```

**Why it's dangerous:** The comment never gets done. The pod dies during a node drain, the service is down for 10 minutes, the on-call engineer gets fired. Replicas are the cheapest reliability win in cloud computing.

**Detection:** Any `replicas: 1` in a non-dev environment. Any service without a `PodDisruptionBudget`.

**Fix:** Minimum `replicas: 2` for stateless services, `replicas: 3` for stateful. Add anti-affinity so replicas land on different nodes.

#### Anti-Pattern: Shared Database Between Services

**Description:**
```python
# "Order Service"
class OrderService:
    def create_order(self, user_id, items):
        # Direct write to the USER table in another service's database
        db.execute("UPDATE users SET last_order_id = %s WHERE id = %s", ...)
```

**Why it's dangerous:** The other service can change the schema without telling you. Migrations break silently. Locks taken by one service starve the other. You have two services but one source of truth — change to either affects both, and neither team owns the schema.

**Detection:** Service A's code references tables that Service B's migrations own. Cross-service joins via raw SQL. Two services with the same `DATABASE_URL`.

**Fix:** Give each service its own database. If Service A needs to update user data, it calls Service B's API or publishes an event that Service B consumes.

#### Anti-Pattern: 2PC / Distributed Transaction Across Services

**Description:**
```python
# WRONG: Coordinating a transaction across two databases
with db_a.begin() as tx_a, db_b.begin() as tx_b:
    tx_a.execute("INSERT INTO orders ...")
    tx_b.execute("INSERT INTO inventory ...")
    # If tx_b fails after tx_a commits... wait, neither committed yet
    # If the coordinator dies between prepaare and commit... indefinite lock
```

**Why it's dangerous:** The coordinator can fail mid-protocol and leave both transactions holding locks indefinitely. Recovery is manual. The "outbox pattern" and "saga pattern" were created specifically because of this.

**Detection:** Use of `XA transactions`, `prepare/commit` two-phase commit, distributed transaction coordinators in code.

**Fix:** Use the **Saga pattern** — local transactions + events + compensating transactions. Use the **Outbox pattern** for at-least-once delivery from a single service.

#### Anti-Pattern: No Timeout on Inter-Service Calls

**Description:**
```python
# WRONG: defaults to infinite wait
response = requests.get("http://inventory-service/stock/123")
```

**Why it's dangerous:** When the upstream service hangs, your thread pool fills with hung requests, your service stops responding to healthy traffic, and the outage cascades. The default `requests.get` timeout is *no timeout* — meaning your service can hang forever waiting for one slow call.

**Detection:** Any `requests.*`, `fetch(`, `client.Do(` without a `timeout=` argument within the same call or wrapped.

**Fix:**
```python
# CORRECT: explicit, short timeout plus retry wrapper
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3, status_forcelist=[502, 503, 504])
adapter = HTTPAdapter(max_retries=retry)
session.mount("http://", adapter)
session.mount("https://", adapter)

response = session.get(
    "http://inventory-service/stock/123",
    timeout=(3.0, 10.0),   # connect, read
)
```

#### Anti-Pattern: Tight Coupling via Shared Library of Business Logic

**Description:**
```python
# shared-lib/pricing.py — shared between OrderService and QuoteService
def calculate_price(user, items, promo_code):
    ...

# OrderService and QuoteService both `pip install shared-lib`
# Now both services must deploy the same version of pricing logic together
```

**Why it's dangerous:** The "shared library" becomes a deployment dependency. To change one calculation, you must deploy both services. Bugs in the library break both. You have microservices with synchronous coupling.

**Detection:** A shared library containing business logic (not just utilities) imported by multiple services.

**Fix:** Move business logic into one service and expose it via an API. Keep shared libraries to utilities (date formatting, logging helpers) — never business rules.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `replicas` | int | 1 | 3 (stateless), 5 (critical) | Number of pod replicas for a service |
| `readinessProbe.initialDelaySeconds` | int | 0 | 5–30 | Wait before first probe to allow startup |
| `readinessProbe.periodSeconds` | int | 10 | 5–10 | How often to probe |
| `readinessProbe.failureThreshold` | int | 3 | 3 | Failed probes before marking unready |
| `livenessProbe.timeoutSeconds` | int | 1 | 1–3 | Per-probe timeout |
| `resources.requests.cpu` | string | varies | 100m–500m | CPU reservation per pod |
| `resources.requests.memory` | string | varies | 128Mi–512Mi | Memory reservation per pod |
| `resources.limits.cpu` | string | unbounded | 1000m | CPU hard cap per pod |
| `resources.limits.memory` | string | unbounded | 512Mi–1Gi | Memory hard cap per pod |
| `PodDisruptionBudget.minAvailable` | int/string | 0 | 1 or 50% | Min pods during voluntary disruption |
| `HorizontalPodAutoscaler.minReplicas` | int | 1 | 2 | Min replicas under autoscaler |
| `HorizontalPodAutoscaler.maxReplicas` | int | 100 | 20–100 | Max replicas under autoscaler |
| `HorizontalPodAutoscaler.targetCPUUtilizationPercentage` | int | 80 | 60–70 | CPU % that triggers scaling |
| `http.client.timeout.connect` | seconds | varies | 3s | Connect timeout for outbound HTTP |
| `http.client.timeout.read` | seconds | varies | 10s | Read timeout for outbound HTTP |
| `http.client.retries.max` | int | 3 | 3 | Max retries for transient failures |
| `http.client.retries.backoff` | seconds | 0.3 | 0.3–1.0 | Exponential backoff base |
| `circuit_breaker.failure_threshold` | int | 5 | 5 | Failures before opening circuit |
| `circuit_breaker.recovery_timeout` | seconds | 30 | 30–60 | Time before half-open probe |
| `kafka.consumer.max.poll.records` | int | 500 | 100–500 | Max records per poll |
| `kafka.consumer.session.timeout.ms` | int | 10000 | 10000–30000 | Session timeout for group |
| `kafka.producer.acks` | string | "1" | "all" | Required acks for durability |

## 7. Integration Points

- **LLD** — HLD defines the boxes; LLD implements each box's internals. A service whose LLD doesn't match its HLD is a violation (e.g., HLD says "stateless" but LLD uses in-memory sticky sessions).
- **Load Balancers / Proxies** — the HLD deployment topology determines where load balancers sit (edge L7 vs. internal L4). Service meshes (Istio, Linkerd) provide mTLS, retries, and circuit breaking as HLD-level cross-cutting concerns.
- **Circuit Breaker** — HLD decisions determine which inter-service calls get breakers; breakers are implemented as LLD-level decorators but their configuration is HLD policy.
- **Caching** — HLD decides which services own which caches; cache invalidation strategy is a cross-service contract.
- **Security Fundamentals** — HLD defines security boundaries (DMZ, private VPC, security groups, WAF) and authentication topology (mTLS, JWT, OAuth).

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Service availability (5xx error rate) | Prometheus + alertmanager | > 1% for 5m → warn, > 5% for 2m → page | Roll back recent deploy; check upstream dependencies |
| End-to-end p99 latency | Prometheus / Grafana | > 1s for 5m → warn, > 3s for 2m → page | Profile slow links; check DB query performance |
| Request rate per service | Prometheus | — | Capacity planning baseline |
| Replication lag (DB replicas, Kafka consumers) | Prometheus | > 10s → warn, > 60s → page | Scale consumer; investigate slow queries |
| Pod restart count | kube-state-metrics | > 3 in 10m → false | Check `kubectl describe` for crash reasons |
| Circuit breaker open count | Prometheus | Any in 5m → warn | Check downstream health |
| Inter-service call failure rate | Prometheus | — | Watch for cascading failures |
| Saturation (CPU/memory) | Prometheus / cAdvisor | > 80% for 15m → warn | Scale out or scale up |
| Queue depth (Kafka lag, SQS) | Prometheus | > 10k backlog → warn | Scale consumers |
| HPA desired vs current replicas | kube-state-metrics | current < desired for 5m | Check scaling cooldown or resource limits |

**Log messages that must be emitted:**

- Service startup/shutdown with version, git SHA, configuration summary
- Every inter-service call with: target service, endpoint, status, latency_ms, retry_count
- Every database query exceeding a slow-query threshold (e.g., > 100ms)
- Every circuit-breaker state transition (closed → open, open → half-open, half-open → closed)
- Every message published/consumed with: topic, partition, offset, idempotency_key
- Every configuration reload with diff of changed keys

**Health indicators:**

- `/health/live` — process is running (cheap, no dependencies checked)
- `/health/ready` — process is ready to serve traffic (checks DB, broker, downstream critical services)
- `/health/startup` — process has finished initial load (for slow-starting services)

## 9. Evolution / Version Tracking

**The 2000s — Monolithic era:** Most systems were single-tier or three-tier applications, deployed to a single application server (WebLogic, JBoss). Scaling meant "buy a bigger box" (vertical scaling). Teams were organized by layer (UI team, DB team) — a structural anti-pattern that produced disconnected code.

**The 2010s — Microservices era:** Netflix, Amazon, and Google published seminal papers (the "microservices premium" essay, the "CALCO" discussion (CAP)), and the industry rapidly moved to microservice architectures. Service meshes (Istio, Linkerd), container orchestrators (Kubernetes), and immutable infrastructure (Terraform, Packer) matured in this period. Many organizations over-rotated — the "microservice premium" is real, and startups with 5 engineers often hurt themselves by adopting the style.

**The 2020s — Pragmatism and platform engineering:** After a decade of microservice proliferation, the industry rediscovered the **modular monolith** (Shopify, GitHub, Basecamp have all written publicly about this). Service meshes moved from "use Istio for everything" to "sidecars where you need them." Platform engineering teams emerged to provide internal developer platforms (IDPs) that abstract the operational complexity. Edge computing and serverless became mainstream for specific workloads (CDN-edge logic, event-driven glue).

**Emerging patterns:**

- **Cell-based architecture** — divide the system into independent "cells" (each cell is a self-contained stack). One cell's failure cannot affect others. Used by AWS, Slack, and large social platforms.
- **Choreographed sagas with outbox + CDC** — services write to outbox tables, Debezium captures changes, publishes to Kafka. Avoids polling, exactly-once semantics.
- **Service mesh lite** — Envoy as a library (Embebed), not a sidecar. Lower resource footprint than Istio sidecars.
- **Internal Developer Platforms (IDPs)** — Backstage, Humanitec, Kratix — abstract Kubernetes from app teams.

**Deprecated patterns:**

- **ESB (Enterprise Service Bus)** — a centralized broker that routes between services. Replaced by direct service-to-service calls + lightweight brokers.
- **CORBA / DCOM / Java RMI** — binary RPC frameworks from the 1990s. Replaced by REST, gRPC.
- **Single big database for all services** — the foundation of the distributed monolith anti-pattern.

## 10. References

- [Software Architecture Patterns — Mark Richards (O'Reilly)](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)
- [Microservices Premium — Simon Brown](https://simonbrown.je/) (and the talk at https://www.youtube.com/watch?v=5OjqUnUgubA)
- [Domain-Driven Design — Eric Evans](https://domainlanguage.com/ddd/)
- [Building Microservices — Sam Newman (O'Reilly, 2nd ed.)](https://samnewman.io/books/building_microservices_2nd_edition/)
- [Designing Data-Intensive Applications — Martin Kleppmann](https://dataintensive.net/)
- [The Twelve-Factor App](https://12factor.net/)
- [Kubernetes Documentation — Production-Grade Container Orchestration](https://kubernetes.io/docs/)
- [Istio Service Mesh Documentation](https://istio.io/latest/docs/)
- [AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/)
- [Microsoft Azure Architecture Center](https://learn.microsoft.com/en-us/azure/architecture/)
- [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework)
- [C4 Model for Visualising Software Architecture — Simon Brown](https://c4model.com/)
- [Architecture Styles — Microsoft Learn](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/)