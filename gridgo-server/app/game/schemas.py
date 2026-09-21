"""
游戏状态数据模型

定义 GameState 及其子结构，用于在 Redis 中存储和管理游戏运行时状态。
所有模型使用 Pydantic，支持 JSON 序列化/反序列化，方便存取 Redis。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ─── 枚举 ───


class GamePhase(str, Enum):
    """游戏阶段（状态机）"""

    TURN_START = "TURN_START"
    WAIT_ROLL = "WAIT_ROLL"
    ROLLING = "ROLLING"
    MOVING = "MOVING"
    TILE_EFFECT = "TILE_EFFECT"
    WAIT_DECISION = "WAIT_DECISION"
    FREE_ACTION = "FREE_ACTION"
    TURN_END = "TURN_END"
    AUCTION = "AUCTION"
    BANKRUPTCY = "BANKRUPTCY"
    GAME_OVER = "GAME_OVER"


class TileType(str, Enum):
    """地块类型"""

    START = "START"
    PROPERTY = "PROPERTY"
    STATION = "STATION"
    UTILITY = "UTILITY"
    CHANCE = "CHANCE"
    FATE = "FATE"
    TAX = "TAX"
    JAIL = "JAIL"
    PARKING = "PARKING"
    GO_TO_JAIL = "GO_TO_JAIL"


class EndReason(str, Enum):
    """游戏结束原因"""

    LAST_STANDING = "last_standing"
    TURN_LIMIT = "turn_limit"
    VOTE_END = "vote_end"


# ─── 子结构 ───


class DiceState(BaseModel):
    """骰子状态"""

    values: list[int] = Field(default_factory=lambda: [0, 0])
    total: int = 0
    is_double: bool = False


class PlayerState(BaseModel):
    """玩家在游戏中的状态"""

    user_id: int
    nickname: str = ""
    cash: int = 0
    position: int = 0
    is_bankrupt: bool = False
    is_in_jail: bool = False
    jail_turns: int = 0  # 在监狱中的回合数
    properties: list[int] = Field(default_factory=list)  # 拥有的地块 position 列表
    get_out_of_jail_cards: int = 0
    is_ai: bool = False
    ai_difficulty: str | None = None
    is_connected: bool = True
    consecutive_timeouts: int = 0  # 连续超时次数


class TileState(BaseModel):
    """地块在游戏中的实时状态"""

    position: int
    name: str = ""
    tile_type: str = ""
    tile_group: str | None = None
    group_color: str | None = None
    price: int | None = None
    build_cost: int | None = None
    rent_0: int | None = None
    rent_1: int | None = None
    rent_2: int | None = None
    rent_3: int | None = None
    rent_4: int | None = None
    rent_5: int | None = None
    tax_amount: int | None = None
    tax_is_percent: bool | None = None
    # ─── 运行时状态 ───
    owner_id: int | None = None  # 拥有者 user_id，null=无主
    build_level: int = 0  # 建筑等级 0-5
    is_mortgaged: bool = False  # 是否抵押


class AuctionState(BaseModel):
    """拍卖状态"""

    tile_position: int = 0
    start_price: int = 0
    current_bid: int = 0
    current_bidder_id: int | None = None
    bidders: list[int] = Field(default_factory=list)  # 参与者 user_id 列表
    countdown: int = 15  # 倒计时秒数


class TradeOffer(BaseModel):
    """交易报价（对齐 docs/GAME_FLOW.md 9.2 交易系统）

    WS 消息：game.trade_offer / game.trade_accept / game.trade_reject
            / game.trade_received / game.trade_completed
    """

    trade_id: str = ""
    from_id: int = 0  # 发起方 user_id
    to_id: int = 0  # 接收方 user_id
    offer_cash: int = 0  # 发起方给出的现金
    request_cash: int = 0  # 发起方索要的现金
    offer_properties: list[int] = Field(default_factory=list)  # 发起方给出的地块 position
    request_properties: list[int] = Field(default_factory=list)  # 发起方索要的地块 position
    created_turn: int = 0  # 发起时的回合数（用于过期判定）


class CardInfo(BaseModel):
    """卡片信息（用于推送）"""

    card_type: str  # CHANCE / FATE
    card_id: str
    name: str
    effect_type: str
    effect_value: int | None = None
    description: str


# ─── 游戏状态主体 ───


class GameState(BaseModel):
    """
    游戏完整状态 — 存储在 Redis `game:{room_id}` 中

    这是游戏引擎的核心数据结构，所有游戏逻辑读写此对象。
    """

    game_id: str = ""
    room_id: str = ""
    map_id: str = "classic"
    turn_number: int = 0
    current_player_index: int = 0
    phase: GamePhase = GamePhase.TURN_START
    players: list[PlayerState] = Field(default_factory=list)
    tiles: list[TileState] = Field(default_factory=list)
    dice: DiceState = Field(default_factory=DiceState)
    consecutive_doubles: int = 0  # 当前玩家连续双数计数
    chance_deck: list[str] = Field(default_factory=list)  # 机会卡牌堆（card_id列表）
    fate_deck: list[str] = Field(default_factory=list)  # 命运卡牌堆（card_id列表）
    chance_discard: list[str] = Field(default_factory=list)  # 机会卡弃牌堆
    fate_discard: list[str] = Field(default_factory=list)  # 命运卡弃牌堆
    auction: AuctionState | None = None
    # ─── 玩家间交易（docs/PROJECT.md 7.2 交易系统） ───
    pending_trades: list[TradeOffer] = Field(default_factory=list)  # 待处理交易提议
    # ─── 车站/设施租金表（从地图模板复制） ───
    station_rent: dict[int, int] = Field(default_factory=dict)  # {owned_count: rent}
    utility_multiplier: dict[int, int] = Field(default_factory=dict)  # {owned_count: multiplier}
    # ─── 元信息 ───
    start_bonus: int = 200
    jail_bail: int = 50
    max_build_level: int = 5
    initial_cash: int = 1500
    max_turns: int = 100
    turn_timeout: int = 30
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # ─── 辅助方法 ───

    def get_current_player(self) -> PlayerState:
        """获取当前行动的玩家"""
        return self.players[self.current_player_index]

    def get_player_by_id(self, user_id: int) -> PlayerState | None:
        """根据 user_id 查找玩家"""
        for p in self.players:
            if p.user_id == user_id:
                return p
        return None

    def get_tile(self, position: int) -> TileState:
        """根据位置获取地块"""
        return self.tiles[position]

    def get_active_players(self) -> list[PlayerState]:
        """获取所有未破产的玩家"""
        return [p for p in self.players if not p.is_bankrupt]

    def get_next_player_index(self) -> int:
        """计算下一个未破产玩家的索引"""
        idx = (self.current_player_index + 1) % len(self.players)
        while self.players[idx].is_bankrupt:
            idx = (idx + 1) % len(self.players)
            # 防止死循环（只剩一人时）
            if idx == self.current_player_index:
                break
        return idx

    def owns_full_group(self, owner_id: int, tile_group: str) -> bool:
        """判断某玩家是否拥有同组的全部地产"""
        if not tile_group:
            return False
        group_tiles = [t for t in self.tiles if t.tile_group == tile_group]
        if not group_tiles:
            return False
        return all(t.owner_id == owner_id for t in group_tiles)

    def count_owned_stations(self, owner_id: int) -> int:
        """计算玩家拥有的车站数量"""
        return sum(1 for t in self.tiles if t.tile_type == "STATION" and t.owner_id == owner_id)

    def count_owned_utilities(self, owner_id: int) -> int:
        """计算玩家拥有的设施数量"""
        return sum(1 for t in self.tiles if t.tile_type == "UTILITY" and t.owner_id == owner_id)

    def get_player_properties(self, user_id: int) -> list[TileState]:
        """获取玩家拥有的所有地块"""
        return [t for t in self.tiles if t.owner_id == user_id]

    def get_group_tiles(self, tile_group: str) -> list[TileState]:
        """获取同组的所有地块"""
        return [t for t in self.tiles if t.tile_group == tile_group]

    def draw_chance_card(self) -> str:
        """从机会卡牌堆抽一张，牌堆耗尽时重新洗牌"""
        if not self.chance_deck:
            self.chance_deck = self.chance_discard.copy()
            self.chance_discard.clear()
            import random
            random.shuffle(self.chance_deck)
        if not self.chance_deck:
            return ""  # 无卡可抽
        return self.chance_deck.pop(0)

    def draw_fate_card(self) -> str:
        """从命运卡牌堆抽一张，牌堆耗尽时重新洗牌"""
        if not self.fate_deck:
            self.fate_deck = self.fate_discard.copy()
            self.fate_discard.clear()
            import random
            random.shuffle(self.fate_deck)
        if not self.fate_deck:
            return ""  # 无卡可抽
        return self.fate_deck.pop(0)

    def discard_card(self, card_type: str, card_id: str) -> None:
        """将使用后的卡放入弃牌堆"""
        if card_type == "CHANCE":
            self.chance_discard.append(card_id)
        else:
            self.fate_discard.append(card_id)

    def calculate_rent(self, tile: TileState, dice_total: int) -> int:
        """计算地块租金"""
        if tile.tile_type == "PROPERTY":
            rents = [tile.rent_0, tile.rent_1, tile.rent_2, tile.rent_3, tile.rent_4, tile.rent_5]
            base_rent = rents[tile.build_level] or 0
            # 垄断加成：拥有同组全部地产且建筑等级=0
            if tile.build_level == 0 and tile.owner_id and self.owns_full_group(tile.owner_id, tile.tile_group or ""):
                return base_rent * 2
            return base_rent

        elif tile.tile_type == "STATION":
            if not tile.owner_id:
                return 0
            count = self.count_owned_stations(tile.owner_id)
            return self.station_rent.get(count, 0)

        elif tile.tile_type == "UTILITY":
            if not tile.owner_id:
                return 0
            count = self.count_owned_utilities(tile.owner_id)
            multiplier = self.utility_multiplier.get(count, 4)
            return dice_total * multiplier

        return 0

    def calculate_total_assets(self, player: PlayerState) -> int:
        """计算玩家总资产"""
        total = player.cash
        for pos in player.properties:
            tile = self.tiles[pos]
            total += tile.price or 0
            total += (tile.build_level or 0) * (tile.build_cost or 0)
            if tile.is_mortgaged:
                total -= (tile.price or 0) // 2  # 抵押扣减
        return total
