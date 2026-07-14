"""
聊天相关的 Pydantic 模型
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── 请求模型 ───


class SendMessageRequest(BaseModel):
    """发送聊天消息请求"""

    content: str = Field(..., min_length=1, max_length=500, description="消息内容")


# ─── 响应模型 ───


class ChatMessage(BaseModel):
    """聊天消息"""

    id: str = Field(..., description="消息 ID（Redis 自增序号）")
    room_id: str = Field(..., description="房间 ID")
    user_id: int = Field(..., description="发送者 ID（AI 为负数）")
    nickname: str = Field(..., description="发送者昵称")
    is_ai: bool = Field(default=False, description="是否 AI 消息")
    content: str = Field(..., description="消息内容")
    created_at: str = Field(..., description="发送时间 ISO 格式")
