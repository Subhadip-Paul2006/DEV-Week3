---
id: foundation.connection-pooling
category: foundation
owning_agent: F-06
maturity: stable
languages:
- any
tags:
- resource-management
- database
- http
- connection-limit
related:
- foundation.caching
- foundation.circuit-breaker
domain: core
---

# Foundation Concept: Connection Pooling

## 1. Overview

Connection pooling maintains a reusable set of pre-established connections to a remote resource so requests borrow and return connections rather than opening a new one for every request. It exists because establishing a connection is expensive: TCP handshake, TLS negotiation, authentication can take 10–100 ms, while the actual work often takes a few milliseconds. A service handling 1000 req/s against a DB taking 50ms to authenticate new connections spends 50,000ms cumulative latency per second on connection creation alone. A pool maintains 10–50 long-lived connections reused across requests, reducing both latency and load on the remote resource. Pools must enforce limits on max connections, timeouts for idle/stuck connections, and validation to ensure returned connections are healthy.

## 2. Core Principles

- Connections must have a bounded lifetime — long-lived connections accumulate state and may be silently closed.
- Idle connections must be validated before reuse — dead connections cause application errors.
- Pool size must be tuned to workload — too small causes queuing, too large exhausts server resources.
- Pool exhaustion must be observable and bounded — requests should fail fast, not block indefinitely.
- Connection acquisition must have a timeout — never wait forever for a connection.
- Pool configuration must be environment-aware — validated through load testing per environment.

## 3. Sub-Concepts

### 3.1 Pool Size and Capacity Planning

**Definition:** The maximum number of concurrent connections maintained by the pool. Must be tuned based on backend capacity, application concurrency, and query latency.

**Why it matters:** Undersized pool creates artificial bottlenecks. Oversized pool overwhelms the backend (database runs out of max_connections, OS runs out of file descriptors).

**Implementation patterns:**

```python
from psycopg_pool import ConnectionPool

pool = ConnectionPool(
    conninfo="postgresql://user:pass@host:5432/db",
    min_size=2,
    max_size=15,
    timeout=30,
    max_idle=600,
    max_lifetime=1800,
)
```

```typescript
import { Pool } from 'pg';

const pool = new Pool({
  max: 20, min: 5,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
  maxLifetimeSeconds: 1800,
});
```

```go
import "github.com/jackc/pgx/v5/pgxpool"

pool, _ := pgxpool.New(ctx, "postgres://user:pass@host/db")
pool.Config().MaxConns = 25
pool.Config().MinConns = 5
pool.Config().MaxConnLifetime = 30 * time.Minute
```

**Common mistakes:** Setting `max_size` very large without knowing DB `max_connections`. Setting min and max to same value.

**Scanner signals:** `maxPoolSize`, `max_pool_size`, `MaxConns` → pool size defined. No size constraint → unbounded risk.

### 3.2 Connection Acquisition and Timeouts

**Definition:** Mechanism by which clients request and wait for a connection. Includes acquisition timeout, checkout timeout, and queue management.

**Why it matters:** Without timeout, threads block indefinitely on exhausted pool, cascading into thread exhaustion.

**Implementation patterns:**

```python
try:
    with pool.connection(timeout=5) as conn:
        cursor = conn.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        return cursor.fetchone()
except PoolTimeout:
    metrics.increment('pool.exhaustion.timeout')
    return get_user_from_cache(user_id) or None
```

```go
ctx, cancel := context.WithTimeout(ctx, 3*time.Second)
defer cancel()

conn, err := pool.Acquire(ctx)
if err != nil {
    if errors.Is(err, context.DeadlineExceeded) { return nil, ErrPoolTimeout }
    return nil, err
}
defer conn.Release()
```

**Scanner signals:** `timeout` on pool initialization → acquisition timeout configured. `context.WithTimeout` around Acquire → timeout enforced. No timeout → unbounded waiting.

### 3.3 Connection Validation and Health Checks

**Definition:** Logic to verify a connection is alive and usable before returning it to the caller.

**Why it matters:** Connections closed by server, network devices, or transient failures cause application errors if reused.

**Implementation patterns:**

```python
# HikariCP — automatic validation on borrow
config = {
    "connectionTestQuery": "SELECT 1",
    "validationTimeout": 5000,
}
```

```go
func (db *DB) HealthCheck(ctx context.Context) error {
    conn, err := db.pool.Acquire(ctx)
    if err != nil { return err }
    defer conn.Release()
    return conn.Ping(ctx)
}
```

**Scanner signals:** `connectionTestQuery`, `testOnBorrow`, `validationQuery` → validation configured. No validation → potentially returning dead connections.

