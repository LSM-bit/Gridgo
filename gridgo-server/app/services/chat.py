"""
聊天业务逻辑层

Redis Key 设计：
  chat:{room_id}       → Sorted Set，score=时间戳，value=消息 JSON
  chat:{room_id}:seq   → 自增序号，用于生成消息 ID

设计说明：
  - 使用 Sorted Set 存储，score 为毫秒时间戳，天然按时间排序
  - 聊天记录与房间共用 TTL，房间销毁时同步清理
  - 获取历史消息时支持游标分页（before 参数）
"""

import json
import time

from app.core.redis import get_redis
from app.schemas.chat import ChatMessage
from app.schemas.room import RoomInfo

CHAT_MAX_LENGTH = 500  # 单条消息最大字符数
CHAT_PAGE_SIZE = 50  # 默认每页消息数
CHAT_MAX_RECORDS = 500  # 每个聊天室最大保留消息数


class ChatService:
    """聊天服务"""

    @staticmethod
    async def send_message(
        room: RoomInfo,
        user_id: int,
        nickname: str,
        is_ai: bool,
        content: str,
    ) -> ChatMessage:
        """发送聊天消息

        Args:
            room:    房间信息（用于校验和获取 room_id）
            user_id: 发送者 ID
            nickname: 发送者昵称
            is_ai:   是否 AI
            content: 消息内容

        Returns:
            ChatMessage 实例
        """
        redis = await get_redis()

        # 截断超长消息
        content = content[:CHAT_MAX_LENGTH]

        # 生成自增消息 ID
        msg_seq = await redis.incr(f"chat:{room.id}:seq")

        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
        now_ms = int(time.time() * 1000)

        msg = ChatMessage(
            id=str(msg_seq),
            room_id=room.id,
            user_id=user_id,
            nickname=nickname,
            is_ai=is_ai,
            content=content,
            created_at=now_iso,
        )

        # 存入 Sorted Set（score=毫秒时间戳，value=消息 JSON）
        chat_key = f"chat:{room.id}"
        await redis.zadd(chat_key, {msg.model_dump_json(): now_ms})

        # 设置与房间相同的 TTL
        await redis.expire(chat_key, 60 * 60 * 24)
        await redis.expire(f"chat:{room.id}:seq", 60 * 60 * 24)

        # 限制聊天记录数量，移除最早的消息
        count = await redis.zcard(chat_key)
        if count > CHAT_MAX_RECORDS:
            # 移除最早的 (count - CHAT_MAX_RECORDS) 条
            await redis.zremrangebyrank(chat_key, 0, count - CHAT_MAX_RECORDS - 1)

        return msg

    @staticmethod
    async def get_messages(
        room_id: str,
        before: str | None = None,
        limit: int = CHAT_PAGE_SIZE,
    ) -> list[ChatMessage]:
        """获取聊天消息（按时间正序返回）

        Args:
            room_id: 房间 ID
            before:  游标，获取此消息 ID 之前的消息（用于向上翻页）
            limit:   返回消息数量上限

        Returns:
            ChatMessage 列表（按时间正序）
        """
        redis = await get_redis()
        chat_key = f"chat:{room_id}"

        if before is not None:
            # 查找 before 消息的时间戳，获取它之前的消息
            # 遍历查找对应 ID 的消息
            all_msgs = await redis.zrange(chat_key, 0, -1)
            before_ts = None
            for raw in all_msgs:
                try:
                    parsed = json.loads(raw)
                    if parsed.get("id") == before:
                        # 需要用 score 查找；换一种方式：按 score 范围查询
                        # 先获取这条消息的 score
                        before_ts = await redis.zscore(chat_key, raw)
                        break
                except (json.JSONDecodeError, KeyError):
                    continue

            if before_ts is not None:
                # 获取 score < before_ts 的最新 limit 条消息
                raw_msgs = await redis.zrangebyscore(
                    chat_key, "-inf", f"({before_ts}", offset=0, count=limit
                )
            else:
                # before 消息不存在，降级为获取最新消息
                raw_msgs = await redis.zrange(chat_key, -limit, -1)
        else:
            # 获取最新的 limit 条消息
            total = await redis.zcard(chat_key)
            start = max(0, total - limit)
            raw_msgs = await redis.zrange(chat_key, start, -1)

        messages = []
        for raw in raw_msgs:
            try:
                messages.append(ChatMessage.model_validate_json(raw))
            except Exception:
                continue

        return messages

    @staticmethod
    async def delete_chat(room_id: str) -> None:
        """删除房间的所有聊天记录（房间销毁时调用）"""
        redis = await get_redis()
        async with redis.pipeline() as pipe:
            pipe.delete(f"chat:{room_id}")
            pipe.delete(f"chat:{room_id}:seq")
            await pipe.execute()
