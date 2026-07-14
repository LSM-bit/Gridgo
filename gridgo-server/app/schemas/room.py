"""
房间相关的 Pydantic 模型
"""

from datetime import datetime

from pydantic import BaseModel, Field


# ─── 请求模型 ───


class CreateRoomRequest(BaseModel):
    """创建房间请求"""

    name: str = Field(default="GridGo 房间", max_length=50, description="房间名称")
    max_players: int = Field(default=8, ge=2, le=8, description="最大玩家数")
    map_id: str = Field(default="classic", description="地图 ID")
    ai_count: int = Field(default=0, ge=0, le=8, description="AI 数量")
    ai_difficulty: str = Field(default="easy", description="AI 难度: easy/medium/hard")

    def model_post_init(self, __context) -> None:
        """校验 ai_count 不超过 max_players"""
        if self.ai_count > self.max_players:
            raise ValueError(f"AI 数量({self.ai_count})不能超过最大玩家数({self.max_players})")


class UpdateRoomRequest(BaseModel):
    """更新房间设置请求（仅房主）"""

    name: str | None = Field(default=None, max_length=50, description="房间名称")
    max_players: int | None = Field(default=None, ge=2, le=8, description="最大玩家数")
    map_id: str | None = Field(default=None, description="地图 ID")
    ai_count: int | None = Field(default=None, ge=0, le=8, description="AI 数量")
    ai_difficulty: str | None = Field(default=None, description="AI 难度: easy/medium/hard")


class JoinRoomRequest(BaseModel):
    """加入房间请求"""

    code: str = Field(..., min_length=6, max_length=6, description="6位房间代码")
    as_spectator: bool = Field(default=False, description="以观战者身份加入")


class SwitchRoleRequest(BaseModel):
    """切换角色请求（玩家 ↔ 观战者）"""

    to_spectator: bool = Field(..., description="True=切换为观战者，False=切换为玩家")


class SpectatorInfo(BaseModel):
    """观战者信息"""

    user_id: int
    username: str
    nickname: str
    avatar: str | None = None
    is_host: bool = False  # 房主也可以是观战者


# ─── 响应模型 ───


class RoomPlayer(BaseModel):
    """房间中的玩家"""

    user_id: int
    username: str
    nickname: str
    avatar: str | None = None
    is_host: bool = False
    is_ready: bool = False
    is_ai: bool = False
    ai_difficulty: str | None = None


class RoomInfo(BaseModel):
    """房间信息"""

    id: str
    code: str
    name: str
    host_id: int
    max_players: int
    map_id: str = "classic"
    ai_count: int = 0
    ai_difficulty: str = "easy"
    status: str  # waiting / playing / finished
    players: list[RoomPlayer] = []
    spectators: list[SpectatorInfo] = []  # 观战者列表
    max_spectators: int = 10  # 最大观战人数
    created_at: datetime | None = None


class RoomListItem(BaseModel):
    """房间列表项（简要信息）"""

    id: str
    code: str
    name: str
    host_nickname: str
    player_count: int
    max_players: int
    map_id: str = "classic"
    ai_count: int = 0
    spectator_count: int = 0  # 观战人数
    status: str
