"""
游戏操作服务

封装 GameEngine，提供面向 API 层的高级接口。
处理游戏初始化、状态查询、操作路由等。
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import app_logger
from app.core.redis import get_redis
from app.game.engine import GameEngine, get_engine, remove_engine
from app.game.events import manager as ws_manager
from app.game.schemas import GameState
from app.schemas.room import RoomInfo
from app.services.chat import ChatService
from app.services.map import MapService
from app.services.room import RoomService


class GameService:
    """游戏操作服务"""

    @staticmethod
    async def init_game(db: AsyncSession, room_id: str) -> GameState:
        """
        初始化游戏

        从房间信息中获取玩家列表，创建游戏引擎，初始化 GameState。

        Args:
            db: 数据库会话
            room_id: 房间 ID

        Returns:
            初始化后的 GameState
        """
        # 获取房间信息
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")

        if room.status != "playing":
            raise ValueError("房间状态不是游戏中")

        # 转换玩家数据
        room_players = [p.model_dump() for p in room.players]

        # 创建引擎并初始化
        engine = get_engine(room_id)
        state = await engine.initialize(db, room_players, room.map_id)

        return state

    @staticmethod
    async def get_game_state(room_id: str) -> GameState | None:
        """获取游戏状态"""
        engine = get_engine(room_id)
        return await engine.load_state()

    @staticmethod
    async def get_snapshot(room_id: str) -> dict:
        """获取游戏状态快照（用于 WebSocket 推送）"""
        engine = get_engine(room_id)
        state = await engine.load_state()
        if not state:
            return {}
        return state.model_dump()

    @staticmethod
    async def handle_roll_dice(room_id: str, player_id: int) -> None:
        """处理掷骰子请求"""
        engine = get_engine(room_id)
        await engine.roll_dice(player_id)

    @staticmethod
    async def handle_buy_property(room_id: str, player_id: int, tile_position: int) -> None:
        """处理购买地产请求"""
        engine = get_engine(room_id)
        await engine.buy_property(player_id, tile_position)

    @staticmethod
    async def handle_decline_property(room_id: str, player_id: int, tile_position: int) -> None:
        """处理放弃购买请求"""
        engine = get_engine(room_id)
        await engine.decline_property(player_id, tile_position)

    @staticmethod
    async def handle_skip_property(room_id: str, player_id: int, tile_position: int) -> None:
        """处理跳过地产请求（不购买也不拍卖）"""
        engine = get_engine(room_id)
        await engine.skip_property(player_id, tile_position)

    @staticmethod
    async def handle_auction_bid(room_id: str, player_id: int, amount: int) -> None:
        """处理拍卖出价"""
        engine = get_engine(room_id)
        await engine.auction_bid(player_id, amount)

    @staticmethod
    async def handle_build_house(room_id: str, player_id: int, tile_position: int) -> None:
        """处理建造房屋请求"""
        engine = get_engine(room_id)
        await engine.build_house(player_id, tile_position)

    @staticmethod
    async def handle_demolish_house(room_id: str, player_id: int, tile_position: int) -> None:
        """处理拆除房屋请求"""
        engine = get_engine(room_id)
        await engine.demolish_house(player_id, tile_position)

    @staticmethod
    async def handle_mortgage_property(room_id: str, player_id: int, tile_position: int) -> None:
        """处理抵押地产请求"""
        engine = get_engine(room_id)
        await engine.mortgage_property(player_id, tile_position)

    @staticmethod
    async def handle_redeem_property(room_id: str, player_id: int, tile_position: int) -> None:
        """处理赎回地产请求"""
        engine = get_engine(room_id)
        await engine.redeem_property(player_id, tile_position)

    @staticmethod
    async def handle_end_turn(room_id: str, player_id: int) -> None:
        """处理结束回合请求"""
        engine = get_engine(room_id)
        await engine.end_turn(player_id)

    @staticmethod
    async def handle_jail_pay_bail(room_id: str, player_id: int) -> None:
        """处理支付保释金请求"""
        engine = get_engine(room_id)
        await engine.jail_pay_bail(player_id)

    @staticmethod
    async def handle_jail_use_card(room_id: str, player_id: int) -> None:
        """处理使用免罪卡请求"""
        engine = get_engine(room_id)
        await engine.jail_use_card(player_id)

    # ─── 交易系统（docs/PROJECT.md 8.3 / GAME_FLOW.md 8.3） ───

    @staticmethod
    async def handle_trade_offer(room_id: str, player_id: int, payload: dict) -> None:
        """处理发起交易请求（game.trade_offer）

        payload: {target_id, offer: {cash, properties}, request: {cash, properties}}
        """
        engine = get_engine(room_id)
        await engine.offer_trade(player_id, payload)

    @staticmethod
    async def handle_trade_accept(room_id: str, player_id: int, trade_id: str) -> None:
        """处理接受交易请求（game.trade_accept）"""
        engine = get_engine(room_id)
        await engine.accept_trade(player_id, trade_id)

    @staticmethod
    async def handle_trade_reject(room_id: str, player_id: int, trade_id: str) -> None:
        """处理拒绝/撤回交易请求（game.trade_reject）"""
        engine = get_engine(room_id)
        await engine.reject_trade(player_id, trade_id)

    # ─── 断线重连（docs/GAME_FLOW.md 9） ───

    @staticmethod
    async def handle_player_connected(room_id: str, player_id: int) -> str | None:
        """玩家 WS 连接/重连：复位连接标记并广播 system.player_reconnected"""
        engine = get_engine(room_id)
        try:
            return await engine.mark_connected(player_id)
        except Exception as e:
            app_logger.warning("重连处理失败: room=%s user=%s error=%s", room_id, player_id, e)
            return None

    @staticmethod
    async def handle_player_disconnected(room_id: str, player_id: int) -> None:
        """玩家 WS 断开：记录离线时刻（用于判定恢复档位）"""
        engine = get_engine(room_id)
        try:
            await engine.mark_disconnected(player_id)
        except Exception as e:
            app_logger.warning("断线标记失败: room=%s user=%s error=%s", room_id, player_id, e)

    # ─── 聊天（docs/PROJECT.md 8.4：chat.send） ───

    @staticmethod
    async def handle_chat_send(room_id: str, user_id: int, content: str) -> dict | None:
        """处理聊天消息（chat.send → 广播 chat.message）"""
        if not content or not str(content).strip():
            return None
        room = await RoomService._get_room(room_id)
        if not room:
            return None
        sender = next((p for p in room.players if p.user_id == user_id), None)
        nickname = sender.nickname if sender else f"玩家{user_id}"
        is_ai = bool(sender.is_ai) if sender else False
        msg = await ChatService.send_message(room, user_id, nickname, is_ai, str(content))
        payload = msg.model_dump()
        await ws_manager.broadcast(room_id, "chat.message", payload)
        return payload

    @staticmethod
    async def cleanup_game(room_id: str) -> None:
        """清理游戏资源"""
        engine = get_engine(room_id)
        await engine.cleanup()
        remove_engine(room_id)

    @staticmethod
    async def ensure_game_initialized(db: AsyncSession, room_id: str) -> GameState:
        """
        确保游戏已初始化（WebSocket 连接时调用）

        如果 Redis 中已有 GameState，直接加载；
        如果没有（服务器重启等情况），从房间信息重新初始化。

        加载后会恢复 AI 回合任务和超时计时器，
        因为这些 asyncio.Task 不会随 Redis 持久化。
        """
        engine = get_engine(room_id)
        state = await engine.load_state()
        if state:
            # 恢复后台任务（AI 回合、超时计时器）
            await engine.resume_active_tasks()
            return state

        # 重新初始化
        return await GameService.init_game(db, room_id)

    @staticmethod
    async def resume_active_tasks(room_id: str) -> None:
        """恢复游戏的后台任务（AI 回合、超时计时器等）"""
        engine = get_engine(room_id)
        await engine.resume_active_tasks()