### 3.4 Connection Lifecycle and Eviction

**Definition:** Policies for when connections are closed: max lifetime (recycle after X), max idle time (close after Y idle), leak detection.

**Why it matters:** Connections held forever leak server resources. Held too briefly waste connection establishment cost.

**Implementation patterns:**

```python
hikari_config = {
    "maximumPoolSize": 15,
    "minIdle": 5,
    "maxLifetime": 1800000,        # 30 min
    "idleTimeout": 600000,         # 10 min
    "leakDetectionThreshold": 60000, # 60 sec
}
```

```go
pool.Config().MaxConnLifetime = 30 * time.Minute
pool.Config().MaxConnLifetimeJitter = 5 * time.Minute  # Avoid synchronized recycling
pool.Config().MaxConnIdleTime = 5 * time.Minute
pool.Config().HealthCheckPeriod = 1 * time.Minute
```

**Scanner signals:** `maxLifetime`/`MaxConnLifetime` → recycling in place. No lifecycle config → connections live forever.

### 3.5 Pool Exhaustion Handling

**Definition:** Behavior when all connections are in use: fail fast, queue with timeout, or shed load.

**Why it matters:** Incorrect handling (block forever, retry indefinitely) amplifies outages. Correct handling degrades gracefully.

**Implementation patterns:**

```python
def handle_query(query):
    try:
        with pool.connection(timeout=3) as conn:
            return conn.execute(query).fetchall()
    except PoolTimeout:
        if query.is_read_only(): return read_replica.execute(query).fetchall()
        raise ServiceUnavailable("Database overloaded")
```

**Scanner signals:** Pool timeout exception handler → exhaustion handled. No handler → silent failure mode.

### 3.6 Resource Limits and File Descriptors

**Definition:** OS-level limits constraining how many connections a process can open. Each connection consumes a file descriptor.

**Why it matters:** Even if DB allows 1000 connections, the process may be limited by `ulimit -n` (default 1024). Pool sizes must fit within OS limits.

**Implementation patterns:**

```bash
# /etc/security/limits.conf
app_user soft nofile 65536
app_user hard nofile 65536
```

```python
import resource
soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
# Required: max_connections_per_service * num_services + buffer
# PostgreSQL(20) + Redis(50) + HTTP(100) + buffer(100) = 270 FDs needed
```

**Scanner signals:** `ulimit -n` in deployment scripts → FD limit raised. No FD limit config → potential silent exhaustion.

### 3.7 Connection Pool Monitoring

**Definition:** Metrics and logs tracking pool health: active connections, idle connections, pending acquires, wait time, timeouts.

**Why it matters:** Pool exhaustion is a common production incident cause. Without monitoring, teams discover it only when users complain.

**Implementation patterns:**

```python
# HikariCP metrics
stats = pool.getMBean()
print(f"Active: {stats.getActiveConnections()}, Idle: {stats.getIdleConnections()}")
```

```go
// Go — pgxpool stats
stats := pool.Stat()
metrics.Gauge("db_pool_acquired_conns").Set(float64(stats.AcquiredConns()))
metrics.Gauge("db_pool_idle_conns").Set(float64(stats.IdleConns()))
metrics.Counter("db_pool_acquire_count").Inc()
```

