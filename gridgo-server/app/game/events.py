"""
游戏事件管理器

负责管理 WebSocket 连接，向房间内所有玩家广播游戏事件消息。
每个房间维护一个连接池，支持：单播、广播、断线检测。
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import WebSocket

from app.core.logging import app_logger


class ConnectionManager:
    """
    连接管理器 — 管理所有游戏房间的 WebSocket 连接

    结构: { room_id: { user_id: WebSocket } }
    """

    _instance: ConnectionManager | None = None
    _connections: dict[str, dict[int, WebSocket]]

    def __new__(cls) -> ConnectionManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connections = {}
        return cls._instance

    # ─── 连接管理 ───

    async def connect(self, room_id: str, user_id: int, websocket: WebSocket) -> None:
        """建立 WebSocket 连接"""
        if room_id not in self._connections:
            self._connections[room_id] = {}
        self._connections[room_id][user_id] = websocket

    def disconnect(self, room_id: str, user_id: int) -> None:
        """断开 WebSocket 连接"""
        if room_id in self._connections:
            self._connections[room_id].pop(user_id, None)
            if not self._connections[room_id]:
                del self._connections[room_id]

    def get_connection(self, room_id: str, user_id: int) -> WebSocket | None:
        """获取指定用户的 WebSocket 连接"""
        return self._connections.get(room_id, {}).get(user_id)

    def get_room_connections(self, room_id: str) -> dict[int, WebSocket]:
        """获取房间内所有连接"""
        return self._connections.get(room_id, {})

    # ─── 消息发送 ───

    async def send_to_player(self, room_id: str, user_id: int, msg_type: str, data: Any) -> None:
        """向单个玩家发送消息"""
        ws = self.get_connection(room_id, user_id)
        if ws:
            try:
                await ws.send_json({
                    "type": msg_type,
                    "data": data,
                    "timestamp": int(time.time() * 1000),
                })
                app_logger.debug("WS → room=%s user=%s type=%s", room_id, user_id, msg_type)
            except Exception as e:
                app_logger.warning("WS 发送失败: room=%s user=%s type=%s error=%s", room_id, user_id, msg_type, e)
                self.disconnect(room_id, user_id)

    async def broadcast(self, room_id: str, msg_type: str, data: Any, exclude: int | None = None) -> None:
        """向房间内所有玩家广播消息"""
        connections = self.get_room_connections(room_id)
        message = {
            "type": msg_type,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        app_logger.debug("WS → broadcast room=%s type=%s connections=%d", room_id, msg_type, len(connections))
        disconnected = []
        for uid, ws in connections.items():
            if uid == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(uid)

        # 清理断开的连接
        for uid in disconnected:
            self.disconnect(room_id, uid)

    async def send_snapshot(self, room_id: str, user_id: int, snapshot: dict) -> None:
        """向单个玩家发送完整游戏状态快照"""
        await self.send_to_player(room_id, user_id, "state.snapshot", snapshot)


# 全局单例
manager = ConnectionManager()
