"""
用户数据库模型
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.utils.snowflake import generate_user_id


class User(Base):
    """用户表"""

    __tablename__ = "users"

    # 主键：64 位雪花 ID（应用层生成，不用自增序列）
    # 由 app/utils/snowflake.py 保证 <= 2^63 - 1 且全局唯一
    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
        default=generate_user_id,
        comment="用户 ID（64 位雪花 ID，非自增）",
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="显示昵称")
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="头像URL")
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, comment="邮箱")
    status: Mapped[int] = mapped_column(default=0, comment="0=正常 1=禁用")
    active_room_id: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="当前活跃房间 ID（同一用户同时只能有一个，NULL=无）"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), comment="注册时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

