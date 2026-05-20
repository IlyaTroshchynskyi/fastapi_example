---
name: redis-patterns
description: Redis data structure patterns, caching strategies, distributed locks, rate limiting, pub/sub, and connection management for production applications.
user-invocable: true
---

# Redis Patterns

Quick reference for Redis best practices across common backend use cases.

## How It Works

Redis is an in-memory data structure store that supports strings, hashes, lists, sets, sorted sets, streams, and more. Individual Redis commands are atomic on a single instance; multi-step workflows require Lua scripts, MULTI/EXEC transactions, or explicit synchronization to stay atomic. Data is optionally persisted via RDB snapshots or AOF logs. Clients communicate over TCP using the RESP protocol; connection pools are essential to avoid per-request handshake overhead.

## When to Activate

- Adding caching to an application
- Implementing rate limiting or throttling
- Building distributed locks or coordination
- Setting up session or token storage
- Using Pub/Sub or Redis Streams for messaging
- Configuring Redis in production (pooling, eviction, clustering)

## Data Structure Cheat Sheet

| Use Case | Structure | Example Key |
|----------|-----------|-------------|
| Simple cache | String | `product:123` |
| User session | Hash | `session:abc` |
| Leaderboard | Sorted Set | `scores:weekly` |
| Unique visitors | Set | `visitors:2024-01-01` |
| Activity feed | List | `feed:user:456` |
| Event stream | Stream | `events:orders` |
| Counters / rate limits | String (INCR) | `ratelimit:user:123` |
| Bloom filter / HLL | HyperLogLog | `hll:pageviews` |

## Core Patterns

### Cache-Aside (Lazy Loading)

```python
import json
from redis.asyncio import Redis

r = Redis(host='localhost', port=6379, decode_responses=True)

async def get_product(product_id: int):
    cache_key = f"product:{product_id}"
    cached = await r.get(cache_key)

    if cached:
        return json.loads(cached)

    product = await db.fetch_one("SELECT * FROM products WHERE id = $1", product_id)
    await r.setex(cache_key, 3600, json.dumps(product))  # TTL: 1 hour
    return product
```

### Write-Through Cache

```python
async def update_product(product_id: int, data: dict):
    # Write to DB first
    await db.execute("UPDATE products SET ... WHERE id = $1", product_id)

    # Immediately update cache
    cache_key = f"product:{product_id}"
    await r.setex(cache_key, 3600, json.dumps(data))
```

### Cache Invalidation

```python
# Tag-based invalidation — group related keys under a set
async def cache_product(product_id: int, category_id: int, data: dict):
    key = f"product:{product_id}"
    tag = f"tag:category:{category_id}"
    async with r.pipeline(transaction=True) as pipe:
        await pipe.setex(key, 3600, json.dumps(data))
        await pipe.sadd(tag, key)
        await pipe.expire(tag, 3600)
        await pipe.execute()

async def invalidate_category(category_id: int):
    tag = f"tag:category:{category_id}"
    keys = await r.smembers(tag)
    if keys:
        await r.delete(*keys)
    await r.delete(tag)
```

### Session Storage

```python
import time
import uuid

async def create_session(user_id: int, ttl: int = 86400) -> str:
    session_id = str(uuid.uuid4())
    key = f"session:{session_id}"
    async with r.pipeline(transaction=True) as pipe:
        await pipe.hset(key, mapping={
            "user_id": user_id,
            "created_at": int(time.time()),
        })
        await pipe.expire(key, ttl)
        await pipe.execute()
    return session_id

async def get_session(session_id: str) -> dict | None:
    data = await r.hgetall(f"session:{session_id}")
    return data if data else None

async def delete_session(session_id: str) -> None:
    await r.delete(f"session:{session_id}")
```

## Rate Limiting

### Fixed Window (Simple)

```python
async def is_rate_limited(user_id: int, limit: int = 100, window: int = 60) -> bool:
    key = f"ratelimit:{user_id}:{int(time.time()) // window}"
    async with r.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, window)
        count, _ = await pipe.execute()
    return count > limit
```

