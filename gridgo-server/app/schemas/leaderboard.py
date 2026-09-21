"""
排行榜相关的 Pydantic 模型

对齐 docs/PROJECT.md D-03：GET /leaderboard 返回积分榜（游客可见）。
"""

from pydantic import BaseModel, Field


class LeaderboardEntry(BaseModel):
    """排行榜单条记录"""

    rank: int = Field(..., description="名次（从 1 开始）")
    user_id: int = Field(..., description="用户 ID")
    username: str = Field(default="", description="用户名")
    nickname: str = Field(..., description="昵称")
    avatar: str | None = Field(default=None, description="头像地址")
    score: int = Field(default=0, description="积分")
    total_games: int = Field(default=0, description="总场次")
    total_wins: int = Field(default=0, description="胜场")
    best_rank: int | None = Field(default=None, description="历史最佳名次")
    win_streak: int = Field(default=0, description="当前连胜")


class LeaderboardResponse(BaseModel):
    """排行榜响应"""

    total: int = Field(default=0, description="榜单总人数")
    limit: int = Field(default=50, description="本次返回条数上限")
    offset: int = Field(default=0, description="偏移量")
    items: list[LeaderboardEntry] = Field(default_factory=list, description="榜单条目")
