---
name: redis-patterns
description: Provides Redis data structure patterns, caching strategies, distributed locks, rate limiting, pub/sub, and connection management for production applications, adapted to this codebase's dependency injection. Use when adding caching to an application, implementing rate limiting or throttling, building distributed locks or coordination, setting up session or token storage, using Pub/Sub or Redis Streams for messaging, or configuring Redis in production (pooling, eviction, clustering).
---

# Redis Patterns

Quick reference for Redis best practices across common backend use cases.

**Related skills:** `python-code-style`, `fastapi-service`.

**Production deployment** — Cluster Mode, Sentinel, eviction policies: [operations.md](operations.md).

## Project Integration

Redis is not wired into this codebase yet. Before the first use:

- Install the client: `uv add redis`
- Add `REDIS_URL: RedisDsn` to `Settings` in `app/core/config.py`
- Create the client once in an `@lru_cache` factory and inject that factory directly with `Depends(get_redis_client)`, the same way `get_settings` and `get_aioboto_session` are injected. Never create a module-level `Redis(...)`, and never add an accessor dependency that reads the client from `request.app.state`
- In `app/lifespan.py`: `await get_redis_client().aclose()` in `finally`. Nothing is needed before `yield` — connections open on the first command

```python
# app/core/infrastructure/redis/redis_client.py
from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(
        settings.REDIS_URL.unicode_string(),
        max_connections=20,  # connection pool size
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
```

Services receive the client through the constructor:

```python
class ProductCacheService:
    def __init__(
        self,
        redis: Annotated[Redis, Depends(get_redis_client)],
        product_repository: Annotated[ProductRepository, Depends(ProductRepository)],
    ) -> None:
        self._redis = redis
        self._product_repository = product_repository
```

Every snippet below is a method of a service built this way: `self._redis` is the injected client. TTLs and Lua scripts are module-level constants above the class. Values are serialized through Pydantic schemas (`model_dump_json` / `model_validate_json`), not raw `dict` + `json`.

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
PRODUCT_CACHE_TTL_SECONDS = 3600  # 1 hour


async def get_product(self, product_id: int) -> ProductSchema:
    cache_key = f'product:{product_id}'
    cached_product = await self._redis.get(cache_key)
    if cached_product is not None:
        return ProductSchema.model_validate_json(cached_product)

    product = await self._product_repository.get_by_id(product_id)
    await self._redis.setex(cache_key, PRODUCT_CACHE_TTL_SECONDS, product.model_dump_json())
    return product
```

### Write-Through Cache

```python
async def update_product(self, product_id: int, product_update: ProductUpdateSchema) -> ProductSchema:
    # Write to DB first
    product = await self._product_repository.update(product_update, product_id)

    # Immediately update cache
    await self._redis.setex(f'product:{product_id}', PRODUCT_CACHE_TTL_SECONDS, product.model_dump_json())
    return product
```

### Cache Invalidation

```python
# Tag-based invalidation — group related keys under a set
async def cache_product(self, product: ProductSchema) -> None:
    key = f'product:{product.id}'
    tag = f'tag:category:{product.category_id}'
    async with self._redis.pipeline(transaction=True) as pipeline:
        await pipeline.setex(key, PRODUCT_CACHE_TTL_SECONDS, product.model_dump_json())
        await pipeline.sadd(tag, key)
        await pipeline.expire(tag, PRODUCT_CACHE_TTL_SECONDS)
        await pipeline.execute()

async def invalidate_category(self, category_id: int) -> None:
    tag = f'tag:category:{category_id}'
    keys = await self._redis.smembers(tag)
    if keys:
        await self._redis.delete(*keys)
    await self._redis.delete(tag)
```

### Session Storage

```python
SESSION_TTL_SECONDS = 86400  # 24 hours


class SessionSchema(BaseModel):
    user_id: int
    created_at: int


async def create_session(self, user_id: int, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    session_id = str(uuid.uuid4())
    key = f'session:{session_id}'
    async with self._redis.pipeline(transaction=True) as pipeline:
        await pipeline.hset(key, mapping={'user_id': user_id, 'created_at': int(time.time())})
        await pipeline.expire(key, ttl_seconds)
        await pipeline.execute()
    return session_id

async def find_session(self, session_id: str) -> SessionSchema | None:
    session_fields = await self._redis.hgetall(f'session:{session_id}')
    return SessionSchema.model_validate(session_fields) if session_fields else None

async def delete_session(self, session_id: str) -> None:
    await self._redis.delete(f'session:{session_id}')
```

## Rate Limiting

### Fixed Window (Simple)

```python
async def is_rate_limited(self, user_id: int, limit: int = 100, window_seconds: int = 60) -> bool:
    key = f'ratelimit:{user_id}:{int(time.time()) // window_seconds}'
    async with self._redis.pipeline(transaction=True) as pipeline:
        await pipeline.incr(key)
        await pipeline.expire(key, window_seconds)
        request_count, _ = await pipeline.execute()
    return request_count > limit
```

### Sliding Window (Lua — Atomic)

```lua
-- sliding_window.lua
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now_ms - window_ms)
local request_count = redis.call('ZCARD', key)

