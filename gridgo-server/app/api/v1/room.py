"""房间接口"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.room import (
    CreateRoomRequest,
    JoinRoomRequest,
    RoomInfo,
    RoomListItem,
    SwitchRoleRequest,
    UpdateRoomRequest,
)
from app.services.room import RoomService

router = APIRouter(prefix="/rooms", tags=["房间"])


@router.get("", response_model=list[RoomListItem])
async def get_rooms():
    """获取等待中的房间列表"""
    try:
        rooms = await RoomService.get_room_list()
        return rooms
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/active", response_model=RoomInfo | None)
async def get_active_room(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的活跃房间（无则返回 null）

    供前端刷新 / 重新打开页面时恢复「返回房间」入口，
    同时作为「同一用户只能有一个活跃房间」的服务端判定依据。
    """
    return await RoomService.get_user_active_room(current_user.id, db)


@router.post("", response_model=RoomInfo, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: CreateRoomRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建房间"""
    try:
        room = await RoomService.create_room(
            db,
            current_user.id,
            name=body.name,
            max_players=body.max_players,
            map_id=body.map_id,
            ai_count=body.ai_count,
            ai_difficulty=body.ai_difficulty,
            password=body.password,
        )
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/by-code/{code}", response_model=RoomInfo)
async def get_room_by_code(code: str):
    """通过房间代码获取房间"""
    try:
        room = await RoomService.get_room_by_code(code)
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{room_id}", response_model=RoomInfo)
async def get_room(room_id: str):
    """获取房间详情"""
    try:
        room = await RoomService.get_room(room_id)
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/join", response_model=RoomInfo)
async def join_room(
    body: JoinRoomRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """加入房间（支持观战模式）"""
    try:
        room = await RoomService.join_room(
            db, current_user.id, body.code, as_spectator=body.as_spectator, password=body.password
        )
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/leave")
async def leave_room(room_id: str, current_user: User = Depends(get_current_user)):
    """离开房间（房主离开时转交房主给其他真人玩家；房内已无真人玩家时销毁房间）"""
    try:
        result = await RoomService.leave_room(room_id, current_user.id)
        return {"code": 0, **result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/ready", response_model=RoomInfo)
async def toggle_ready(room_id: str, current_user: User = Depends(get_current_user)):
    """准备/取消准备"""
    try:
        room = await RoomService.toggle_ready(room_id, current_user.id)
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/switch-role", response_model=RoomInfo)
async def switch_role(
    room_id: str,
    body: SwitchRoleRequest,
    current_user: User = Depends(get_current_user),
):
    """切换角色（玩家 ↔ 观战者）"""
    try:
        room = await RoomService.switch_role(room_id, current_user.id, to_spectator=body.to_spectator)
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{room_id}/settings", response_model=RoomInfo)
async def update_room_settings(
    room_id: str,
    body: UpdateRoomRequest,
    current_user: User = Depends(get_current_user),
):
    """更新房间设置（仅房主）"""
    try:
        room = await RoomService.update_room(
            room_id,
            current_user.id,
            name=body.name,
            max_players=body.max_players,
            map_id=body.map_id,
            ai_count=body.ai_count,
            ai_difficulty=body.ai_difficulty,
            password=body.password,
            clear_password=body.clear_password,
        )
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ─── 文档既有口径的兼容路由（docs/PROJECT.md L793）───
# 文档声明「修改房间设置 = PUT /rooms/{room_id}/config」，
# 实现为 PATCH /rooms/{room_id}/settings。为消除不一致，两条路径等价可用。


@router.put("/{room_id}/config", response_model=RoomInfo)
async def update_room_config_alias(
    room_id: str,
    body: UpdateRoomRequest,
    current_user: User = Depends(get_current_user),
):
    """更新房间设置（等价于 PATCH /rooms/{room_id}/settings）"""
    return await update_room_settings(room_id, body, current_user)


@router.post("/{room_id}/start", response_model=RoomInfo)
async def start_game(
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """房主开始游戏"""
    try:
        await RoomService.start_game(room_id, current_user.id, db=db)
        room = await RoomService.get_room(room_id)
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{room_id}/reset", response_model=RoomInfo)
async def reset_room(
    room_id: str,
    current_user: User = Depends(get_current_user),
):
    """房主重置房间（游戏结束后返回准备阶段）"""
    try:
        room = await RoomService.reset_room(room_id, current_user.id)
        return room
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
