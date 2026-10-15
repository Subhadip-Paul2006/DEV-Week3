---
id: foundation.consistent-hashing
category: foundation
owning_agent: F-12
maturity: stable
languages:
- any
tags:
- distributed-systems
- ring-topology
- virtual-nodes
- load-balancing
related:
- foundation.db-scaling
- foundation.load-balancers
- foundation.caching
domain: core
---

# Consistent Hashing

## 1. Overview

Consistent hashing maps data keys and storage nodes onto a shared circular hash space (the "ring"), enabling minimal-disruption redistribution when nodes are added or removed. Traditional hash partitioning uses `hash(key) % N`, where N is the fixed node count. When N changes, every key must remap — causing a full migration. Consistent hashing solves this by placing both keys and nodes on a ring ordered by hash value. A key maps to the first node encountered when moving clockwise. When a node joins or leaves, only keys in the affected ring arc are remapped. This property makes it the foundational algorithm for distributed caches, sharded databases, CDNs, and peer-to-peer networks.

## 2. Core Principles

- **The ring is a sorted circle of hash values.** Both keys and nodes are hashed into the same numeric range (typically 0 to 2^160 or 2^256) and placed in sorted order.
- **Each key maps to the next clockwise node.** From the key's position, move clockwise to find the first node. That node owns the key.
- **Node addition only affects keys between the new node and its predecessor.** Only the affected ring arc redistributes, not the entire dataset.
- **Node removal only affects keys owned by that node.** Those keys fall to the next clockwise node with no impact on other keys.
- **Virtual nodes prevent load imbalance.** Each physical node claims multiple virtual positions, enabling fine-grained load distribution.
- **The hash function must be uniform.** A non-uniform hash creates hotspots, defeating the algorithm's purpose.
- **Consistent hashing is partitioning, not replication.** It determines *where* data lives, not *how many copies* exist.

## 3. Sub-Concepts

### 3.1 Ring Topology

**Definition:** The ring is a circular sorted structure containing hash values of all nodes and virtual nodes.

**Why it matters:** Implementation determines lookup performance. A naive array requires O(N) lookups; a sorted list with binary search achieves O(log N).

**Implementation (Python):**
```python
import bisect
import hashlib

class ConsistentHashRing:
    def __init__(self, num_virtual_nodes=150):
        self.ring = []
        self.num_virtual = num_virtual_nodes
        self._node_hashes = {}

    def _hash(self, key):
        return int(hashlib.sha1(key.encode()).hexdigest(), 16) % (2**32)

    def add_node(self, node_id):
        hashes = []
        for i in range(self.num_virtual):
            h = self._hash(f"{node_id}#{i}")
            bisect.insort(self.ring, (h, node_id))
            hashes.append(h)
        self._node_hashes[node_id] = hashes

    def get_node(self, key):
        if not self.ring:
            raise ValueError("No nodes")
        h = self._hash(key)
        idx = bisect.bisect_left(self.ring, (h, ""))
        if idx >= len(self.ring):
            idx = 0
        return self.ring[idx][1]
```

**Implementation (Go):**
```go
type ConsistentHash struct {
    mu       sync.RWMutex
    ring     []uint32
    hashMap  map[uint32]string
    vnodes   int
}

func NewConsistentHash(vnodes int) *ConsistentHash {
    return &ConsistentHash{hashMap: make(map[uint32]string), vnodes: vnodes}
}

func (c *ConsistentHash) Add(node string) {
    for i := 0; i < c.vnodes; i++ {
        hash := crc32.ChecksumIEEE([]byte(fmt.Sprintf("%s#%d", node, i)))
        c.ring = append(c.ring, hash)
        c.hashMap[hash] = node
    }
    sort.Slice(c.ring, func(i, j int) bool { return c.ring[i] < c.ring[j] })
}

func (c *ConsistentHash) Get(key string) string {
    hash := crc32.ChecksumIEEE([]byte(key))
    idx := sort.Search(len(c.ring), func(i int) bool { return c.ring[i] >= hash })
    if idx == len(c.ring) { idx = 0 }
    return c.hashMap[c.ring[idx]]
}
```

