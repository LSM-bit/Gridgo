"""断线重连档位单测（docs/GAME_FLOW.md 9）

覆盖：≤30s 增量 / 30s~3min 快照 / >3min 判退出 的边界判定，
以及引擎重连相关内部状态的初始化。不依赖 Redis / PostgreSQL。
"""

from app.game.engine import (
    RECONNECT_AI_WINDOW,
    RECONNECT_INCREMENT_WINDOW,
    GameEngine,
    reconnect_mode,
)


def test_windows_are_documented_values():
    assert RECONNECT_INCREMENT_WINDOW == 30
    assert RECONNECT_AI_WINDOW == 180


def test_reconnect_mode_boundaries():
    assert reconnect_mode(None) == "reconnect"
    assert reconnect_mode(0) == "resume_incremental"
    assert reconnect_mode(29.9) == "resume_incremental"
    assert reconnect_mode(30) == "resume_incremental"
    assert reconnect_mode(30.1) == "resume_snapshot"
    assert reconnect_mode(180) == "resume_snapshot"
    assert reconnect_mode(180.1) == "left_game"
    assert reconnect_mode(3600) == "left_game"


def test_engine_reconnect_state_initialized():
    engine = GameEngine("test-room")
    assert engine._ai_substitute == set()
    assert engine._disconnected_at == {}
    assert engine._turn_logs == []
    assert engine._rent_stats == {}
