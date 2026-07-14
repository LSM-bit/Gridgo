"""
Redis 连接管理

注意：当前使用 Redis 5.x，需要 protocol=2 强制 RESP2 协议，
因为 redis-py 5.x 默认使用 RESP3（需要 Redis 6+）。
"""

from redis.asyncio import ConnectionPool, Redis

from app.core.config import settings

redis: Redis | None = None


async def get_redis() -> Redis:
    """获取 Redis 客户端（依赖注入用）"""
    if redis is None:
        raise RuntimeError("Redis 未初始化，请先调用 init_redis()")
    return redis


async def init_redis() -> Redis:
    """初始化 Redis 连接"""
    global redis
    # protocol=2 强制 RESP2，兼容 Redis 5.x
    pool = ConnectionPool.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        protocol=2,
    )
    redis = Redis(connection_pool=pool)
    await redis.ping()
    print(f"[GridGo] Redis connected: {settings.REDIS_URL}")
    return redis


async def close_redis() -> None:
    """关闭 Redis 连接"""
    global redis
    if redis is not None:
        await redis.close()
        redis = None
        print("[GridGo] Redis disconnected")
