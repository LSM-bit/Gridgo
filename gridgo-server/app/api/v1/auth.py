"""
认证接口
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenData,
    UserInfo,
)
from app.services.auth import AuthService, _build_user_info
from app.services.token import blacklist_token, remove_refresh_token_on_logout

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    try:
        result = await AuthService.register(db, body.username, body.password, body.nickname)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    try:
        result = await AuthService.login(db, body.username, body.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenData)
async def refresh_token(body: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """刷新 Token"""
    try:
        result = await AuthService.refresh_token(db, body.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout")
async def logout(request: Request, current_user: User = Depends(get_current_user)):
    """用户登出

    将当前 Access Token 加入黑名单，并删除 Refresh Token 白名单。
    """
    # 从请求头提取 Bearer Token
    auth_header = request.headers.get("Authorization", "")
    token_str = auth_header.replace("Bearer ", "")

    # 解析 jti，加入黑名单
    payload = decode_token(token_str)
    if payload:
        jti = payload.get("jti")
        if jti:
            await blacklist_token(jti, "access")

    # 删除 Refresh Token 白名单（使 refresh token 也失效）
    await remove_refresh_token_on_logout(current_user.id)

    return {"code": 0, "message": "登出成功"}


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return _build_user_info(current_user)
