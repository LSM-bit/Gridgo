"""
Token Redis 管理服务

Redis Key 设计：
  - token:access:{jti}   → access token 白名单，值为 user_id
  - token:refresh:{user_id} → refresh token 白名单，值为 jti（同用户只保留最新）
  - token:blacklist:{jti}   → 黑名单（登出时使用）

其中 jti (JWT ID) 是 token 中的唯一标识，由 security.py 在生成 token 时注入。
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import decode_token


def _generate_jti() -> str:
    """生成唯一 Token ID"""
    return uuid.uuid4().hex


def _get_access_ttl() -> int:
    """Access Token Redis TTL（秒）"""
    return settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _get_refresh_ttl() -> int:
    """Refresh Token Redis TTL（秒）"""
    return settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


async def store_access_token(jti: str, user_id: int) -> None:
    """存储 Access Token 到 Redis 白名单"""
    redis = await get_redis()
    key = f"token:access:{jti}"
    await redis.set(key, str(user_id), ex=_get_access_ttl())


async def store_refresh_token(jti: str, user_id: int) -> None:
    """存储 Refresh Token 到 Redis 白名单（同用户只保留最新，实现单设备登录）"""
    redis = await get_redis()
    key = f"token:refresh:{user_id}"
    await redis.set(key, jti, ex=_get_refresh_ttl())


async def is_access_token_valid(jti: str) -> bool:
    """检查 Access Token 是否在白名单且未被拉黑"""
    redis = await get_redis()
    # 检查黑名单
    if await redis.exists(f"token:blacklist:{jti}"):
        return False
    # 检查白名单
    return await redis.exists(f"token:access:{jti}") > 0


async def is_refresh_token_valid(jti: str, user_id: int) -> bool:
    """检查 Refresh Token 是否是当前有效的（未被替换/拉黑）"""
    redis = await get_redis()
    # 检查黑名单
    if await redis.exists(f"token:blacklist:{jti}"):
        return False
    # 检查白名单：存储的 jti 必须与传入的一致
    stored_jti = await redis.get(f"token:refresh:{user_id}")
    return stored_jti == jti


async def blacklist_token(jti: str, token_type: str) -> None:
    """将 Token 加入黑名单（登出时使用）"""
    redis = await get_redis()
    # 根据类型设置不同的 TTL
    ttl = _get_access_ttl() if token_type == "access" else _get_refresh_ttl()
    await redis.set(f"token:blacklist:{jti}", "1", ex=ttl)


async def revoke_user_tokens(user_id: int) -> None:
    """撤销用户所有 Token（修改密码/封禁时使用）"""
    redis = await get_redis()
    # 删除 refresh token 白名单，使所有 refresh token 失效
    await redis.delete(f"token:refresh:{user_id}")
    # access token 无法批量删除（不知道 jti），
    # 但可以在 get_current_user 中额外检查一个 user 版本号，此处暂不实现


async def remove_refresh_token_on_logout(user_id: int) -> None:
    """登出时删除 refresh token 白名单"""
    redis = await get_redis()
    await redis.delete(f"token:refresh:{user_id}")
