"""
用户统计与排行榜服务

数据来源：user_stats（聚合统计，对局结束时更新）
排行榜缓存：Redis（docs/PROJECT.md A-3 声明"Redis 用于排行榜"），
            缓存键 leaderboard:{limit}:{offset}，TTL 60s，结算后主动失效。
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stats import UserStats
from app.models.user import User

logger = logging.getLogger(__name__)

WIN_SCORE = 30  # docs/GAME_FLOW.md 4.2：胜者 score += 30
LOSE_SCORE = 10  # docs/GAME_FLOW.md 4.2：败者 score -= 10
LEADERBOARD_CACHE_TTL = 60
LEADERBOARD_CACHE_PATTERN = "leaderboard:*"


class StatsService:
    """用户统计 / 排行榜"""

    # ─── 结算 ───

    @staticmethod
    async def apply_game_settlement(
        ranking_data: list[dict],
        *,
        winner_id: int | None,
        end_reason: str = "",
        rent_stats: dict[int, dict[str, int]] | None = None,
    ) -> None:
        """
        对局结束后更新 user_stats

        Args:
            ranking_data: 排名列表，元素含 user_id / rank / is_bankrupt / is_ai
            winner_id: 胜者 user_id（AI 为负数）
            end_reason: 结束原因（last_standing / turn_limit / vote_end）
            rent_stats: {user_id: {"collected": int, "paid": int}} 本局租金流水
        """
        # 延迟导入，避免与 core.database 的循环依赖
        from app.core.database import async_session

        rent_stats = rent_stats or {}
        try:
            async with async_session() as db:
                for entry in ranking_data:
                    uid = entry.get("user_id")
                    if uid is None or uid < 0 or entry.get("is_ai"):
                        continue  # AI 不参与统计

                    row = await db.get(UserStats, uid)
                    if row is None:
                        row = UserStats(user_id=uid, score=0)
                        db.add(row)
                        await db.flush()

                    rank = int(entry.get("rank") or 0)
                    is_winner = uid == winner_id

                    row.total_games = (row.total_games or 0) + 1
                    if is_winner:
                        row.total_wins = (row.total_wins or 0) + 1
                        row.win_streak = (row.win_streak or 0) + 1
                        row.best_win_streak = max(row.best_win_streak or 0, row.win_streak)
                        row.score = (row.score or 0) + WIN_SCORE
                    else:
                        row.win_streak = 0
                        row.score = (row.score or 0) - LOSE_SCORE

                    if entry.get("is_bankrupt"):
                        row.total_bankruptcies = (row.total_bankruptcies or 0) + 1

                    flow = rent_stats.get(int(uid)) or {}
                    row.total_rent_collected = (row.total_rent_collected or 0) + int(flow.get("collected", 0))
                    row.total_rent_paid = (row.total_rent_paid or 0) + int(flow.get("paid", 0))

                    if rank > 0:
                        row.best_rank = rank if not row.best_rank else min(row.best_rank, rank)

                    db.add(row)

                await db.commit()
            logger.info("[UserStats] settlement applied: winner_id=%s reason=%s", winner_id, end_reason)
        except Exception as e:  # 统计失败不影响对局结束流程
            logger.error("[UserStats] settlement failed: %s", e)

        await StatsService.invalidate_leaderboard_cache()

    # ─── 查询 ───

    @staticmethod
    async def get_stats(db: AsyncSession, user_id: int) -> dict:
        """获取单个用户的统计（不存在时返回零值）"""
        row = await db.get(UserStats, user_id)
        if row is None:
            return {
                "score": 0,
                "total_games": 0,
                "total_wins": 0,
                "total_bankruptcies": 0,
                "total_rent_collected": 0,
                "total_rent_paid": 0,
                "best_rank": None,
                "win_streak": 0,
                "best_win_streak": 0,
            }
        return {
            "score": row.score or 0,
            "total_games": row.total_games or 0,
            "total_wins": row.total_wins or 0,
            "total_bankruptcies": row.total_bankruptcies or 0,
            "total_rent_collected": row.total_rent_collected or 0,
            "total_rent_paid": row.total_rent_paid or 0,
            "best_rank": row.best_rank,
            "win_streak": row.win_streak or 0,
            "best_win_streak": row.best_win_streak or 0,
        }

    @staticmethod
    async def get_leaderboard(db: AsyncSession, limit: int = 50, offset: int = 0) -> dict:
        """
        获取排行榜（按 score 降序，同分按胜场降序、user_id 升序）

        Returns:
            {"total": int, "items": [...]}
        """
        cache_key = f"leaderboard:{limit}:{offset}"
        redis = await StatsService._redis()

        if redis is not None:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning("[Leaderboard] cache read failed: %s", e)

        rows_q = await db.execute(
            select(UserStats, User)
            .join(User, User.id == UserStats.user_id)
            .where(UserStats.total_games > 0)
            .order_by(
                UserStats.score.desc(),
                UserStats.total_wins.desc(),
                UserStats.user_id.asc(),
            )
            .offset(offset)
            .limit(limit)
        )
        rows = rows_q.all()

        total_q = await db.execute(
            select(func.count()).select_from(UserStats).where(UserStats.total_games > 0)
        )
        total = total_q.scalar() or 0

        items = []
        for i, (stat, user) in enumerate(rows):
            games = stat.total_games or 0
            wins = stat.total_wins or 0
            items.append(
                {
                    "rank": offset + i + 1,
                    "user_id": user.id,
                    "username": user.username,
                    "nickname": user.nickname,
                    "avatar": user.avatar,
                    "score": stat.score or 0,
                    "total_games": games,
                    "total_wins": wins,
                    "win_rate": round(wins / games, 4) if games else 0.0,
                    "win_streak": stat.win_streak or 0,
                    "best_rank": stat.best_rank,
                }
            )

        result = {"total": total, "items": items}

        if redis is not None:
            try:
                await redis.set(cache_key, json.dumps(result, ensure_ascii=False), ex=LEADERBOARD_CACHE_TTL)
            except Exception as e:
                logger.warning("[Leaderboard] cache write failed: %s", e)

        return result

    # ─── 缓存 ───

    @staticmethod
    async def invalidate_leaderboard_cache() -> None:
        """排行榜缓存失效（结算后调用）"""
        redis = await StatsService._redis()
        if redis is None:
            return
        try:
            keys = [key async for key in redis.scan_iter(match=LEADERBOARD_CACHE_PATTERN)]
            if keys:
                await redis.delete(*keys)
        except Exception as e:
            logger.warning("[Leaderboard] cache invalidate failed: %s", e)

    @staticmethod
    async def _redis():
        """安全获取 Redis 客户端（不可用时返回 None）"""
        try:
            from app.core.redis import get_redis

            return await get_redis()
        except Exception as e:
            logger.warning("[Leaderboard] redis unavailable: %s", e)
            return None
