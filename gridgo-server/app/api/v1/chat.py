"""聊天接口"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatMessage, SendMessageRequest
from app.schemas.room import RoomPlayer, SpectatorInfo
from app.services.chat import ChatService
from app.services.room import RoomService

router = APIRouter(prefix="/rooms/{room_id}/chat", tags=["聊天"])


def _find_player(room_players: list[RoomPlayer], user_id: int) -> RoomPlayer | None:
    """在房间玩家列表中查找指定玩家"""
    return next((p for p in room_players if p.user_id == user_id), None)


def _find_spectator(room_spectators: list[SpectatorInfo], user_id: int) -> SpectatorInfo | None:
    """在房间观战者列表中查找指定观战者"""
    return next((s for s in room_spectators if s.user_id == user_id), None)


@router.get("", response_model=list[ChatMessage])
async def get_messages(
    room_id: str,
    before: str | None = Query(default=None, description="游标：获取此消息 ID 之前的消息"),
    limit: int = Query(default=50, ge=1, le=100, description="每页消息数量"),
):
    """获取聊天消息（局内外共用）"""
    # 校验房间存在
    try:
        await RoomService.get_room(room_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

    messages = await ChatService.get_messages(room_id, before=before, limit=limit)
    return messages


@router.post("", response_model=ChatMessage, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: str,
    body: SendMessageRequest,
    current_user: User = Depends(get_current_user),
):
    """发送聊天消息（局内外共用，玩家和观战者均可发送）"""
    # 校验房间存在
    try:
        room = await RoomService.get_room(room_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="房间不存在")

    # 校验用户在房间中（玩家或观战者均可）
    player = _find_player(room.players, current_user.id)
    spectator = _find_spectator(room.spectators, current_user.id)
    if not player and not spectator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不在该房间中，无法发送消息",
        )

    # 优先使用玩家昵称，其次观战者昵称
    nickname = player.nickname if player else (spectator.nickname if spectator else current_user.nickname)

    msg = await ChatService.send_message(
        room=room,
        user_id=current_user.id,
        nickname=nickname,
        is_ai=False,
        content=body.content,
    )
    return msg
