---
id: foundation.caching
category: foundation
owning_agent: F-01
maturity: stable
languages:
- any
tags:
- key-value
- distributed
- in-memory
- performance
related:
- foundation.connection-pooling
- foundation.cap-consistency
domain: core
---

# Foundation Concept: Caching

## 1. Overview

Caching stores frequently accessed data in a high-speed layer so subsequent requests are served faster than querying the original data source. It exists because the speed gap between memory and disk/database access is six orders of magnitude — L1 cache is ~0.5 ns while a database round-trip is 1–50 ms. Caching reduces latency, decreases backend load, and improves throughput. The fundamental challenge is data staleness: any data stored outside the source of truth can become inconsistent with it, and every caching strategy must explicitly address invalidation.

## 2. Core Principles

- Cached data must have a TTL or invalidation strategy — data without expiry is stale data.
- The source of truth must always remain the persistent data store — caching is a performance optimization, not a replacement.
- Cache keys must be namespaced to prevent collisions between different data types sharing the same cluster.
- Cache reads must never cause thundering herd failures — popular entries must not expire simultaneously.
- Cache invalidation must be explicit and deterministic — relying on eventual consistency without defined rules is a reliability anti-pattern.

## 3. Sub-Concepts

### 3.1 Cache Topologies

**Definition:** The architectural pattern determining where the cache lives relative to the application and data store. Primary topologies: cache-aside (lazy loading), write-through, write-behind.

**Why it matters:** Each topology makes different tradeoffs between read/write performance, consistency, and complexity. Wrong topology for your access pattern results in stale data or unnecessary database load.

**Implementation patterns:**

*Cache-aside (lazy loading)* — check cache first, load from DB on miss, populate cache:

```python
import redis, json
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_user(user_id):
    cache_key = f"user:{user_id}"
    cached = r.get(cache_key)
    if cached: return json.loads(cached)
    user = db.query("SELECT * FROM users WHERE id=%s", user_id).fetchone()
    if user:
        r.setex(cache_key, 3600, json.dumps(dict(user)))
    return dict(user) if user else None
```

```go
func GetUser(ctx context.Context, rdb *redis.Client, userID string) (*User, error) {
    val, err := rdb.Get(ctx, fmt.Sprintf("user:%s", userID)).Result()
    if err == nil {
        var user User; json.Unmarshal([]byte(val), &user); return &user, nil
    }
    user, err := fetchUserFromDB(ctx, userID)
    if err != nil { return nil, err }
    if user != nil { rdb.SetEX(ctx, fmt.Sprintf("user:%s", userID), user, time.Hour) }
    return user, nil
}
```

*Write-through* — write to both cache and database synchronously:

```python
def update_user(user_id, data):
    db.execute("UPDATE users SET name=%s WHERE id=%s", data['name'], user_id)
    r.setex(f"user:{user_id}", 3600, json.dumps(data))
```

**Common mistakes:** Using cache-aside for write-heavy workloads without considering double write overhead; using write-behind without a durable write-ahead log (data loss on crash).

**Scanner signals:** `SETEX`, `setex`, `SetEX` calls → cache-aside writes present. `EXPIRE` called separately from `SET` → correct pattern. No cache write logic around DB UPDATE/INSERT → missing invalidation.

### 3.2 Cache Key Design

**Definition:** Strategy for generating and organizing cache keys to ensure uniqueness, support bulk invalidation, and avoid collisions across tenants or data types.

**Why it matters:** Poor key design causes cache pollution, accidental collisions leading to data corruption, and inability to perform bulk invalidation.

**Implementation patterns:**

```python
# GOOD: Namespaced key with version prefix for atomic invalidation
CACHE_VERSION = "v2"
def cache_key(entity_type, entity_id):
    return f"cache:{CACHE_VERSION}:{entity_type}:{entity_id}"
# Produces: cache:v2:user:123
# To invalidate: r.delete("cache:v2:user:*")
```

