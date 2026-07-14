"""
用户相关的 Pydantic 模型
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


# ─── 请求模型 ───


class UpdateProfileRequest(BaseModel):
    """修改个人信息请求"""

    nickname: str | None = Field(default=None, min_length=1, max_length=50, description="显示昵称")
    avatar: str | None = Field(default=None, max_length=255, description="头像URL")
    email: str | None = Field(default=None, max_length=100, description="邮箱")

    @field_validator("nickname")
    @classmethod
    def nickname_not_blank(cls, v: str | None) -> str | None:
        if v is not None and v.strip() == "":
            raise ValueError("昵称不能为空白")
        return v


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., min_length=6, max_length=72, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=72, description="新密码")


# ─── 响应模型 ───


class UserProfile(BaseModel):
    """用户详细信息（个人中心用）"""

    id: int
    username: str
    nickname: str
    avatar: str | None = None
    email: str | None = None
    status: int = 0
    created_at: datetime | None = None


class UserStats(BaseModel):
    """用户统计数据"""

    total_games: int = 0
    wins: int = 0
    total_assets: int = 0
    avg_rank: float = 0.0
    bankruptcies: int = 0


class GameRecordItem(BaseModel):
    """对局记录条目"""

    id: int
    room_id: str
    map_id: str
    total_turns: int
    player_count: int
    winner_id: int | None
    winner_nickname: str | None = None
    end_reason: str
    created_at: datetime | None = None
    # 当前用户在这局中的成绩
    my_rank: int | None = None
    my_total_assets: int | None = None
    my_is_bankrupt: bool | None = None


class GameRecordDetail(BaseModel):
    """对局记录详情（含所有玩家成绩）"""

    id: int
    room_id: str
    map_id: str
    total_turns: int
    player_count: int
    winner_id: int | None
    end_reason: str
    created_at: datetime | None = None
    players: list["GamePlayerItem"] = []


class GamePlayerItem(BaseModel):
    """对局中的玩家成绩"""

    user_id: int
    nickname: str
    rank: int
    total_assets: int
    is_bankrupt: bool
    is_ai: bool
    ai_difficulty: str | None = None
