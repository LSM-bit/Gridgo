"""
认证相关的 Pydantic 模型
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ─── 请求模型 ───


class RegisterRequest(BaseModel):
    """注册请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=72, description="密码")
    nickname: str = Field(..., min_length=1, max_length=50, description="显示昵称")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("用户名只能包含字母和数字")
        return v


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""

    refresh_token: str = Field(..., description="Refresh Token")


# ─── 响应模型 ───


class UserInfo(BaseModel):
    """用户信息"""

    id: int
    username: str
    nickname: str
    avatar: str | None = None
    status: int = 0
    created_at: datetime | None = None


class TokenData(BaseModel):
    """Token 数据"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(BaseModel):
    """认证响应（含用户信息和 Token）"""

    user: UserInfo
    token: TokenData