**Scanner signals:** Metric names `pool_*`, `db_pool_*` → monitoring in place. No pool metrics → blind spot.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Import of pool library | Any | regex: `psycopg_pool\|sqlalchemy.pool\|pgxpool\|HikariCP\|pg.Pool\|ConnectionPool` | High |
| Pool initialization | Any | regex: `Pool\(\|ConnectionPool\(\|pgxpool.New\|HikariCP\|create_engine(` | High |
| `maxPoolSize`/`max_size` config | Any | regex: `maxPoolSize\|max_pool_size\|max:.*\d+\|MaxConns` | High |
| `minPoolSize`/`min_size` config | Any | regex: `minPoolSize\|min_size\|min:.*\d+\|MinConns` | Medium |
| Pool timeout config | Any | regex: `acquireTimeout\|acquire_timeout\|connectionTimeoutMillis\|AcquireTimeout` | High |
| Connection test/validation query | Any | regex: `connectionTestQuery\|validationQuery\|testOnBorrow\|SELECT 1` | High |
| Max lifetime config | Any | regex: `maxLifetime\|MaxConnLifetime\|maxLifetimeSeconds` | High |
| Leak detection threshold | Any | regex: `leakDetectionThreshold\|leak_detection\|leakThreshold` | High |
| `release()`/`Release()` in code | Any | regex: `\.release()\|conn\.Release()\|defer.*Release` | High |
| Pool metrics emission | Any | regex: `pool.*total.*idle\|pool_total_count\|db_pool.*count` | High |
| DB_URL / DATABASE_URL env | Any | regex: `DATABASE_URL\|DB_POOL\|POSTGRES_HOST` | High |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Direct connection creation in request handlers | Any | `psycopg2.connect\|mysql.connector.connect` in handler paths | High |
| No pool library in dependencies | Any | DB used but no pool library detected | High |
| No acquisition timeout | Any | Pool without `acquire_timeout`/`connectionTimeout` | Medium |
| No connection validation | Any | Pool without `testOnBorrow`/`validationQuery` | Medium |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Pool size > 100 (exceeds DB capacity) | Any | `max_size > 100` in app config | High |
| No max lifetime | Any | Missing `maxLifetime`/`MaxConnLifetime`/`connection_max_age` | High |
| No idle timeout | Any | Missing `idleTimeout`/`MaxConnIdleTime` | High |
| Acquire timeout = 0 | Any | regex: `acquireTimeout\s*[=:]\s*0\|connectionTimeoutMillis\s*[=:]\s*0` | High |
| Min and max to same value | Any | `min: 10, max: 10` | Medium |
| Hardcoded credentials | Any | Password string in connection config | High |
| No leak detection | Any | Pool without `leakDetectionThreshold` | Medium |
| `sslmode=disable` in production | Any | Production connection string with disabled SSL | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Per-Request Connection Creation

**Description:**
```python
def get_user(user_id):
    conn = psycopg2.connect(host="db", database="app", user="app", password="secret")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    conn.close()
    return cursor.fetchone()
```

**Why it's dangerous:** Each request pays connection creation cost (50-200ms). Under load, exhausts DB connections.

**Fix:**
```python
pool = ConnectionPool(conninfo="...", min_size=5, max_size=20)

def get_user(user_id):
    with pool.connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
```

### Anti-Pattern: Unbounded Pool Size

**Description:**
```python
pool = ConnectionPool(conninfo="...", max_size=sys.maxsize)
```

**Why it's dangerous:** Pool grows to thousands under load, exhausting database `max_connections`.

**Fix:** Calculate based on DB capacity: `pool_size = (db_max_connections - reserve) / app_instances`.

### Anti-Pattern: No Acquisition Timeout

**Description:**
```python
pool = ConnectionPool(conninfo="...", max_size=10)  # No timeout = infinite wait
with pool.connection() as conn:  # May hang forever if pool exhausted
```

**Why it's dangerous:** Request threads block indefinitely, cascading into complete service halt.

**Fix:**
```python
pool = ConnectionPool(conninfo="...", min_size=5, max_size=15, timeout=5)
```

### Anti-Pattern: Connection Leak (Not Returning)

**Description:**
```python
def get_user(user_id):
    conn = pool.getconn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    # If exception occurs before return, connection leaked
    pool.putconn(conn)
    return user
```

**Why it's dangerous:** Each exception leaks a connection. Pool exhausted after enough leaks.

**Fix:**
```python
def get_user(user_id):
    with pool.connection() as conn:  # Auto-released even on exception
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        return cursor.fetchone()
```

### Anti-Pattern: Synchronous Pool in Async Context

**Description:**
```python
async def get_user_async(user_id):
    with psycopg2_pool.connection() as conn:  # Synchronous — blocks event loop
        return conn.execute("SELECT...")
```

**Why it's dangerous:** Blocking event loop prevents other requests from being processed.

**Fix:**
```python
pool = await asyncpg.create_pool(host="db", min_size=5, max_size=15)
async def get_user_async(user_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)
```

### Anti-Pattern: Pool Size Without DB Capacity Planning

**Description:**
```python
pool = ConnectionPool(conninfo="...", max_size=200)  # DB max_connections = 100
```

**Why it's dangerous:** Total connections exceed database limit → connection refused for all clients.

**Fix:** Calculate: `(db_max_connections - reserve) / app_instances`.

### Anti-Pattern: Hardcoded Credentials

**Description:**
```python
pool = ConnectionPool(conninfo="postgresql://admin:secret@db-prod/db")
```

**Why it's dangerous:** Credentials visible in source control. Compromise = production DB access.