**Common mistakes:**
- Using `hash(key) % N` and calling it consistent hashing. This is standard modulo partitioning.
- No wrap-around at the end of the ring — keys with hash > all node hashes disappear.
- Unsorted ring with linear scan — O(N) lookups.

**Scanner signals:**
- `Positive`: `bisect_left` / `sort.Search` with ring array.
- `Positive`: Virtual node loop with key suffix.
- `Negative`: Simple `% N` with dynamic node count.
- `Negative`: No wrap-around (`idx == len(ring)` fallback).

### 3.2 Virtual Nodes (Vnodes)

**Definition:** Each physical node claims multiple hash positions on the ring. Typically 100–256 vnodes per physical node.

**Why it matters:** With only physical nodes, a node with an unlucky position can own a disproportionately large arc. Vnodes provide even distribution and enable fine-grained rebalancing without moving entire physical machines.

**Vnode distribution comparison:**

| Nodes | Vnodes/Node | Total Vnodes | Max std dev |
|-------|-------------|--------------|-------------|
| 3 | 0 (physical only) | 3 | ~0.29 (very uneven) |
| 3 | 100 | 300 | ~0.04 (even) |
| 10 | 256 | 2560 | ~0.02 (very even) |

**Implementation:**
```typescript
class VirtualNodeRing {
    private ring: { hash: number; nodeId: string }[] = [];
    private vnodesPerNode = 256;

    addNode(nodeId: string) {
        for (let i = 0; i < this.vnodesPerNode; i++) {
            const hash = this.hashKey(`${nodeId}:vnode-${i}`);
            this.ring.push({ hash, nodeId });
        }
        this.ring.sort((a, b) => a.hash - b.hash);
    }
}
```

**Common mistakes:**
- Too few vnodes (< 10 per node) — equivalent to physical-node-only hashing.
- Too many vnodes (> 1000) — increases memory and ring operation cost.

**Scanner signals:**
- `Positive`: Loop generating multiple hashes per node with index.
- `Negative`: Single hash per node in a dynamic-scaling system.

### 3.3 Replication

**Definition:** Assign the next N nodes clockwise as replicas for each key. The replication factor determines how many copies exist.

**Why it matters:** A single node failure must not cause data loss. Replication ensures fallback to neighboring nodes on the ring.

```python
def get_replicas(self, key, replication_factor):
    idx = bisect.bisect_left(self.ring, (self._hash(key), ""))
    replicas, seen = [], set()
    for i in range(len(self.ring)):
        pos = (idx + i) % len(self.ring)
        node = self.ring[pos][1]
        if node not in seen:
            replicas.append(node)
            seen.add(node)
        if len(replicas) >= replication_factor:
            break
    return replicas
```

**Common mistakes:**
- Replication factor of 1 — single node failure = data loss.
- All replicas in one availability zone.

**Scanner signals:**
- `Positive`: `replication_factor` configured; multi-node write acknowledgment.
- `Negative`: RF=1 in a system with <3 nodes; all nodes in single AZ.

### 3.4 Rebalancing

**Definition:** Redistributing keys when nodes join or leave. Only keys in the affected ring arc move.

**Why it matters:** Consistent hashing enables minimal-disruption rebalancing. A full migration is unnecessary — only the affected arc needs streaming.

```python
def rebalance(new_node_id):
    new_node_hash = ring._hash(new_node_id)
    idx = bisect.bisect_left(ring.ring, (new_node_hash, ""))
    predecessor_idx = (idx - 1) % len(ring.ring)
    predecessor_hash = ring.ring[predecessor_idx][0]

    keys_to_migrate = query_keys_in_range(predecessor_hash, new_node_hash)
    for i in range(0, len(keys_to_migrate), batch_size):
        batch = keys_to_migrate[i:i + batch_size]
        migrate_batch(batch, new_node_id)
        time.sleep(0.5)  # Rate limit
        report_progress(i / len(keys_to_migrate))
```

**Common mistakes:**
- Synchronous bulk migration during deployment.
- No rate limiting — saturates network and destination node.

