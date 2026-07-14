"""
AI 模块包

提供 AI 玩家实例创建与管理：
  - BaseAIPlayer:   AI 玩家基类
  - EasyAI:         简单难度
  - MediumAI:       中等难度
  - HardAI:         困难难度
  - AIPlayerFactory: 工厂方法
"""

from app.game.ai.player import (
    AIPlayerFactory,
    BaseAIPlayer,
    EasyAI,
    HardAI,
    MediumAI,
)

__all__ = [
    "BaseAIPlayer",
    "EasyAI",
    "MediumAI",
    "HardAI",
    "AIPlayerFactory",
]
