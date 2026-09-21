"""WebSocket 协议契约单测（docs/PROJECT.md 7.2 / 8.4）

覆盖：/ws/game 路由注册（REST 前缀 + ws 前缀）、观战者操作拦截清单包含
交易与聊天、消息路由支持 game.trade_* / chat.send。
不建立真实连接。
"""

import inspect
import sys

from app.api.ws.game_ws import SPECTATOR_BLOCKED_TYPES, _handle_message, game_websocket
from app.main import app


def _iter_routes(routes):
    """递归展开 include_router 包装（不同 FastAPI 版本包装类型不同）"""
    for route in routes:
        yield route
        inner = getattr(route, "original_router", None) or getattr(route, "router", None)
        if inner is not None and getattr(inner, "routes", None):
            yield from _iter_routes(inner.routes)


def test_ws_game_route_registered():
    paths = []
    for route in _iter_routes(app.routes):
        if "websocket" in type(route).__name__.lower():
            paths.append(getattr(route, "path", "") or "")
    assert "/game" in paths, f"未注册游戏 WebSocket 路由: {paths}"
    # 挂载前缀为 /ws（app.include_router(ws_router, prefix="/ws")）→ 对外路径 /ws/game
    main_source = inspect.getsource(sys.modules["app.main"])
    assert 'ws_router, prefix="/ws"' in main_source.replace("'", '"')


def test_ws_handshake_requires_room_id_first_frame():
    source = inspect.getsource(game_websocket)
    assert "receive_json" in source
    assert "room_id" in source
    assert "4003" in source  # 缺少 room_id 的关闭码


def test_spectator_blocked_types_cover_trade_and_chat():
    for msg_type in ("game.trade_offer", "game.trade_accept", "game.trade_reject", "chat.send"):
        assert msg_type in SPECTATOR_BLOCKED_TYPES


def test_message_router_supports_trade_and_chat():
    source = inspect.getsource(_handle_message)
    for msg_type in (
        "game.trade_offer",
        "game.trade_accept",
        "game.trade_reject",
        "chat.send",
        "system.ping",
    ):
        assert f'"{msg_type}"' in source, f"消息路由缺少 {msg_type}"


def test_legacy_type_aliases_normalized():
    from app.api.ws.game_ws import ALIAS_TYPES

    assert ALIAS_TYPES["game.decline_buy"] == "game.decline_property"
    assert ALIAS_TYPES["game.jail_pay"] == "game.jail_pay_bail"
    source = inspect.getsource(_handle_message)
    assert "ALIAS_TYPES.get(msg_type, msg_type)" in source


def test_chat_send_accepts_message_alias():
    source = inspect.getsource(_handle_message)
    assert 'data.get("content")' in source
    assert 'data.get("message")' in source  # docs/PROJECT.md 7.2.2 旧字段兼容


def test_friend_and_leaderboard_routers_mounted():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/friends" in paths, "好友路由未挂载"
    assert "/api/v1/leaderboard" in paths, "排行榜路由未挂载"
