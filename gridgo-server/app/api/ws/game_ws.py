"""
游戏 WebSocket 处理

处理游戏内的实时通信：
  - 连接鉴权（JWT Token）
  - 消息路由（根据 type 分发到 GameService）
  - 观战者限制（只读，不可操作）
  - 断线重连
  - 心跳检测
"""

import time

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import async_session
from app.core.logging import app_logger
from app.game.events import manager as ws_manager
from app.services.auth import AuthService
from app.services.game import GameService
from app.services.room import RoomService

router = APIRouter()


async def _authenticate_websocket(token: str) -> int | None:
    """WebSocket 鉴权，返回 user_id 或 None"""
    try:
        async with async_session() as db:
            user = await AuthService.get_current_user(db, token)
            return user.id
    except Exception as e:
        app_logger.warning("WS 认证异常: %s", e)
        return None


@router.websocket("/game")
async def game_websocket(websocket: WebSocket, token: str = Query(...)):
    """
    游戏 WebSocket 端点

    连接方式: ws://host/ws/game?token=<access_token>
    玩家和观战者共用此端点，观战者只能接收消息，不能发送游戏操作。
    """
    # 1. 鉴权
    user_id = await _authenticate_websocket(token)
    if user_id is None:
        app_logger.warning("WS 认证失败: token 无效")
        await websocket.close(code=4001, reason="认证失败")
        return

    # 2. 等待客户端发送 room_id
    await websocket.accept()
    try:
        init_msg = await websocket.receive_json()
    except Exception:
        app_logger.warning("WS 初始化消息格式错误: user_id=%s", user_id)
        await websocket.close(code=4002, reason="初始化消息格式错误")
        return

    room_id = init_msg.get("room_id")
    if not room_id:
        app_logger.warning("WS 缺少 room_id: user_id=%s, init_msg=%s", user_id, init_msg)
        await websocket.close(code=4003, reason="缺少 room_id")
        return

    # 成员校验：未加入房间的用户不允许建立连接（防止绕过前端守卫直连 WS）
    try:
        room = await RoomService.get_room(room_id)
    except ValueError:
        app_logger.warning("WS 房间不存在: user_id=%s, room_id=%s", user_id, room_id)
        await websocket.close(code=4003, reason="房间不存在")
        return

    is_member = any(p.user_id == user_id for p in room.players) or any(
        s.user_id == user_id for s in room.spectators
    )
    if not is_member:
        app_logger.warning("WS 拒绝非成员连接: user_id=%s, room_id=%s", user_id, room_id)
        await websocket.close(code=4006, reason="你不在该房间中")
        return

    # 检查是否是观战者
    is_spectator = await RoomService.is_spectator(room_id, user_id)

    app_logger.info("WS 连接: user_id=%s, room_id=%s, spectator=%s", user_id, room_id, is_spectator)

    # 3. 确保游戏已初始化
    async with async_session() as db:
        try:
            state = await GameService.ensure_game_initialized(db, room_id)
        except ValueError as e:
            app_logger.warning("WS 游戏初始化失败: room_id=%s, error=%s", room_id, e)
            await websocket.close(code=4004, reason=str(e))
            return

    if not state:
        app_logger.warning("WS 游戏状态不存在: room_id=%s", room_id)
        await websocket.close(code=4005, reason="游戏状态不存在")
        return

    # 4. 注册连接
    await ws_manager.connect(room_id, user_id, websocket)

    # 发送当前状态快照（包含观战者标识）
    snapshot = await GameService.get_snapshot(room_id)
    snapshot["is_spectator"] = is_spectator
    await websocket.send_json({
        "type": "state.snapshot",
        "data": snapshot,
        "timestamp": int(time.time() * 1000),
    })
    app_logger.info("WS 快照已发送: room_id=%s, user_id=%s, spectator=%s", room_id, user_id, is_spectator)

    # 断线重连：先复位玩家连接标记（解除离线状态与 AI 代打），再恢复后台任务。
    # 顺序很关键：若先 resume，重连玩家在引擎中仍被判为「离线 / AI 代打」，
    # 会误启动 AI 任务与自己抢操作，导致该玩家的回合被 AI 抢走或卡住（问题④）。
    # （docs/GAME_FLOW.md 9：≤30s → resume_incremental；30s~3min → resume_snapshot；>3min → left_game）
    if not is_spectator:
        try:
            await GameService.handle_player_connected(room_id, user_id)
        except Exception as e:
            app_logger.warning("WS 重连处理失败: room_id=%s, user_id=%s, error=%s", room_id, user_id, e)

    # 重连时恢复后台任务（AI 回合、超时计时器等）
    # asyncio.Task 不会随 Redis 持久化，所以每次 WS 重连时都需要检查
    try:
        await GameService.resume_active_tasks(room_id)
    except Exception as e:
        app_logger.warning("WS 重连恢复任务失败: room_id=%s, error=%s", room_id, e)

    # 广播连接通知
    if is_spectator:
        await ws_manager.broadcast(room_id, "system.spectator_connected", {
            "user_id": user_id,
        }, exclude=user_id)
    else:
        await ws_manager.broadcast(room_id, "system.player_connected", {
            "player_id": user_id,
        }, exclude=user_id)

    # 5. 消息循环
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")
            msg_data = data.get("data", {})

            app_logger.info(
                "WS ← room=%s user=%s type=%s data=%s",
                room_id, user_id, msg_type, _truncate(str(msg_data)),
            )

            try:
                await _handle_message(room_id, user_id, msg_type, msg_data, is_spectator=is_spectator)
            except ValueError as e:
                # 非法操作（不满足回合/资金/规则约束）只回一条 system.error，
                # 不能中断连接，否则前端只能看到「WS 已断开」而无任何原因提示
                app_logger.warning(
                    "WS 操作被拒绝: room=%s user=%s type=%s error=%s", room_id, user_id, msg_type, e
                )
                await ws_manager.send_to_player(room_id, user_id, "system.error", {
                    "code": 40006,
                    "message": str(e),
                    "action": msg_type,
                })

    except WebSocketDisconnect:
        app_logger.info("WS 断开: room_id=%s, user_id=%s", room_id, user_id)
    except Exception as e:
        app_logger.error("WS 异常: room_id=%s, user_id=%s, error=%s", room_id, user_id, e)
    finally:
        # 6. 断线处理
        ws_manager.disconnect(room_id, user_id)
        if is_spectator:
            await ws_manager.broadcast(room_id, "system.spectator_disconnected", {
                "user_id": user_id,
            })
        else:
            # 记录离线时刻，用于判定重连恢复档位（docs/GAME_FLOW.md 9）
            try:
                await GameService.handle_player_disconnected(room_id, user_id)
            except Exception as e:
                app_logger.warning("WS 断线标记失败: room_id=%s, user_id=%s, error=%s", room_id, user_id, e)
            await ws_manager.broadcast(room_id, "system.player_disconnected", {
                "player_id": user_id,
                "mode": "offline",
            })