**Scanner signals:**
- `Positive`: Rate-limited migration with progress tracking.
- `Negative`: Bulk copy in deploy scripts.

### 3.5 Hash Function Selection

**Definition:** The function mapping keys/nodes to ring positions. Must be uniform and deterministic.

| Hash Function | Speed | Uniformity | Use Case |
|---------------|-------|------------|----------|
| CRC32 | Fastest | Good | Caching, CDN |
| MurmurHash3 | Very fast | Excellent | General purpose |
| SHA-1 | Slow | Excellent | Security-sensitive |
| MD5 | Moderate | Excellent | Legacy |

**Critical:** Python's built-in `hash()` is randomized per process — never use it for ring positions.

**Scanner signals:**
- `Positive`: Explicit hash function (crc32, murmur3, sha1).
- `Negative`: Built-in `hash()` in Python; truncation to <32 bits.

### 3.6 Failure Detection

**Definition:** Detecting departed nodes so their keys can be served from replicas.

**Phi accrual failure detector:**
```python
class PhiAccrualDetector:
    def phi(self, node_id):
        elapsed = time.time() - self.last_heartbeat[node_id]
        intervals = self.intervals[node_id]
        mean = sum(intervals) / len(intervals)
        std = (sum((x - mean)**2 for x in intervals) / len(intervals)) ** 0.5
        return -math.log10(1 - math.exp(-elapsed / mean))

    def is_dead(self, node_id):
        return self.phi(node_id) > self.threshold  # threshold = 8
```

**Common mistakes:**
- Fixed timeout for failure detection (causes false positives/negatives with variable network latency).
- No hinted handoff — data on dead nodes is unreachable.

**Scanner signals:**
- `Positive`: Heartbeat, phi accrual, or timeout logic; replica fallback on error.
- `Negative`: No failure detection; hard-coded timeout.

## 4. Scanner Signals

### 4.1 Presence

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Ring with binary search lookup | Any | AST: sorted list + `bisect_left` / `sort.Search` | High |
| Virtual node loop | Any | Regex: `for.*range.*virtual\|vnodes` | High |
| Wrap-around logic | Any | Regex: `idx >= len\|idx = 0\|idx % len` | High |
| Replication factor param | Any | Regex: `replication_factor\|RF\s*=` | Medium |
| Multi-node write ack | Any | Regex: `quorum\|ACK.*\d+\|write_concern` | Medium |
| Hinted handoff | Any | Regex: `hint.*handoff\|hinted_replica` | Medium |
| AZ/rack awareness | Config | Regex: `rack\|availability_zone\|NetworkTopology` | Medium |

### 4.2 Absence

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Modulo hashing with dynamic nodes | Any | Regex: `%\s*\d+` with dynamic node list | High |
| No virtual nodes | Any | Single entry per physical node | Medium |
| No replication factor | Any | Absence of `replication_factor` + >1 node | High |
| Static node list | Any | Node list as constant, no add/remove | Medium |
| No failure detection | Any | No heartbeat / phi / timeout logic | Medium |

### 4.3 Misconfiguration

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| `hash()` for ring positions | Python | Regex: `hash\(` in ring code | High |
| Too few vnodes (< 10) | Any | Regex: `range\(\d+\)` where N < 10 | Medium |
| RF = 1 | Any | Regex: `replication_factor\s*=\s*1` | High |
| Single AZ for all nodes | Config | All nodes in same AZ | Medium |
| No wrap-around | Any | Missing `idx = 0` fallback | High |
| Truncation to <32 bits | Any | `% 2**16\|& 0xFF` | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Modulo Hashing Called Consistent Hashing

```python
# WRONG: This is NOT consistent hashing
def get_node(key, nodes):
    h = hash(key)
    return nodes[h % len(nodes)]
```

**Why:** When N changes, every key remaps. Adding 1 node to 100 causes ~99% of keys to move, triggering a full migration.

**Fix:** Use true ring-based consistent hashing with virtual nodes.

### Anti-Pattern: No Virtual Nodes

```python
# WRONG: Only physical nodes on ring
ring = [hash(node) for node in nodes]  # 3 nodes = 3 positions
```