**Fix:**
```python
pool = ConnectionPool(conninfo=f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}/db")
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `maxPoolSize`/`max_size`/`MaxConns` | int | varies | 10–25 | Max concurrent connections |
| `minPoolSize`/`min_size`/`MinConns` | int | 0 | 2–5 | Min idle connections maintained |
| `acquireTimeout`/`timeout` | int (seconds) | 30 | 3–10 | Max wait for available connection |
| `connectionTestQuery`/`validationQuery` | string | (varies) | "SELECT 1" | Query to validate connections |
| `testOnBorrow` | bool | true | true | Validate before lending |
| `validationTimeout` | int (ms) | 5000 | 3000–5000 | Max time for validation query |
| `maxLifetime`/`MaxConnLifetime` | int (ms) | 1800000 | 1800000 | Recycle connections after this |
| `maxLifetimeJitter` | int (ms) | 0 | 300000 | Jitter to prevent synchronized recycling |
| `idleTimeout`/`MaxConnIdleTime` | int (ms) | 600000 | 300000 | Close idle connections after this |
| `leakDetectionThreshold` | int (ms) | 0 (disabled) | 60000 | Alert if connection not returned in time |
| `socketTimeout`/`queryTimeout` | int (ms) | 0 | 30000 | Per-query timeout |
| `sslMode` | string | "prefer" | "require" | SSL mode |
| `statementTimeout` | int (ms) | 0 | 30000 | Server-side statement timeout |
| `DB_POOL_MAX_SIZE` | env | 10 | 15–25 | Override pool max |
| `DB_POOL_MIN_SIZE` | env | 0 | 2–5 | Override pool min |
| `DB_ACQUIRE_TIMEOUT_SECONDS` | env | 30 | 5 | Override acquisition timeout |
| `ulimit_nofile` | OS | 1024 | 65536 | Process file descriptor limit |

## 7. Integration Points

- **Depends on:** Remote resource (database, Redis, HTTP service) supports multiple concurrent connections.
- **Used by:** All request handlers accessing backend resources, background jobs, health checks.
- **Pairs with caching:** Caching reduces DB queries → reduces connection pool pressure. Cache hit rate determines effective pool utilization.
- **Pairs with circuit breakers:** When DB is unhealthy, CB prevents requests from attempting to acquire connections.
- **Interacts with resource limits:** Connection pools compete for OS file descriptors. A process with PostgreSQL pool (20), Redis pool (50), HTTP (100) needs ~270 FDs.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Active connections | Prometheus | > 80% of max → warn | Approaching exhaustion |
| Idle connections | Prometheus | < min_size → warn | Under-provisioned |
| Pending acquires | Prometheus | Sustained > 0 → warn | Undersized pool or slow queries |
| Acquisition time p99 | Prometheus | > 1s warn, > 5s page | Pool contention |
| Pool exhaustion events | Prometheus | Any → warn | Scale pool or add replicas |
| Acquisition failures | Prometheus | > 1% → page | Pool exhausted or DB unavailable |
| Leaked connections | Prometheus | Any → page | Code bug; connection not released |
| Validation failures | Prometheus | > 1% → warn | DB health issues |

**Log messages:**
```
INFO: Pool: total=15, idle=8, acquired=7, max=20
WARN: Pool acquisition took 3.2s for query=SELECT users
WARN: Pool exhaustion: 20/20 in use, 5 requests waiting
ERROR: Connection leak: held for 62s (threshold=60s)
WARN: Validation failed: connection reset by peer
```

**Alerts:** Utilization > 90% for 5 min → page. Acquisition timeout rate > 1% → page. Leaked connections → page immediately.

## 9. Evolution / Version Tracking

Early database access used ODBC/JDBC with naive connection creation. c3p0 and DBCP (mid-2000s) introduced dedicated pool libraries with leak detection and statement caching. HikariCP (2010+) became the de facto Java standard with aggressive optimization and `((cores * 2) + spindles)` sizing formula.

SQLAlchemy Pool (Python), pgxpool (Go), node-postgres Pool (TypeScript) are current standards. Serverless-friendly pools (AWS RDS Proxy, Cloud SQL Auth Proxy) broker connections between ephemeral instances and persistent DB connections.

Deprecated: per-request connection creation, unbounded pool sizes, infinite acquisition timeouts, no validation, no leak detection.

## 10. References

- HikariCP — About Pool Sizing: https://github.com/brettwooldridge/HikariCP/wiki/About-Pool-Sizing
- pgxpool (Go): https://pkg.go.dev/github.com/jackc/pgx/v5/pgxpool
- psycopg3 Pool: https://www.psycopg.org/psycopg3/docs/advanced/pool.html
- node-postgres Pool: https://node-postgres.com/apis/pool
- AWS RDS Proxy: https://aws.amazon.com/rds/proxy/
- Pgbouncer: https://www.pgbouncer.org/
- SQLAlchemy Pooling: https://docs.sqlalchemy.org/en/20/core/pooling.html
