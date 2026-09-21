"""
房间持久化模型（对齐 docs/PROJECT.md 6.2 的 rooms / room_players）

设计说明：
  - 运行时的房间状态仍以「内存 + Redis」为准（app/services/room.py 是唯一入口），
    本模型是写穿透（write-through）镜像，用于房间历史追溯与
    game_records.room_id 的关联语义对齐。
  - rooms.id 采用 VARCHAR(32)：运行时房间 ID 是 12 位 uuid 短串，
    且 game_records.room_id 已是 String(32)，保持一致才能建立真实关联。
  - status 采用枚举编码 0=等待 / 1=游戏中 / 2=已结束（文档 6.2 口径）。
  - room_players.ai_difficulty 采用字符串（easy/medium/hard），
    与 game_players.ai_difficulty（String(10)）及运行时 PlayerState 保持一致。
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Room(Base):
    """房间表（Redis 运行时状态的持久化镜像）"""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="房间 ID")
    room_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, comment="6 位房间代码")
    name: Mapped[str] = mapped_column(String(50), nullable=False, default="GridGo 房间", comment="房间名称")
    host_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="房主 user_id")
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="房间密码哈希（无密码为 NULL）"
    )
    max_players: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=8, comment="最大玩家数")
    map_id: Mapped[str] = mapped_column(String(32), nullable=False, default="classic", comment="地图 ID")
    ai_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, comment="AI 数量")
    ai_difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="easy", comment="AI 难度")
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="0=等待 1=游戏中 2=已结束"
    )
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="房间配置快照")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    __table_args__ = (Index("ix_rooms_status", "status"),)


class RoomPlayerRow(Base):
    """房间玩家表（房间内玩家 / AI 的持久化镜像）"""

    __tablename__ = "room_players"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    room_id: Mapped[str] = mapped_column(String(32), nullable=False, comment="房间 ID")
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="玩家 user_id（AI 为负数）")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="显示昵称")
    is_host: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否房主")
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已准备")
    is_ai: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否 AI")
    ai_difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="AI 难度")
    is_spectator: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否观战者")
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="加入时间")

    __table_args__ = (
        UniqueConstraint("room_id", "user_id", name="uq_room_players_room_user"),
        Index("ix_room_players_room_id", "room_id"),
    )