def _truncate(s: str, max_len: int = 200) -> str:
    """截断过长字符串"""
    return s[:max_len] + "…" if len(s) > max_len else s


# 观战者禁止的操作类型
SPECTATOR_BLOCKED_TYPES = {
    "game.roll_dice",
    "game.buy_property",
    "game.decline_property",
    "game.skip_property",
    "game.auction_bid",
    "game.build",
    "game.demolish",
    "game.mortgage",
    "game.redeem",
    "game.end_turn",
    "game.quit_game",
    "game.jail_pay_bail",
    "game.jail_use_card",
    "game.trade_offer",
    "game.trade_accept",
    "game.trade_reject",
    "chat.send",
}


# 文档历史别名 → 当前规范类型（docs/PROJECT.md 7.2.2）
ALIAS_TYPES = {
    "game.decline_buy": "game.decline_property",
    "game.jail_pay": "game.jail_pay_bail",
}


async def _handle_message(room_id: str, user_id: int, msg_type: str, data: dict, *, is_spectator: bool = False) -> None:
    """消息路由"""

    # ─── 兼容别名归一 ───
    msg_type = ALIAS_TYPES.get(msg_type, msg_type)

    # ─── 心跳 ───
    if msg_type == "system.ping":
        ws = ws_manager.get_connection(room_id, user_id)
        if ws:
            await ws.send_json({
                "type": "system.pong",
                "data": {},
                "timestamp": int(time.time() * 1000),
            })
        return

    # ─── 观战者操作拦截 ───
    if is_spectator and msg_type in SPECTATOR_BLOCKED_TYPES:
        app_logger.warning("WS 观战者操作被拒绝: room=%s user=%s type=%s", room_id, user_id, msg_type)
        ws = ws_manager.get_connection(room_id, user_id)
        if ws:
            await ws.send_json({
                "type": "system.error",
                "data": {"code": 40005, "message": "观战者无法执行游戏操作"},
                "timestamp": int(time.time() * 1000),
            })
        return

    # ─── 游戏操作 ───
    if msg_type == "game.roll_dice":
        await GameService.handle_roll_dice(room_id, user_id)

    elif msg_type == "game.buy_property":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_buy_property(room_id, user_id, int(tile_position))

    elif msg_type == "game.decline_property":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_decline_property(room_id, user_id, int(tile_position))

    elif msg_type == "game.skip_property":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_skip_property(room_id, user_id, int(tile_position))

    elif msg_type == "game.auction_bid":
        amount = data.get("amount")
        if amount is not None:
            await GameService.handle_auction_bid(room_id, user_id, int(amount))

    elif msg_type == "game.build":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_build_house(room_id, user_id, int(tile_position))

    elif msg_type == "game.demolish":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_demolish_house(room_id, user_id, int(tile_position))

    elif msg_type == "game.mortgage":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_mortgage_property(room_id, user_id, int(tile_position))

    elif msg_type == "game.redeem":
        tile_position = data.get("tile_id")
        if tile_position is not None:
            await GameService.handle_redeem_property(room_id, user_id, int(tile_position))

    elif msg_type == "game.end_turn":
        await GameService.handle_end_turn(room_id, user_id)

    elif msg_type == "game.quit_game":
        # 强制退出本局：该玩家由 AI 接管继续对局；房间内无真人时解散房间
        result = await GameService.handle_quit_game(room_id, user_id)
        ws = ws_manager.get_connection(room_id, user_id)
        if ws and not result.get("dissolved"):
            await ws.send_json({
                "type": "game.quit_result",
                "data": {
                    "ok": bool(result.get("ok")),
                    "reason": result.get("reason"),
                    "ai_difficulty": result.get("ai_difficulty"),
                },
                "timestamp": int(time.time() * 1000),
            })

    elif msg_type == "game.jail_pay_bail":
        await GameService.handle_jail_pay_bail(room_id, user_id)

    elif msg_type == "game.jail_use_card":
        await GameService.handle_jail_use_card(room_id, user_id)

    # ─── 玩家间交易（docs/PROJECT.md 7.2） ───
    elif msg_type == "game.trade_offer":
        await GameService.handle_trade_offer(room_id, user_id, data)

    elif msg_type == "game.trade_accept":
        trade_id = data.get("trade_id")
        if trade_id:
            await GameService.handle_trade_accept(room_id, user_id, str(trade_id))

    elif msg_type == "game.trade_reject":
        trade_id = data.get("trade_id")
        if trade_id:
            await GameService.handle_trade_reject(room_id, user_id, str(trade_id))

    # ─── 聊天（docs/PROJECT.md 8.4） ───
    elif msg_type == "chat.send":
        # 载荷字段以 content 为准，兼容文档旧写法 message
        content = data.get("content")
        if content is None:
            content = data.get("message")
        if content:
            await GameService.handle_chat_send(room_id, user_id, str(content))

    # ─── 兼容：拍卖由服务端广播，客户端不可主动发起 ───
    elif msg_type == "game.auction_start":
        # 客户端不主动发起拍卖，仅作兼容提示（拍卖由服务端广播）
        app_logger.warning("WS 客户端尝试主动发起拍卖，已忽略: room=%s user=%s", room_id, user_id)

    else:
        app_logger.warning("WS 未知消息类型: room=%s user=%s type=%s", room_id, user_id, msg_type)
        ws = ws_manager.get_connection(room_id, user_id)
        if ws:
            await ws.send_json({
                "type": "system.error",
                "data": {"code": 40004, "message": f"Unknown message type: {msg_type}"},
                "timestamp": int(time.time() * 1000),
            })