**Common mistakes:** Keys like `user_data` without entity ID — causes data leakage. Keys including timestamps directly making invalidation impossible. Keys exceeding 250 bytes wasting memory.

**Scanner signals:** Cache keys lacking namespace prefix → review for collisions. Missing tenant ID in multi-tenant systems → potential data leakage. Key patterns > 250 characters → memory waste.

### 3.3 TTL and Expiration Strategies

**Definition:** Time-to-live is the duration after which a cached entry is automatically evicted. Strategies: absolute TTL (fixed expiry), sliding TTL (expiry extended on access), differentiated TTL based on data volatility.

**Why it matters:** TTL too short → cache efficiency drops. TTL too long → stale data causes correctness issues.

**Implementation patterns:**

```python
# Sliding TTL — expiry reset on each access
def get_with_sliding_ttl(key, ttl=300):
    pipe = r.pipeline()
    pipe.get(key); pipe.expire(key, ttl)
    val, _ = pipe.execute()
    return val

# Differentiated TTL
TTL_MAP = {
    "user:profile": 86400,   # 24h — rarely changes
    "product:price": 60,     # 1m — high volatility
}
```

**Common mistakes:** `TTL = 0` or `-1` → infinite expiry, unbounded memory growth. Single TTL for all data types.

**Scanner signals:** `setex` with TTL <= 0 → misconfiguration. All `setex` calls use same TTL → overly simplistic. No `expire`/`setex` calls → missing TTL entirely.

### 3.4 Cache Invalidation

**Definition:** Removing or updating stale entries when underlying data changes. Strategies: TTL-based (time-based eviction) and event-based (explicit invalidation on mutation).

**Why it matters:** Incorrect invalidation causes stale reads. Over-aggressive invalidation causes stampedes. Missing invalidation causes silent data corruption.

**Implementation patterns:**

```python
def update_product_price(product_id, new_price):
    db.execute("UPDATE products SET price=%s WHERE id=%s", new_price, product_id)
    keys = [
        f"product:{product_id}",
        f"product:{product_id}:price",
        f"category:{get_category(product_id)}:products",
    ]
    r.delete(*keys)
```

**Common mistakes:** Updating DB without invalidating cache → stale data until TTL. Only deleting exact key without derived keys.

**Scanner signals:** DB UPDATE/INSERT without corresponding `cache.delete`/`DEL` → missing invalidation. `FLUSHALL`/`flushall` in production → dangerous.

### 3.5 Eviction Policies

**Definition:** Algorithm a cache uses to choose entries for removal when reaching memory limit. Common policies: LRU, LFU, FIFO, TTL-based.

**Why it matters:** Eviction policy determines which data stays under memory pressure. Poor policy causes cache pollution where useless data evicts frequently accessed data.

**Implementation patterns:**

```python
# Check eviction policy
config = r.config_get('maxmemory-policy')
# Should be 'allkeys-lru' or 'volatile-lru'
```

```go
config := bigcache.DefaultConfig(10 * time.Minute)
config.HardMaxCacheSize = 100 // 100 MB max
```

**Common mistakes:** No `maxmemory` on Redis → unbounded memory growth → OOM. `noeviction` policy without write-error handling.

**Scanner signals:** `maxmemory-policy` in config → eviction policy present. `maxmemory` set → memory bound configured (good). No `maxmemory` → unbounded risk. `lru_cache` without `maxsize` → unbounded Python cache.

### 3.6 Cache Warming and Preloading

**Definition:** Populating cache with expected data before it is requested, during startup, after deployments, or before traffic spikes.

**Why it matters:** Cold starts cause cache stampedes. Preloading eliminates initial latency spike and prevents thundering herd on shared data.

**Implementation patterns:**

```python
async def warm_cache():
    hot = db.query("SELECT * FROM products WHERE is_hot=true LIMIT 100").fetchall()
    pipe = r.pipeline()
    for p in hot:
        pipe.setex(f"product:{p['id']}", 1800, json.dumps(p))
    pipe.execute()
```

