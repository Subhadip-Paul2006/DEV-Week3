---
id: foundation.db-scaling
category: foundation
owning_agent: F-11
maturity: stable
languages:
- any
tags:
- sharding
- read-replicas
- indexing
- partitioning
related:
- foundation.cap-consistency
- foundation.consistent-hashing
- foundation.connection-pooling
domain: core
---

# Database Scaling

## 1. Overview

Database scaling is the practice of adapting a database system to handle increasing data volume, query load, and concurrency without degrading performance. A single instance has hard limits on CPU, memory, disk I/O, and network bandwidth. Once approached, the system slows or fails. Scaling addresses this by either making the single instance more powerful (vertical scaling) or distributing workload across multiple instances (horizontal scaling). Every production system growing beyond a few thousand queries per second must confront these decisions, and the choice affects latency, consistency, cost, and operational complexity for the application's entire lifetime.

## 2. Core Principles

- **Vertical scaling has a hard ceiling.** You can add CPU, RAM, and faster disks up to the largest instance class, but beyond that point no money buys more single-machine capacity.
- **Horizontal scaling is the only long-term path for unbounded growth.** Distributing data and queries across nodes enables near-infinite scaling at the cost of added complexity.
- **Read and write workloads scale differently.** Reads parallelize cheaply with replicas; writes are fundamentally harder since every write must hit the authoritative store.
- **Partitioning trades simplicity for throughput.** Once sharded, cross-shard queries, distributed transactions, and resharding become expensive problems.
- **Indexes accelerate reads but slow writes.** Every index reduces INSERT/UPDATE throughput because the structure must also be maintained.
- **Connection pooling is mandatory at scale.** Without a pool, connection exhaustion causes cascading failures before query throughput limits are reached.
- **The bottleneck always moves.** Optimizing one layer shifts contention to another. Monitoring must track the full stack.

## 3. Sub-Concepts

### 3.1 Vertical Scaling (Scale-Up)

**Definition:** Increasing capacity of a single server by adding CPU, RAM, faster storage (NVMe), or network bandwidth.

**Why it matters:** No code changes are needed. For early-stage teams, this is the correct default. The danger is treating it as permanent when the workload has outgrown the largest available instance class.

**Implementation patterns:**
- AWS: migrate from `db.m5.large` (2 vCPU, 8 GB) to `db.m6i.16xlarge` (64 vCPU, 256 GB).
- PostgreSQL tuning: `shared_buffers = 25% RAM`, `work_mem = 16–64MB`, `maintenance_work_mem = 1–2GB`.

**Common mistakes:**
- Assuming vertical scaling is free. Large instances cost 10–50x more.
- Ignoring that a single large instance is a bigger single point of failure than a cluster.

**Scanner signals:**
- `Positive`: Instance class spec in IaC (e.g., `instance_type = "db.r6g.4xlarge"`).
- `Negative`: No read-replicas for service with >10k daily active users.

### 3.2 Read Replicas

**Definition:** Secondary instances maintaining an asynchronous copy of primary data. All reads can be directed to replicas while writes go to the primary.

**Why it matters:** Most workloads are read-heavy (80–95% reads). Replicas scale read capacity with minimal code changes. The tradeoff is replication lag — stale data makes replicas unsuitable for read-after-write consistency.

**Implementation patterns:**

```python
# CORRECT: Route reads to replicas, writes to primary
from sqlalchemy import create_engine

primary_engine = create_engine(PRIMARY_DB_URL)
replica_engines = [create_engine(url) for url in REPLICA_URLS.split(",")]

def get_read_session():
    return Session(random.choice(replica_engines))

def get_write_session():
    return Session(primary_engine)
```

```typescript
// CORRECT: Separate connection strings
const primary = new PrismaClient({ datasources: { db: { url: PRIMARY_URL } } });
const replica = new PrismaClient({ datasources: { db: { url: REPLICA_URL } } });
```

**Common mistakes:**
- Writing to replicas via DNS round-robin.
- Not monitoring replication lag. A replica 30s behind looks identical to a healthy one without metrics.
- Assuming eventual consistency is acceptable for all reads.

**Scanner signals:**
- `Positive`: `read_only = on` in DB config; separate read/write connection strings in code.
- `Negative`: Single connection string for all operations in a service with >5 DB instances.
- `Negative`: No replication lag monitoring (`Seconds_Behind_Master` not collected).

