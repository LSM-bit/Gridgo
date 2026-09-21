"""
统计数据库模型（对齐 docs/PROJECT.md 6.2 的 user_stats / game_turn_logs）

  - user_stats：每名玩家一行的累计统计，排行榜（GET /leaderboard）与个人中心数据源。
    结算规则见 docs/GAME_FLOW.md 4.2：胜者 +30 分、败者 -10 分。
  - game_turn_logs：逐回合操作日志，记录骰子、操作类型与操作详情。
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserStats(Base):
    """用户统计表 — 游戏结束时更新"""

    __tablename__ = "user_stats"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, comment="用户 ID")
    total_games: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总局数")
    total_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="总胜场")
    total_bankruptcies: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="破产次数")
    total_rent_collected: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, comment="累计收取租金"
    )
    total_rent_paid: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="累计支付租金")
    best_rank: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="历史最佳排名")
    win_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="当前连胜")
    best_win_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="历史最高连胜")
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="积分（排行榜排序依据）")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class GameTurnLog(Base):
    """回合日志表 — 记录每回合的骰子与操作"""

    __tablename__ = "game_turn_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="对局记录 ID（game_records.id）")
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="回合数")
    player_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="操作玩家 user_id（AI 为负数）")
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型")
    action_data: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="操作详情")
    dice_values: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="骰子点数，如 3,5")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="记录时间")

    __table_args__ = ()
