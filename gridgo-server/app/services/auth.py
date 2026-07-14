"""
认证业务逻辑层
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import AuthResponse, TokenData, UserInfo
from app.services.token import (
    is_access_token_valid,
    is_refresh_token_valid,
    store_access_token,
    store_refresh_token,
)


def _build_user_info(user: User) -> UserInfo:
    """从 ORM 对象构建 UserInfo，避免触发 SQLAlchemy 懒加载"""
    return UserInfo(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        avatar=user.avatar,
        status=user.status,
    )


async def _create_token_pair(user_id: int, username: str) -> TokenData:
    """生成 Token 对并存储到 Redis"""
    token_data = {"sub": str(user_id), "username": username}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # 解析 jti，存入 Redis
    access_payload = decode_token(access_token)
    refresh_payload = decode_token(refresh_token)

    await store_access_token(access_payload["jti"], user_id)
    await store_refresh_token(refresh_payload["jti"], user_id)

    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
    )


class AuthService:
    """认证服务"""

    @staticmethod
    async def register(
        db: AsyncSession,
        username: str,
        password: str,
        nickname: str,
    ) -> AuthResponse:
        """用户注册"""
        # 检查用户名是否已存在
        result = await db.execute(select(User).where(User.username == username))
        if result.scalars().first():
            raise ValueError("用户名已存在")

        # 创建用户
        user = User(
            username=username,
            password_hash=get_password_hash(password),
            nickname=nickname,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)

        # 生成 Token 并存入 Redis
        token = await _create_token_pair(user.id, user.username)

        return AuthResponse(user=_build_user_info(user), token=token)

    @staticmethod
    async def login(
        db: AsyncSession,
        username: str,
        password: str,
    ) -> AuthResponse:
        """用户登录"""
        # 查找用户
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        if not user:
            raise ValueError("用户名或密码错误")

        # 验证密码
        if not verify_password(password, user.password_hash):
            raise ValueError("用户名或密码错误")

        # 检查状态
        if user.status != 0:
            raise ValueError("账号已被禁用")

        # 生成 Token 并存入 Redis
        token = await _create_token_pair(user.id, user.username)

        return AuthResponse(user=_build_user_info(user), token=token)

    @staticmethod
    async def refresh_token(
        db: AsyncSession,
        refresh_token: str,
    ) -> TokenData:
        """刷新 Token"""
        # 解码 refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("无效的 Refresh Token")

        jti = payload.get("jti")
        user_id = int(payload.get("sub"))

        # 检查 Redis 中该 refresh token 是否有效
        if not await is_refresh_token_valid(jti, user_id):
            raise ValueError("Refresh Token 已失效，请重新登录")

        # 查找用户
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user or user.status != 0:
            raise ValueError("用户不存在或已被禁用")

        # 生成新 Token 对并存储
        token = await _create_token_pair(user.id, user.username)
        return token

    @staticmethod
    async def get_current_user(
        db: AsyncSession,
        token: str,
    ) -> User:
        """根据 Token 获取当前用户"""
        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            raise ValueError("无效的 Access Token")

        jti = payload.get("jti")

        # 检查 Redis 中该 access token 是否有效
        if not await is_access_token_valid(jti):
            raise ValueError("Access Token 已失效，请重新登录")

        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalars().first()
        if not user:
            raise ValueError("用户不存在")
        if user.status != 0:
            raise ValueError("账号已被禁用")

        return user