### 3.3 Sharding (Horizontal Partitioning)

**Definition:** Splitting a logical dataset across multiple physical databases based on a shard key, so each shard holds a disjoint subset.

**Why it matters:** A single instance has finite capacity. Sharding distributes storage and compute for linear-ish write scaling. The cost is cross-shard query complexity, resharding migration, and irreversible shard-key decisions.

**Shard key strategies:**

| Strategy | Best For | Tradeoff |
|----------|----------|----------|
| Hash-based | Even distribution | Range queries require fan-out to all shards |
| Range-based | Time-series data | Hotspots on recent data |
| Directory-based | Maximum flexibility | Directory becomes a bottleneck |

**Implementation:**

```python
# CORRECT: Hash-based sharding with MD5
import hashlib

def get_shard_id(user_id, shard_count=16):
    hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    return hash_val % shard_count

# WRONG: Sequential shard assignment
# shard_id = user_id % shard_count  # Creates hotspots with sequential IDs
```

**Shard key selection rules:**
- The shard key must be in the WHERE clause of most common queries.
- Choose a key you cannot change later.
- Use a power of 2 for shard count (8, 16, 32) to simplify rebalancing.

**Scanner signals:**
- `Positive`: Shard router middleware; `shard_id` column in table schema.
- `Negative`: Single database URL for tables >100M rows; JOIN queries referencing different connection pools.

### 3.4 Indexing Strategies

**Definition:** Auxiliary data structures (B-trees, GIN, GiST) that let the database find rows without scanning the entire table.

**Why it matters:** A sequential scan on 100M rows takes seconds; an index lookup takes milliseconds. Every index slows writes.

**PostgreSQL examples:**
```sql
-- CORRECT: Composite index matching WHERE clause order
CREATE INDEX idx_orders_user_status ON orders (user_id, status)
WHERE deleted_at IS NULL;

-- CORRECT: Partial index for frequently queried subset
CREATE INDEX idx_active_users_email ON users (email)
WHERE account_status = 'active';

-- WRONG: Index on low-cardinality column (boolean, 2 values)
CREATE INDEX idx_users_is_active ON users (is_active);  -- optimizer ignores this
```

**Index types:**

| Type | Best For | Tradeoff |
|------|----------|----------|
| B-tree | Range queries, equality | Default, works for most cases |
| Hash | Exact-match only | No range queries |
| GIN | Full-text, JSONB, arrays | Larger size, slower writes |
| GiST | Geospatial, range types | Specialized |
| BRIN | Large append-only data | Minimal storage, only for ordered data |

**Common mistakes:**
- Indexing columns never used in WHERE/JOIN clauses. Validate with EXPLAIN ANALYZE.
- Over-indexing write-heavy tables (5+ indexes can cut write throughput by 30–50%).
- Not using covering indexes (INCLUDE in PostgreSQL) to avoid heap lookups.

**Scanner signals:**
- `Positive`: `CREATE INDEX` in migrations; `EXPLAIN ANALYZE` in tests; `pg_stat_statements` configured.
- `Negative`: No indexes on foreign key columns; table >50M rows with no indexes.

### 3.5 Connection Pooling

**Definition:** Pre-established connection pools reused across requests instead of opening a new connection per request.

**Why it matters:** TCP + TLS + auth takes 5–50ms per connection. At 100 req/s, that is 500ms–5s of pure overhead. PostgreSQL defaults to 100 max connections; without pooling, spikes exhaust this limit quickly.

**PgBouncer configuration:**
```ini
[pgbouncer]
default_pool_size = 20
max_client_conn = 1000
pool_mode = transaction
server_idle_timeout = 600
server_lifetime = 3600
```