**Scanner signals:** Functions named `warm_cache`, `preload_cache` → warming pattern present. Startup scripts querying DB and writing to cache → warming logic.

## 4. Scanner Signals

### 4.1 Presence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| Import of Redis client | Python, TypeScript, Go | regex: `import redis\|import ioredis\|go-redis\|"github.com/redis/go-redis"` | High |
| Import of Memcached client | Any | regex: `import memcache\|import pylibmc\|"github.com/bradfitz/gomemcache"` | High |
| Cache decorator on function | Python | AST: `@cache`, `@cache_page`, `@lru_cache` | High |
| `SETEX`/`setex`/`SetEX` call | Any | regex: `\.setex\(|SetEX\(` | High |
| `EXPIRE`/`expire` call | Any | regex: `\.expire\(|expire(` | High |
| In-memory cache initialization | Any | regex: `lru_cache\|NewEvictingLRU\|bigcache.New` | Medium |
| Cache middleware registration | TypeScript | regex: `Cache-Control\|cacheMiddleware\|addCache` | High |
| `CACHE_TTL`, `REDIS_URL` env vars | Any | regex: `CACHE_\w+\|REDIS_\w+\|MEMCACHE` | High |
| Cache warmer function | Any | regex: `warm_cache\|preload_cache\|cache_warmup` | Medium |
| Redis Cluster instantiation | Any | regex: `RedisCluster\|ClusterClient` | High |
| `cache.delete`/`cache.clear`/`DEL` in invalidation path | Any | regex: `cache\.(delete\|clear)\|\.del(\()` | Medium |
| `maxmemory-policy` in Redis config | Any | regex: `maxmemory-policy\|maxmemory\|eviction.*policy` | High |
| TTL constants in code | Any | regex: `TTL_.*=\|CACHE_TTL.*=\|ttl.*=.*[0-9]` | Medium |
| `stale-while-revalidate` header | Any | regex: `stale-while-revalidate\|stale_while_revalidate` | Medium |

### 4.2 Absence Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| No cache-related imports | Any | Absence of all Presence Signals across codebase | High |
| No cache configuration files | Any | No `redis.conf`, `cache*.yaml`, `CACHE_*` env vars | High |
| All data access goes directly to DB queries | Any | No cache decorator or wrapper around any query path | High |
| No `SETEX`/`EXPIRE` calls, only `SET` | Any | `SET` found without `EXPIRE`/`SETEX` within 10 lines | High |

### 4.3 Misconfiguration Signals

| Signal | Languages | Scanner Pattern | Confidence |
|---------|-----------|-----------------|------------|
| `SET` without `EXPIRE`/`SETEX` (no TTL) | Any | `\.set\(` without `\.setex\|expire` within 5 lines | High |
| TTL = 0 or -1 (infinite) | Any | `setex(.*,\s*0)\|ex=0\|ex=-1` | High |
| No eviction policy in Redis config | Any | `redis.conf` exists but no `maxmemory-policy` line | High |
| `maxmemory` not set on Redis | Any | `redis.conf` without `maxmemory` | High |
| Unbounded `lru_cache` (no maxsize) | Python | `@lru_cache` without `maxsize=N` | Medium |
| Hardcoded cache credentials | Any | `password.*=.*["'][^"]+["']` in cache config | High |
| `FLUSHALL` or `FLUSHDB` in production | Any | regex: `FLUSHALL\|FLUSHDB` | High |
| All keys use identical TTL | Any | Multiple `setex` with same TTL for different data types | Medium |

## 5. Anti-Patterns

### Anti-Pattern: Cache Without TTL

**Description:**
```python
r.set('user:123', user_data)  # No EXPIRE
```

**Why it's dangerous:** Data changes in DB but cache never invalidates. Users see stale data indefinitely. Over time, cache fills with dead entries evicting useful data.

