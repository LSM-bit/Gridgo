"""结算积分常量与交易协议单测（docs/GAME_FLOW.md 4.2、PROJECT.md 7.2）

覆盖：胜 +30 / 败 -10 常量、TradeOffer 字段契约、GameState.pending_trades 默认空。
不依赖 Redis / PostgreSQL。
"""

from app.game.schemas import GamePhase, GameState, TradeOffer
from app.services.stats import LOSE_SCORE, WIN_SCORE


def test_settlement_score_constants():
    assert WIN_SCORE == 30
    assert LOSE_SCORE == 10


def test_trade_offer_contract():
    trade = TradeOffer(trade_id="abc123", from_id=1, to_id=2, offer_cash=100, request_properties=[7])
    assert trade.offer_properties == []
    assert trade.request_cash == 0
    assert trade.created_turn == 0


def test_game_state_pending_trades_default_empty():
    state = GameState(game_id="g1", room_id="r1", phase=GamePhase.FREE_ACTION)
    assert state.pending_trades == []
    state.pending_trades.append(TradeOffer(trade_id="t1", from_id=1, to_id=2))
    assert len(state.pending_trades) == 1
