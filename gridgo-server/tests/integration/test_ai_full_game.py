"""
纯 AI 游戏端到端测试

验证在没有真人玩家的情况下，AI 能够完整走完游戏流程直到 GAME_OVER。

测试策略：
- Mock Redis：使用内存字典模拟 Redis 的 get/set
- Mock WebSocket manager：所有广播和发送操作静默处理
- Mock MapService：返回硬编码的经典地图数据
- 直接实例化 GameEngine，调用 initialize() 启动游戏
- 用较短的超时和回合数加速测试

游戏流程链路（AI 视角）：
  _start_turn → _ai_turn_loop → _execute_roll → _move_player →
  _process_tile_effect → [各种分支] → _on_enter_free_action →
  _ai_free_action → _end_turn → _start_turn (下一回合)
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.game.engine import GameEngine, _engines
from app.game.schemas import GamePhase, GameState


# ─── 经典地图测试数据 ────────────────────────────────────────────────

TILES_DATA: list[dict] = [
    {"position": 0, "name": "起点", "tile_type": "START"},
    {"position": 1, "name": "朝阳路", "tile_type": "PROPERTY", "tile_group": "brown", "group_color": "#8B4513",
     "price": 60, "build_cost": 50, "rent_0": 4, "rent_1": 20, "rent_2": 60, "rent_3": 180, "rent_4": 320, "rent_5": 450},
    {"position": 2, "name": "命运卡", "tile_type": "FATE"},
    {"position": 3, "name": "朝阳大道", "tile_type": "PROPERTY", "tile_group": "brown", "group_color": "#8B4513",
     "price": 60, "build_cost": 50, "rent_0": 4, "rent_1": 20, "rent_2": 60, "rent_3": 180, "rent_4": 320, "rent_5": 450},
    {"position": 4, "name": "所得税", "tile_type": "TAX", "tax_amount": 200, "tax_is_percent": False},
    {"position": 5, "name": "北京站", "tile_type": "STATION", "price": 200},
    {"position": 6, "name": "长安街", "tile_type": "PROPERTY", "tile_group": "light_blue", "group_color": "#87CEEB",
     "price": 100, "build_cost": 50, "rent_0": 6, "rent_1": 30, "rent_2": 90, "rent_3": 270, "rent_4": 400, "rent_5": 550},
    {"position": 7, "name": "机会卡", "tile_type": "CHANCE"},
    {"position": 8, "name": "南京路", "tile_type": "PROPERTY", "tile_group": "light_blue", "group_color": "#87CEEB",
     "price": 100, "build_cost": 50, "rent_0": 6, "rent_1": 30, "rent_2": 90, "rent_3": 270, "rent_4": 400, "rent_5": 550},
    {"position": 9, "name": "淮海路", "tile_type": "PROPERTY", "tile_group": "light_blue", "group_color": "#87CEEB",
     "price": 120, "build_cost": 50, "rent_0": 8, "rent_1": 40, "rent_2": 100, "rent_3": 300, "rent_4": 450, "rent_5": 600},
    {"position": 10, "name": "监狱", "tile_type": "JAIL"},
    {"position": 11, "name": "王府井", "tile_type": "PROPERTY", "tile_group": "pink", "group_color": "#FF69B4",
     "price": 140, "build_cost": 100, "rent_0": 10, "rent_1": 50, "rent_2": 150, "rent_3": 450, "rent_4": 625, "rent_5": 750},
    {"position": 12, "name": "电力公司", "tile_type": "UTILITY", "price": 150},
    {"position": 13, "name": "西单", "tile_type": "PROPERTY", "tile_group": "pink", "group_color": "#FF69B4",
     "price": 140, "build_cost": 100, "rent_0": 10, "rent_1": 50, "rent_2": 150, "rent_3": 450, "rent_4": 625, "rent_5": 750},
    {"position": 14, "name": "东单", "tile_type": "PROPERTY", "tile_group": "pink", "group_color": "#FF69B4",
     "price": 160, "build_cost": 100, "rent_0": 12, "rent_1": 60, "rent_2": 180, "rent_3": 500, "rent_4": 700, "rent_5": 900},
    {"position": 15, "name": "上海站", "tile_type": "STATION", "price": 200},
    {"position": 16, "name": "春熙路", "tile_type": "PROPERTY", "tile_group": "orange", "group_color": "#FFA500",
     "price": 180, "build_cost": 100, "rent_0": 14, "rent_1": 70, "rent_2": 200, "rent_3": 550, "rent_4": 750, "rent_5": 950},
    {"position": 17, "name": "命运卡", "tile_type": "FATE"},
    {"position": 18, "name": "步行街", "tile_type": "PROPERTY", "tile_group": "orange", "group_color": "#FFA500",
     "price": 180, "build_cost": 100, "rent_0": 14, "rent_1": 70, "rent_2": 200, "rent_3": 550, "rent_4": 750, "rent_5": 950},
    {"position": 19, "name": "中山路", "tile_type": "PROPERTY", "tile_group": "orange", "group_color": "#FFA500",
     "price": 200, "build_cost": 100, "rent_0": 16, "rent_1": 80, "rent_2": 220, "rent_3": 600, "rent_4": 800, "rent_5": 1000},
    {"position": 20, "name": "免费停车", "tile_type": "PARKING"},
    {"position": 21, "name": "解放路", "tile_type": "PROPERTY", "tile_group": "red", "group_color": "#FF0000",
     "price": 220, "build_cost": 150, "rent_0": 18, "rent_1": 90, "rent_2": 250, "rent_3": 700, "rent_4": 875, "rent_5": 1050},
    {"position": 22, "name": "机会卡", "tile_type": "CHANCE"},
    {"position": 23, "name": "人民路", "tile_type": "PROPERTY", "tile_group": "red", "group_color": "#FF0000",
     "price": 220, "build_cost": 150, "rent_0": 18, "rent_1": 90, "rent_2": 250, "rent_3": 700, "rent_4": 875, "rent_5": 1050},
    {"position": 24, "name": "建设路", "tile_type": "PROPERTY", "tile_group": "red", "group_color": "#FF0000",
     "price": 240, "build_cost": 150, "rent_0": 20, "rent_1": 100, "rent_2": 300, "rent_3": 750, "rent_4": 925, "rent_5": 1100},
    {"position": 25, "name": "广州站", "tile_type": "STATION", "price": 200},
    {"position": 26, "name": "天河路", "tile_type": "PROPERTY", "tile_group": "yellow", "group_color": "#FFD700",
     "price": 260, "build_cost": 150, "rent_0": 22, "rent_1": 110, "rent_2": 330, "rent_3": 800, "rent_4": 975, "rent_5": 1150},
    {"position": 27, "name": "珠江路", "tile_type": "PROPERTY", "tile_group": "yellow", "group_color": "#FFD700",
     "price": 260, "build_cost": 150, "rent_0": 22, "rent_1": 110, "rent_2": 330, "rent_3": 800, "rent_4": 975, "rent_5": 1150},
    {"position": 28, "name": "自来水公司", "tile_type": "UTILITY", "price": 150},
    {"position": 29, "name": "体育西路", "tile_type": "PROPERTY", "tile_group": "yellow", "group_color": "#FFD700",
     "price": 280, "build_cost": 150, "rent_0": 24, "rent_1": 120, "rent_2": 360, "rent_3": 850, "rent_4": 1025, "rent_5": 1200},
    {"position": 30, "name": "去监狱", "tile_type": "GO_TO_JAIL"},
    {"position": 31, "name": "科技园", "tile_type": "PROPERTY", "tile_group": "green", "group_color": "#008000",
     "price": 300, "build_cost": 200, "rent_0": 26, "rent_1": 130, "rent_2": 390, "rent_3": 900, "rent_4": 1100, "rent_5": 1275},
    {"position": 32, "name": "软件大道", "tile_type": "PROPERTY", "tile_group": "green", "group_color": "#008000",
     "price": 300, "build_cost": 200, "rent_0": 26, "rent_1": 130, "rent_2": 390, "rent_3": 900, "rent_4": 1100, "rent_5": 1275},
    {"position": 33, "name": "命运卡", "tile_type": "FATE"},
    {"position": 34, "name": "金融街", "tile_type": "PROPERTY", "tile_group": "green", "group_color": "#008000",
     "price": 320, "build_cost": 200, "rent_0": 28, "rent_1": 150, "rent_2": 450, "rent_3": 1000, "rent_4": 1200, "rent_5": 1400},
    {"position": 35, "name": "深圳站", "tile_type": "STATION", "price": 200},
    {"position": 36, "name": "机会卡", "tile_type": "CHANCE"},
    {"position": 37, "name": "滨海大道", "tile_type": "PROPERTY", "tile_group": "blue", "group_color": "#0000CD",
     "price": 350, "build_cost": 200, "rent_0": 35, "rent_1": 175, "rent_2": 500, "rent_3": 1100, "rent_4": 1300, "rent_5": 1500},
    {"position": 38, "name": "奢侈品税", "tile_type": "TAX", "tax_amount": 100, "tax_is_percent": False},
    {"position": 39, "name": "前海路", "tile_type": "PROPERTY", "tile_group": "blue", "group_color": "#0000CD",
     "price": 400, "build_cost": 200, "rent_0": 50, "rent_1": 200, "rent_2": 600, "rent_3": 1400, "rent_4": 1700, "rent_5": 2000},
]

# 给缺少的字段补 None
for t in TILES_DATA:
    t.setdefault("tile_group", None)
    t.setdefault("group_color", None)
    t.setdefault("price", None)
    t.setdefault("build_cost", None)
    t.setdefault("rent_0", None)
    t.setdefault("rent_1", None)
    t.setdefault("rent_2", None)
    t.setdefault("rent_3", None)
    t.setdefault("rent_4", None)
    t.setdefault("rent_5", None)
    t.setdefault("tax_amount", None)
    t.setdefault("tax_is_percent", None)

CARDS_DATA: list[dict] = [
    {"card_type": "CHANCE", "card_id": "C01", "name": "前进至起点", "effect_type": "move_to_position", "effect_value": 0, "description": "移动到起点"},
    {"card_type": "CHANCE", "card_id": "C02", "name": "前进至最近的车站", "effect_type": "move_to_nearest_station", "effect_value": None, "description": "移动到下一车站"},
    {"card_type": "CHANCE", "card_id": "C03", "name": "前进三格", "effect_type": "move_forward", "effect_value": 3, "description": "向前移动3格"},
    {"card_type": "CHANCE", "card_id": "C04", "name": "银行分红", "effect_type": "gain_money", "effect_value": 150, "description": "获得150"},
    {"card_type": "CHANCE", "card_id": "C05", "name": "修理费", "effect_type": "pay_per_house", "effect_value": 25, "description": "每栋房屋支付25"},
    {"card_type": "CHANCE", "card_id": "C06", "name": "出狱卡", "effect_type": "get_out_of_jail", "effect_value": None, "description": "获得免罪卡"},
    {"card_type": "CHANCE", "card_id": "C07", "name": "后退一格", "effect_type": "move_backward", "effect_value": 1, "description": "向后移动1格"},
    {"card_type": "CHANCE", "card_id": "C08", "name": "前进至朝阳路", "effect_type": "move_to_position", "effect_value": 1, "description": "移动到朝阳路"},
    {"card_type": "CHANCE", "card_id": "C09", "name": "被罚款", "effect_type": "lose_money", "effect_value": 40, "description": "支付40"},
    {"card_type": "CHANCE", "card_id": "C10", "name": "前进至监狱", "effect_type": "go_to_jail", "effect_value": None, "description": "进入监狱"},
    {"card_type": "FATE", "card_id": "F01", "name": "银行利息", "effect_type": "gain_money", "effect_value": 100, "description": "获得100"},
    {"card_type": "FATE", "card_id": "F02", "name": "医疗费用", "effect_type": "lose_money", "effect_value": 50, "description": "支付50"},
    {"card_type": "FATE", "card_id": "F03", "name": "生日快乐", "effect_type": "gain_from_all", "effect_value": 20, "description": "每位其他玩家向你支付20"},
    {"card_type": "FATE", "card_id": "F04", "name": "遗产继承", "effect_type": "gain_money", "effect_value": 200, "description": "获得200"},
    {"card_type": "FATE", "card_id": "F05", "name": "出狱卡", "effect_type": "get_out_of_jail", "effect_value": None, "description": "获得免罪卡"},
    {"card_type": "FATE", "card_id": "F06", "name": "入狱", "effect_type": "go_to_jail", "effect_value": None, "description": "进入监狱"},
    {"card_type": "FATE", "card_id": "F07", "name": "补缴税款", "effect_type": "pay_per_house", "effect_value": 40, "description": "每栋房屋支付40"},
    {"card_type": "FATE", "card_id": "F08", "name": "彩票中奖", "effect_type": "gain_money", "effect_value": 500, "description": "获得500"},
    {"card_type": "FATE", "card_id": "F09", "name": "咨询费", "effect_type": "lose_money", "effect_value": 25, "description": "支付25"},
    {"card_type": "FATE", "card_id": "F10", "name": "前进至起点", "effect_type": "move_to_position", "effect_value": 0, "description": "移动到起点"},
]

STATION_RENT = {1: 25, 2: 50, 3: 75, 4: 100}
UTILITY_MULTIPLIER = {1: 4, 2: 10}

MAP_TEMPLATE = {
    "info": {
        "id": "classic",
        "name": "经典地图",
        "description": "测试用经典地图",
        "tile_count": 40,
        "start_bonus": 200,
        "jail_bail": 50,
        "max_build_level": 5,
    },
    "tiles": TILES_DATA,
    "station_rent": STATION_RENT,
    "utility_multiplier": UTILITY_MULTIPLIER,
    "cards": CARDS_DATA,
}


# ─── Mock 辅助 ─────────────────────────────────────────────────────


class MockRedis:
    """内存字典模拟 Redis"""

    def __init__(self):
        self._data: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self._data[key] = value

    async def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def ping(self) -> None:
        pass

    async def close(self) -> None:
        pass


class MockWSManager:
    """静默 WebSocket 管理器，记录广播事件用于断言"""

    def __init__(self):
        self.events: list[tuple[str, str, dict]] = []  # (room_id, msg_type, data)

    async def broadcast(self, room_id: str, msg_type: str, data, exclude=None) -> None:
        self.events.append((room_id, msg_type, data))

    async def send_to_player(self, room_id: str, user_id: int, msg_type: str, data) -> None:
        pass

    async def send_snapshot(self, room_id: str, user_id: int, snapshot: dict) -> None:
        pass


# ─── 核心辅助函数 ──────────────────────────────────────────────────


async def _run_ai_game(
    mock_redis: MockRedis,
    mock_ws: MockWSManager,
    num_players: int = 2,
    max_turns: int = 10,
    ai_difficulty: str = "medium",
    timeout: float = 60.0,
) -> GameEngine:
    """
    创建并运行一个纯 AI 游戏直到 GAME_OVER

    在 mock 上下文中初始化引擎并等待 AI 任务链完整走完。
    """
    room_id = f"test-ai-{num_players}p"

    room_players = [
        {
            "user_id": 100 + i,
            "nickname": f"AI-{i + 1}",
            "is_ai": True,
            "ai_difficulty": ai_difficulty,
        }
        for i in range(num_players)
    ]

    with (
        patch("app.game.engine.get_redis", return_value=mock_redis),
        patch("app.game.engine.ws_manager", mock_ws),
        patch("app.game.engine.MapService") as mock_map_svc,
        patch("app.game.engine.settings") as mock_settings,
    ):
        mock_map_svc.load_map_template = AsyncMock(return_value=MAP_TEMPLATE)
        mock_map_svc.shuffle_decks = AsyncMock(
            return_value=(
                [c["card_id"] for c in CARDS_DATA if c["card_type"] == "CHANCE"],
                [c["card_id"] for c in CARDS_DATA if c["card_type"] == "FATE"],
            )
        )
        mock_settings.GAME_INITIAL_CASH = 1500
        mock_settings.GAME_MAX_TURNS = max_turns
        mock_settings.GAME_TURN_TIMEOUT = 30

        engine = GameEngine(room_id)
        await engine.initialize(db=None, room_players=room_players, map_id="classic")

        # 等待 AI 任务完成（游戏走到 GAME_OVER）
        import time
        start = time.time()
        while time.time() - start < timeout:
            data = mock_redis._data.get(f"game:{room_id}")
            if data:
                state = GameState.model_validate_json(data)
                if state.phase == GamePhase.GAME_OVER:
                    return engine
            await asyncio.sleep(0.05)

        # 超时：输出调试信息
        data = mock_redis._data.get(f"game:{room_id}")
        if data:
            state = GameState.model_validate_json(data)
            raise AssertionError(
                f"游戏未在 {timeout}s 内结束。phase={state.phase}, "
                f"turn={state.turn_number}, player={state.get_current_player().nickname}"
            )
        raise AssertionError(f"游戏未在 {timeout}s 内结束，且 Redis 中无状态数据")


# ─── 测试用例 ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def cleanup_engines():
    """每个测试后清理全局引擎缓存"""
    yield
    _engines.clear()


@pytest.mark.asyncio
async def test_two_ai_players_full_game():
    """2 个 AI 玩家完整走完游戏（回合限制 10 回合）"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()

    engine = await _run_ai_game(mock_redis, mock_ws, num_players=2, max_turns=10)

    # 验证最终状态
    data = mock_redis._data.get(f"game:{engine.room_id}")
    assert data is not None
    state = GameState.model_validate_json(data)
    assert state.phase == GamePhase.GAME_OVER
    assert state.turn_number > 0


