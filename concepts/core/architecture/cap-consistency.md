---
id: foundation.cap-consistency
category: foundation
owning_agent: F-10
maturity: stable
languages:
- any
tags:
- consistency
- availability
- partition-tolerance
- tradeoffs
related:
- foundation.db-scaling
- foundation.caching
- foundation.idempotency
domain: core
---

# CAP Consistency

## 1. Overview

The CAP theorem states that a distributed data store cannot simultaneously provide all three of: **Consistency** (every read receives the most recent write), **Availability** (every request receives a response, without guarantee that it contains the most recent write), and **Partition tolerance** (the system continues to operate despite an arbitrary number of messages being dropped or delayed by the network). In any real distributed system, a network partition will eventually occur. The designer must choose between sacrificing **Consistency** (CP: data is correct but some requests fail or return stale data) or sacrificing **Availability** (AP: every request returns a response, but it may be stale). CAP is not a binary switch — it is a spectrum of consistency models from strong consistency (linearizability) to eventual consistency, with causal consistency and session consistency in between. It exists because engineers must make intentional trade-offs; the wrong default for the wrong workload causes subtle bugs that are nearly impossible to debug in production.

## 2. Core Principles

- **Partition tolerance is non-negotiable.** Every distributed system over a network must handle partitions. The only question is whether you handle them gracefully (AP) or stop serving (CP). Choosing "no partitions" means choosing a single-node system — not a distributed one.
- **During a partition, you choose C or A.** When the network is healthy, you can have both. When a partition occurs, you cannot. Design your system with explicit partitions in mind: what does each node do when it can't reach the others?
- **Eventual consistency is not "eventually correct."** It is "guaranteed to converge if no new writes arrive." With a continuous write stream, convergence may never complete. Set SLAs on maximum staleness, not just "eventually."
- **Causal consistency is achievable with reasonable overhead.** If you only need "if I read X and then write Y, everyone sees X before Y" — causal consistency is the sweet spot. Implementable via vector clocks or version vectors.
- **Latency is inversely correlated with consistency.** Strong consistency requires synchronizing multiple replicas before returning, which adds network round-trips. Weaker consistency models return faster. Measure the cost in p99 latency, not just "fast" or "slow."
- **CAP is about data stores, not entire systems.** A system may be CP for its user database and AP for its product catalog. Design per-datastore, not per-application.
- **Choose your consistency model per operation, not per system.** A shopping cart can be session-consistent (the user's reads see their own writes) while inventory must be strongly consistent (you cannot sell the last item to two buyers).

## 3. Sub-Concepts

### 3.1 The Three Properties (C, A, P) — Formal Definitions

**Consistency (C):** Every read returns the most recent write or an error. Formalized as *linearizability* (also called atomic consistency): all operations appear to execute in a total order consistent with real-time. If write W completes before read R begins, R must see W (or a later write).

**Availability (A):** Every request receives a (non-error) response, without the requirement that it contains the most recent version of the information. The system guarantees a response within a reasonable time.

**Partition tolerance (P):** The system continues to operate despite an arbitrary number of messages being dropped or delayed between nodes. The network may fail to deliver some messages or deliver them late.

**Why it matters:** The formal definitions expose what engineers get wrong: "available" does not mean "fast" or "successful write" — it means "non-error response." "Consistent" does not mean "the data is there" — it means "the most recent write."

### 3.2 CP Systems — Sacrifice Availability

**Definition:** A CP system sacrifices availability during a partition: some nodes may stop accepting writes to preserve data consistency. The canonical example: a replicated database where the primary cannot reach a majority of replicas — it steps down and rejects writes until quorum is restored.

**Examples:**
- **MongoDB replica set** — when primary loses majority, it steps down. Writes are rejected. Reads can continue from secondaries (but they may be stale) — MongoDB calls this "read preference" and defaults to `primary` (consistent but unavailable during partitions).
- **HBase / ZooKeeper** — require quorum for writes. Lose majority = write rejection.
- **Google Spanner (by default)** — TrueTime API + Paxos means every write requires a quorum commit. During partitions, unpartitioned shards continue; partitioned shards pause writes.
- **PostgreSQL with synchronous replication** — `synchronous_commit=on` means the primary waits for at least one synchronous standby to confirm. If that standby is partitioned, writes hang (not rejected — but effectively unavailable).

**Trade-offs:** Strong consistency guarantees. Users get correct data. During partitions, writes may be rejected (503) or may time out. Engineer must choose: accept 503s, or weaken consistency.

### 3.3 AP Systems — Sacrifice Consistency

**Definition:** An AP system sacrifices consistency during a partition: every node continues accepting reads and writes, but different nodes may return different data. The system reconciles conflicts when the partition heals.

**Examples:**
- **Amazon DynamoDB (default)** — each partition has 3 replicas; any replica can serve reads and accept writes. Reconciliation via vector clocks (Dynamo style) or last-write-wins (DynamoDB, using a server-side timestamp).
- **Cassandra** — tunable consistency per query. Writes are always accepted by the local node (local quorum = 1). During partition, different nodes have different data. Read-repair merges on next read.
- **DNS** — the quintessential AP system. Cached entries may be stale. Eventually all caches expire and the correct value propagates. DNS has never been unavailable — but it has been incorrect.
- **Riak** — multi-master, vector clocks for conflict resolution. Every node accepts writes.

**Trade-offs:** Always available. Reads and writes never fail (locally). Conflicts must be resolved. Last-write-wins is simple but can lose data. Vector clocks are precise but require application-level merge logic.

### 3.4 Consistency Models — Full Spectrum

| Model | Guarantee | Read Latency | Write Latency | Partitions | Example Systems |
|---|---|---|---|---|---|
| Linearizability (strong) | All reads see latest write | Higher (quorum read) | Higher (quorum write) | Reject or downgrade | Spanner, Zookeeper |
| Sequential consistency | All operations appear in a total order | Medium | Medium | Reject | Some CP systems |
| Causal consistency | Causally related writes seen in order | Lower | Lower | Continue; track causality | DynamoDB with vector clocks |
| Session consistency | User's own writes visible in their session | Lower | Lower | Continue per-session | DynamoDB (per-client monotonic), Redis |
| Eventual consistency | All replicas converge eventually | Lowest | Lowest | Continue fully | Cassandra, DynamoDB default, DNS |

**Definitions of each model:**

**Linearizability:** The strongest model. Every operation appears to take effect instantaneously at some point between its start and end. Equivalent to having a single authoritative copy. Requires quorum reads AND quorum writes (or a consensus protocol like Paxos/Raft).

**Sequential consistency:** Operations appear in some sequential order; all processes see the same order. Does not require real-time ordering — a read can see a write that started after it.

**Causal consistency:** If operation A causally precedes operation B (A → B, meaning B reads A's write or follows A in the same session), then all processes see A before B. Concurrent operations (no causal link) may appear in any order. Vector clocks or version vectors are the standard implementation.

**Session consistency:** A stronger form of eventual consistency within a single client session. Once a client writes X, all subsequent reads in the same session see X. Monotonic reads (client always sees newer or equal data) and monotonic writes (client's writes are applied in order) are the sub-guarantees.

**Eventual consistency:** If no new writes are made, all replicas will eventually converge. No guarantees about when "eventually" is. Staleness can range from milliseconds to hours depending on replication lag, anti-entropy intervals, and write frequency.

### 3.5 Quorum Reads and Writes

**Definition:** In a replicated system with N replicas, a write must be confirmed by W replicas, and a read must contact R replicas. The quorum condition is `W + R > N` — this ensures at least one replica has seen the latest write.

**Why it matters:** Quorums are the building block of tunable consistency. Violating `W + R > N` means reads may return stale data even when all replicas are reachable.

**Implementation:**
```python
# DynamoDB-style: tunable per-request consistency
import boto3

dynamodb = boto3.client('dynamodb')

# Strongly consistent read (W+R > N with N=3, W=3, R=1)
resp = dynamodb.get_item(
    TableName='inventory',
    Key={'product_id': {'S': 'SKU-12345'}},
    ConsistentRead=True,        # reads from leader only
)

# Eventually consistent read (default, cheaper)
resp = dynamodb.get_item(
    TableName='inventory',
    Key={'product_id': {'S': 'SKU-12345'}},
    ConsistentRead=False,       # reads from any replica
)
```
```go
// Cassandra-style: tunable consistency per query
import "github.com/gocql/gocql"

cluster := gocql.NewCluster("cassandra-1", "cassandra-2", "cassandra-3")
cluster.Keyspace = "inventory"
cluster.Consistency = gocql.Quorum  // default

// Strong read: QUORUM (majority of replicas)
if err := session.Query(
    "SELECT stock FROM inventory WHERE product_id = ?",
    "SKU-12345",
).Consistency(gocql.Quorum).Exec(); err != nil {
    return err
}

// Fast read: ONE (any replica)
if err := session.Query(
    "SELECT name FROM products WHERE product_id = ?",
    "SKU-12345",
).Consistency(gocql.One).Exec(); err != nil {
    return err
}
```

**Configuration table:**

| N (Replicas) | W (Write quorum) | R (Read quorum) | Behavior |
|---|---|---|---|
| 3 | 2 | 2 | `2+2>3` → Strong. 1 replica can be stale. |
| 3 | 1 | 1 | `1+1≤3` → Weak. Stale reads possible. |
| 3 | 3 | 1 | `3+1>3` → Strong reads, slow writes. |
| 5 | 3 | 3 | `3+3>5` → Strong. Tolerates 2 replica failures. |
| 5 | 2 | 2 | `2+2≤5` → Weak. Fast, but stale reads likely. |

**Scanner signals:** `ConsistentRead`, `Consistency(gocql.Quorum/All/LocalQuorum)`, `write_concern` (MongoDB), `read_concern` (MongoDB), `min_insync_replicas` (Kafka), `acks=all` (Kafka), quorum config in Raft/Paxos implementations.

### 3.6 Conflict Resolution (Last-Write-Wins, Vector Clocks, CRDTs)

**Definition:** When two nodes accept conflicting writes during a partition (both wrote X=1 and X=2), the system must resolve the conflict when the partition heals.

**Last-Write-Wins (LWW):** The write with the latest timestamp wins. Simple, requires no merge logic. Loses data if clock skew is present (NTP drift or manual clock changes). Used by DynamoDB (server-side timestamp, not client-side — mitigates clock skew but doesn't eliminate it).

**Vector clocks:** Each node maintains a vector of `{node_id: counter}`. If `VC(A) < VC(B)` (A's counters are a subset of B's), B causally follows A and wins. If neither dominates, there is a conflict — the application must merge. Used by Riak, Voldemort.

**CRDTs (Conflict-free Replicated Data Types):** Data structures with mathematical merge functions that are guaranteed to converge. No conflict detection needed — merge always produces the same result. Examples: OR-Set (add-wins set), G-Counter (grow-only counter), PN-Counter (positive-negative counter). Used by Riak (Riak DT), Akka Distributed Data, Redis Enterprise Active-Active.

**Why it matters:** Conflict resolution is where AP systems pay their tax. LWW is invisible but may silently lose writes. Vector clocks require application-level merge. CRDTs are mathematically safe but limited to specific data types.

**Scanner signals:** `VectorClock`, `last_write_wins`, `LWW`, `merge` function in data model, CRDT type names (`ORSet`, `GCounter`, `PNCounter`, `LWWRegister`), `conflict_resolution` config.

### 3.7 Session and Client-Side Consistency

**Definition:** Session consistency guarantees that within a single client session, reads see the client's own writes and reads are monotonically increasing (you never go backward). This is the minimum acceptable consistency for interactive applications.

**Implementation patterns:**
- **DynamoDB session tokens** — the response includes a `SessionToken`; including it in subsequent reads ensures the session sees its own writes.
- **Redis (single-master)** — reads from the master are strongly consistent; reads from replicas are eventually consistent. For session consistency, pin the session to the master or use `WAIT` command.
- **Cassandra** — `LOCAL_SERIAL` consistency for LWT (lightweight transactions using Paxos); `LOCAL_QUORUM` for normal session reads.

```python
# DynamoDB session consistency via session token
import boto3
dynamodb = boto3.client('dynamodb')

session_token = None
# Write
resp = dynamodb.put_item(
    TableName='cart',
    Item={'user_id': {'S': 'user-1'}, 'item': {'S': 'SKU-99'}},
    ReturnValues='ALL_OLD',
)
session_token = resp.get('SessionToken')

# Read with session token — sees own writes
resp = dynamodb.get_item(
    TableName='cart',
    Key={'user_id': {'S': 'user-1'}},
    ConsistentRead=False,   # cheaper
    SessionToken=session_token,
)
```

**Scanner signals:** `SessionToken` returned and re-sent; sticky session cookies; pinned connection to primary node; `WAIT` command in Redis code; `SERIAL` / `LOCAL_SERIAL` in Cassandra queries.

### 3.8 Anti-Entropy and Read Repair

**Definition:** Anti-entropy is the background process that reconciles divergent replicas. Read repair fixes inconsistencies when they are detected during reads: if a read from replica A returns X=1 and a read from replica B returns X=2, the system detects the conflict and repairs both replicas.

**Why it matters:** AP systems are not "eventually consistent by magic." They require active reconciliation: Merkle trees for efficient diffing (Cassandra), background repair tasks (Riak), or implicit read-repair on every read (DynamoDB). Without anti-entropy, replicas diverge forever.

**Scanner signals:** `anti_entropy`, `read_repair`, `MerkleTree`, `nodetool repair` (Cassandra), `repair_interval`, background reconciliation jobs.

### 3.9 Consistency in Message Queues

**Definition:** Message queues bring consistency concerns at the consumer level. Kafka guarantees per-partition ordering (causal within a partition) but not global ordering. RabbitMQ guarantees per-queue FIFO. SQS FIFO guarantees per-group ordering. A consumer reading from multiple partitions sees no cross-partition ordering guarantee.

**Why it matters:** If you process `order_created` and `order_paid` from different partitions, `order_paid` may arrive before `order_created`. The consumer must handle out-of-order events (buffer and sort by timestamp, or use a partition key).

**Scanner signals:** Partition key on producer; ordering key in Pub/Sub; FIFO queue declarations; out-of-order handling in consumer code (sorted merge, sequence-number check).

### 3.10 Consistency Monitoring and Observability

**Key metrics for consistency:**
- **Replica lag:** time difference between the latest write on the primary and the latest data visible on a replica. In MySQL replication: `Seconds_Behind_Master`. In Cassandra: `WriteLatency` vs `ReadRepairLatency`.
- **Staleness percentage:** % of reads that return data older than N seconds. Measured by comparing read timestamp with the latest write timestamp.
- **Conflict rate:** number of conflicting writes detected per second during anti-entropy or read-repair.
- **Consistency violations:** count of linearizability violations detected by Jepsen tests or production verification (if using a verification layer).
- **Quorum failure rate:** % of reads/writes that fail because the quorum cannot be formed (timeout or unreachable replicas).

**Scanner signals:** `seconds_behind_master`, `replica_lag`, `staleness`, `conflict_rate`, `read_repair_count`, `quorum_timeout` metrics in Prometheus.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Strong consistency flag in DB config | All | regex: `ConsistentRead\|synchronous_commit\|read_concern.*majority\|read_concern.*linearizable` | High |
| Quorum read/write config | All | regex: `QUORUM\|QUORUM\|All\|local_quorum\|majority\|w.*quorum` | High |
| Vector clock or version vector import | All | regex: `VectorClock\|version_vector\|version_vector` | Medium |
| CRDT type in data model | All | regex: `ORSet\|GCounter\|PNCounter\|LWWRegister\|GSet\|TwoPhaseSet` | High |
| `ConsistentRead=True` in DB call | Python | regex: `ConsistentRead\s*=\s*True` | High |
| `synchronous_commit` config in PostgreSQL | Config, SQL | regex: `synchronous_commit\s*=\s*(?:on\|remote_write\|remote_apply)` | High |
| `write_concern` set in MongoDB | All | regex: `writeConcern\|w.*majority\|w.*quorum` | High |
| Session token propagation | Python | regex: `SessionToken` in both request and response | Medium |
| `WAIT` command in Redis | Go, Python | regex: `WAIT\s+\d+\s+\d+` | Medium |
| Kafka `acks=all` with `min.insync.replicas` | Config | regex: `acks\s*[:=]\s*all\|min\.insync\.replicas\s*[:=]\s*[2-9]` | High |
| Read repair config | All | regex: `read_repair\|read_repair_chance` | Medium |
| Cassandra consistency level set per query | All | regex: `Consistency\(.*(?:QUORUM\|ALL\|SERIAL)` | High |
| Conflict resolution function | All | regex: `resolve_conflict\|merge\|conflict_resolver` | Medium |
| Anti-entropy / repair job | All | regex: `anti_entropy\|repair\|repair_interval\|nodetool.repair` | Medium |
| Replication factor > 1 | Config, SQL | regex: `REPLICAS\s*[>=]\s*[2-9]\|replication_factor\s*[:=]\s*[2-9]` | High |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Database with replication = 1 | SQL, Config | regex: `REPLICAS\s*=\s*1\|replication_factor\s*=\s*1` | High |
| No quorum on multi-replica system | All | heuristic: N>1 but no W/R quorum config found | Medium |
| Kafka producer with `acks=0` or `acks=1` | Config | regex: `acks\s*[:=]\s*[01]` | High |
| Reads from DB replica without consistency hint | All | AST: `read_replica` / replica connection used without `ConsistentRead` or similar flag | Medium |
| AP system (Cassandra/DynamoDB) with no conflict resolution | All | heuristic: conflict-handling code absent in DynamoDB/Cassandra project | Medium |
| Multi-master writes without merge logic | All | heuristic: >1 write endpoint for same data store, no `merge` or `conflict_resolver` | Medium |
| No anti-entropy / repair job for replicated data | All | regex: absence of `repair\|anti_entropy\|read_repair` in cron or scheduler | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Replication factor = 1 with claims of "distributed" | Config, SQL | regex: `REPLICAS\s*[:=]\s*1` with no sharding or partition config | High |
| `acks=0` on Kafka in production | Config | regex: `acks\s*[:=]\s*0` | High |
| Quorum write + no quorum read (`R=1, W=N, R+W≤N`) | All | heuristic: strong write config but reads from single replica without quorum | Medium |
| MongoDB with `w:1` (no write concern) | All | regex: `writeConcern.*w.*1\|w\s*[:=]\s*1` | High |
| LWW with client-side timestamps | All | regex: `last_modified.*client\|timestamp.*from.*request` | High |
| Cassandra `LOCAL_ONE` for financial data | All | regex: `Consistency\(LOCAL_ONE\|Consistency\(ONE` | High |
| No `min.insync.replicas` on Kafka topics | Config | regex: absence of `min\.insync\.replicas` in topic config | Medium |
| DynamoDB without `ConsistentRead` when needed | Python | regex: `ConsistentRead\s*=\s*False` on inventory/financial table queries | Medium |
| AP system with zero conflict resolution strategy | All | heuristic: DynamoDB/Cassandra/Riak in use with no `conflict_resolver\|merge\|TTL` config | Medium |
| Session consistency without session token | All | AST: session reads without re-sending `SessionToken` from the write response | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Confusing "Available" with "Fast"

**Description:** Setting timeouts so low that quorum reads always fail, making the system technically available (returns an error) but practically useless.

```python
# ❌ WRONG — timeout shorter than a single quorum read latency
# Quorum read on 3 replicas with 100 ms RTT = ~200 ms round trip
# Setting read timeout to 50 ms means every read fails.
CONFIG.read_timeout = 0.05
```

**Why it's dangerous:** The system is "available" in the CAP sense (returns an error, not a hang), but it is functionally broken. No read ever succeeds.

**Detection:** Read timeout < 2× estimated quorum read latency for the replication topology.

**Fix:** Set timeouts ≥ 3× expected quorum latency. Measure actual latencies with Prometheus and configure based on p99.

### Anti-Pattern: CP System That Refuses ALL Writes During Transient Partition

**Description:** The primary steps down because it lost quorum with secondaries, and the application has no write-path to any replica.

```yaml
# MongoDB replica set: primary steps down when it can't reach 1 of 2 secondaries
# But the application only writes to the primary
# Result: 0 nodes accepting writes during a 30-second network glitch
```

**Why it's dangerous:** A brief network partition makes the entire database read-only. In an e-commerce system, this means checkout is impossible.

**Detection:** CP system with write path only to primary; no fallback for write availability.

**Fix:** Configure a secondary as a readable secondary (MongoDB secondaryPreferred) and use causal consistency for read-your-writes. Or use an AP system for write availability with conflict resolution.

### Anti-Pattern: Using LWW on Clocks Without NTP

**Description:** Last-write-wins with client-generated timestamps on machines with unsynchronized clocks.

```python
# ❌ WRONG — client-side timestamp for LWW
record['last_modified'] = datetime.now().isoformat()
```

**Why it's dangerous:** Clock skew between two clients can mean "client A wrote at 12:01:00 but their clock was 5 minutes fast, so their write has a timestamp of 12:06:00" and "client B wrote at 12:01:05 (correct time) but their write has a timestamp of 12:01:05." LWW picks client A's write as the winner — even though client B's write happened later in real time.

**Detection:** Client-side timestamps used for conflict resolution without NTP enforcement.

**Fix:** Use server-side timestamps (let the broker/database assign the timestamp) or use vector clocks / CRDTs instead of LWW.

### Anti-Pattern: AP System Without Conflict Resolution

**Description:** Multi-master replication without any merge or conflict resolution logic.

```python
# DynamoDB multi-master writes: both succeed, conflict is invisible
# On next read, DynamoDB returns the last-write-wins result
# The losing write is silently dropped
```

**Why it's dangerous:** In a shopping cart, user A adds item X, user B adds item Y, both from different regions. With LWW, only one item survives. The user's cart is silently corrupted.

**Detection:** DynamoDB/Cassandra/Riak without any conflict detection in the application layer; no version vector or LWW-aware merge.

**Fix:** Implement application-level merge: retrieve all versions and let the user resolve, or use a CRDT (OR-Set for shopping carts).

### Anti-Pattern: Tunable Consistency Misconfigured for Critical Data

**Description:** Setting `Consistency=ONE` for reads of financial data.

```go
// ❌ WRONG — inventory check with consistency level ONE
session.Query(
    "SELECT stock FROM inventory WHERE product_id = ?", sku,
).Consistency(gocql.One).Exec()
// Reads from any replica. A replica may not have the latest sell.
// Two nodes both read stock=1 from different replicas, both sell the last item.
```

**Why it's dangerous:** Stale reads on inventory cause overselling. In a payment system, stale reads cause double charges.

**Detection:** `Consistency(ONE)` / `Consistency(LOCAL_ONE)` / `ConsistentRead=False` on inventory, payment, or balance queries.

**Fix:** Use `QUORUM` for reads on critical data. If performance is a concern, use `LOCAL_QUORUM` (same datacenter) to minimize latency while preserving consistency.

### Anti-Pattern: No Staleness SLA on Eventually Consistent Reads

**Description:** "The data is eventually consistent" without any bound on "eventually."

**Why it's dangerous:** In a microservices architecture, service A reads from a cache that is refreshed every 5 minutes. Service B writes to the DB. If service A reads stale data for 5 minutes, users see stale prices, stale availability, stale balances. The inconsistency window can be the full TTL of the cache.

**Detection:** Cache TTLs > 30 seconds without staleness monitoring; no `last_updated` timestamp served alongside stale data.

**Fix:** Set a maximum staleness SLA (e.g., 30 seconds). Monitor staleness. Serve a "data is refreshing" indicator to users when data is near the staleness boundary.

### Anti-Pattern: Confusing CA with "Good"

**Description:** Selecting a single-node system (CA by default) and calling it "CA" on a CAP diagram.

**Why it's dangerous:** A single-node system is not distributed; it trivially satisfies CA by never encountering partitions. Calling it CA gives a false sense of architectural soundness. The moment you add a second node, partitions become real and you must choose.

**Detection:** Single-node deployment described as "CA system" in design docs.

**Fix:** Label single-node systems as "non-distributed." Add a second node in testing and measure partition behavior.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|---|---|---|---|---|
| `REPLICATION_FACTOR` | int | 1 | 3 | Number of replicas per partition/shard. 1 = no redundancy. |
| `DB_WRITE_CONCERN` | string | `acknowledged` (MongoDB) | `majority` | When is a write acknowledged to the client? |
| `DB_READ_CONCERN` | string | `local` | `majority` (for critical reads) | What data must a read reflect? |
| `DB_SYNCHRONOUS_COMMIT` | string | `on` (PostgreSQL) | `on` or `remote_write` | PostgreSQL synchronous commit level. |
| `CASSANDRA_CONSISTENCY_READ` | string | `ONE` | `QUORUM` (critical), `ONE` (non-critical) | Read consistency level per query. |
| `CASSANDRA_CONSISTENCY_WRITE` | string | `QUORUM` | `QUORUM` | Write consistency level. |
| `DYNAMODB_CONSISTENT_READ` | bool | `False` | `True` for critical tables | Strongly consistent read (slower, more cost). |
| `DYNAMODB_REPLICAS` | int | 3 (multi-AZ) | 3 | Managed by AWS; verify in console. |
| `KAFKA_MIN_INSYNC_REPLICAS` | int | 1 | 2–3 | Min replicas for ack=all to succeed. |
| `KAFKA_ACKS` | string | `1` | `all` | Producer acknowledgment level. |
| `KAFKA_REPLICATION_FACTOR` | int | 1 | 3 | Topic replication factor. |
| `CACHE_TTL_SECONDS` | int | 300 | 30–300 | Staleness ceiling. Depends on SLO. |
| `ANTI_ENTROPY_INTERVAL` | int (s) | 3600 | 600–3600 | How often to run anti-entropy repair. |
| `READ_REPAIR_CHANCE` | float | 0.1 | 0.1 | Probability of read-repair on each read. |
| `VECTOR_CLOCK_TTL` | int (h) | 72 | 72–168 | Max age of vector clock entries (garbage collection). |
| `CONFLICT_RESOLUTION_STRATEGY` | string | `last_write_wins` | varies | Strategy for merge: `last_write_wins`, `merge`, `custom`. |
| `MAX_STALENESS_SECONDS` | int | 30 | 30 | SLA for maximum data staleness. |
| `SESSION_TOKEN_TTL` | int (s) | 3600 | 3600 | How long a DynamoDB session token is valid. |

## 7. Integration Points

- **Depends on:** A replicated data store (PostgreSQL with streaming replication, Cassandra, DynamoDB, Spanner, Kafka for log-based consistency); consensus protocol (Raft, Paxos) for CP guarantees; NTP synchronization for LWW timestamps.
- **Used by:** Every service that reads or writes shared state. API handlers (choose consistency per endpoint), background processors, caching layers, session stores, payment services.
- **Related concepts:**
  - **`foundation.db-scaling`:** Replication is the mechanism. CAP is the decision framework for how replication is used (CP vs AP, quorum config).
  - **`foundation.caching`:** Caching is a deliberate trade-off toward availability (fast reads) and against consistency (stale reads). Cache TTL is the staleness bound.
  - **`foundation.idempotency`:** Idempotency is how you make writes safe in an AP system. If writes can be duplicated during conflict resolution, idempotency ensures the user is not double-charged.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| `replica_lag_seconds` | Prometheus | > 5 s → warn; > 30 s → page | Replica is falling behind; check network or disk |
| `read_repair_total` | Prometheus | > 0 → warn | Conflicts detected; check write patterns |
| `stale_read_total` (reconstructed via timestamp diff) | Prometheus | > 1% → warn | Too many stale reads from AP system |
| `quorum_timeout_total` | Prometheus | > 0 → page | Replicas unreachable; partition or overload |
| `conflict_rate` | Prometheus | > 0.01% of writes → warn | Multi-master writes without conflict resolution |
| `consistency_violation_total` | Prometheus | > 0 → page | Jepsen test detected linearizability violation |
| `write_latency_seconds` p99 (quorum writes) | Prometheus | > 2× SLO → page | Quorum is slow; check replica health |
| `replica_count` | Prometheus | < RF → page | Replica count dropped below replication factor |
| `cache_hit_ratio` | Prometheus | < 80% → warn | Cache eviction too aggressive; stale data risk |
| `cache_staleness_seconds` | Prometheus | > max_staleness_seconds → page | Cache TTL exceeded; data is stale |

## 9. Evolution / Version Tracking

**Pre-distributed era (1970s–1990s):** Single-node databases with ACID transactions (IBM DB2, Oracle, PostgreSQL). Consistency was trivially guaranteed. No partitions, no availability concern.

**Two-phase commit (2PC) era (1980s–2000s):** Distributed transactions used 2PC/XA to achieve atomic commits across multiple nodes. Guaranteed consistency and durability, but required all participants to be available during the commit phase — effectively CP with a blocking coordinator. Replaced by sagas for most microservices use cases.

**CAP formalized (2000):** Seth Gilbert and Nancy Lynch proved that in the presence of partitions, a system cannot provide both consistency and availability. The result was surprising because many systems claimed both.

**Dynamo era (2007):** Amazon's Dynamo paper (published at SOSP 2007) popularized AP systems. DynamoDB used vector clocks, Merkle trees, sloppy quorum, and hinted handoff. The insight: availability can be traded for consistency, and conflicts can be resolved lazily.

**Spanner / TrueTime (2012):** Google's Spanner paper (OSDI 2012) demonstrated that CP is achievable at global scale using TrueTime (GPS + atomic clocks with bounded clock uncertainty). `TrueTime.wait()` ensures that the uncertainty interval (`ε`) is known — two non-overlapping intervals guarantee real-time ordering. This made globally-consistent distributed databases practical.

**Modern era (2018+):**
- **Tunable consistency:** DynamoDB, Cassandra, and Cosmos DB let developers pick the consistency level per operation. The default is session consistency (sensible for most applications).
- **Read/write path isolation:** Systems like FaunaDB use Calvin (pre-transaction agreement) for linearizability without 2PC round-trips.
- **Serverless databases:** Aurora Serverless v2, Neon, PlanetScale — auto-scaling with consistency guarantees.
- **Edge computing:** Edge caches are AP by nature. Consistency is enforced via version vectors and merge functions at the origin.

**Deprecated patterns:** "Just use 2PC for everything" (blocks on coordinator failure); "we don't need to think about CAP because we're a small team" (all systems have partitions — whether you think about them or not); "we're CA because we're a single node" (CA is meaningless without partitions).

## 10. References

- Gilbert, S. and Lynch, N. — "Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerance Web Services" (2002) — https://www.glassbeam.com/sites/default/files/pdf/brewers-conjecture.pdf
- Amazon Dynamo paper (SOSP 2007) — https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
- Google Spanner (OSDI 2012) — https://www.usenix.org/system/files/conference/osdi12/osdi12-final-4.pdf
- "Designing Data-Intensive Applications" (Kleppmann, O'Reilly, 2017) — Chapters 5, 7, 9
- MongoDB Replication — https://www.mongodb.com/docs/manual/replication/
- Cassandra consistency levels — https://cassandra.apache.org/doc/latest/cassandra/operating/read_write_consistency.html
- DynamoDB consistency models — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html
- Jepsen testing — https://jepsen.io/ — empirical proof of consistency violations in real systems
- CRDTs — Shapiro et al., "Conflict-free Replicated Data Types" (Symposium on Stabilization, Safety, and Security, 2011) — https://inria.hal.science/hal-00932833/file/paper.pdf
- Voldemort vector clocks — https://www.project-voldemort.com/voldemort/
- Riak DT (CRDTs) — https://riak.com/assets/riak-dt2.pdf
- Brewer's CAP Theorem — https://en.wikipedia.org/wiki/CAP_theorem
- "A Note on Distributed Systems" (Lamport, 1978) — https://lamport.azurewebsites.net/pubs/time-clocks.pdf
