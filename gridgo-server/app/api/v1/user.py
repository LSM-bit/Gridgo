"""用户接口"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.game_record import GamePlayer, GameRecord
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    GamePlayerItem,
    GameRecordDetail,
    GameRecordItem,
    UpdateProfileRequest,
    UserProfile,
    UserStats,
)

router = APIRouter(prefix="/users", tags=["用户"])


@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """获取当前用户详细信息"""
    return current_user


@router.patch("/me", response_model=UserProfile)
async def update_my_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户个人信息"""
    if body.nickname is not None:
        current_user.nickname = body.nickname
    if body.avatar is not None:
        current_user.avatar = body.avatar
    if body.email is not None:
        # 检查邮箱是否已被其他用户占用
        if body.email:
            existing = await db.execute(
                select(User).where(User.email == body.email, User.id != current_user.id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="该邮箱已被使用",
                )
        current_user.email = body.email

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user


@router.post("/me/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    # 验证旧密码
    from app.core.security import verify_password

    if not verify_password(body.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )

    # 设置新密码
    from app.core.security import get_password_hash

    current_user.password_hash = get_password_hash(body.new_password)
    db.add(current_user)
    await db.flush()
    return {"message": "密码修改成功"}


@router.get("/me/stats", response_model=UserStats)
async def get_my_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户统计数据"""
    # 总局数
    total_q = await db.execute(
        select(func.count()).where(GamePlayer.user_id == current_user.id, GamePlayer.is_ai == False)
    )
    total_games = total_q.scalar() or 0

    # 胜场数（排名第1且非AI）
    wins_q = await db.execute(
        select(func.count()).where(GamePlayer.user_id == current_user.id, GamePlayer.rank == 1, GamePlayer.is_ai == False)
    )
    wins = wins_q.scalar() or 0

    # 总资产
    assets_q = await db.execute(
        select(func.coalesce(func.sum(GamePlayer.total_assets), 0)).where(
            GamePlayer.user_id == current_user.id, GamePlayer.is_ai == False
        )
    )
    total_assets = assets_q.scalar() or 0

    # 平均排名
    avg_rank_q = await db.execute(
        select(func.coalesce(func.avg(GamePlayer.rank), 0)).where(
            GamePlayer.user_id == current_user.id, GamePlayer.is_ai == False
        )
    )
    avg_rank = round(float(avg_rank_q.scalar() or 0), 2)

    # 破产次数
    bankrupt_q = await db.execute(
        select(func.count()).where(
            GamePlayer.user_id == current_user.id, GamePlayer.is_bankrupt == True, GamePlayer.is_ai == False
        )
    )
    bankruptcies = bankrupt_q.scalar() or 0

    return UserStats(
        total_games=total_games,
        wins=wins,
        total_assets=total_assets,
        avg_rank=avg_rank,
        bankruptcies=bankruptcies,
    )


@router.get("/me/records", response_model=list[GameRecordItem])
async def get_my_records(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的对局记录"""
    # 查询该用户参与的对局
    q = (
        select(GameRecord, GamePlayer)
        .join(GamePlayer, GameRecord.id == GamePlayer.game_id)
        .where(GamePlayer.user_id == current_user.id, GamePlayer.is_ai == False)
        .order_by(GameRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    items = []
    for record, player in rows:
        # 查询赢家昵称
        winner_nickname = None
        if record.winner_id:
            wp_q = await db.execute(
                select(GamePlayer.nickname).where(
                    GamePlayer.game_id == record.id, GamePlayer.user_id == record.winner_id
                )
            )
            winner_nickname = wp_q.scalar_one_or_none()

        items.append(
            GameRecordItem(
                id=record.id,
                room_id=record.room_id,
                map_id=record.map_id,
                total_turns=record.total_turns,
                player_count=record.player_count,
                winner_id=record.winner_id,
                winner_nickname=winner_nickname,
                end_reason=record.end_reason,
                created_at=record.created_at,
                my_rank=player.rank,
                my_total_assets=player.total_assets,
                my_is_bankrupt=player.is_bankrupt,
            )
        )

    return items


@router.get("/records/{game_id}", response_model=GameRecordDetail)
async def get_game_record_detail(
    game_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取对局记录详情（含所有玩家成绩）"""
    record_q = await db.execute(select(GameRecord).where(GameRecord.id == game_id))
    record = record_q.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对局记录不存在")

    # 查询该对局所有玩家
    players_q = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == game_id).order_by(GamePlayer.rank)
    )
    players = players_q.scalars().all()

    return GameRecordDetail(
        id=record.id,
        room_id=record.room_id,
        map_id=record.map_id,
        total_turns=record.total_turns,
        player_count=record.player_count,
        winner_id=record.winner_id,
        end_reason=record.end_reason,
        created_at=record.created_at,
        players=[
            GamePlayerItem(
                user_id=p.user_id,
                nickname=p.nickname,
                rank=p.rank,
                total_assets=p.total_assets,
                is_bankrupt=p.is_bankrupt,
                is_ai=p.is_ai,
                ai_difficulty=p.ai_difficulty,
            )
            for p in players
        ],
    )


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取指定用户统计数据"""
    # 检查用户存在
    user_q = await db.execute(select(User).where(User.id == user_id))
    if not user_q.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    total_q = await db.execute(
        select(func.count()).where(GamePlayer.user_id == user_id, GamePlayer.is_ai == False)
    )
    total_games = total_q.scalar() or 0

    wins_q = await db.execute(
        select(func.count()).where(GamePlayer.user_id == user_id, GamePlayer.rank == 1, GamePlayer.is_ai == False)
    )
    wins = wins_q.scalar() or 0

    assets_q = await db.execute(
        select(func.coalesce(func.sum(GamePlayer.total_assets), 0)).where(
            GamePlayer.user_id == user_id, GamePlayer.is_ai == False
        )
    )
    total_assets = assets_q.scalar() or 0

    avg_rank_q = await db.execute(
        select(func.coalesce(func.avg(GamePlayer.rank), 0)).where(
            GamePlayer.user_id == user_id, GamePlayer.is_ai == False
        )
    )
    avg_rank = round(float(avg_rank_q.scalar() or 0), 2)

    bankrupt_q = await db.execute(
        select(func.count()).where(
            GamePlayer.user_id == user_id, GamePlayer.is_bankrupt == True, GamePlayer.is_ai == False
        )
    )
    bankruptcies = bankrupt_q.scalar() or 0

    return UserStats(
        total_games=total_games,
        wins=wins,
        total_assets=total_assets,
        avg_rank=avg_rank,
        bankruptcies=bankruptcies,
    )


@router.get("/{user_id}/records", response_model=list[GameRecordItem])
async def get_user_records(
    user_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取指定用户的对局记录"""
    # 检查用户存在
    user_q = await db.execute(select(User).where(User.id == user_id))
    if not user_q.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    q = (
        select(GameRecord, GamePlayer)
        .join(GamePlayer, GameRecord.id == GamePlayer.game_id)
        .where(GamePlayer.user_id == user_id, GamePlayer.is_ai == False)
        .order_by(GameRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()

    items = []
    for record, player in rows:
        winner_nickname = None
        if record.winner_id:
            wp_q = await db.execute(
                select(GamePlayer.nickname).where(
                    GamePlayer.game_id == record.id, GamePlayer.user_id == record.winner_id
                )
            )
            winner_nickname = wp_q.scalar_one_or_none()

        items.append(
            GameRecordItem(
                id=record.id,
                room_id=record.room_id,
                map_id=record.map_id,
                total_turns=record.total_turns,
                player_count=record.player_count,
                winner_id=record.winner_id,
                winner_nickname=winner_nickname,
                end_reason=record.end_reason,
                created_at=record.created_at,
                my_rank=player.rank,
                my_total_assets=player.total_assets,
                my_is_bankrupt=player.is_bankrupt,
            )
        )

    return items
