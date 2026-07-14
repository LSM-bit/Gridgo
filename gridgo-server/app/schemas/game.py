"""
游戏相关的 Pydantic 模型
"""

from pydantic import BaseModel, Field


class GameInfoResponse(BaseModel):
    """游戏信息响应"""

    game_id: str
    room_id: str
    map_id: str
    turn_number: int
    current_player_id: int | None = None
    phase: str
    player_count: int
    is_over: bool = False


class PlayerRanking(BaseModel):
    """玩家排名"""

    rank: int
    user_id: int
    nickname: str
    total_assets: int
    is_bankrupt: bool = False
    is_ai: bool = False


class GameOverData(BaseModel):
    """游戏结束数据"""

    end_reason: str
    winner_id: int | None = None
    rankings: list[PlayerRanking] = []
    total_turns: int = 0