### Sliding Window (Lua — Atomic)

```lua
-- sliding_window.lua
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
    -- Use unique member (now + sequence) to avoid collisions within the same millisecond
    local seq_key = key .. ':seq'
    local seq = redis.call('INCR', seq_key)
    redis.call('EXPIRE', seq_key, math.ceil(window / 1000))
    redis.call('ZADD', key, now, now .. '-' .. seq)
    redis.call('EXPIRE', key, math.ceil(window / 1000))
    return 1
end
return 0
```

```python
SLIDING_WINDOW_SCRIPT = open('sliding_window.lua').read()

async def allow_request(user_id: int) -> bool:
    key = f"ratelimit:sliding:{user_id}"
    now = int(time.time() * 1000)
    result = await r.eval(SLIDING_WINDOW_SCRIPT, 1, key, now, 60000, 100)
    return bool(result)
```

## Distributed Locks

### Distributed Lock (Single Node — SET NX PX)

```python
import uuid

async def acquire_lock(resource: str, ttl_ms: int = 5000) -> str | None:
    lock_key = f"lock:{resource}"
    token = str(uuid.uuid4())
    acquired = await r.set(lock_key, token, px=ttl_ms, nx=True)
    return token if acquired else None

async def release_lock(resource: str, token: str) -> bool:
    release_script = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """
    result = await r.eval(release_script, 1, f"lock:{resource}", token)
    return bool(result)

# Usage
token = await acquire_lock("order:payment:123")
if token:
    try:
        await process_payment()
    finally:
        await release_lock("order:payment:123", token)
```

> For multi-node setups use the `redlock-py` library which implements the full Redlock algorithm.

## Pub/Sub & Streams

### Pub/Sub (Fire-and-Forget)

```python
# Publisher
async def publish_event(channel: str, payload: dict) -> None:
    await r.publish(channel, json.dumps(payload))

# Subscriber — run as a background task (e.g. asyncio.create_task)
async def subscribe_events(channel: str) -> None:
    async with r.pubsub() as pubsub:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await handle(json.loads(message['data']))
```

### Redis Streams (Durable Queue)

```python
# Producer
async def emit(stream: str, event: dict) -> None:
    await r.xadd(stream, event, maxlen=10000)  # Cap stream length

# Consumer group — guarantees at-least-once delivery
try:
    await r.xgroup_create('events:orders', 'processor', id='0', mkstream=True)
except Exception:
    pass  # Group already exists

async def consume(stream: str, group: str, consumer: str) -> None:
    while True:
        messages = await r.xreadgroup(group, consumer, {stream: '>'}, count=10, block=2000)
        for _, entries in (messages or []):
            for msg_id, data in entries:
                await process(data)
                await r.xack(stream, group, msg_id)
```

> Prefer **Streams** over Pub/Sub when you need delivery guarantees, consumer groups, or replay.

## Key Design

### Naming Conventions

```
# Pattern: resource:id:field
user:123:profile
order:456:status
cache:product:789

# Pattern: namespace:resource:id
myapp:session:abc123
myapp:ratelimit:user:123

# Pattern: resource:date (time-bound keys)
stats:pageviews:2024-01-01
```

### TTL Strategy

| Data Type | Suggested TTL |
|-----------|--------------|
| User session | 24h (`86400`) |
| API response cache | 5–15 min |
| Rate limit window | Match window size |
| Short-lived tokens | 5–10 min |
| Leaderboard | 1h–24h |
| Static/reference data | 1h–1 week |

Always set a TTL. Keys without TTL accumulate indefinitely and cause memory pressure.

## Connection Management

### Connection Pooling

```python
from redis.asyncio import Redis, ConnectionPool

pool = ConnectionPool(
    host='localhost',
    port=6379,
    db=0,
    max_connections=20,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

r = Redis(connection_pool=pool)
```

