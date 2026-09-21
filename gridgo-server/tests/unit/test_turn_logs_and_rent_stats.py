"""回合日志 / 租金流水单测（docs/PROJECT.md 6.2、GAME_FLOW.md 8.2）

覆盖：_log_turn 产出的缓冲条目字段与 game_turn_logs 列对齐、_add_rent_stat 聚合。
不依赖 Redis / PostgreSQL。
"""

from app.game.engine import GameEngine
from app.game.schemas import DiceState, GamePhase, GameState, PlayerState
from app.models.stats import GameTurnLog

TURN_LOG_COLUMNS = {
    "game_id",
    "turn_number",
    "player_id",
    "action_type",
    "action_data",
    "dice_values",
}


def _make_engine() -> GameEngine:
    engine = GameEngine("test-room")
    engine.state = GameState(
        game_id="g1",
        room_id="test-room",
        turn_number=7,
        phase=GamePhase.FREE_ACTION,
        players=[
            PlayerState(user_id=1, nickname="A", cash=1000),
            PlayerState(user_id=2, nickname="B", cash=1000),
        ],
        dice=DiceState(values=[3, 5], total=8),
    )
    return engine


def test_log_turn_fields_align_with_model():
    engine = _make_engine()
    engine._log_turn("roll", 1, {"dice": [3, 5], "total": 8})

    assert len(engine._turn_logs) == 1
    entry = engine._turn_logs[0]
    # game_id 在落库阶段由 _save_game_record 补齐
    assert set(entry.keys()) == TURN_LOG_COLUMNS - {"game_id"}
    assert entry["turn_number"] == 7
    assert entry["player_id"] == 1
    assert entry["action_type"] == "roll"
    assert entry["dice_values"] == "3,5"

    # 键与 ORM 列名一致，可直接构造 GameTurnLog
    log = GameTurnLog(game_id=1, **entry)
    assert log.action_data == {"dice": [3, 5], "total": 8}


def test_log_turn_without_state_is_noop():
    engine = GameEngine("test-room")
    engine._log_turn("roll", 1, {})
    assert engine._turn_logs == []


def test_add_rent_stat_accumulates():
    engine = _make_engine()
    engine._add_rent_stat(1, collected=100)
    engine._add_rent_stat(1, collected=50)
    engine._add_rent_stat(1, paid=20)
    engine._add_rent_stat(2, paid=70)

    assert engine._rent_stats[1] == {"collected": 150, "paid": 20}
    assert engine._rent_stats[2]["paid"] == 70
