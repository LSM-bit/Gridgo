"""
好友接口

对齐 docs/PROJECT.md S-04：好友申请、好友列表、删除好友。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.friend import (
    FriendItem,
    FriendRequestBody,
    FriendRequestItem,
    RespondFriendRequest,
)
from app.services.friends import FriendService

router = APIRouter(prefix="/friends", tags=["好友"])


@router.get("", response_model=list[FriendItem])
async def list_friends(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取好友列表"""
    return await FriendService.list_friends(db, current_user.id)


@router.get("/requests", response_model=list[FriendRequestItem])
async def list_friend_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取收到的好友申请"""
    return await FriendService.list_requests(db, current_user.id)


@router.post("/requests", status_code=status.HTTP_201_CREATED)
async def send_friend_request(
    body: FriendRequestBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送好友申请"""
    try:
        relation = await FriendService.send_request(db, current_user.id, body.target_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "好友申请已发送", "request_id": relation.id}


@router.post("/requests/{request_id}/respond")
async def respond_friend_request(
    request_id: int,
    body: RespondFriendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认 / 拒绝好友申请"""
    try:
        relation = await FriendService.respond_request(db, current_user.id, request_id, body.accept)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "已接受好友申请" if relation.status == 1 else "已拒绝好友申请"}


@router.delete("/{friend_id}")
async def delete_friend(
    friend_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除好友"""
    try:
        await FriendService.delete_friend(db, current_user.id, friend_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "已删除好友"}