**Detection:** Scanner looks for `SET` without `EXPIRE`/`SETEX` within 3 lines.

**Fix:**
```python
r.setex('user:123', 3600, user_data)  # 1 hour TTL
```

### Anti-Pattern: Cache Stampede on Popular Key Expiry

**Description:**
```python
def get_popular_product(id):
    return cache.get(f"product:{id}")  # All requests miss simultaneously
```

**Why it's dangerous:** All concurrent requests hit DB simultaneously when popular key expires, overwhelming it.

**Detection:** Cache reads on hot paths without locking or staggered TTL.

**Fix:**
```python
# Singleflight deduplication + jittered TTL
import random
lock_key = f"lock:product:{id}"
if cache.add(lock_key, "1", nx=True, ex=10):
    try:
        data = load_from_db(id)
        cache.setex(f"product:{id}", 3600 + random.randint(-360, 360), data)
        return data
    finally: cache.delete(lock_key)
```

### Anti-Pattern: Stale Data Due to Missing Invalidation

**Description:**
```python
db.execute("UPDATE users SET email=%s WHERE id=%s", new_email, user_id)
# Forgot: r.delete(f"user:{user_id}")
```

**Why it's dangerous:** DB has correct data, cache returns old data until TTL expires.

**Detection:** Scanner looks for DB UPDATE/INSERT without corresponding cache DEL in same scope.

**Fix:**
```python
db.execute("UPDATE users SET email=%s WHERE id=%s", new_email, user_id)
r.delete(f"user:{user_id}", f"user:{user_id}:profile")
```

### Anti-Pattern: Cache Key Collision

**Description:**
```python
r.set("data", product_info)    # Product service
r.set("data", config_settings)  # Overwrites!
```

**Why it's dangerous:** Different services overwrite each other's entries. Hard-to-debug data corruption in shared clusters.

**Detection:** Cache keys lacking namespace prefix (just `"data"` instead of `"product:123"`).

**Fix:**
```python
def product_key(id): return f"product:{id}"
def config_key(name): return f"config:{name}"
```

### Anti-Pattern: Cache Penetration (Querying Nonexistent Data)

**Description:**
```python
def get_user(id):
    return cache.get(f"user:{id}") or db.query(f"SELECT * FROM users WHERE id={id}")
```

**Why it's dangerous:** Attackers query 1M nonexistent IDs → all miss cache → all hit DB. Denial-of-service vector.

**Detection:** Cache-get followed by DB query with no check for existence.

**Fix:**
```python
def get_user(id):
    cached = cache.get(f"user:{id}")
    if cached: return cached
    user = db.query("SELECT * FROM users WHERE id=%s", id).fetchone()
    if user:
        cache.setex(f"user:{id}", 3600, serialize(user))
        return user
    cache.setex(f"user:{id}:null", 60, "1")  # Cache the absence
    return None
```

### Anti-Pattern: Unbounded Local Cache Growth

**Description:**
```python
@lru_cache(maxsize=None)  # Unbounded!
def get_all_products(): return fetch_all_products()
```

**Why it's dangerous:** Cache grows without limit, consuming all memory → OOM kills.

**Detection:** `@lru_cache` without `maxsize` or with `maxsize=None`.

**Fix:**
```python
@lru_cache(maxsize=1024)
def get_all_products(): return fetch_all_products()
```

## 6. Configuration Reference