**Python (SQLAlchemy):**
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=True,
    pool_timeout=30,
)
```

**Go (pgxpool):**
```go
config.MaxConns = 25
config.MinConns = 5
config.MaxConnLifetime = time.Hour
config.MaxConnIdleTime = 30 * time.Minute
config.HealthCheckPeriod = time.Minute
```

**Common mistakes:**
- Not setting `pool_recycle`. Databases close idle connections; without recycling, the pool hands out dead connections.
- `pool_size` too large. Each PostgreSQL connection consumes ~10 MB; 200 connections = 2 GB server memory.

**Scanner signals:**
- `Positive`: PgBouncer `pgbouncer.ini`; `pool_size` / `maxConns` in app config.
- `Negative`: Raw `psycopg2.connect()` or `pgx.Connect()` per request; `pool_size` = 0 or >100.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| PgBouncer / ProxySQL config files | Any | File: `pgbouncer.ini`, `proxysql.cnf` | High |
| CREATE INDEX in migrations | SQL | Regex: `CREATE\s+(UNIQUE\s+)?INDEX` | High |
| Multiple DATABASE_URL env vars | Any | Regex: `DATABASE_(PRIMARY\|REPLICA\|WRITE\|READ)` | High |
| Replication config in DB init | Any | Regex: `primary_conninfo\|CHANGE REPLICATION SOURCE` | High |
| Shard router middleware | Python, Go, TS | AST: `shard` in name + routing logic | High |
| Connection pool config | Any | Regex: `pool_size\|maxConns\|poolSize\|max_overflow` | High |
| EXPLAIN ANALYZE in tests | SQL | Regex: `EXPLAIN\s+ANALYZE` | Medium |
| read_only = on in config | Config | Regex: `default_transaction_read_only\s*=\s*on` | High |
| Partitioned table definitions | SQL | Regex: `PARTITION\s+BY\|PARTITIONED\s+TABLE` | High |
| Replication lag monitoring | Any | Regex: `Seconds_Behind_Master\|pg_stat_replication` | High |
| Multiple DB connections in ORM | Any | AST: multiple `create_engine\|pgxpool` calls | High |
| VACUUM schedule | SQL | Regex: `VACUUM\|autovacuum` | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No indexes on foreign key columns | SQL | FK constraint without adjacent `CREATE INDEX` | High |
| No connection pool | Any | Absence of `pool_size\|maxConns` in codebase | High |
| Single DATABASE_URL | Any | Exactly one `DATABASE_URL\|DB_URL` variable | Medium |
| No replication for >1M row tables | SQL | Table row count > 1M, no replica config | Medium |
| No VACUUM / ANALYZE schedule | SQL | Absence in cron/scripts | Medium |
| No shard key on >100M row tables | SQL | Row count > 100M, no shard column | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| pool_size = 0 | Python | Regex: `pool_size\s*=\s*0` | High |
| Sequential sharding: `id % N` | Any | Regex: `%\s*\d+.*shard` | High |
| Index on low-cardinality column | SQL | Regex: `CREATE INDEX.*boolean\|enum.*2 values` | Medium |
| TTL not set on cache pattern | Any | `SET` without `EXPIRE` in adjacent lines | High |
| Replication lag > 5s without alerting | Config | Absence of lag threshold config | Medium |
| max_connections < pool_size sum | Config | `max_connections` lower than combined pool sizes | High |
| Sync I/O in async handler | Python, TS | AST: async func with sync `cursor.execute` | Medium |

## 5. Anti-Patterns

### Anti-Pattern: No Connection Pool

```python
# WRONG: Opens a new connection per request
@app.route('/users/<user_id>')
def get_user(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return jsonify(result)
```

**Why it's dangerous:** Each connection takes 5–50ms to establish. At 100 req/s, that is 500ms–5s of pure overhead. PostgreSQL defaults to 100 max connections; within seconds, the DB is saturated.

**Fix:**
```python
# CORRECT: Connection pool
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=10, pool_pre_ping=True)
with engine.connect() as conn:
    result = conn.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_id})
    return jsonify(result.fetchone()._asdict())
