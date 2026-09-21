"""
好友关系模型（对齐 docs/PROJECT.md 6.2 的 friendships）

status 编码：0=待确认（好友申请）1=已接受（好友）2=已拒绝
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Friendship(Base):
    """好友关系表（申请 + 关系共用一张表）"""

    __tablename__ = "friendships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="发起方 user_id")
    friend_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="接收方 user_id")
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, comment="0=待确认 1=已接受 2=已拒绝"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="申请时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "friend_id", name="uq_friendships_user_friend"),
        Index("ix_friendships_friend_id", "friend_id"),
    )