| Parameter | Type | Default | Recommended | Description |
|-----------|------|---------|-------------|-------------|
| `redis_maxmemory` | string | 0 (unlimited) | 75% of RAM | Max memory Redis can use before eviction |
| `redis_maxmemory_policy` | string | noeviction | allkeys-lru | Eviction policy |
| `redis_maxmemory_samples` | int | 5 | 10 | Keys sampled for eviction candidate selection |
| `REDIS_URL` | string | localhost:6379 | redis://host:6379/0 | Redis connection URL |
| `CACHE_TTL_DEFAULT` | int | 300 | 3600 | Default TTL in seconds |
| `CACHE_TTL_USER_SESSION` | int | 1800 | 1800 | Session data TTL (30 min) |
| `CACHE_TTL_STATIC_CONTENT` | int | 86400 | 86400 | Static content TTL (24h) |
| `CACHE_KEY_PREFIX` | string | (none) | app_name:env: | Key prefix for namespacing |
| `CACHE_MAX_CONNECTIONS` | int | 10 | 50 | Redis connection pool size |
| `CACHE_SOCKET_TIMEOUT` | int | 5 | 3 | Socket timeout in seconds |
| `CACHE_CONNECT_TIMEOUT` | int | 5 | 3 | Connection establishment timeout |
| `local_cache_maxsize` | int | 128 | 512 | Max entries for in-process LRU caches |
| `stale_while_revalidate_seconds` | int | 0 | 30 | Seconds to serve stale data while refreshing |

## 7. Integration Points

- **Depends on:** A persistent data store (database, object storage, external API) as source of truth.
- **Used by:** API handlers (cache query results), background workers (cache computed results), CDN edge nodes (cache static assets), session stores (cache auth state).
- **Pairs with connection pooling:** Cache reduces DB load, reducing connection pool pressure. Both manage finite expensive resources.
- **Pairs with circuit breakers:** If Redis becomes unavailable, circuit breaker detects failure and falls back to DB or returns degraded responses, preventing cascading failures.
- **Interacts with CAP consistency:** Caching introduces eventual consistency. The CAP theorem's Consistency is violated when DB is updated but cache still serves old data.

## 8. Observability

| Metric | Tool | Threshold | Action |
|--------|------|-----------|--------|
| Cache hit rate | Prometheus | < 80% warn, < 60% page | Check TTL, key design, workload shift |
| Cache miss rate | Prometheus | Rising trend 15 min | Check for stampede or uncached queries |
| Redis memory usage | Prometheus | > 80% max → warn, > 95% → page | Increase maxmemory, review eviction |
| Cache latency p99 | Prometheus | > 5ms → warn, > 20ms → page | Check Redis CPU, pool saturation |
| Evicted keys rate | Prometheus | Non-zero → warn | Memory pressure; increase maxmemory |
| Keyspace hit ratio | Redis INFO | < 0.9 → review | Poor cache utilization |
| Connection pool utilization | Prometheus | > 80% → warn | Increase max connections |
| Cache error rate | Prometheus | > 1% → page | Check Redis availability |

## 9. Evolution / Version Tracking

Early caching used memcached (2003) with manual population/invalidation. Redis emerged in 2010 as the dominant cache, introducing richer data types and built-in eviction. Frameworks like Django Cache and Spring Cache provided abstraction layers. The industry settled on Redis + cache-aside as the default.

From 2018 onward, microservices introduced cache namespace isolation and distributed coordination. CDN edge caching (Cloudflare Workers, Vercel Edge Cache) pushed caching closer to users. Emerging patterns: probabilistic early expiration for stampede prevention, singleflight for deduplicating misses, and event-sourced architectures where caches are rebuilt from event logs.

Deprecated: cache as primary data store without DB fallback, `FLUSHALL` for invalidation, single-node Redis without failover.

## 10. References

- Redis Persistence and Eviction docs: https://redis.io/docs/latest/operate/oss/reference/persistence/
- Cache-Aside Pattern — Microsoft: https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside
- Marc Brooker on Thundering Herd: https://brooker.co.za/blog/2022/02/28/thundering-herd.html
- Go singleflight package: https://pkg.go.dev/golang.org/x/sync/singleflight
- ioredis: https://github.com/redis/ioredis
- "Cache Invalidation: The Hard Problem": https://www.pwelcl.net/posts/2020-04-12-cache-invalidation-the-hard-problem/
