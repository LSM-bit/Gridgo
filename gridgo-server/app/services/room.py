"""
房间业务逻辑层

Redis Key 设计：
  room:{id}          → 房间详情 JSON
  room:code:{code}   → code → id 映射
  room:list          → 等待中的房间 ID 集合
"""

import logging
import random
import string
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis import get_redis
from app.core.security import get_password_hash, verify_password
from app.game.ai import AIPlayerFactory
from app.models.room import Room, RoomPlayerRow
from app.models.user import User
from app.schemas.room import RoomInfo, RoomListItem, RoomPlayer, SpectatorInfo
from app.services.chat import ChatService

logger = logging.getLogger(__name__)

ROOM_TTL = 60 * 60 * 4
# 房间在 Redis 中的存活时间（秒），4 小时后自动过期删除
# 用途：防止已结束/无人维护的房间残留在 Redis 中占用内存
# 每次房间操作（加入/离开/准备等）都会刷新 TTL，活跃房间不会过期


def _generate_room_code() -> str:
    """生成 6 位房间代码"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _generate_room_id() -> str:
    """生成房间 ID"""
    import uuid

    return uuid.uuid4().hex[:12]


def _user_room_key(user_id: int) -> str:
    """用户 → 当前活跃房间 ID 的索引 Key

    用于「同一用户同时只能有一个活跃房间」约束：
    创建/加入房间时写入，离开/房间销毁时删除。
    """
    return f"user:room:{user_id}"


def _is_room_member(room: RoomInfo, user_id: int) -> bool:
    """判断用户是否为房间成员（玩家或观战者）"""
    return any(p.user_id == user_id for p in room.players) or any(
        s.user_id == user_id for s in room.spectators
    )


def _room_member_ids(room: RoomInfo) -> list[int]:
    """房间内全部真人成员 ID（玩家 + 观战者，排除 AI 负数 ID）"""
    ids = [p.user_id for p in room.players if p.user_id > 0]
    ids += [s.user_id for s in room.spectators if s.user_id > 0]
    return list(dict.fromkeys(ids))



class RoomService:
    """房间服务"""

    @staticmethod
    async def create_room(
        db: AsyncSession,
        host_id: int,
        name: str = "GridGo 房间",
        max_players: int = 8,
        map_id: str = "classic",
        ai_count: int = 0,
        ai_difficulty: str = "easy",
        password: str | None = None,
    ) -> RoomInfo:
        """创建房间

        Args:
            password: 房间密码（可选，见 docs/PROJECT.md L650「rooms.password 加密存储」）
        """
        redis = await get_redis()

        # 查找房主信息
        result = await db.execute(select(User).where(User.id == host_id))
        host = result.scalars().first()
        if not host:
            raise ValueError("用户不存在")

        # 同一用户同时只能有一个活跃房间（多网页开多房间会被拒绝）
        existing = await RoomService.get_user_active_room(host_id, db)
        if existing is not None:
            raise ValueError(f"你已在房间 {existing.code} 中，请先离开该房间再创建")

        # 校验 ai_count 不超过 max_players
        if ai_count > max_players:
            raise ValueError("AI 数量不能超过最大玩家数")

        # 当 ai_count == max_players 时，所有玩家位都被 AI 占满，房主自动成为观战者
        host_as_spectator = ai_count >= max_players

        # 生成唯一 code
        code = _generate_room_code()
        while await redis.exists(f"room:code:{code}"):
            code = _generate_room_code()

        room_id = _generate_room_id()
        now = datetime.now(timezone.utc).isoformat()

        # 构建 AI 玩家列表（使用 AIPlayerFactory 生成）
        ai_players_list = []
        ai_players = AIPlayerFactory.create_batch(ai_count, ai_difficulty)
        for ai in ai_players:
            ai_dict = ai.to_room_player_dict(ai_difficulty)
            ai_players_list.append(RoomPlayer(**ai_dict))

        # 根据是否房主观战，决定房主放在玩家列表还是观战者列表
        if host_as_spectator:
            players = ai_players_list  # 玩家位全给 AI
            spectators = [
                SpectatorInfo(
                    user_id=host.id,
                    username=host.username,
                    nickname=host.nickname,
                    avatar=host.avatar,
                    is_host=True,
                )
            ]
        else:
            # 初始玩家列表：房主 + AI
            players = [
                RoomPlayer(
                    user_id=host.id,
                    username=host.username,
                    nickname=host.nickname,
                    avatar=host.avatar,
                    is_host=True,
                    is_ready=False,
                    is_ai=False,
                    ai_difficulty=None,
                )
            ] + ai_players_list
            spectators = []

        room = RoomInfo(
            id=room_id,
            code=code,
            name=name,
            host_id=host_id,
            max_players=max_players,
            map_id=map_id,
            ai_count=ai_count,
            ai_difficulty=ai_difficulty,
            status="waiting",
            players=players,
            spectators=spectators,
            has_password=bool(password),
            created_at=now,
        )

        # 存储到 Redis
        room_key = f"room:{room_id}"
        code_key = f"room:code:{code}"
        pwd_key = f"room:pwd:{room_id}"
        room_json = room.model_dump_json()
        pwd_hash = get_password_hash(password) if password else None

        async with redis.pipeline() as pipe:
            pipe.set(room_key, room_json, ex=ROOM_TTL)
            pipe.set(code_key, room_id, ex=ROOM_TTL)
            pipe.sadd("room:list", room_id)
            if pwd_hash:
                pipe.set(pwd_key, pwd_hash, ex=ROOM_TTL)
            await pipe.execute()

        # 写穿透到 PostgreSQL（rooms / room_players）
        await RoomService._persist_room(room, password_hash=pwd_hash)

        # 绑定「用户 → 活跃房间」索引（保证同一用户同时只有一个活跃房间）
        await RoomService._bind_user_room(host_id, room_id)

        return room

    @staticmethod
    async def verify_room_password(room_id: str, password: str | None) -> None:
        """校验房间密码

        - 未设置密码的房间：直接通过
        - 设置了密码的房间：必须提供正确密码（哈希比对）
        """
        redis = await get_redis()
        stored = await redis.get(f"room:pwd:{room_id}")
        if not stored:
            return
        if not password:
            raise ValueError("该房间需要密码")
        if not verify_password(password, stored):
            raise ValueError("房间密码错误")

    @staticmethod
    async def update_room(
        room_id: str,
        host_id: int,
        name: str | None = None,
        max_players: int | None = None,
        map_id: str | None = None,
        ai_count: int | None = None,
        ai_difficulty: str | None = None,
        password: str | None = None,
        clear_password: bool = False,
    ) -> RoomInfo:
        """更新房间设置（仅房主）

        Args:
            password: 设置新密码（留空表示不改动）
            clear_password: 是否清除密码
        """
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")

        if room.host_id != host_id:
            raise ValueError("只有房主可以修改房间设置")

        if room.status != "waiting":
            raise ValueError("游戏已开始，无法修改设置")

        # 先统一校验，避免部分更新导致数据不一致
        real_players = [p for p in room.players if not p.is_ai]
        non_host_real_players = [p for p in real_players if p.user_id != room.host_id]
        current_ai_count = len([p for p in room.players if p.is_ai])

        # 计算目标值（未传的字段保持原值）
        target_max_players = max_players if max_players is not None else room.max_players
        target_ai_count = ai_count if ai_count is not None else current_ai_count
        target_difficulty = ai_difficulty if ai_difficulty is not None else room.ai_difficulty

        # 校验：AI 数量不能超过最大玩家数
        if target_ai_count > target_max_players:
            raise ValueError("AI 数量不能超过最大玩家数")

        # 校验：非房主真人 + AI 不能超过最大人数（房主可以自动变观战者，但其他真人不行）
        if len(non_host_real_players) + target_ai_count > target_max_players:
            raise ValueError("非房主真人 + AI 数量不能超过最大玩家数，房主可切换为观战者")

        # 判断房主是否需要自动变为观战者
        host_in_players = any(p.user_id == room.host_id for p in real_players)
        need_host_spectate = host_in_players and (len(real_players) + target_ai_count > target_max_players)

        # 校验通过，开始更新字段
        if name is not None:
            room.name = name
        room.max_players = target_max_players
        if map_id is not None:
            room.map_id = map_id
        room.ai_difficulty = target_difficulty

        # 更新已有 AI 的难度
        for p in room.players:
            if p.is_ai:
                p.ai_difficulty = target_difficulty

        # 调整 AI 数量
        if target_ai_count > current_ai_count:
            # 增加 AI（使用 AIPlayerFactory 生成）
            existing_ai_indices = [
                abs(p.user_id) - 1 for p in room.players if p.is_ai
            ]
            next_index = (max(existing_ai_indices) + 1) if existing_ai_indices else 0

            for i in range(target_ai_count - current_ai_count):
                ai = AIPlayerFactory.create(next_index + i, target_difficulty)
                ai_dict = ai.to_room_player_dict(target_difficulty)
                room.players.append(RoomPlayer(**ai_dict))
        elif target_ai_count < current_ai_count:
            # 减少 AI（移除末尾的 AI）
            ai_to_remove = current_ai_count - target_ai_count
            for _ in range(ai_to_remove):
                for j in range(len(room.players) - 1, -1, -1):
                    if room.players[j].is_ai:
                        room.players.pop(j)
                        break

        room.ai_count = target_ai_count

        # 如果房主需要自动变为观战者，从玩家列表移除并加入观战者列表
        if need_host_spectate:
            host_player = next(p for p in room.players if p.user_id == room.host_id)
            room.players = [p for p in room.players if p.user_id != room.host_id]
            # 检查观战者列表中是否已有房主
            if not any(s.user_id == room.host_id for s in room.spectators):
                room.spectators.append(
                    SpectatorInfo(
                        user_id=host_player.user_id,
                        username=host_player.username,
                        nickname=host_player.nickname,
                        avatar=host_player.avatar,
                        is_host=True,
                    )
                )

        # ─── 房间密码更新（docs/PROJECT.md L650）───
        pwd_hash: str | None = None
        if password or clear_password:
            redis = await get_redis()
            if password:
                room.has_password = True
                pwd_hash = get_password_hash(password)
                await redis.set(f"room:pwd:{room.id}", pwd_hash, ex=ROOM_TTL)
            if clear_password:
                room.has_password = False
                await redis.delete(f"room:pwd:{room.id}")

        await RoomService._save_room(room)

        # 密码变更后同步持久化镜像（rooms.password_hash）
        if password or clear_password:
            await RoomService._persist_room(
                room, password_hash=pwd_hash, clear_password=clear_password
            )
        return room

    @staticmethod
    async def join_room(
        db: AsyncSession,
        user_id: int,
        code: str,
        as_spectator: bool = False,
        password: str | None = None,
    ) -> RoomInfo:
        """加入房间（或以观战者身份加入）

        Args:
            password: 房间密码（房间设置了密码时必填）
        """
        redis = await get_redis()

        # 通过 code 找到 room_id
        room_id = await redis.get(f"room:code:{code}")
        if not room_id:
            raise ValueError("房间不存在或已过期")

        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在或已过期")

        # 密码校验（观战也需要密码，避免未授权围观）
        await RoomService.verify_room_password(room_id, password)

        # 同一用户同时只能有一个活跃房间（多网页开多房间会被拒绝）
        existing = await RoomService.get_user_active_room(user_id, db)
        if existing is not None and existing.id != room.id:
            raise ValueError(f"你已在房间 {existing.code} 中，请先离开该房间再加入")

        # 检查是否已在房间中（玩家或观战者）
        for p in room.players:
            if p.user_id == user_id:
                raise ValueError("你已在此房间中")
        for s in room.spectators:
            if s.user_id == user_id:
                raise ValueError("你已在此房间中")

        # 查找用户信息
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise ValueError("用户不存在")

        if as_spectator:
            # 观战模式：waiting / playing 都可以加入
            if len(room.spectators) >= room.max_spectators:
                raise ValueError("观战席已满")
            room.spectators.append(
                SpectatorInfo(
                    user_id=user.id,
                    username=user.username,
                    nickname=user.nickname,
                    avatar=user.avatar,
                )
            )
        else:
            # 正常加入：只能在 waiting 时加入
            if room.status != "waiting":
                raise ValueError("游戏已开始，无法加入，可以观战")
            if len(room.players) >= room.max_players:
                raise ValueError("房间已满，可以观战")
            room.players.append(
                RoomPlayer(
                    user_id=user.id,
                    username=user.username,
                    nickname=user.nickname,
                    avatar=user.avatar,
                    is_host=False,
                    is_ready=False,
                    is_ai=False,
                    ai_difficulty=None,
                )
            )

        await RoomService._save_room(room)

        # 绑定「用户 → 活跃房间」索引（保证同一用户同时只有一个活跃房间）
        await RoomService._bind_user_room(user_id, room_id)
        return room

    @staticmethod
    async def leave_room(
        room_id: str,
        user_id: int,
    ) -> dict:
        """离开房间

        房主离开 → 销毁房间
        普通玩家离开 → 移除玩家
        观战者离开 → 移除观战者
        """
        redis = await get_redis()

        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")

        # 检查是否是玩家
        is_player = any(p.user_id == user_id for p in room.players)
        # 检查是否是观战者
        is_spectator = any(s.user_id == user_id for s in room.spectators)

        if not is_player and not is_spectator:
            raise ValueError("你不在该房间中")

        # 房主离开 → 销毁房间（无论房主是玩家还是观战者）
        if room.host_id == user_id:
            await RoomService._delete_room(room)
            return {"destroyed": True, "message": "房主离开，房间已销毁"}

        # 观战者离开 → 直接移除
        if is_spectator:
            room.spectators = [s for s in room.spectators if s.user_id != user_id]
            await RoomService._save_room(room)
            # 解绑「用户 → 活跃房间」索引
            await RoomService._unbind_user_room(user_id)
            return {"destroyed": False, "message": "已离开观战席"}

        # 普通玩家离开 → 移除
        room.players = [p for p in room.players if p.user_id != user_id]

        if not room.players:
            # 房间无人，删除（_delete_room 会统一清理全部成员索引）
            await RoomService._delete_room(room)
            return {"destroyed": True, "message": "房间已销毁"}

        await RoomService._save_room(room)
        # 解绑「用户 → 活跃房间」索引
        await RoomService._unbind_user_room(user_id)
        return {"destroyed": False, "message": "已离开房间"}

    @staticmethod
    async def switch_role(
        room_id: str,
        user_id: int,
        to_spectator: bool,
    ) -> RoomInfo:
        """切换角色：玩家 ↔ 观战者

        Args:
            room_id: 房间 ID
            user_id: 用户 ID
            to_spectator: True=切换为观战者，False=切换为玩家

        规则：
            - 玩家 → 观战者：waiting/playing 均可，房主身份保留
            - 观战者 → 玩家：仅 waiting 且有空位时允许
        """
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")

        # 查找当前角色
        player_idx = next((i for i, p in enumerate(room.players) if p.user_id == user_id), None)
        spectator_idx = next((i for i, s in enumerate(room.spectators) if s.user_id == user_id), None)

        if to_spectator:
            # ─── 玩家 → 观战者 ───
            if player_idx is None:
                raise ValueError("你不是玩家，无法切换为观战者")

            if len(room.spectators) >= room.max_spectators:
                raise ValueError("观战席已满")

            player = room.players[player_idx]
            is_host = player.is_host

            # 从玩家列表移除，加入观战者列表（房主身份保留）
            room.players.pop(player_idx)
            room.spectators.append(
                SpectatorInfo(
                    user_id=player.user_id,
                    username=player.username,
                    nickname=player.nickname,
                    avatar=player.avatar,
                    is_host=is_host,
                )
            )

        else:
            # ─── 观战者 → 玩家 ───
            if spectator_idx is None:
                raise ValueError("你不是观战者，无法切换为玩家")

            if room.status != "waiting":
                raise ValueError("游戏已开始，无法从观战席加入玩家")

            if len(room.players) >= room.max_players:
                raise ValueError("房间已满，无法切换为玩家")

            spectator = room.spectators[spectator_idx]
            is_host = spectator.is_host

            # 从观战者列表移除，加入玩家列表
            room.spectators.pop(spectator_idx)
            room.players.append(
                RoomPlayer(
                    user_id=spectator.user_id,
                    username=spectator.username,
                    nickname=spectator.nickname,
                    avatar=spectator.avatar,
                    is_host=is_host,
                    is_ready=False,
                    is_ai=False,
                    ai_difficulty=None,
                )
            )

        await RoomService._save_room(room)
        return room

    @staticmethod
    async def toggle_ready(
        room_id: str,
        user_id: int,
    ) -> RoomInfo:
        """切换准备状态"""
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")

        if room.host_id == user_id:
            raise ValueError("房主无需准备")

        if not any(p.user_id == user_id for p in room.players):
            raise ValueError("你不在该房间中")

        for p in room.players:
            if p.user_id == user_id:
                p.is_ready = not p.is_ready
                break

        await RoomService._save_room(room)
        return room

    @staticmethod
    async def start_game(
        room_id: str,
        host_id: int,
        db=None,
    ) -> str:
        """房主开始游戏

        Args:
            room_id:  房间 ID
            host_id:  房主用户 ID
            db:       数据库会话（用于初始化游戏引擎加载地图）

        Returns:
            game_id（目前使用 room_id 作为 game_id）
        """
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")

        if room.host_id != host_id:
            raise ValueError("只有房主可以开始游戏")

        # 至少需要 2 名玩家（含 AI）
        if len(room.players) < 2:
            raise ValueError("至少需要 2 名玩家才能开始")

        # 检查所有非房主真人玩家是否准备（AI 默认已准备）
        all_ready = all(p.is_ready or p.is_host or p.is_ai for p in room.players)
        if not all_ready:
            raise ValueError("还有玩家未准备")

        # 更新状态
        room.status = "playing"
        await RoomService._save_room(room)

        # 从等待列表移除
        redis = await get_redis()
        await redis.srem("room:list", room_id)

        # 初始化游戏引擎（GameState 会存入 Redis，首回合会自动开始）
        if db is not None:
            from app.services.game import GameService
            await GameService.init_game(db, room_id)

        return room_id

    @staticmethod
    async def get_room(room_id: str) -> RoomInfo:
        """获取房间详情"""
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")
        return room

    @staticmethod
    async def get_room_by_code(code: str) -> RoomInfo:
        """通过房间代码获取房间"""
        redis = await get_redis()
        room_id = await redis.get(f"room:code:{code}")
        if not room_id:
            raise ValueError("房间不存在或已过期")
        return await RoomService.get_room(room_id)

    @staticmethod
    async def get_room_list() -> list[RoomListItem]:
        """获取等待中的房间列表，同时清理 room:list 中的无效 ID"""
        redis = await get_redis()
        room_ids = await redis.smembers("room:list")

        rooms = []
        stale_ids: list[str] = []  # 已过期或已不在等待状态的房间 ID

        for rid in room_ids:
            room = await RoomService._get_room(rid)
            if not room:
                # room:{id} 已过期或被删除，属于残留数据
                stale_ids.append(rid)
                continue
            if room.status != "waiting":
                # 房间已开始游戏但未从 list 移除（异常情况）
                stale_ids.append(rid)
                continue
            host = next((p for p in room.players if p.is_host), None)
            rooms.append(
                RoomListItem(
                    id=room.id,
                    code=room.code,
                    name=room.name,
                    host_nickname=host.nickname if host else "未知",
                    player_count=len(room.players),
                    max_players=room.max_players,
                    map_id=room.map_id,
                    ai_count=room.ai_count,
                    spectator_count=len(room.spectators),
                    has_password=room.has_password,
                    status=room.status,
                )
            )

        # 批量清理无效 ID，防止 room:list 无限膨胀
        if stale_ids:
            await redis.srem("room:list", *stale_ids)

        return rooms

    @staticmethod
    async def update_room_status(room_id: str, status: str) -> None:
        """更新房间状态（用于游戏结束时标记为 finished）"""
        room = await RoomService._get_room(room_id)
        if not room:
            return
        room.status = status
        await RoomService._save_room(room)

    @staticmethod
    async def reset_room(room_id: str, host_id: int) -> RoomInfo:
        """
        重置房间到等待状态（房主操作，游戏结束后返回准备阶段）

        - 将房间状态改回 waiting
        - 将真人玩家的准备状态重置
        - 重新生成 AI 玩家
        - 重新加入等待列表
        """
        room = await RoomService._get_room(room_id)
        if not room:
            raise ValueError("房间不存在")
        if room.host_id != host_id:
            raise ValueError("只有房主才能重置房间")
        if room.status != "finished":
            raise ValueError("只有已结束的房间才能重置")

        # 重置状态
        room.status = "waiting"

        # 重置真人玩家的准备状态
        for p in room.players:
            if not p.is_ai:
                p.is_ready = False

        # 重新生成 AI 玩家（保留 ai_count 配置）
        real_players = [p for p in room.players if not p.is_ai]
        ai_players_list: list[RoomPlayer] = []
        if room.ai_count > 0:
            ai_instances = AIPlayerFactory.create_batch(room.ai_count, room.ai_difficulty)
            for ai in ai_instances:
                ai_dict = ai.to_room_player_dict(room.ai_difficulty)
                ai_players_list.append(RoomPlayer(**ai_dict))

        room.players = real_players + ai_players_list

        # 清空观战者列表（除了房主观战者）
        # 房主如果是观战者，保留
        host_spectator = [s for s in room.spectators if s.user_id == host_id]
        room.spectators = host_spectator

        await RoomService._save_room(room)

        # 重新加入等待列表
        redis = await get_redis()
        await redis.sadd("room:list", room.id)

        return room

    # ─── 私有方法 ───

    @staticmethod
    async def is_spectator(room_id: str, user_id: int) -> bool:
        """检查用户是否是房间的观战者"""
        room = await RoomService._get_room(room_id)
        if not room:
            return False
        return any(s.user_id == user_id for s in room.spectators)

    @staticmethod
    async def _get_room(room_id: str) -> RoomInfo | None:
        """从 Redis 获取房间"""
        redis = await get_redis()
        data = await redis.get(f"room:{room_id}")
        if not data:
            return None
        return RoomInfo.model_validate_json(data)

    @staticmethod
    async def _save_room(room: RoomInfo) -> None:
        """保存房间到 Redis（并写穿透到 PostgreSQL 镜像）"""
        redis = await get_redis()
        room_key = f"room:{room.id}"
        await redis.set(room_key, room.model_dump_json(), ex=ROOM_TTL)
        # 刷新 code 映射的 TTL
        await redis.expire(f"room:code:{room.code}", ROOM_TTL)
        # 刷新密码 Key 的 TTL（存在时）
        await redis.expire(f"room:pwd:{room.id}", ROOM_TTL)
        # 写穿透到 rooms / room_players
        await RoomService._persist_room(room)

    @staticmethod
    async def _delete_room(room: RoomInfo) -> None:
        """删除房间（同时清理聊天记录与成员活跃索引）"""
        redis = await get_redis()
        async with redis.pipeline() as pipe:
            pipe.delete(f"room:{room.id}")
            pipe.delete(f"room:code:{room.code}")
            pipe.delete(f"room:pwd:{room.id}")
            pipe.srem("room:list", room.id)
            await pipe.execute()

        # 清理成员「用户 → 活跃房间」索引，避免残留导致用户无法再创建 / 加入房间
        await RoomService._unbind_room_members(room)

        # 清理聊天记录
        await ChatService.delete_chat(room.id)

        # 写穿透：房间销毁 → rooms.status = 2（已结束），保留历史不做物理删除
        await RoomService._mark_room_ended(room)

    # ─── 活跃房间索引（同一用户同时只能有一个活跃房间）───

    @staticmethod
    async def get_user_active_room(
        user_id: int,
        db: AsyncSession | None = None,
    ) -> RoomInfo | None:
        """获取用户当前活跃房间（无则返回 None）

        - Redis 索引 `user:room:{user_id}` 为运行时权威来源
        - 索引命中但用户已不是房间成员（或房间已过期）→ 视为脏数据，自动清理
        - Redis 索引缺失时回退到 users.active_room_id 持久化镜像
        """
        redis = await get_redis()
        room_id = await redis.get(_user_room_key(user_id))

        room = await RoomService._get_room(room_id) if room_id else None
        if room is not None and _is_room_member(room, user_id):
            return room

        if room_id:
            # 房间已过期或用户已被移除，清理索引
            await redis.delete(_user_room_key(user_id))
            await RoomService._set_active_room_mirror(user_id, None)

        # 回退到持久化镜像（跨实例 / Redis 重启场景）
        mirrored_id = await RoomService._active_room_id_from_db(user_id, db)
        if not mirrored_id:
            return None

        room = await RoomService._get_room(mirrored_id)
        if room is None or not _is_room_member(room, user_id):
            await RoomService._set_active_room_mirror(user_id, None)
            return None

        await RoomService._bind_user_room(user_id, room.id)
        return room

    @staticmethod
    async def _bind_user_room(user_id: int, room_id: str) -> None:
        """绑定「用户 → 活跃房间」索引（Redis + 持久化镜像）"""
        redis = await get_redis()
        await redis.set(_user_room_key(user_id), room_id, ex=ROOM_TTL)
        await RoomService._set_active_room_mirror(user_id, room_id)

    @staticmethod
    async def _unbind_user_room(user_id: int) -> None:
        """解绑「用户 → 活跃房间」索引（Redis + 持久化镜像）"""
        redis = await get_redis()
        await redis.delete(_user_room_key(user_id))
        await RoomService._set_active_room_mirror(user_id, None)

    @staticmethod
    async def _unbind_room_members(room: RoomInfo) -> None:
        """房间销毁时批量解绑全部成员索引（仅解绑仍指向本房间的成员）"""
        member_ids = _room_member_ids(room)
        if not member_ids:
            return

        redis = await get_redis()
        keys = [_user_room_key(uid) for uid in member_ids]
        owners = await redis.mget(*keys)
        stale_keys = [key for key, owner in zip(keys, owners) if owner == room.id]
        if stale_keys:
            await redis.delete(*stale_keys)

        await RoomService._clear_active_room_mirror(member_ids, room.id)

    @staticmethod
    async def _set_active_room_mirror(user_id: int, room_id: str | None) -> None:
        """把活跃房间写入 users.active_room_id（镜像，失败仅记日志）"""
        try:
            from app.core.database import async_session
        except Exception as e:  # pragma: no cover
            logger.warning("[RoomService] database unavailable: %s", e)
            return

        try:
            async with async_session() as db:
                user = await db.get(User, user_id)
                if user is None:
                    return
                if user.active_room_id == room_id:
                    return
                user.active_room_id = room_id
                await db.commit()
        except Exception as e:
            logger.warning("[RoomService] set active_room mirror for %s failed: %s", user_id, e)

    @staticmethod
    async def _clear_active_room_mirror(user_ids: list[int], room_id: str) -> None:
        """房间销毁时批量清理 users.active_room_id 镜像（仅清理仍指向本房间的用户）"""
        try:
            from app.core.database import async_session
        except Exception as e:  # pragma: no cover
            logger.warning("[RoomService] database unavailable: %s", e)
            return

        try:
            async with async_session() as db:
                result = await db.execute(
                    select(User).where(
                        User.id.in_(user_ids), User.active_room_id == room_id
                    )
                )
                changed = False
                for user in result.scalars().all():
                    user.active_room_id = None
                    changed = True
                if changed:
                    await db.commit()
        except Exception as e:
            logger.warning("[RoomService] clear active_room mirror for %s failed: %s", room_id, e)

    @staticmethod
    async def _active_room_id_from_db(
        user_id: int,
        db: AsyncSession | None = None,
    ) -> str | None:
        """读取 users.active_room_id 持久化镜像"""
        try:
            if db is not None:
                user = await db.get(User, user_id)
                return user.active_room_id if user is not None else None

            from app.core.database import async_session

            async with async_session() as session:
                user = await session.get(User, user_id)
                return user.active_room_id if user is not None else None
        except Exception as e:
            logger.warning("[RoomService] read active_room mirror for %s failed: %s", user_id, e)
            return None

    # ─── 持久化镜像 ───

    @staticmethod
    async def _persist_room(
        room: RoomInfo,
        password_hash: str | None = None,
        clear_password: bool = False,
    ) -> None:
        """把房间运行时状态镜像写入 rooms / room_players（docs/PROJECT.md 6.2）

        - 运行时以 Redis 为准，本方法只做镜像，异常仅记录日志，不影响主流程
        - room_players 采用「先删后插」保证镜像与运行时一致
        - password_hash：传入时同步 rooms.password_hash（房间密码持久化镜像）；
          clear_password=True 表示清除密码（写 NULL）
        """
        try:
            from app.core.database import async_session
        except Exception as e:  # pragma: no cover
            logger.warning("[RoomService] database unavailable: %s", e)
            return

        status_code = {"waiting": 0, "playing": 1, "finished": 2}.get(room.status, 0)
        try:
            async with async_session() as db:
                row = await db.get(Room, room.id)
                if row is None:
                    row = Room(id=room.id, room_code=room.code)
                    db.add(row)

                row.room_code = room.code
                row.name = room.name
                row.host_id = room.host_id
                row.max_players = room.max_players
                row.map_id = room.map_id
                row.ai_count = room.ai_count
                row.ai_difficulty = room.ai_difficulty
                row.status = status_code
                row.config = room.model_dump(mode="json")

                # 房间密码哈希镜像（Redis 为主，PostgreSQL 为持久化副本）
                if password_hash is not None:
                    row.password_hash = password_hash
                elif clear_password:
                    row.password_hash = None

                await db.execute(delete(RoomPlayerRow).where(RoomPlayerRow.room_id == room.id))
                for p in room.players:
                    db.add(
                        RoomPlayerRow(
                            room_id=room.id,
                            user_id=p.user_id,
                            nickname=p.nickname,
                            is_host=p.is_host,
                            is_ready=p.is_ready,
                            is_ai=p.is_ai,
                            ai_difficulty=p.ai_difficulty,
                            is_spectator=False,
                        )
                    )
                for s in room.spectators:
                    db.add(
                        RoomPlayerRow(
                            room_id=room.id,
                            user_id=s.user_id,
                            nickname=s.nickname,
                            is_host=s.is_host,
                            is_ready=False,
                            is_ai=False,
                            ai_difficulty=None,
                            is_spectator=True,
                        )
                    )
                await db.commit()
        except Exception as e:
            logger.warning("[RoomService] persist room %s failed: %s", room.id, e)

    @staticmethod
    async def _mark_room_ended(room: RoomInfo) -> None:
        """房间销毁时把镜像标记为已结束（保留房间历史记录）"""
        try:
            from app.core.database import async_session

            async with async_session() as db:
                row = await db.get(Room, room.id)
                if row is not None:
                    row.status = 2
                    await db.commit()
        except Exception as e:
            logger.warning("[RoomService] mark room %s ended failed: %s", room.id, e)
