"""
好友相关的 Pydantic 模型

对齐 docs/PROJECT.md S-04：好友申请、好友列表、删除好友。
"""

from datetime import datetime

from pydantic import BaseModel, Field


class FriendRequestBody(BaseModel):
    """发送好友申请"""

    target_id: int = Field(..., description="目标用户 ID")


class RespondFriendRequest(BaseModel):
    """处理好友申请"""

    accept: bool = Field(..., description="True=接受，False=拒绝")


class FriendItem(BaseModel):
    """好友列表项"""

    user_id: int
    username: str
    nickname: str
    avatar: str | None = None
    score: int = 0
    total_games: int = 0
    total_wins: int = 0
    friendship_id: int


class FriendRequestItem(BaseModel):
    """收到的好友申请"""

    request_id: int
    user_id: int
    username: str
    nickname: str
    avatar: str | None = None
    created_at: datetime | None = None