if request_count < limit then
    -- Use unique member (now + sequence) to avoid collisions within the same millisecond
    local sequence_key = key .. ':seq'
    local sequence = redis.call('INCR', sequence_key)
    redis.call('EXPIRE', sequence_key, math.ceil(window_ms / 1000))
    redis.call('ZADD', key, now_ms, now_ms .. '-' .. sequence)
    redis.call('EXPIRE', key, math.ceil(window_ms / 1000))
    return 1
end
return 0
```

Keep the script next to the service module and load it once, resolved relative to the module — not the working directory:

```python
SLIDING_WINDOW_SCRIPT = Path(__file__).with_name('sliding_window.lua').read_text()


async def allow_request(self, user_id: int, limit: int = 100, window_ms: int = 60000) -> bool:
    key = f'ratelimit:sliding:{user_id}'
    now_ms = int(time.time() * 1000)
    is_allowed = await self._redis.eval(SLIDING_WINDOW_SCRIPT, 1, key, now_ms, window_ms, limit)
    return bool(is_allowed)
```

## Distributed Locks

### Distributed Lock (Single Node — SET NX PX)

```python
LOCK_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


async def acquire_lock(self, resource: str, ttl_ms: int = 5000) -> str | None:
    token = str(uuid.uuid4())
    is_acquired = await self._redis.set(f'lock:{resource}', token, px=ttl_ms, nx=True)
    return token if is_acquired else None

async def release_lock(self, resource: str, token: str) -> bool:
    is_released = await self._redis.eval(LOCK_RELEASE_SCRIPT, 1, f'lock:{resource}', token)
    return bool(is_released)

# Usage
token = await self.acquire_lock('order:payment:123')
if token:
    try:
        await self._process_payment()
    finally:
        await self.release_lock('order:payment:123', token)
```

> For multi-node setups use the `redlock-py` library which implements the full Redlock algorithm.

## Pub/Sub & Streams

### Pub/Sub (Fire-and-Forget)

```python
# Publisher
async def publish_event(self, channel: str, event: EventSchema) -> None:
    await self._redis.publish(channel, event.model_dump_json())

# Subscriber — run as a background task (e.g. asyncio.create_task)
async def subscribe_events(self, channel: str) -> None:
    async with self._redis.pubsub() as pubsub:
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await self._send_notification(EventSchema.model_validate_json(message['data']))
```

### Redis Streams (Durable Queue)

```python
# Producer
async def append_event(self, stream: str, event_fields: dict[str, str]) -> None:
    await self._redis.xadd(stream, event_fields, maxlen=10000)  # Cap stream length

# Consumer group — guarantees at-least-once delivery
async def create_consumer_group_if_missing(self, stream: str, group: str) -> None:
    try:
        await self._redis.xgroup_create(stream, group, id='0', mkstream=True)
    except ResponseError as error:
        if 'BUSYGROUP' not in str(error):  # BUSYGROUP = group already exists; anything else is a real error
            raise

async def consume_events(self, stream: str, group: str, consumer: str) -> None:
    while True:
        stream_batches = await self._redis.xreadgroup(group, consumer, {stream: '>'}, count=10, block=2000)
        for _, entries in stream_batches or []:
            for entry_id, event_fields in entries:
                await self._apply_event(event_fields)
                await self._redis.xack(stream, group, entry_id)
```

`ResponseError` comes from `redis.exceptions`.

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
| Module-level `Redis(...)` or lock registry | Global state — breaks DI and does not work across workers | Inject the client via `Depends(get_redis_client)`; lock in Redis |

### Cache Miss Stampede Prevention

Uses `acquire_lock`/`release_lock` from the Distributed Locks section above, so it also holds across multiple workers. Pick the lock TTL above the expected `load_value` duration.

```python
STAMPEDE_RETRY_DELAY_SECONDS = 0.05


async def get_or_load_value(
    self, key: str, load_value: Callable[[], Awaitable[str]], ttl_seconds: int = 300
) -> str:
    cached_value = await self._redis.get(key)
    if cached_value is not None:
        return cached_value

    token = await self.acquire_lock(key)
    while token is None:  # another worker is rebuilding the value — wait and re-read
        await asyncio.sleep(STAMPEDE_RETRY_DELAY_SECONDS)
        cached_value = await self._redis.get(key)
        if cached_value is not None:
            return cached_value
        token = await self.acquire_lock(key)

    try:
        cached_value = await self._redis.get(key)  # Re-check after acquiring lock
        if cached_value is not None:
            return cached_value
        loaded_value = await load_value()
        await self._redis.setex(key, ttl_seconds, loaded_value)
        return loaded_value
    finally:
        await self.release_lock(key, token)
```

## Examples

**Add caching to a FastAPI endpoint:**
Use cache-aside with `await self._redis.setex(...)` and a 5-minute TTL on the response. Key on the request parameters. Never cache responses containing raw PHI or other sensitive user data (emails, names, raw payloads) — cache opaque IDs or safe aggregate data only.

**Rate-limit an API by user:**
Use fixed-window with `async with self._redis.pipeline(transaction=True)` for low-traffic endpoints; use sliding-window Lua with `await self._redis.eval(...)` for accurate per-user throttling.

**Coordinate a background job across workers:**
Use `await self.acquire_lock(...)` with a TTL that exceeds the expected job duration. Always release in a `finally` block.

**Fan-out notifications to multiple subscribers:**
Use `async with self._redis.pubsub()` for fire-and-forget. Switch to Streams with `await self._redis.xreadgroup(...)` if you need guaranteed delivery or replay for late consumers.

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
