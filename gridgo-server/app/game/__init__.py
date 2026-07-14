"""
游戏引擎包

提供游戏核心逻辑：
  - schemas: 游戏状态数据模型（GameState, PlayerState, TileState 等）
  - engine:  游戏引擎（GameEngine），状态机驱动的回合循环
  - events:  WebSocket 事件管理器（ConnectionManager）
"""

from app.game.engine import GameEngine, get_engine, remove_engine
from app.game.events import manager as ws_manager
from app.game.schemas import GamePhase, GameState

__all__ = [
    "GameState",
    "GamePhase",
    "GameEngine",
    "get_engine",
    "remove_engine",
    "ws_manager",
]
