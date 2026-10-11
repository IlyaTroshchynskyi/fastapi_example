# Redis Operations — Cluster, Sentinel, Eviction

Production deployment reference for the `redis-patterns` skill. Build these clients inside `get_redis_client()` (see Project Integration in `SKILL.md`) in place of `Redis.from_url` — never at module level.

## Connection Management

### Cluster Mode

```python
from redis.asyncio.cluster import ClusterNode, RedisCluster

RedisCluster(
    startup_nodes=[ClusterNode('redis-1', 6379)],
    decode_responses=True,
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
