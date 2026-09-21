"""拍卖规则单测（docs/GAME_FLOW.md 5）

覆盖：起拍价 = 购买价 × 50%（最低 1）、最小加价幅度、AuctionState 默认值。
不依赖 Redis / PostgreSQL。
"""

from app.game.engine import MIN_BID_INCREMENT, GameEngine, compute_start_price
from app.game.schemas import AuctionState


def test_start_price_is_half_of_price():
    assert compute_start_price(200) == 100
    assert compute_start_price(300) == 150
    assert compute_start_price(220) == 110


def test_start_price_floor_is_one():
    assert compute_start_price(0) == 1
    assert compute_start_price(None) == 1
    assert compute_start_price(1) == 1


def test_min_bid_increment_constant():
    assert MIN_BID_INCREMENT == 10
    assert GameEngine.MIN_BID_INCREMENT == MIN_BID_INCREMENT


def test_auction_state_defaults():
    auction = AuctionState(tile_position=5, start_price=100, current_bid=100)
    assert auction.countdown == 15
    assert auction.current_bidder_id is None
    assert auction.bidders == []