**Why:** With 3 nodes, distribution variance is ~0.29. One node may own 50% of data.

**Fix:** Use 100–256 vnodes per physical node.

### Anti-Pattern: No Wrap-Around

```python
# WRONG: Keys with hash > all node hashes get no assignment
idx = bisect.bisect_left(ring, (h, ""))
return ring[idx][1]  # IndexError if idx == len(ring)
```

**Fix:**
```python
if idx >= len(ring):
    idx = 0
return ring[idx][1]
```

### Anti-Pattern: Single Replica

RF=1 means any node failure = permanent data loss for all keys it owned. Always use RF >= 3.

### Anti-Pattern: Synchronous Full Rebalancing

Migrating all keys during deployment saturates the network and causes timeouts. Only migrate the affected ring arc, rate-limited.

### Anti-Pattern: Inconsistent Hash Functions

Different hash functions across services cause key-to-node divergence. Define as a shared library and version explicitly.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `vnodes_per_node` | int | 100–256 | 150–256 | Virtual nodes per physical node |
| `hash_function` | enum | SHA-1 | murmur3 / SHA-1 | Ring position hash function |
| `replication_factor` | int | 1 | 3 | Copies of each key |
| `num_tokens` | int | 256 | 256 | Vnodes per node (Cassandra) |
| `partitioner` | enum | murmur3 | murmur3 / byte-ordered | Distribution algorithm |
| `ring_lookup_timeout_ms` | int | 50 | 10–50 | Ring membership lookup timeout |
| `rebalance_concurrency` | int | 4 | 4–8 | Parallel migration streams |
| `rebalance_rate_limit_kbps` | int | 0 | 50000–100000 | Migration bandwidth throttle |
| `hinted_handoff_window_hrs` | int | 3 | 3–12 | Hours to keep hints for dead nodes |
| `gossip_interval_sec` | int | 1 | 1–5 | Seconds between heartbeats |

## 7. Integration Points

- **Depends on:** Shared, deterministic hash function consistent across all services and restarts.
- **Depends on:** Gossip protocol or membership service to track ring node health.
- **Used by:** Distributed caches (Redis Cluster, DynamoDB), sharded DBs (Vitess, Citus), load balancers (NGINX hash module).
- **Used by:** P2P networks (Kademlia DHT, BitTorrent) for content distribution.
- **Related to:** DB scaling — consistent hashing is the preferred shard key distribution strategy.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Ring distribution variance | Custom | StdDev > 0.1 → warn | Check vnode count |
| Rebalancing progress | Custom | Stalled > 1hr → warn | Check network, destination health |
| Key lookup latency | APM | > 5ms → warn | Ring too large, not using binary search |
| Failed key lookups | App logs | Any → page | Ring wrap-around bug |
| Migration rate | Custom | < 100 keys/sec → warn | Network bottleneck |
| Virtual nodes per physical node | Config audit | < 50 → warn | Low vnode count causes imbalance |
| Gossip failure rate | Metrics | > 5% → warn | Network partition |

## 9. Evolution

**1997:** David Karger et al. introduced consistent hashing for web caching (ring with physical nodes only). **2007:** Amazon Dynamo formalized vnodes, preference lists, hinted handoff. **2008:** Cassandra adopted vnodes as standard. **Current:** 100–256 vnodes/ node, murmur3/SHA-1, RF=3 across AZs. **Emerging:** Weighted consistent hashing for heterogeneous nodes; jump consistent hash for O(1) lookups; rendezvous hashing as ring alternative.

## 10. References

- Karger et al. — "Web Caching with Consistent Hashing" (1997): https://dl.acm.org/doi/10.1145/645530.655866
- DynamoDB Partitioning: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.Partitions.html
- Cassandra Architecture: https://cassandra.apache.org/doc/latest/architecture/
- Redis Cluster: https://redis.io/docs/management/scaling/
- Kleppmann — "Designing Data-Intensive Applications": https://dataintensive.net/
- Jump Consistent Hash (Google 2014): https://arxiv.org/abs/1406.2294
- NGINX Consistent Hashing: https://nginx.org/en/docs/http/ngx_http_upstream_hash_module.html
