"""游戏接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.game.replay import parse_replay_data
from app.models.game_record import GamePlayer, GameRecord
from app.models.user import User
from app.schemas.game import GameInfoResponse
from app.services.game import GameService
from app.services.room import RoomService

router = APIRouter(prefix="/games", tags=["游戏"])


@router.get("/{room_id}", response_model=GameInfoResponse)
async def get_game(room_id: str):
    """获取对局信息"""
    state = await GameService.get_game_state(room_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对局不存在")

    current_player = state.get_current_player()
    return GameInfoResponse(
        game_id=state.game_id,
        room_id=state.room_id,
        map_id=state.map_id,
        turn_number=state.turn_number,
        current_player_id=current_player.user_id if current_player else None,
        phase=state.phase.value,
        player_count=len(state.get_active_players()),
        is_over=state.phase.value == "GAME_OVER",
    )


@router.get("/{room_id}/state")
async def get_game_state(room_id: str):
    """获取完整游戏状态（调试用）"""
    snapshot = await GameService.get_snapshot(room_id)
    if not snapshot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对局不存在")
    return {"code": 0, "data": snapshot}


@router.get("/{room_id}/log")
async def get_game_log(room_id: str, db: AsyncSession = Depends(get_db)):
    """获取对局日志（从 game_records 查询已结束的对局）"""
    result = await db.execute(
        select(GameRecord).where(GameRecord.room_id == room_id)
    )
    record = result.scalars().first()
    if not record:
        return {"code": 0, "data": None}

    # 查询玩家记录
    result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == record.id).order_by(GamePlayer.rank)
    )
    players = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "game_id": record.id,
            "room_id": record.room_id,
            "map_id": record.map_id,
            "total_turns": record.total_turns,
            "winner_id": record.winner_id,
            "end_reason": record.end_reason,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "players": [
                {
                    "rank": p.rank,
                    "user_id": p.user_id,
                    "nickname": p.nickname,
                    "total_assets": p.total_assets,
                    "is_bankrupt": p.is_bankrupt,
                    "is_ai": p.is_ai,
                }
                for p in players
            ],
        },
    }


@router.post("/{room_id}/surrender")
async def surrender(
    room_id: str,
    current_user: User = Depends(get_current_user),
):
    """投降（将自己标记为破产）"""
    state = await GameService.get_game_state(room_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对局不存在")

    player = state.get_player_by_id(current_user.id)
    if not player:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="你不在该对局中")

    if player.is_bankrupt:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="你已破产")

    # 标记破产（欠银行）
    from app.game.engine import get_engine
    engine = get_engine(room_id)
    await engine.load_state()
    await engine._handle_bankruptcy(current_user.id, creditor_id=0, debt=0)
    player.is_bankrupt = True
    await engine._save_state()

    # 检查游戏是否结束
    active = state.get_active_players()
    if len(active) <= 1:
        await engine._game_over(engine.state.EndReason.LAST_STANDING if hasattr(engine.state, 'EndReason') else "last_standing")

    return {"code": 0, "message": "已投降"}


# ─── 对局回放 & 历史记录 ───


@router.get("/replay/{game_id}")
async def get_game_replay(
    game_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取对局回放数据（含解析后的操作序列）"""
    result = await db.execute(
        select(GameRecord).where(GameRecord.id == game_id)
    )
    record = result.scalars().first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对局记录不存在")

    # 解析压缩的操作序列
    replay = parse_replay_data(
        init_snapshot_json=record.config_snapshot,
        actions_encoded=record.actions or "",
        final_snapshot_json=record.final_snapshot,
    )

    # 查询玩家记录
    result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == record.id).order_by(GamePlayer.rank)
    )
    players = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "game_id": record.id,
            "room_id": record.room_id,
            "map_id": record.map_id,
            "total_turns": record.total_turns,
            "winner_id": record.winner_id,
            "end_reason": record.end_reason,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "players": [
                {
                    "rank": p.rank,
                    "user_id": p.user_id,
                    "nickname": p.nickname,
                    "total_assets": p.total_assets,
                    "settlement_amount": p.settlement_amount,
                    "is_bankrupt": p.is_bankrupt,
                    "is_ai": p.is_ai,
                }
                for p in players
            ],
            "replay": replay,
        },
    }


@router.get("/history/{user_id}")
async def get_user_game_history(
    user_id: int,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的对局历史记录"""
    # 只能查看自己的历史，或公开数据
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权查看他人历史")

    # 查询该用户参与的对局
    result = await db.execute(
        select(GamePlayer)
        .where(GamePlayer.user_id == user_id)
        .order_by(GamePlayer.id.desc())
        .offset(offset)
        .limit(limit)
    )
    player_records = result.scalars().all()

    if not player_records:
        return {"code": 0, "data": [], "total": 0}

    # 获取对应的对局记录
    game_ids = [p.game_id for p in player_records]
    result = await db.execute(
        select(GameRecord).where(GameRecord.id.in_(game_ids))
    )
    game_records = {r.id: r for r in result.scalars().all()}

    # 获取每场对局的所有玩家
    result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id.in_(game_ids))
    )
    all_players = result.scalars().all()

    # 按 game_id 分组
    players_by_game: dict[int, list] = {}
    for p in all_players:
        players_by_game.setdefault(p.game_id, []).append(p)

    # 组装返回数据
    history = []
    for pr in player_records:
        game = game_records.get(pr.game_id)
        if not game:
            continue
        game_players = players_by_game.get(pr.game_id, [])
        game_players.sort(key=lambda p: p.rank)
        history.append({
            "game_id": game.id,
            "room_id": game.room_id,
            "map_id": game.map_id,
            "total_turns": game.total_turns,
            "end_reason": game.end_reason,
            "created_at": game.created_at.isoformat() if game.created_at else None,
            "my_rank": pr.rank,
            "my_settlement": pr.settlement_amount,
            "winner_id": game.winner_id,
            "players": [
                {
                    "rank": p.rank,
                    "user_id": p.user_id,
                    "nickname": p.nickname,
                    "total_assets": p.total_assets,
                    "settlement_amount": p.settlement_amount,
                    "is_bankrupt": p.is_bankrupt,
                    "is_ai": p.is_ai,
                }
                for p in game_players
            ],
        })

    return {"code": 0, "data": history, "total": len(player_records)}
