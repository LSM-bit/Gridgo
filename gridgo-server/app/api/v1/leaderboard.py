"""
排行榜接口

对齐 docs/PROJECT.md D-03 / A-3：提供 GET /leaderboard（游客可见），
数据源 user_stats，Redis 缓存 60s。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.services.stats import StatsService

router = APIRouter(prefix="/leaderboard", tags=["排行榜"])


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=100, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    db: AsyncSession = Depends(get_db),
):
    """获取排行榜（按积分降序，同分按胜场降序）"""
    data = await StatsService.get_leaderboard(db, limit=limit, offset=offset)
    return LeaderboardResponse(
        total=data["total"],
        limit=limit,
        offset=offset,
        items=[LeaderboardEntry(**item) for item in data["items"]],
    )