```

### Anti-Pattern: Writing to Replicas

```typescript
// WRONG: LB round-robins to all nodes including read-only replicas
const client = new Client({ connectionString: LOAD_BALANCER_URL });
await client.query("INSERT INTO orders ...");  // Corrupts replica
```

**Why it's dangerous:** Replicas are read-only. Writing to a replica causes data divergence and silent corruption.

**Fix:**
```typescript
const primary = new Client({ connectionString: PRIMARY_DB_URL });
const replica = new Client({ connectionString: REPLICA_DB_URL });
// Always use primary for writes
```

### Anti-Pattern: Sharding Before Needed

Building sharding for <10k QPS and <500GB data.

**Why it's dangerous:** Adds enormous complexity (cross-shard JOINs, resharding, operational tooling). Premature sharding is the top cause of database incidents in early-stage companies.

**Fix:** Use vertical scaling, read replicas, and connection pooling first. Only shard when the write load exceeds a single primary's capacity.

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `shared_buffers` (PG) | int | 128MB | 25% of RAM | Buffer pool for caching data pages |
| `work_mem` (PG) | int | 4MB | 16–64MB | Memory per sort/hash operation |
| `pool_size` (SQLAlchemy) | int | 5 | 10–20 | Persistent connections in pool |
| `max_overflow` (SQLAlchemy) | int | 10 | 5–10 | Extra connections under load |
| `pool_recycle` (SQLAlchemy) | int | -1 | 1800 | Force connection refresh (seconds) |
| `pool_pre_ping` (SQLAlchemy) | bool | False | True | Test connection health before use |
| `default_pool_size` (PgBouncer) | int | 20 | 20–50 | Server connections per (user, DB) |
| `pool_mode` (PgBouncer) | enum | session | transaction | When to return connection to pool |
| `server_idle_timeout` (PgBouncer) | int | 600 | 300–600 | Close idle connections after N seconds |
| `innodb_buffer_pool_size` (MySQL) | int | 128MB | 50–70% of RAM | InnoDB buffer pool |
| `innodb_flush_log_at_trx_commit` (MySQL) | int | 1 | 1 (durable), 2 (balanced) | Flush redo log at commit |
| `sync_binlog` (MySQL) | int | 0 | 1 for durability | Fsync binlog after N transactions |

## 7. Integration Points

- **Depends on:** OS file descriptor limits (`ulimit -n`) must exceed the sum of all pool sizes across app servers.
- **Depends on:** Monitoring infrastructure must access database metrics endpoints (`pg_stat_*` views).
- **Used by:** Application servers configure connection pools; every request handler acquires and releases from the pool.
- **Used by:** ORM frameworks manage connection lifecycle but require correct pool configuration.
- **Related to:** Load balancers distribute across read replicas; consistent hashing is preferred for resharding.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Query latency p50 | Prometheus | > 50ms → warn | Check slow queries, missing indexes |
| Query latency p99 | Prometheus | > 500ms → page | Check lock contention, replication lag |
| Connection pool utilization | Prometheus | > 80% → warn | Increase pool or reduce long queries |
| Replication lag | Prometheus | > 2s → warn, > 10s → page | Check replica load, network |
| Active vs max connections | PG `pg_stat_activity` | > 80% → warn | Increase max or add pooler |
| Index hit ratio | PG `pg_statio_user_indexes` | < 99% → warn | Add indexes, check bloat |
| Slow queries | pg_stat_statements | > 5% of queries > 1s → page | Optimize queries |
| Deadlocks per minute | PG log | > 0 → warn | Review transaction ordering |

## 9. Evolution

**Original approach (1990s–2000s):** Exclusively vertical scaling. A single Oracle/DB2 on increasingly powerful hardware. Broke down at web scale.

**Current best practice:** Layered scaling — vertical for moderate growth, read replicas for read-heavy loads, sharding only when genuinely needed. Managed services (RDS, Cloud SQL, AlloyDB) handle replication and failover automatically. CDC (Debezium) enables CQRS patterns.

**Emerging:** Serverless databases (Neon, Turso), HTAP systems (TiDB, Spanner), and storage-compute separation (Aurora, Neon).

**Deprecated:** Master-slave terminology (use primary-replica); manual failover scripts; MySQL MyISAM engine.

## 10. References

- PostgreSQL Scaling: https://www.postgresql.org/docs/current/scaling.html
- PgBouncer Documentation: https://www.pgbouncer.org/usage.html
- MySQL Scaling: https://dev.mysql.com/doc/refman/8.0/en/scaling.html
- "Designing Data-Intensive Applications" (Kleppmann): https://dataintensive.net/
- AWS RDS Proxy: https://aws.amazon.com/blogs/database/amazon-rds-proxy-now-generally-available/
- Citus Sharding Explained: https://www.citusdata.com/blog/2016/03/30/fundamentals_collected_posts_on_sharding/
- Percona Indexing Best Practices: https://www.percona.com/blog/2016/03/17/the-ultimate-mysql-indexing-best-practices-guide/
- Debezium CDC: https://debezium.io/documentation/reference/stable/index.html