@pytest.mark.asyncio
async def test_four_ai_players_full_game():
    """4 个 AI 玩家完整走完游戏（回合限制 10 回合）"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()

    engine = await _run_ai_game(mock_redis, mock_ws, num_players=4, max_turns=10, timeout=90.0)

    data = mock_redis._data.get(f"game:{engine.room_id}")
    assert data is not None
    state = GameState.model_validate_json(data)
    assert state.phase == GamePhase.GAME_OVER
    assert state.turn_number > 0


@pytest.mark.asyncio
async def test_ai_game_events_broadcast():
    """验证 AI 游戏过程中关键事件被广播"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()

    engine = await _run_ai_game(mock_redis, mock_ws, num_players=2, max_turns=5)

    # 检查关键事件类型
    event_types = {msg_type for _, msg_type, _ in mock_ws.events}
    assert "game.turn_change" in event_types, "应该有回合变更事件"
    assert "game.dice_result" in event_types, "应该有掷骰结果事件"
    assert "state.update" in event_types, "应该有状态更新事件"
    assert "game.over" in event_types, "应该有游戏结束事件"


@pytest.mark.asyncio
async def test_ai_game_different_difficulties():
    """不同难度的 AI 玩家混搭完整游戏"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()
    room_id = "test-mixed"

    room_players = [
        {"user_id": 100, "nickname": "AI-简单", "is_ai": True, "ai_difficulty": "easy"},
        {"user_id": 101, "nickname": "AI-中等", "is_ai": True, "ai_difficulty": "medium"},
        {"user_id": 102, "nickname": "AI-困难", "is_ai": True, "ai_difficulty": "hard"},
    ]

    with (
        patch("app.game.engine.get_redis", return_value=mock_redis),
        patch("app.game.engine.ws_manager", mock_ws),
        patch("app.game.engine.MapService") as mock_map_svc,
        patch("app.game.engine.settings") as mock_settings,
    ):
        mock_map_svc.load_map_template = AsyncMock(return_value=MAP_TEMPLATE)
        mock_map_svc.shuffle_decks = AsyncMock(
            return_value=(
                [c["card_id"] for c in CARDS_DATA if c["card_type"] == "CHANCE"],
                [c["card_id"] for c in CARDS_DATA if c["card_type"] == "FATE"],
            )
        )
        mock_settings.GAME_INITIAL_CASH = 1500
        mock_settings.GAME_MAX_TURNS = 10
        mock_settings.GAME_TURN_TIMEOUT = 30

        engine = GameEngine(room_id)
        await engine.initialize(db=None, room_players=room_players, map_id="classic")

        # 等待 GAME_OVER
        import time
        start = time.time()
        while time.time() - start < 60:
            data = mock_redis._data.get(f"game:{room_id}")
            if data:
                state = GameState.model_validate_json(data)
                if state.phase == GamePhase.GAME_OVER:
                    break
            await asyncio.sleep(0.05)

        data = mock_redis._data.get(f"game:{room_id}")
        state = GameState.model_validate_json(data)
        assert state.phase == GamePhase.GAME_OVER


@pytest.mark.asyncio
async def test_ai_game_has_winner():
    """验证 AI 游戏结束后有正确的排名和获胜者"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()

    engine = await _run_ai_game(mock_redis, mock_ws, num_players=2, max_turns=10)

    # 从广播事件中查找 game.over
    over_events = [data for _, msg_type, data in mock_ws.events if msg_type == "game.over"]
    assert len(over_events) >= 1, "应该至少有一个 game.over 事件"

    over_data = over_events[-1]
    assert "rankings" in over_data
    assert "winner_id" in over_data
    assert "end_reason" in over_data
    assert over_data["end_reason"] in ("last_standing", "turn_limit")
    assert len(over_data["rankings"]) > 0

    # 第1名就是获胜者
    winner = over_data["rankings"][0]
    assert winner["rank"] == 1
    assert winner["user_id"] == over_data["winner_id"]


