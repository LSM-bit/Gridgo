"""
游戏记录数据库模型

用于游戏结束后持久化对局记录和玩家成绩。
"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GameRecord(Base):
    """对局记录表 — 游戏结束时写入"""

    __tablename__ = "game_records"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room_id: Mapped[str] = mapped_column(String(32), nullable=False, comment="房间 ID")
    map_id: Mapped[str] = mapped_column(String(32), nullable=False, comment="地图 ID")
    total_turns: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总回合数")
    player_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="玩家数量")
    winner_id: Mapped[int] = mapped_column(nullable=True, comment="胜者 user_id（AI 为负数）")
    end_reason: Mapped[str] = mapped_column(String(20), nullable=False, comment="结束原因: last_standing / turn_limit / vote_end")
    config_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True, comment="对局配置快照 JSON")
    actions: Mapped[str | None] = mapped_column(Text, nullable=True, comment="压缩编码的操作序列")
    final_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最终状态快照 JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")


class GamePlayer(Base):
    """对局玩家表 — 记录每位玩家的最终成绩"""

    __tablename__ = "game_players"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="对局记录 ID")
    user_id: Mapped[int] = mapped_column(nullable=False, comment="玩家 user_id（AI 为负数）")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="显示昵称")
    rank: Mapped[int] = mapped_column(Integer, nullable=False, comment="最终排名")
    total_assets: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="最终总资产")
    settlement_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="结算金额（正=盈利，负=亏损")
    is_bankrupt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否破产")
    is_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否 AI")
    ai_difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="AI 难度")