### Cluster Mode

```python
from redis.asyncio.cluster import RedisCluster

r = RedisCluster(
    startup_nodes=[{"host": "redis-1", "port": 6379}],
    decode_responses=True,
    skip_full_coverage_check=True,
)
```

### Sentinel (High Availability)

```python
from redis.asyncio.sentinel import Sentinel

sentinel = Sentinel(
    [('sentinel-1', 26379), ('sentinel-2', 26379)],
    socket_timeout=0.5,
)
master = sentinel.master_for('mymaster', decode_responses=True)
replica = sentinel.slave_for('mymaster', decode_responses=True)
```

## Eviction Policies

| Policy | Behavior | Best For |
|--------|----------|----------|
| `noeviction` | Error on write when full | Queues / critical data |
| `allkeys-lru` | Evict least recently used | General cache |
| `volatile-lru` | LRU only among keys with TTL | Mixed data store |
| `allkeys-lfu` | Evict least frequently used | Skewed access patterns |
| `volatile-ttl` | Evict soonest-to-expire | Prioritize long-lived data |

Set via `redis.conf`: `maxmemory-policy allkeys-lru`

## Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Keys with no TTL | Memory grows unbounded | Always set TTL |
| `KEYS *` in production | Blocks the server (O(N)) | Use `SCAN` cursor |
| Storing large blobs (>100KB) | Slow serialization, memory pressure | Store reference + fetch from object store |
| Single Redis for everything | No isolation between cache & queue | Use separate DBs or instances |
| Ignoring connection pool limits | Connection exhaustion under load | Size pool to workload |
| Not handling cache miss stampede | Thundering herd on cold start | Use locks or probabilistic early expiry |
| `FLUSHALL` without thought | Wipes entire instance | Scope deletes by key pattern |

### Cache Miss Stampede Prevention

```python
import asyncio

_locks: dict[str, asyncio.Lock] = {}
_locks_mutex = asyncio.Lock()

async def get_with_lock(key: str, fetch_fn, ttl: int = 300):
    cached = await r.get(key)
    if cached:
        return json.loads(cached)

    async with _locks_mutex:
        if key not in _locks:
            _locks[key] = asyncio.Lock()
        lock = _locks[key]

    async with lock:
        cached = await r.get(key)  # Re-check after acquiring lock
        if cached:
            return json.loads(cached)
        value = await fetch_fn()
        await r.setex(key, ttl, json.dumps(value))
        return value
```

> For multi-process deployments, replace the in-process lock with `acquire_lock`/`release_lock` from the Distributed Locks section above.

## Examples

**Add caching to a FastAPI endpoint:**
Use cache-aside with `await r.setex(...)` and a 5-minute TTL on the response. Key on the request parameters. Never cache responses containing raw PHI — cache opaque IDs or safe aggregate data only.

**Rate-limit an API by user:**
Use fixed-window with `async with r.pipeline(transaction=True)` for low-traffic endpoints; use sliding-window Lua with `await r.eval(...)` for accurate per-user throttling.

**Coordinate a background job across workers:**
Use `await acquire_lock(...)` with a TTL that exceeds the expected job duration. Always release in a `finally` block.

**Fan-out notifications to multiple subscribers:**
Use `async with r.pubsub()` for fire-and-forget. Switch to Streams with `await r.xreadgroup(...)` if you need guaranteed delivery or replay for late consumers.

## Quick Reference

| Pattern | When to Use |
|---------|-------------|
| Cache-aside | Read-heavy, tolerate slight staleness |
| Write-through | Strong consistency required |
| Distributed lock | Prevent concurrent access to a resource |
| Sliding window rate limit | Accurate per-user throttling |
| Redis Streams | Durable event queue with consumer groups |
| Pub/Sub | Broadcast with no delivery guarantees needed |
| Sorted Set leaderboard | Ranked scoring, pagination |
| HyperLogLog | Approximate unique count at low memory |