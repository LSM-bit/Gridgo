"""
好友关系服务

对齐 docs/PROJECT.md S-04 / 6.2 friendships 表：
  - 好友申请 / 接受 / 拒绝 / 删除
  - 好友列表（含昵称、头像、当前积分）
status 编码：0=待确认 1=已接受 2=已拒绝
"""

from __future__ import annotations

import logging

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friend import Friendship
from app.models.stats import UserStats
from app.models.user import User

logger = logging.getLogger(__name__)

STATUS_PENDING = 0
STATUS_ACCEPTED = 1
STATUS_REJECTED = 2


class FriendService:
    """好友关系服务"""

    @staticmethod
    async def send_request(db: AsyncSession, user_id: int, target_id: int) -> Friendship:
        """发送好友申请"""
        if user_id == target_id:
            raise ValueError("不能添加自己为好友")

        target = await db.get(User, target_id)
        if not target or target.status != 0:
            raise ValueError("目标用户不存在")

        # 已存在的关系（任一方向）
        existing = await FriendService._find_relation(db, user_id, target_id)
        if existing:
            if existing.status == STATUS_ACCEPTED:
                raise ValueError("你们已经是好友")
            if existing.status == STATUS_PENDING:
                if existing.user_id == user_id:
                    raise ValueError("好友申请已发送，等待对方确认")
                raise ValueError("对方已向你发送好友申请，请直接确认")
            # 已拒绝 → 允许重新发起（复用同一行）
            existing.user_id = user_id
            existing.friend_id = target_id
            existing.status = STATUS_PENDING
            db.add(existing)
            await db.flush()
            return existing

        relation = Friendship(user_id=user_id, friend_id=target_id, status=STATUS_PENDING)
        db.add(relation)
        await db.flush()
        return relation

    @staticmethod
    async def respond_request(
        db: AsyncSession, user_id: int, request_id: int, accept: bool
    ) -> Friendship:
        """确认 / 拒绝好友申请（仅接收方可操作）"""
        relation = await db.get(Friendship, request_id)
        if not relation or relation.status != STATUS_PENDING:
            raise ValueError("好友申请不存在或已处理")
        if relation.friend_id != user_id:
            raise ValueError("无权处理该好友申请")

        relation.status = STATUS_ACCEPTED if accept else STATUS_REJECTED
        db.add(relation)
        await db.flush()
        return relation

    @staticmethod
    async def delete_friend(db: AsyncSession, user_id: int, friend_id: int) -> None:
        """删除好友（删除双向关系）"""
        relation = await FriendService._find_relation(db, user_id, friend_id)
        if not relation or relation.status != STATUS_ACCEPTED:
            raise ValueError("你们还不是好友")
        await db.delete(relation)
        await db.flush()

    @staticmethod
    async def list_friends(db: AsyncSession, user_id: int) -> list[dict]:
        """好友列表（含积分）"""
        q = await db.execute(
            select(Friendship, User, UserStats)
            .join(
                User,
                or_(
                    (Friendship.user_id == user_id) & (User.id == Friendship.friend_id),
                    (Friendship.friend_id == user_id) & (User.id == Friendship.user_id),
                ),
            )
            .outerjoin(UserStats, UserStats.user_id == User.id)
            .where(
                Friendship.status == STATUS_ACCEPTED,
                or_(Friendship.user_id == user_id, Friendship.friend_id == user_id),
            )
        )
        rows = q.all()
        return [
            {
                "user_id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "score": (stat.score if stat else 0) or 0,
                "total_games": (stat.total_games if stat else 0) or 0,
                "total_wins": (stat.total_wins if stat else 0) or 0,
                "friendship_id": relation.id,
            }
            for relation, user, stat in rows
        ]

    @staticmethod
    async def list_requests(db: AsyncSession, user_id: int) -> list[dict]:
        """收到的好友申请（待确认）"""
        q = await db.execute(
            select(Friendship, User)
            .join(User, User.id == Friendship.user_id)
            .where(Friendship.friend_id == user_id, Friendship.status == STATUS_PENDING)
            .order_by(Friendship.created_at.desc())
        )
        rows = q.all()
        return [
            {
                "request_id": relation.id,
                "user_id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "avatar": user.avatar,
                "created_at": relation.created_at,
            }
            for relation, user in rows
        ]

    @staticmethod
    async def are_friends(db: AsyncSession, user_a: int, user_b: int) -> bool:
        """判断两人是否为好友"""
        relation = await FriendService._find_relation(db, user_a, user_b)
        return bool(relation and relation.status == STATUS_ACCEPTED)

    # ─── 内部 ───

    @staticmethod
    async def _find_relation(db: AsyncSession, user_a: int, user_b: int) -> Friendship | None:
        q = await db.execute(
            select(Friendship).where(
                or_(
                    (Friendship.user_id == user_a) & (Friendship.friend_id == user_b),
                    (Friendship.user_id == user_b) & (Friendship.friend_id == user_a),
                )
            )
        )
        return q.scalars().first()