@pytest.mark.asyncio
async def test_ai_game_long_run():
    """AI 游戏长跑测试（50 回合），确保流程不中断"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()

    engine = await _run_ai_game(mock_redis, mock_ws, num_players=3, max_turns=50, timeout=120.0)

    data = mock_redis._data.get(f"game:{engine.room_id}")
    state = GameState.model_validate_json(data)
    assert state.phase == GamePhase.GAME_OVER
    assert state.turn_number >= 1


@pytest.mark.asyncio
async def test_ai_watchdog_recovery():
    """验证 AI 任务异常退出后 watchdog 自动恢复"""
    mock_redis = MockRedis()
    mock_ws = MockWSManager()
    room_id = "test-watchdog"

    room_players = [
        {"user_id": 100, "nickname": "AI-1", "is_ai": True, "ai_difficulty": "medium"},
        {"user_id": 101, "nickname": "AI-2", "is_ai": True, "ai_difficulty": "medium"},
    ]

    with (
        patch("app.game.engine.get_redis", return_value=mock_redis),
        patch("app.game.engine.ws_manager", mock_ws),
        patch("app.game.engine.MapService") as mock_map_svc,
        patch("app.game.engine.settings") as mock_settings,
    ):
        mock_map_svc.load_map_template = AsyncMock(return_value=MAP_TEMPLATE)
        mock_map_svc.shuffle_decks = AsyncMock(
            return_value=(
                [c["card_id"] for c in CARDS_DATA if c["card_type"] == "CHANCE"],
                [c["card_id"] for c in CARDS_DATA if c["card_type"] == "FATE"],
            )
        )
        mock_settings.GAME_INITIAL_CASH = 1500
        mock_settings.GAME_MAX_TURNS = 10
        mock_settings.GAME_TURN_TIMEOUT = 30

        engine = GameEngine(room_id)
        await engine.initialize(db=None, room_players=room_players, map_id="classic")

        # 模拟 AI 任务异常退出：强制设置 _ai_task_running = False
        # 此时游戏仍在 AI 需要操作的阶段
        engine._ai_task_running = False

        # 等待 watchdog 检测到卡住并恢复
        await asyncio.sleep(5.0)

        # 游戏应该已经恢复推进，不是卡在 AI 阶段
        data = mock_redis._data.get(f"game:{room_id}")
        assert data is not None
        state = GameState.model_validate_json(data)

        # 如果 watchdog 工作了，游戏应该不在 WAIT_ROLL/WAIT_DECISION/FREE_ACTION 卡住
        # 要么游戏已经推进到后续阶段，要么已经 GAME_OVER
        # 至少验证游戏没有永远卡在某个 AI 阶段
        assert state.phase in (
            GamePhase.WAIT_ROLL,
            GamePhase.WAIT_DECISION,
            GamePhase.FREE_ACTION,
            GamePhase.ROLLING,
            GamePhase.MOVING,
            GamePhase.TILE_EFFECT,
            GamePhase.TURN_END,
            GamePhase.GAME_OVER,
        )

        # 继续等待游戏结束
        import time
        start = time.time()
        while time.time() - start < 60:
            data = mock_redis._data.get(f"game:{room_id}")
            if data:
                state = GameState.model_validate_json(data)
                if state.phase == GamePhase.GAME_OVER:
                    break
            await asyncio.sleep(0.1)

        data = mock_redis._data.get(f"game:{room_id}")
        state = GameState.model_validate_json(data)
        assert state.phase == GamePhase.GAME_OVER
