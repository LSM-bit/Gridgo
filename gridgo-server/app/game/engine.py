"""
游戏引擎核心

GameEngine 是游戏对局的核心驱动，负责：
  - 状态机流转（TURN_START → WAIT_ROLL → ... → TURN_END）
  - 回合循环控制
  - AI 回合自动执行
  - 超时处理
  - 游戏状态 Redis 持久化
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import datetime

from app.core.config import settings
from app.core.redis import get_redis
from app.game.events import manager as ws_manager
from app.game.schemas import (
    AuctionState,
    CardInfo,
    DiceState,
    EndReason,
    GamePhase,
    GameState,
    PlayerState,
    TileState,
)
from app.game.replay import ReplayRecorder
from app.services.map import MapService

GAME_TTL = 60 * 60 * 24  # GameState 在 Redis 中的 TTL: 24 小时


def _player_idx(state: GameState, player_id: int) -> int:
    """根据 player_id 获取在 players 列表中的索引，找不到返回 -1"""
    for i, p in enumerate(state.players):
        if p.user_id == player_id:
            return i
    return -1


class GameEngine:
    """
    游戏引擎 — 每局游戏对应一个实例

    使用方式：
        engine = GameEngine(room_id)
        await engine.initialize(db, room_players, map_id)
        ...
        await engine.roll_dice(player_id)
        await engine.buy_property(player_id, tile_position)
        ...
    """

    def __init__(self, room_id: str) -> None:
        self.room_id = room_id
        self.state: GameState | None = None
        self._lock = asyncio.Lock()  # 并发安全锁
        self._timers: dict[str, asyncio.Task] = {}  # 计时器任务
        self._ai_task_running = False  # 防止重复创建 AI 任务
        self._ai_task_ref: asyncio.Task | None = None  # AI 任务引用，防止 GC
        self._replay: ReplayRecorder | None = None  # 对局回放记录器

    # ═══════════════════════════════════════════════════════
    # 游戏初始化
    # ═══════════════════════════════════════════════════════

    async def initialize(
        self,
        db,
        room_players: list[dict],
        map_id: str = "classic",
    ) -> GameState:
        """
        初始化游戏

        Args:
            db: 数据库会话
            room_players: 房间玩家列表，每个元素为 RoomPlayer 的 dict
            map_id: 地图 ID
        """
        # 1. 加载地图模板
        template = await MapService.load_map_template(db, map_id)
        map_info = template["info"]

        # 2. 创建玩家状态
        players = []
        for p in room_players:
            ps = PlayerState(
                user_id=p["user_id"],
                nickname=p["nickname"],
                cash=settings.GAME_INITIAL_CASH,
                position=0,
                is_ai=p.get("is_ai", False),
                ai_difficulty=p.get("ai_difficulty"),
            )
            players.append(ps)

        # 3. 随机玩家顺序
        random.shuffle(players)

        # 4. 初始化地块状态
        tiles = []
        for t in template["tiles"]:
            ts = TileState(
                position=t["position"],
                name=t["name"],
                tile_type=t["tile_type"],
                tile_group=t.get("tile_group"),
                group_color=t.get("group_color"),
                price=t.get("price"),
                build_cost=t.get("build_cost"),
                rent_0=t.get("rent_0"),
                rent_1=t.get("rent_1"),
                rent_2=t.get("rent_2"),
                rent_3=t.get("rent_3"),
                rent_4=t.get("rent_4"),
                rent_5=t.get("rent_5"),
                tax_amount=t.get("tax_amount"),
                tax_is_percent=t.get("tax_is_percent"),
            )
            tiles.append(ts)

        # 5. 洗牌卡组
        chance_deck, fate_deck = await MapService.shuffle_decks(template)

        # 5.1 缓存卡片数据到 Redis（供 _get_cards_list 查找卡片信息）
        self._cached_cards = template["cards"]
        redis = await get_redis()
        import json
        await redis.set(f"game:{self.room_id}:cards", json.dumps(template["cards"]), ex=GAME_TTL)

        # 6. 创建 GameState
        game_id = uuid.uuid4().hex[:12]
        self.state = GameState(
            game_id=game_id,
            room_id=self.room_id,
            map_id=map_id,
            turn_number=0,
            current_player_index=0,
            phase=GamePhase.TURN_START,
            players=players,
            tiles=tiles,
            chance_deck=chance_deck,
            fate_deck=fate_deck,
            station_rent=template["station_rent"],
            utility_multiplier=template["utility_multiplier"],
            start_bonus=map_info["start_bonus"],
            jail_bail=map_info["jail_bail"],
            max_build_level=map_info["max_build_level"],
            initial_cash=settings.GAME_INITIAL_CASH,
            max_turns=settings.GAME_MAX_TURNS,
            turn_timeout=settings.GAME_TURN_TIMEOUT,
        )

        # 6.1 初始化回放记录器
        self._replay = ReplayRecorder()
        self._replay.set_init_state(self.state)

        # 7. 存入 Redis
        await self._save_state()

        # 8. 启动第一个回合
        await self._start_turn()

        return self.state

    # ═══════════════════════════════════════════════════════
    # 从 Redis 加载引擎
    # ═══════════════════════════════════════════════════════

    async def load_state(self) -> GameState | None:
        """从 Redis 加载游戏状态"""
        redis = await get_redis()
        data = await redis.get(f"game:{self.room_id}")
        if not data:
            return None
        self.state = GameState.model_validate_json(data)

        # 恢复卡片缓存
        try:
            cards_data = await redis.get(f"game:{self.room_id}:cards")
            if cards_data:
                import json
                self._cached_cards = json.loads(cards_data)
        except Exception:
            pass

        return self.state

    async def resume_active_tasks(self) -> None:
        """
        根据当前游戏状态恢复后台任务（AI 回合、超时计时器）

        在 WS 重连或引擎重新加载状态后调用，
        因为 asyncio.Task 和计时器不会随 Redis 持久化。
        """
        if not self.state or self.state.phase == GamePhase.GAME_OVER:
            return

        # 取消所有可能残留的旧任务
        self._cancel_all_timers()

        player = self.state.get_current_player()
        if not player:
            return

        logger = logging.getLogger(__name__)
        logger.info(f"resume_active_tasks phase={self.state.phase} player_id={player.user_id} is_ai={player.is_ai}")

        # 根据当前阶段恢复对应的任务
        if self.state.phase == GamePhase.WAIT_ROLL:
            if player.is_ai:
                self._start_ai_task(self._ai_turn_loop(player))
            else:
                self._start_timer("roll", self.state.turn_timeout, self._on_roll_timeout)

        elif self.state.phase == GamePhase.WAIT_DECISION:
            if player.is_ai:
                tile = self.state.get_tile(player.position)
                if tile:
                    self._start_ai_task(self._ai_buy_decision(player, tile))
            else:
                self._start_timer("decision", 15, self._on_decision_timeout)

        elif self.state.phase == GamePhase.FREE_ACTION:
            if player.is_ai:
                self._start_ai_task(self._ai_free_action(player))
            else:
                self._start_timer("free_action", self.state.turn_timeout, self._on_free_action_timeout)

        elif self.state.phase in (GamePhase.TURN_START, GamePhase.ROLLING, GamePhase.MOVING, GamePhase.TILE_EFFECT):
            # 这些是瞬态阶段，理论上不应该停留。
            # 安全起见，如果是 AI 回合，重新启动 AI 循环
            if player.is_ai:
                self._start_ai_task(self._ai_turn_loop(player))
            else:
                # 真人玩家的瞬态阶段，短暂等待后重新检查
                # 可能是上一次操作中途断开，尝试恢复
                if self.state.phase == GamePhase.TURN_START:
                    self.state.phase = GamePhase.WAIT_ROLL
                    await self._save_state()
                    self._start_timer("roll", self.state.turn_timeout, self._on_roll_timeout)

        elif self.state.phase == GamePhase.TURN_END:
            # TURN_END 是过渡阶段，_end_turn 应该继续推进到下一回合
            # 如果卡在这里说明 AI 任务在 _end_turn 中途异常了
            if player.is_ai:
                logger.info(f"resume_active_tasks: TURN_END phase, re-calling _end_turn for AI player={player.nickname}")
                self._start_ai_task(self._resume_end_turn())

    async def _resume_end_turn(self) -> None:
        """从 TURN_END 阶段恢复：重新执行回合结束逻辑"""
        await self.load_state()
        if not self.state or self.state.phase == GamePhase.GAME_OVER:
            return
        # 直接重新调用 _end_turn，它会检查状态并推进到下一回合
        await self._end_turn()

    async def _save_state(self) -> None:
        """保存游戏状态到 Redis，并广播最新快照给所有客户端"""
        if not self.state:
            return
        try:
            redis = await get_redis()
            await redis.set(f"game:{self.room_id}", self.state.model_dump_json(), ex=GAME_TTL)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"_save_state Redis write failed: room_id={self.room_id} error={e}")
            # 不抛出异常，避免 AI 任务因 Redis 写入失败而中断

        # 广播完整状态快照，让前端自动刷新 UI
        try:
            await ws_manager.broadcast(self.room_id, "state.update", self.state.model_dump())
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"_save_state broadcast failed: room_id={self.room_id} error={e}")

    # ═══════════════════════════════════════════════════════
    # 回合流程
    # ═══════════════════════════════════════════════════════

    def _start_ai_task(self, coro) -> None:
        """安全启动 AI 任务，防止重复创建"""
        if self._ai_task_running:
            return
        self._ai_task_running = True

        async def _wrapped():
            try:
                await coro
            except Exception:
                logger = logging.getLogger(__name__)
                logger.exception(f"AI task crashed, room_id={self.room_id}")
                # 异常后尝试恢复：重新加载状态并恢复 AI 任务
                try:
                    await self.load_state()
                    if self.state and self.state.phase != GamePhase.GAME_OVER:
                        self._ai_task_running = False
                        await self.resume_active_tasks()
                        return
                except Exception:
                    logger.exception(f"AI task recovery failed, room_id={self.room_id}")
            finally:
                self._ai_task_running = False
                # 正常完成后，检查游戏是否仍需要 AI 推进
                # 如果是（比如 AI 提前返回但游戏还没结束），延迟后自动恢复
                try:
                    await asyncio.sleep(2.0)
                    await self._ai_watchdog()
                except Exception:
                    pass

        task = asyncio.create_task(_wrapped())
        # 存储任务引用，防止被 GC 回收
        self._ai_task_ref = task

    async def _ai_watchdog(self) -> None:
        """
        AI 守护进程：定期检查游戏是否卡住

        如果游戏处于应由 AI 操作的阶段但 _ai_task_running 为 False，
        说明 AI 任务已经异常终止，需要恢复。
        """
        if not self.state or self.state.phase == GamePhase.GAME_OVER:
            return

        player = self.state.get_current_player()
        if not player or not player.is_ai:
            return

        # AI 应该在操作的阶段（包括 TURN_END，因为 _end_turn 会继续推进）
        ai_phases = {GamePhase.WAIT_ROLL, GamePhase.WAIT_DECISION, GamePhase.FREE_ACTION,
                     GamePhase.TURN_START, GamePhase.ROLLING, GamePhase.MOVING, GamePhase.TILE_EFFECT,
                     GamePhase.TURN_END}

        if self.state.phase in ai_phases and not self._ai_task_running:
            logger = logging.getLogger(__name__)
            logger.warning(
                f"AI watchdog detected stalled game! room_id={self.room_id} "
                f"phase={self.state.phase} player={player.nickname}, recovering..."
            )
            await self.resume_active_tasks()

    async def _start_turn(self) -> None:
        """回合开始"""
        if not self.state:
            return

        self.state.turn_number += 1
        self.state.phase = GamePhase.WAIT_ROLL
        self.state.consecutive_doubles = 0
        player = self.state.get_current_player()

        # 广播回合变更
        await ws_manager.broadcast(self.room_id, "game.turn_change", {
            "current_player_id": player.user_id,
            "current_player_nickname": player.nickname,
            "turn_number": self.state.turn_number,
            "is_ai": player.is_ai,
        })

        await self._save_state()

        # 如果是 AI，延迟后自动掷骰
        if player.is_ai:
            if self._ai_task_running:
                # 已在 AI 任务中（链式调用），直接 await
                await self._ai_turn_loop(player)
            else:
                self._start_ai_task(self._ai_turn_loop(player))

        else:
            # 真人玩家启动超时计时器
            self._start_timer("roll", self.state.turn_timeout, self._on_roll_timeout)

    async def _ai_turn_loop(self, player: PlayerState) -> None:
        """AI 回合自动执行循环"""
        logger = logging.getLogger(__name__)
        logger.info(f"AI turn loop start: room_id={self.room_id} player={player.nickname} turn={self.state.turn_number if self.state else '?'}")

        # 重新加载状态（可能已被其他操作修改）
        await self.load_state()
        if not self.state or self.state.phase == GamePhase.GAME_OVER:
            logger.info(f"AI turn loop skip: state={'None' if not self.state else self.state.phase}")
            return

        current = self.state.get_current_player()
        if current.user_id != player.user_id:
            logger.info(f"AI turn loop skip: not current player (expected={player.user_id} actual={current.user_id})")
            return  # 已经不是此玩家的回合

        # 检查是否在监狱
        if current.is_in_jail:
            await self._ai_jail_decision(current)
            return

        # 掷骰子
        await self._execute_roll(current.user_id)

    async def _ai_jail_decision(self, player: PlayerState) -> None:
        """AI 监狱决策"""
        await self.load_state()

        if player.get_out_of_jail_cards > 0:
            await self._use_jail_card(player.user_id, auto_roll=True)
        elif player.cash > 200:
            await self._pay_jail_bail(player.user_id, auto_roll=True)
        else:
            # 尝试掷双数出狱
            await self._execute_roll(player.user_id)

    # ═══════════════════════════════════════════════════════
    # 掷骰子
    # ═══════════════════════════════════════════════════════

    async def roll_dice(self, player_id: int) -> None:
        """
        玩家请求掷骰子

        Args:
            player_id: 发起掷骰的玩家 ID
        """
        async with self._lock:
            await self.load_state()
            if not self.state:
                return

            player = self.state.get_current_player()
            if player.user_id != player_id:
                return
            if self.state.phase not in (GamePhase.WAIT_ROLL,):
                return

            self._cancel_timer("roll")
            await self._execute_roll(player_id)

    async def _execute_roll(self, player_id: int) -> None:
        """执行掷骰子逻辑"""
        if not self.state:
            return

        player = self.state.get_current_player()
        if player.user_id != player_id:
            return

        self.state.phase = GamePhase.ROLLING

        # 生成骰子
        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        is_double = d1 == d2
        self.state.dice = DiceState(values=[d1, d2], total=d1 + d2, is_double=is_double)

        # 回放记录：掷骰子
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_roll(self.state.turn_number, idx, d1, d2)

        # 连续双数检查
        if is_double:
            self.state.consecutive_doubles += 1
            if self.state.consecutive_doubles >= 3:
                # 连续3次双数，直接入狱
                await ws_manager.broadcast(self.room_id, "game.dice_result", {
                    "player_id": player_id,
                    "dice": [d1, d2],
                    "total": d1 + d2,
                    "is_double": True,
                    "speed_trap": True,
                })
                await self._send_to_jail(player_id, reason="speed_trap")
                return
        else:
            self.state.consecutive_doubles = 0

        # 广播骰子结果
        await ws_manager.broadcast(self.room_id, "game.dice_result", {
            "player_id": player_id,
            "dice": [d1, d2],
            "total": d1 + d2,
            "is_double": is_double,
        })

        await self._save_state()

        # 在监狱中的玩家：仅双数可出狱
        if player.is_in_jail:
            if is_double:
                # 双数出狱
                player.is_in_jail = False
                player.jail_turns = 0
                await ws_manager.broadcast(self.room_id, "game.jail_released", {
                    "player_id": player_id,
                    "method": "double",
                })
                # 回放记录：双数出狱
                if self._replay:
                    idx = _player_idx(self.state, player_id)
                    self._replay.record_jail(self.state.turn_number, idx, "r")
                # 出狱后正常移动
                await self._move_player(player_id)
            else:
                # 非双数，监狱回合+1
                player.jail_turns += 1
                if player.jail_turns >= 3:
                    # 强制保释
                    bail = self.state.jail_bail
                    player.cash -= bail
                    player.is_in_jail = False
                    player.jail_turns = 0
                    # 回放记录：强制保释
                    if self._replay:
                        idx = _player_idx(self.state, player_id)
                        self._replay.record_jail(self.state.turn_number, idx, "b")
                        self._replay.record_money(self.state.turn_number, idx, -bail)
                    await ws_manager.broadcast(self.room_id, "game.jail_released", {
                        "player_id": player_id,
                        "method": "forced_bail",
                        "amount": bail,
                    })
                    await self._move_player(player_id)
                else:
                    # 继续关押，回合结束
                    await self._end_turn()
            return

        # 正常移动
        await self._move_player(player_id)

    # ═══════════════════════════════════════════════════════
    # 棋子移动
    # ═══════════════════════════════════════════════════════

    async def _move_player(self, player_id: int, steps: int | None = None) -> None:
        """
        移动玩家棋子

        Args:
            player_id: 玩家 ID
            steps: 移动步数（None 时使用骰子点数）
        """
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        self.state.phase = GamePhase.MOVING
        move_steps = steps if steps is not None else self.state.dice.total
        old_pos = player.position
        new_pos = (old_pos + move_steps) % len(self.state.tiles)
        passed_go = new_pos < old_pos  # 经过起点

        player.position = new_pos

        # 回放记录：移动
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_move(self.state.turn_number, idx, new_pos)
            if passed_go:
                self._replay.record_money(self.state.turn_number, idx, self.state.start_bonus)
        if passed_go:
            player.cash += self.state.start_bonus
            await ws_manager.send_to_player(self.room_id, player_id, "game.pass_go", {
                "amount": self.state.start_bonus,
                "cash": player.cash,
            })

        # 广播移动
        await ws_manager.broadcast(self.room_id, "game.player_moved", {
            "player_id": player_id,
            "from": old_pos,
            "to": new_pos,
            "steps": move_steps,
            "passed_go": passed_go,
        })

        await self._save_state()

        # 触发地块效果
        await self._process_tile_effect(player_id)

    async def _move_player_to_position(self, player_id: int, target_pos: int, collect_go_bonus: bool = True) -> None:
        """
        将玩家移动到指定位置（卡片效果等）

        Args:
            player_id: 玩家 ID
            target_pos: 目标位置
            collect_go_bonus: 是否收取过路费（前进类卡片收，入狱类不收）
        """
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        old_pos = player.position
        passed_go = target_pos < old_pos  # 正向移动经过起点

        player.position = target_pos

        # 回放记录：卡片效果移动
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_move(self.state.turn_number, idx, target_pos)

        if collect_go_bonus and passed_go:
            player.cash += self.state.start_bonus
            await ws_manager.send_to_player(self.room_id, player_id, "game.pass_go", {
                "amount": self.state.start_bonus,
                "cash": player.cash,
            })
            if self._replay:
                self._replay.record_money(self.state.turn_number, _player_idx(self.state, player_id), self.state.start_bonus)

        await ws_manager.broadcast(self.room_id, "game.player_moved", {
            "player_id": player_id,
            "from": old_pos,
            "to": target_pos,
            "steps": (target_pos - old_pos) % len(self.state.tiles),
            "passed_go": collect_go_bonus and passed_go,
        })

        await self._save_state()

    # ═══════════════════════════════════════════════════════
    # 地块效果
    # ═══════════════════════════════════════════════════════

    async def _process_tile_effect(self, player_id: int) -> None:
        """处理玩家到达地块后的效果"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        tile = self.state.get_tile(player.position)
        logger = logging.getLogger(__name__)
        logger.info(f"tile_effect player_id={player_id} position={player.position} tile_name={tile.name} tile_type={tile.tile_type}")

        self.state.phase = GamePhase.TILE_EFFECT

        if tile.tile_type == "START":
            # 起点奖金已在移动时发放
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)

        elif tile.tile_type == "PROPERTY":
            await self._process_buyable_tile(player_id, tile)

        elif tile.tile_type == "STATION":
            await self._process_buyable_tile(player_id, tile)

        elif tile.tile_type == "UTILITY":
            await self._process_buyable_tile(player_id, tile)

        elif tile.tile_type == "CHANCE":
            await self._process_card(player_id, "CHANCE")

        elif tile.tile_type == "FATE":
            await self._process_card(player_id, "FATE")

        elif tile.tile_type == "TAX":
            await self._process_tax(player_id, tile)

        elif tile.tile_type == "JAIL":
            # 仅停留
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)

        elif tile.tile_type == "GO_TO_JAIL":
            await self._send_to_jail(player_id, reason="go_to_jail")
            return  # 入狱直接回合结束

        elif tile.tile_type == "PARKING":
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)

    async def _process_buyable_tile(self, player_id: int, tile: TileState) -> None:
        """处理可购买地块（PROPERTY/STATION/UTILITY）"""
        if not self.state:
            return

        if tile.owner_id is None:
            # 无主地产 → 等待购买决策
            self.state.phase = GamePhase.WAIT_DECISION
            await ws_manager.broadcast(self.room_id, "game.tile_event", {
                "player_id": player_id,
                "tile_id": tile.position,
                "tile_name": tile.name,
                "event_type": "property_unowned",
                "price": tile.price,
            })
            await self._save_state()

            # AI 决策
            player = self.state.get_player_by_id(player_id)
            if player.is_ai:
                # AI 子流程直接 await，不创建新 task
                await self._ai_buy_decision(player, tile)
            else:
                self._start_timer("decision", 15, self._on_decision_timeout)

        elif tile.owner_id == player_id:
            # 己方地产 → 可升级
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)

        else:
            # 他人地产 → 支付租金
            rent = self.state.calculate_rent(tile, self.state.dice.total)
            if rent > 0:
                await self._pay_rent(player_id, tile.owner_id, rent, tile)
            # 租金支付后进入自由行动
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)

    async def _pay_rent(self, from_id: int, to_id: int, amount: int, tile: TileState) -> None:
        """支付租金"""
        if not self.state:
            return

        payer = self.state.get_player_by_id(from_id)
        receiver = self.state.get_player_by_id(to_id)

        if not payer or not receiver:
            return

        # 抵押的地产不收租
        if tile.is_mortgaged:
            return

        if payer.cash < amount:
            # 现金不足，进入破产处理
            await self._handle_bankruptcy(from_id, to_id, amount)
            return

        payer.cash -= amount
        receiver.cash += amount

        # 回放记录：支付租金
        if self._replay:
            payer_idx = _player_idx(self.state, from_id)
            self._replay.record_rent(self.state.turn_number, payer_idx, tile.position)
            self._replay.record_money(self.state.turn_number, payer_idx, -amount)
            receiver_idx = _player_idx(self.state, to_id)
            self._replay.record_money(self.state.turn_number, receiver_idx, amount)

        await ws_manager.broadcast(self.room_id, "game.rent_paid", {
            "from_id": from_id,
            "to_id": to_id,
            "amount": amount,
            "tile_id": tile.position,
            "tile_name": tile.name,
            "payer_cash": payer.cash,
            "receiver_cash": receiver.cash,
        })

        await self._save_state()

    async def _process_tax(self, player_id: int, tile: TileState) -> None:
        """处理税收"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        amount = tile.tax_amount or 0
        if tile.tax_is_percent:
            amount = int(player.cash * (tile.tax_amount or 10) / 100)

        if player.cash < amount:
            await self._handle_bankruptcy(player_id, creditor_id=0, debt=amount)
        else:
            player.cash -= amount
            # 回放记录：缴税
            if self._replay:
                idx = _player_idx(self.state, player_id)
                self._replay.record_money(self.state.turn_number, idx, -amount)
            await ws_manager.broadcast(self.room_id, "game.tax_paid", {
                "player_id": player_id,
                "amount": amount,
                "tile_name": tile.name,
                "cash": player.cash,
            })

        self.state.phase = GamePhase.FREE_ACTION
        await self._save_state()
        await self._on_enter_free_action(player_id)

    # ═══════════════════════════════════════════════════════
    # 卡片效果
    # ═══════════════════════════════════════════════════════

    async def _process_card(self, player_id: int, card_type: str) -> None:
        """抽取并执行卡片效果"""
        logger = logging.getLogger(__name__)
        logger.info(f"card_process_start player_id={player_id} card_type={card_type}")

        if not self.state:
            return

        # 抽卡
        if card_type == "CHANCE":
            # 如果牌堆和弃牌堆都空，重新初始化
            if not self.state.chance_deck and not self.state.chance_discard:
                chance_ids = [c["card_id"] for c in await self._get_cards_list() if c["card_type"] == "CHANCE"]
                random.shuffle(chance_ids)
                self.state.chance_deck = chance_ids
                logger.info(f"chance_deck_refilled count={len(chance_ids)}")
            card_id = self.state.draw_chance_card()
        else:
            if not self.state.fate_deck and not self.state.fate_discard:
                fate_ids = [c["card_id"] for c in await self._get_cards_list() if c["card_type"] == "FATE"]
                random.shuffle(fate_ids)
                self.state.fate_deck = fate_ids
                logger.info(f"fate_deck_refilled count={len(fate_ids)}")
            card_id = self.state.draw_fate_card()

        logger.info(f"card_drawn card_type={card_type} card_id={card_id} chance_deck_len={len(self.state.chance_deck)} fate_deck_len={len(self.state.fate_deck)}")

        if not card_id:
            # 牌堆为空，跳过卡片效果
            logger.warning("card_deck_empty", card_type=card_type)
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)
            return

        # 查找卡片信息
        cards_list = await self._get_cards_list()
        logger.info(f"cards_list_loaded count={len(cards_list)}")

        card_info = None
        for c in cards_list:
            if c["card_id"] == card_id and c["card_type"] == card_type:
                card_info = c
                break

        if not card_info:
            # 卡片信息未找到，跳过
            logger.warning(f"card_not_found card_id={card_id} card_type={card_type}")
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)
            return

        # 广播抽卡
        await ws_manager.broadcast(self.room_id, "game.card_drawn", {
            "player_id": player_id,
            "card_type": card_type,
            "card_id": card_id,
            "card_name": card_info["name"],
            "effect_type": card_info["effect_type"],
            "effect_value": card_info["effect_value"],
            "description": card_info["description"],
        })

        # 回放记录：抽卡
        if self._replay:
            idx = _player_idx(self.state, player_id)
            replay_card_type = "C" if card_type == "CHANCE" else "F"
            self._replay.record_card(self.state.turn_number, idx, replay_card_type, card_id)

        # 执行卡片效果
        await self._execute_card_effect(player_id, card_info)

        # 使用后的卡放入弃牌堆（免罪卡除外）
        if card_info["effect_type"] != "get_out_of_jail":
            self.state.discard_card(card_type, card_id)

        await self._save_state()

    async def _get_cards_list(self) -> list[dict]:
        """获取卡片列表（优先内存缓存，其次 Redis，最后懒加载）"""
        logger = logging.getLogger(__name__)

        # 1. 内存缓存
        cards = getattr(self, "_cached_cards", None)
        if cards:
            logger.info(f"cards_from_memory count={len(cards)}")
            return cards

        # 2. Redis 缓存
        try:
            redis = await get_redis()
            import json
            data = await redis.get(f"game:{self.room_id}:cards")
            if data:
                cards = json.loads(data)
                self._cached_cards = cards
                logger.info(f"cards_from_redis count={len(cards)}")
                return cards
            else:
                logger.warning(f"cards_redis_miss key=game:{self.room_id}:cards")
        except Exception as e:
            logger.error(f"cards_redis_error error={str(e)}")

        # 3. 兜底：从数据库加载
        try:
            from app.core.database import async_session
            async with async_session() as db:
                template = await MapService.load_map_template(db, self.state.map_id)
                cards = template["cards"]
                self._cached_cards = cards
                # 写入 Redis 供后续使用
                redis = await get_redis()
                await redis.set(f"game:{self.room_id}:cards", json.dumps(cards), ex=GAME_TTL)
                logger.info(f"cards_from_db count={len(cards)}")
                return cards
        except Exception as e:
            logger.error(f"cards_db_error error={str(e)}")
            return []

    async def _execute_card_effect(self, player_id: int, card: dict) -> None:
        """执行卡片效果"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        effect = card["effect_type"]
        value = card.get("effect_value")

        if effect == "move_to_position":
            target = value or 0
            await self._move_player_to_position(player_id, target, collect_go_bonus=True)
            # 移动后触发地块效果
            await self._process_tile_effect(player_id)

        elif effect == "move_forward":
            steps = value or 0
            await self._move_player(player_id, steps=steps)
            # _move_player 已包含地块效果

        elif effect == "move_backward":
            steps = value or 0
            new_pos = (player.position - steps) % len(self.state.tiles)
            await self._move_player_to_position(player_id, new_pos, collect_go_bonus=False)
            await self._process_tile_effect(player_id)

        elif effect == "move_to_nearest_station":
            # 移动到最近的车站
            stations = [i for i, t in enumerate(self.state.tiles) if t.tile_type == "STATION"]
            nearest = min(stations, key=lambda s: (s - player.position) % len(self.state.tiles))
            await self._move_player_to_position(player_id, nearest, collect_go_bonus=True)
            # 需付双倍租金
            tile = self.state.get_tile(nearest)
            if tile.owner_id and tile.owner_id != player_id and not tile.is_mortgaged:
                rent = self.state.calculate_rent(tile, self.state.dice.total) * 2
                await self._pay_rent(player_id, tile.owner_id, rent, tile)
            else:
                await self._process_tile_effect(player_id)

        elif effect == "gain_money":
            amount = value or 0
            player.cash += amount
            # 回放记录：卡片获得金钱
            if self._replay:
                idx = _player_idx(self.state, player_id)
                self._replay.record_money(self.state.turn_number, idx, amount)
            await ws_manager.broadcast(self.room_id, "game.money_change", {
                "player_id": player_id,
                "amount": amount,
                "cash": player.cash,
                "reason": card["name"],
            })

        elif effect == "lose_money":
            amount = value or 0
            if player.cash < amount:
                await self._handle_bankruptcy(player_id, creditor_id=0, debt=amount)
            else:
                player.cash -= amount
                # 回放记录：卡片失去金钱
                if self._replay:
                    idx = _player_idx(self.state, player_id)
                    self._replay.record_money(self.state.turn_number, idx, -amount)
                await ws_manager.broadcast(self.room_id, "game.money_change", {
                    "player_id": player_id,
                    "amount": -amount,
                    "cash": player.cash,
                    "reason": card["name"],
                })

        elif effect == "pay_per_house":
            # 每栋房屋支付 value，酒店按 value*4
            total = 0
            for pos in player.properties:
                tile = self.state.tiles[pos]
                if tile.build_level > 0 and tile.build_level < 5:
                    total += value * tile.build_level
                elif tile.build_level == 5:
                    total += value * 4  # 酒店
            if player.cash < total:
                await self._handle_bankruptcy(player_id, creditor_id=0, debt=total)
            else:
                player.cash -= total
                # 回放记录：卡片按房屋付费
                if self._replay:
                    idx = _player_idx(self.state, player_id)
                    self._replay.record_money(self.state.turn_number, idx, -total)
                await ws_manager.broadcast(self.room_id, "game.money_change", {
                    "player_id": player_id,
                    "amount": -total,
                    "cash": player.cash,
                    "reason": card["name"],
                })

        elif effect == "gain_from_all":
            amount_per = value or 0
            total_gained = 0
            for p in self.state.get_active_players():
                if p.user_id != player_id:
                    pay = min(amount_per, p.cash)
                    p.cash -= pay
                    total_gained += pay
            player.cash += total_gained
            # 回放记录：卡片从全体获得
            if self._replay:
                idx = _player_idx(self.state, player_id)
                self._replay.record_money(self.state.turn_number, idx, total_gained)
            await ws_manager.broadcast(self.room_id, "game.money_change", {
                "player_id": player_id,
                "amount": total_gained,
                "cash": player.cash,
                "reason": card["name"],
            })

        elif effect == "go_to_jail":
            await self._send_to_jail(player_id, reason="card")
            return  # 不进入自由行动

        elif effect == "get_out_of_jail":
            player.get_out_of_jail_cards += 1
            await ws_manager.broadcast(self.room_id, "game.get_out_of_jail_card", {
                "player_id": player_id,
                "card_name": card["name"],
                "total_cards": player.get_out_of_jail_cards,
            })

        # 如果不是入狱，且当前不是其他流程，进入自由行动
        if effect not in ("go_to_jail", "move_to_position", "move_forward", "move_backward", "move_to_nearest_station"):
            self.state.phase = GamePhase.FREE_ACTION
            await self._save_state()
            await self._on_enter_free_action(player_id)

    # ═══════════════════════════════════════════════════════
    # 监狱机制
    # ═══════════════════════════════════════════════════════

    async def _send_to_jail(self, player_id: int, reason: str = "go_to_jail") -> None:
        """将玩家送入监狱"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        player.is_in_jail = True
        player.jail_turns = 0
        player.position = 10  # 监狱位置

        # 回放记录：入狱（移动到监狱位置）
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_move(self.state.turn_number, idx, 10)

        await ws_manager.broadcast(self.room_id, "game.jail_sent", {
            "player_id": player_id,
            "reason": reason,
        })

        await self._save_state()
        # 入狱直接回合结束
        await self._end_turn()

    async def _pay_jail_bail(self, player_id: int, auto_roll: bool = False) -> None:
        """支付保释金"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player or not player.is_in_jail:
            return

        bail = self.state.jail_bail
        player.cash -= bail
        player.is_in_jail = False
        player.jail_turns = 0

        # 回放记录：保释金出狱
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_jail(self.state.turn_number, idx, "b")
            self._replay.record_money(self.state.turn_number, idx, -bail)

        await ws_manager.broadcast(self.room_id, "game.jail_released", {
            "player_id": player_id,
            "method": "bail",
            "amount": bail,
            "cash": player.cash,
        })

        self.state.phase = GamePhase.WAIT_ROLL
        await self._save_state()

        # AI 出狱后自动掷骰子移动
        if auto_roll:
            await self._execute_roll(player_id)

    async def _use_jail_card(self, player_id: int, auto_roll: bool = False) -> None:
        """使用免罪卡出狱"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player or not player.is_in_jail or player.get_out_of_jail_cards <= 0:
            return

        player.get_out_of_jail_cards -= 1
        player.is_in_jail = False
        player.jail_turns = 0

        # 回放记录：免罪卡出狱
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_jail(self.state.turn_number, idx, "c")

        await ws_manager.broadcast(self.room_id, "game.jail_released", {
            "player_id": player_id,
            "method": "card",
            "remaining_cards": player.get_out_of_jail_cards,
        })

        self.state.phase = GamePhase.WAIT_ROLL
        await self._save_state()

        # AI 出狱后自动掷骰子移动
        if auto_roll:
            await self._execute_roll(player_id)

    # ═══════════════════════════════════════════════════════
    # 玩家操作
    # ═══════════════════════════════════════════════════════

    # ═══════════════════════════════════════════════════════
    # 玩家操作（公开方法 + 内部实现）
    # ═══════════════════════════════════════════════════════

    # --- 购买地产 ---

    async def buy_property(self, player_id: int, tile_position: int) -> None:
        """购买地产（公开接口，带锁）"""
        async with self._lock:
            await self.load_state()
            await self._do_buy_property(player_id, tile_position)

    async def _do_buy_property(self, player_id: int, tile_position: int) -> None:
        """购买地产（内部实现，无锁，AI 可直接调用）"""
        if not self.state:
            return

        player = self.state.get_current_player()
        if player.user_id != player_id:
            return

        tile = self.state.get_tile(tile_position)
        if tile.owner_id is not None:
            return
        if player.cash < (tile.price or 0):
            return

        self._cancel_timer("decision")

        # 扣款
        player.cash -= tile.price
        tile.owner_id = player_id
        player.properties.append(tile_position)

        # 回放记录：购买地产
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_buy(self.state.turn_number, idx, tile_position)
            self._replay.record_money(self.state.turn_number, idx, -(tile.price or 0))

        await ws_manager.broadcast(self.room_id, "game.property_bought", {
            "player_id": player_id,
            "tile_id": tile_position,
            "tile_name": tile.name,
            "price": tile.price,
            "cash": player.cash,
        })

        # 进入自由行动
        self.state.phase = GamePhase.FREE_ACTION
        await self._save_state()
        await self._on_enter_free_action(player_id)

    # --- 跳过地产 ---

    async def skip_property(self, player_id: int, tile_position: int) -> None:
        """跳过地产（公开接口，带锁）"""
        async with self._lock:
            await self.load_state()
            await self._do_skip_property(player_id, tile_position)

    async def _do_skip_property(self, player_id: int, tile_position: int) -> None:
        """跳过地产（内部实现，无锁）"""
        if not self.state:
            return

        player = self.state.get_current_player()
        if player.user_id != player_id:
            return

        self._cancel_timer("decision")

        # 回放记录：跳过地产
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_skip(self.state.turn_number, idx, tile_position)

        await ws_manager.broadcast(self.room_id, "game.property_skipped", {
            "player_id": player_id,
            "tile_id": tile_position,
        })

        # 进入自由行动
        self.state.phase = GamePhase.FREE_ACTION
        await self._save_state()
        await self._on_enter_free_action(player_id)

    # --- 放弃购买 ---

    async def decline_property(self, player_id: int, tile_position: int) -> None:
        """放弃购买（公开接口，带锁）"""
        async with self._lock:
            await self.load_state()
            await self._do_decline_property(player_id, tile_position)

    async def _do_decline_property(self, player_id: int, tile_position: int) -> None:
        """放弃购买（内部实现，无锁）"""
        if not self.state:
            return

        player = self.state.get_current_player()
        if player.user_id != player_id:
            return

        self._cancel_timer("decision")

        # 回放记录：放弃购买
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_decline(self.state.turn_number, idx)

        await ws_manager.broadcast(self.room_id, "game.property_declined", {
            "player_id": player_id,
            "tile_id": tile_position,
        })

        # 进入自由行动
        self.state.phase = GamePhase.FREE_ACTION
        await self._save_state()
        await self._on_enter_free_action(player_id)

    async def auction_bid(self, player_id: int, amount: int) -> None:
        """拍卖出价"""
        async with self._lock:
            await self.load_state()
            if not self.state or not self.state.auction:
                return

            auction = self.state.auction
            if player_id not in auction.bidders:
                return
            if amount <= auction.current_bid:
                return

            player = self.state.get_player_by_id(player_id)
            if not player or player.cash < amount:
                return

            auction.current_bid = amount
            auction.current_bidder_id = player_id

            # 回放记录：拍卖出价
            if self._replay:
                idx = _player_idx(self.state, player_id)
                self._replay.record_auction_bid(self.state.turn_number, idx, amount)

            # 重置倒计时
            self._cancel_timer("auction")
            self._start_timer("auction", 15, self._on_auction_timeout)

            await ws_manager.broadcast(self.room_id, "game.auction_update", {
                "tile_id": auction.tile_position,
                "current_bid": amount,
                "bidder_id": player_id,
            })

            await self._save_state()

    # --- 建造房屋 ---

    async def build_house(self, player_id: int, tile_position: int) -> None:
        """建造房屋（公开接口，带锁）"""
        async with self._lock:
            await self.load_state()
            await self._do_build_house(player_id, tile_position)

    async def _do_build_house(self, player_id: int, tile_position: int) -> None:
        """建造房屋（内部实现，无锁，AI 可直接调用）"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        tile = self.state.get_tile(tile_position)

        if not player or tile.owner_id != player_id:
            return
        if tile.build_level >= self.state.max_build_level:
            return
        if not self.state.owns_full_group(player_id, tile.tile_group or ""):
            return
        if player.cash < (tile.build_cost or 0):
            return

        # 均匀建造检查：同组内不能有超过1级差距
        group_tiles = self.state.get_group_tiles(tile.tile_group or "")
        for gt in group_tiles:
            if gt.position != tile_position and gt.build_level < tile.build_level:
                return  # 必须先升级等级低的

        player.cash -= tile.build_cost
        tile.build_level += 1

        # 回放记录：建造房屋
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_build(self.state.turn_number, idx, tile_position)
            self._replay.record_money(self.state.turn_number, idx, -(tile.build_cost or 0))

        await ws_manager.broadcast(self.room_id, "game.building_built", {
            "player_id": player_id,
            "tile_id": tile_position,
            "tile_name": tile.name,
            "level": tile.build_level,
            "cost": tile.build_cost,
            "cash": player.cash,
        })

        await self._save_state()

    # --- 拆除房屋 ---

    async def demolish_house(self, player_id: int, tile_position: int) -> None:
        """拆除房屋（公开接口，带锁）"""
        async with self._lock:
            await self.load_state()
            await self._do_demolish_house(player_id, tile_position)

    async def _do_demolish_house(self, player_id: int, tile_position: int) -> None:
        """拆除房屋（内部实现，无锁）"""
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        tile = self.state.get_tile(tile_position)

        if not player or tile.owner_id != player_id:
            return
        if tile.build_level <= 0:
            return

        # 均匀拆除检查：同组内不能有超过1级差距
        group_tiles = self.state.get_group_tiles(tile.tile_group or "")
        for gt in group_tiles:
            if gt.position != tile_position and gt.build_level > tile.build_level:
                return  # 必须先拆除等级高的

        refund = (tile.build_cost or 0) // 2
        player.cash += refund
        tile.build_level -= 1

        # 回放记录：拆除房屋
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_demolish(self.state.turn_number, idx, tile_position)
            self._replay.record_money(self.state.turn_number, idx, refund)

        await ws_manager.broadcast(self.room_id, "game.building_demolished", {
            "player_id": player_id,
            "tile_id": tile_position,
            "level": tile.build_level,
            "refund": refund,
            "cash": player.cash,
        })

        await self._save_state()

    # --- 抵押地产 ---

    async def mortgage_property(self, player_id: int, tile_position: int) -> None:
        """抵押地产"""
        async with self._lock:
            await self.load_state()
            if not self.state:
                return

            player = self.state.get_player_by_id(player_id)
            tile = self.state.get_tile(tile_position)

            if not player or tile.owner_id != player_id or tile.is_mortgaged:
                return
            if tile.build_level > 0:
                return  # 有建筑不能抵押，需先拆除

            mortgage_value = (tile.price or 0) // 2
            player.cash += mortgage_value
            tile.is_mortgaged = True

            # 回放记录：抵押
            if self._replay:
                idx = _player_idx(self.state, player_id)
                self._replay.record_mortgage(self.state.turn_number, idx, tile_position)
                self._replay.record_money(self.state.turn_number, idx, mortgage_value)

            await ws_manager.broadcast(self.room_id, "game.property_mortgaged", {
                "player_id": player_id,
                "tile_id": tile_position,
                "mortgage_value": mortgage_value,
                "cash": player.cash,
            })

            await self._save_state()

    # --- 赎回地产 ---

    async def redeem_property(self, player_id: int, tile_position: int) -> None:
        """赎回地产"""
        async with self._lock:
            await self.load_state()
            if not self.state:
                return

            player = self.state.get_player_by_id(player_id)
            tile = self.state.get_tile(tile_position)

            if not player or tile.owner_id != player_id or not tile.is_mortgaged:
                return

            redeem_cost = int((tile.price or 0) // 2 * 1.1)  # 抵押额 + 10%
            if player.cash < redeem_cost:
                return

            player.cash -= redeem_cost
            tile.is_mortgaged = False

            # 回放记录：赎回
            if self._replay:
                idx = _player_idx(self.state, player_id)
                self._replay.record_redeem(self.state.turn_number, idx, tile_position)
                self._replay.record_money(self.state.turn_number, idx, -redeem_cost)

            await ws_manager.broadcast(self.room_id, "game.property_redeemed", {
                "player_id": player_id,
                "tile_id": tile_position,
                "redeem_cost": redeem_cost,
                "cash": player.cash,
            })

            await self._save_state()

    async def end_turn(self, player_id: int) -> None:
        """结束回合（公开接口，带锁）"""
        async with self._lock:
            await self.load_state()
            if not self.state:
                return

            player = self.state.get_current_player()
            if player.user_id != player_id:
                return

            self._cancel_timer("free_action")
            await self._end_turn()

    async def jail_pay_bail(self, player_id: int) -> None:
        """支付保释金"""
        async with self._lock:
            await self.load_state()
            await self._pay_jail_bail(player_id)
            # _pay_jail_bail 内部已设置 phase=WAIT_ROLL，真人玩家需手动掷骰

    async def jail_use_card(self, player_id: int) -> None:
        """使用免罪卡"""
        async with self._lock:
            await self.load_state()
            await self._use_jail_card(player_id)
            # _use_jail_card 内部已设置 phase=WAIT_ROLL，真人玩家需手动掷骰

    # ═══════════════════════════════════════════════════════
    # 自由行动 & 回合结束
    # ═══════════════════════════════════════════════════════

    async def _on_enter_free_action(self, player_id: int) -> None:
        """进入自由行动阶段"""
        if not self.state:
            return

        player = self.state.get_current_player()
        self.state.phase = GamePhase.FREE_ACTION
        await self._save_state()

        if player.is_ai:
            if self._ai_task_running:
                await self._ai_free_action(player)
            else:
                self._start_ai_task(self._ai_free_action(player))
        else:
            self._start_timer("free_action", self.state.turn_timeout, self._on_free_action_timeout)

    async def _ai_free_action(self, player: PlayerState) -> None:
        """AI 自由行动"""
        await self.load_state()

        if not self.state or self.state.get_current_player().user_id != player.user_id:
            return

        # 简单 AI 策略：尝试升级有垄断的地产
        if player.ai_difficulty in ("medium", "hard"):
            for pos in player.properties:
                tile = self.state.tiles[pos]
                if (
                    tile.tile_type == "PROPERTY"
                    and tile.build_level < self.state.max_build_level
                    and not tile.is_mortgaged
                    and self.state.owns_full_group(player.user_id, tile.tile_group or "")
                    and player.cash >= (tile.build_cost or 0) * 2  # 保留应急资金
                ):
                    await self._do_build_house(player.user_id, pos)

        # 结束回合
        await self._end_turn()

    async def _ai_buy_decision(self, player: PlayerState, tile: TileState) -> None:
        """AI 购买决策"""
        await self.load_state()

        if not self.state or self.state.get_current_player().user_id != player.user_id:
            return

        should_buy = False

        if player.ai_difficulty == "easy":
            should_buy = random.random() > 0.5
        elif player.ai_difficulty == "medium":
            # 保留应急资金
            should_buy = player.cash >= (tile.price or 0) + 200
        else:
            # 困难 AI：更激进的购买策略
            should_buy = player.cash >= (tile.price or 0) + 100

        if should_buy and player.cash >= (tile.price or 0):
            await self._do_buy_property(player.user_id, tile.position)
        else:
            await self._do_decline_property(player.user_id, tile.position)

    async def _end_turn(self) -> None:
        """回合结束处理"""
        if not self.state:
            return

        logger = logging.getLogger(__name__)
        logger.info(f"_end_turn: room_id={self.room_id} turn={self.state.turn_number} player_idx={self.state.current_player_index}")

        self._cancel_all_timers()

        # 回放记录：结束回合
        if self._replay:
            current = self.state.get_current_player()
            idx = _player_idx(self.state, current.user_id)
            self._replay.record_end_turn(self.state.turn_number, idx)

        # 检查游戏结束
        active = self.state.get_active_players()
        if len(active) <= 1:
            self.state.phase = GamePhase.TURN_END
            await self._game_over(EndReason.LAST_STANDING)
            return

        if self.state.turn_number >= self.state.max_turns:
            self.state.phase = GamePhase.TURN_END
            await self._game_over(EndReason.TURN_LIMIT)
            return

        # 双数可再掷一次（必须本回合掷出了双数，且连续双数次数 < 3）
        if self.state.dice.is_double and self.state.consecutive_doubles > 0 and self.state.consecutive_doubles < 3 and not self.state.get_current_player().is_in_jail:
            # 重置 dice 状态，避免下次 end_turn 重复触发 extra_roll
            self.state.dice = DiceState(values=[0, 0], total=0, is_double=False)
            self.state.phase = GamePhase.WAIT_ROLL
            await self._save_state()
            # 回放记录：双数再掷
            if self._replay:
                idx = _player_idx(self.state, self.state.get_current_player().user_id)
                self._replay.record_extra_roll(self.state.turn_number, idx)
            await ws_manager.broadcast(self.room_id, "game.extra_roll", {
                "player_id": self.state.get_current_player().user_id,
                "reason": "double",
            })
            player = self.state.get_current_player()
            if player.is_ai:
                # 如果已在 AI 任务中，直接 await；否则启动新任务
                if self._ai_task_running:
                    await self._ai_turn_loop(player)
                else:
                    self._start_ai_task(self._ai_turn_loop(player))
            else:
                self._start_timer("roll", self.state.turn_timeout, self._on_roll_timeout)
            return

        # 切换到下一个玩家（先改 phase 再 save，避免 Redis 中存留 TURN_END）
        self.state.current_player_index = self.state.get_next_player_index()
        self.state.phase = GamePhase.WAIT_ROLL
        await self._save_state()
        await self._start_turn()

    # ═══════════════════════════════════════════════════════
    # 破产处理
    # ═══════════════════════════════════════════════════════

    async def _handle_bankruptcy(self, player_id: int, creditor_id: int, debt: int) -> None:
        """
        处理破产

        Args:
            player_id: 破产玩家 ID
            creditor_id: 债权人 ID（0=银行）
            debt: 欠款金额
        """
        if not self.state:
            return

        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        # V1.0 简化处理：直接破产
        player.is_bankrupt = True

        if creditor_id == 0:
            # 欠银行：地产变为无主
            for pos in player.properties:
                tile = self.state.tiles[pos]
                tile.owner_id = None
                tile.build_level = 0
                tile.is_mortgaged = False
        else:
            # 欠其他玩家：资产转移
            creditor = self.state.get_player_by_id(creditor_id)
            if creditor:
                creditor.cash += player.cash
                for pos in player.properties:
                    tile = self.state.tiles[pos]
                    tile.owner_id = creditor_id
                    creditor.properties.append(pos)
                player.cash = 0

        player.properties.clear()

        # 回放记录：破产
        if self._replay:
            idx = _player_idx(self.state, player_id)
            self._replay.record_money(self.state.turn_number, idx, -debt)

        await ws_manager.broadcast(self.room_id, "game.player_bankrupt", {
            "player_id": player_id,
            "creditor_id": creditor_id,
            "debt": debt,
        })

        await self._save_state()

    # ═══════════════════════════════════════════════════════
    # 游戏结束
    # ═══════════════════════════════════════════════════════

    async def _game_over(self, reason: EndReason) -> None:
        """游戏结束"""
        if not self.state:
            return

        # 防重入保护：避免 _game_over 被多次调用导致重复写库
        if getattr(self, '_game_over_called', False):
            return
        self._game_over_called = True

        self.state.phase = GamePhase.GAME_OVER
        self._cancel_all_timers()

        # 计算排名
        active = self.state.get_active_players()
        rankings = sorted(active, key=lambda p: self.state.calculate_total_assets(p), reverse=True)

        # 加入破产玩家
        bankrupt = [p for p in self.state.players if p.is_bankrupt]
        rankings.extend(bankrupt)

        ranking_data = []
        for i, p in enumerate(rankings):
            ranking_data.append({
                "rank": i + 1,
                "user_id": p.user_id,
                "nickname": p.nickname,
                "total_assets": self.state.calculate_total_assets(p) if not p.is_bankrupt else 0,
                "is_ai": p.is_ai,
                "is_bankrupt": p.is_bankrupt,
            })

        winner_id = rankings[0].user_id if rankings else None

        # 保存对局记录到数据库（先保存以获取 record_id）
        game_record_id = await self._save_game_record(reason, ranking_data, winner_id)

        await ws_manager.broadcast(self.room_id, "game.over", {
            "end_reason": reason.value,
            "winner_id": winner_id,
            "rankings": ranking_data,
            "total_turns": self.state.turn_number,
            "game_record_id": game_record_id,
        })

        await self._save_state()

        # 更新房间状态为 finished
        try:
            from app.services.room import RoomService
            await RoomService.update_room_status(self.room_id, "finished")
        except Exception as e:
            logging.getLogger(__name__).error(f"[GameRecord] Failed to update room status: {e}")

    async def _save_game_record(self, reason: EndReason, ranking_data: list[dict], winner_id: int | None) -> int | None:
        """游戏结束后将对局记录写入数据库，返回记录 ID"""
        if not self.state:
            return None
        try:
            import json as _json

            from app.core.database import async_session
            from app.models.game_record import GamePlayer, GameRecord

            # 生成回放数据
            replay_init = None
            replay_actions = None
            replay_final = None
            if self._replay:
                replay_data = self._replay.finalize(self.state, ranking_data)
                replay_init = _json.dumps(replay_data.init_state, ensure_ascii=False)
                replay_actions = replay_data.actions_encoded
                replay_final = _json.dumps(replay_data.final_state, ensure_ascii=False)

            async with async_session() as db:
                try:
                    # 创建对局记录
                    record = GameRecord(
                        room_id=self.room_id,
                        map_id=self.state.map_id,
                        total_turns=self.state.turn_number,
                        player_count=len(self.state.players),
                        winner_id=winner_id,
                        end_reason=reason.value,
                        config_snapshot=replay_init,
                        actions=replay_actions,
                        final_snapshot=replay_final,
                    )
                    db.add(record)
                    await db.flush()

                    # 创建玩家记录
                    for entry in ranking_data:
                        # 结算金额 = 最终总资产 - 初始资金
                        settlement = entry["total_assets"] - self.state.initial_cash
                        gp = GamePlayer(
                            game_id=record.id,
                            user_id=entry["user_id"],
                            nickname=entry["nickname"],
                            rank=entry["rank"],
                            total_assets=entry["total_assets"],
                            settlement_amount=settlement,
                            is_bankrupt=entry["is_bankrupt"],
                            is_ai=entry["is_ai"],
                            ai_difficulty=None,  # 从 PlayerState 获取
                        )
                        # 找到对应玩家的 AI 难度
                        for p in self.state.players:
                            if p.user_id == entry["user_id"]:
                                gp.ai_difficulty = p.ai_difficulty
                                break
                        db.add(gp)

                    await db.commit()
                    logging.getLogger(__name__).info(f"[GameRecord] Saved game record {record.id} for room {self.room_id}")
                    return record.id
                except Exception:
                    await db.rollback()
                    raise
        except Exception as e:
            # 对局记录保存失败不应影响游戏结束流程
            logging.getLogger(__name__).error(f"[GameRecord] Failed to save game record for room {self.room_id}: {e}")
            return None

    # ═══════════════════════════════════════════════════════
    # 超时处理
    # ═══════════════════════════════════════════════════════

    def _start_timer(self, name: str, seconds: int, callback) -> None:
        """启动超时计时器"""
        self._cancel_timer(name)
        self._timers[name] = asyncio.create_task(self._timer_task(name, seconds, callback))

    def _cancel_timer(self, name: str) -> None:
        """取消计时器"""
        task = self._timers.pop(name, None)
        if task and not task.done():
            task.cancel()

    def _cancel_all_timers(self) -> None:
        """取消所有计时器"""
        for name in list(self._timers.keys()):
            self._cancel_timer(name)

    async def _timer_task(self, name: str, seconds: int, callback) -> None:
        """计时器任务"""
        try:
            await asyncio.sleep(seconds)
            await callback()
        except asyncio.CancelledError:
            pass

    async def _on_roll_timeout(self) -> None:
        """掷骰超时"""
        if not self.state:
            return
        player = self.state.get_current_player()
        if player.is_ai:
            return
        player.consecutive_timeouts += 1
        if player.consecutive_timeouts >= 3:
            # 标记断线
            player.is_connected = False
            await ws_manager.broadcast(self.room_id, "system.player_disconnected", {
                "player_id": player.user_id,
            })
            # AI 暂代
            self._start_ai_task(self._ai_turn_loop(player))
        else:
            await self._execute_roll(player.user_id)

    async def _on_decision_timeout(self) -> None:
        """购买决策超时 → 默认放弃"""
        if not self.state:
            return
        player = self.state.get_current_player()
        tile = self.state.get_tile(player.position)
        await self.decline_property(player.user_id, tile.position)

    async def _on_free_action_timeout(self) -> None:
        """自由行动超时 → 自动结束回合"""
        if not self.state:
            return
        player = self.state.get_current_player()
        await self._end_turn()

    async def _on_auction_timeout(self) -> None:
        """拍卖超时 → 结束拍卖"""
        if not self.state or not self.state.auction:
            return

        auction = self.state.auction
        tile = self.state.get_tile(auction.tile_position)

        if auction.current_bidder_id:
            # 有人出价
            winner = self.state.get_player_by_id(auction.current_bidder_id)
            if winner and winner.cash >= auction.current_bid:
                winner.cash -= auction.current_bid
                tile.owner_id = auction.current_bidder_id
                winner.properties.append(auction.tile_position)

                await ws_manager.broadcast(self.room_id, "game.auction_end", {
                    "tile_id": auction.tile_position,
                    "winner_id": auction.current_bidder_id,
                    "final_price": auction.current_bid,
                })
        else:
            # 无人出价
            await ws_manager.broadcast(self.room_id, "game.auction_end", {
                "tile_id": auction.tile_position,
                "winner_id": None,
                "final_price": 0,
            })

        self.state.auction = None
        self.state.phase = GamePhase.FREE_ACTION
        await self._save_state()

        current = self.state.get_current_player()
        await self._on_enter_free_action(current.user_id)

    # ═══════════════════════════════════════════════════════
    # 快照
    # ═══════════════════════════════════════════════════════

    def get_snapshot(self) -> dict:
        """获取游戏状态快照"""
        if not self.state:
            return {}
        return self.state.model_dump()

    # ═══════════════════════════════════════════════════════
    # 清理
    # ═══════════════════════════════════════════════════════

    async def cleanup(self) -> None:
        """清理游戏资源"""
        self._cancel_all_timers()
        redis = await get_redis()
        await redis.delete(f"game:{self.room_id}")


# ─── 引擎实例管理 ───

_engines: dict[str, GameEngine] = {}


def get_engine(room_id: str) -> GameEngine:
    """获取或创建游戏引擎实例"""
    if room_id not in _engines:
        _engines[room_id] = GameEngine(room_id)
    return _engines[room_id]


def remove_engine(room_id: str) -> None:
    """移除引擎实例"""
    engine = _engines.pop(room_id, None)
    if engine:
        engine._cancel_all_timers()
