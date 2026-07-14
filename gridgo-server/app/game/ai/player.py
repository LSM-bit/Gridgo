"""
AI 玩家实例

设计思路：
  - BaseAIPlayer 是所有 AI 的基类，定义通用属性与操作接口
  - EasyAI / MediumAI / HardAI 继承基类，实现不同难度的决策逻辑
  - AIPlayerFactory 工厂方法根据难度字符串创建对应 AI 实例
  - AI 以 RoomPlayer 身份存在于房间中，is_ai=True，user_id 为负数
  - AI 决策逻辑通过 GameEngine 的 _ai_* 方法驱动，此处定义策略接口
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ─── AI 昵称池 ───

AI_NAMES_POOL: list[str] = [
    "阿尔法", "贝塔", "伽马", "德尔塔", "艾普西隆",
    "泽塔", "伊塔", "西塔", "卡帕", "拉姆达",
    "缪", "纽", "欧米克戎", "派", "柔",
    "西格玛", "陶", "斐", "普赛", "欧米伽",
]


def _pick_ai_name(index: int) -> str:
    """根据索引从名称池中选取 AI 昵称，超出范围则追加编号"""
    if index < len(AI_NAMES_POOL):
        return AI_NAMES_POOL[index]
    return f"AI-{index + 1}"


# ─── AI 玩家基类 ───


@dataclass
class BaseAIPlayer(ABC):
    """
    AI 玩家基类

    Attributes:
        ai_index:     AI 在房间中的序号（从 0 开始），用于生成 user_id 和昵称
        difficulty:   难度标识: easy / medium / hard
        user_id:      负数 ID，在房间中唯一标识此 AI
        nickname:     显示昵称
        is_ready:     AI 默认已准备
        is_ai:        固定为 True
    """

    ai_index: int
    difficulty: str = "easy"
    user_id: int = field(init=False)
    nickname: str = field(init=False)
    is_ready: bool = field(default=True, init=False)
    is_ai: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        self.user_id = -(self.ai_index + 1)
        self.nickname = _pick_ai_name(self.ai_index)

    # ─── 决策接口 ───

    @abstractmethod
    def should_buy_property(self, game_state: dict, property_info: dict) -> bool:
        """
        是否购买地产

        Args:
            game_state:     当前游戏状态快照
            property_info:  地产信息（position, price, tile_group, rent_0 等）

        Returns:
            True 表示购买，False 表示放弃
        """
        ...

    @abstractmethod
    def should_build_house(self, game_state: dict, tile_info: dict) -> bool:
        """
        是否在指定地块建造房屋

        Args:
            game_state:  当前游戏状态快照
            tile_info:   地块信息

        Returns:
            True 表示建造
        """
        ...

    @abstractmethod
    def get_auction_bid(self, game_state: dict, tile_info: dict, current_bid: int) -> int | None:
        """
        拍卖出价

        Args:
            game_state:   当前游戏状态
            tile_info:    拍卖地块信息
            current_bid:  当前最高出价

        Returns:
            出价金额，None 表示不出价
        """
        ...

    @abstractmethod
    def should_mortgage(self, game_state: dict, tile_info: dict) -> bool:
        """
        是否抵押地产（在现金不足时）

        Args:
            game_state:  当前游戏状态
            tile_info:   地块信息

        Returns:
            True 表示抵押
        """
        ...

    @abstractmethod
    def choose_jail_action(self, game_state: dict, player_info: dict) -> str:
        """
        监狱中的决策

        Args:
            game_state:   当前游戏状态
            player_info:  玩家自身信息

        Returns:
            "card" (使用免罪卡) / "bail" (支付保释金) / "roll" (掷骰尝试双数)
        """
        ...

    def to_room_player_dict(self, room_difficulty: str) -> dict:
        """转换为 RoomPlayer 兼容的字典，用于存入 Redis 房间数据"""
        return {
            "user_id": self.user_id,
            "username": f"AI_{self.ai_index + 1}",
            "nickname": self.nickname,
            "avatar": None,
            "is_host": False,
            "is_ready": True,
            "is_ai": True,
            "ai_difficulty": room_difficulty,
        }


# ─── 难度子类 ───


class EasyAI(BaseAIPlayer):
    """简单难度 AI — 随机决策为主"""

    def should_buy_property(self, game_state: dict, property_info: dict) -> bool:
        """50% 概率购买，不考虑策略"""
        price = property_info.get("price", 0)
        cash = game_state.get("cash", 0)
        if cash < price:
            return False
        return random.random() > 0.5

    def should_build_house(self, game_state: dict, tile_info: dict) -> bool:
        """30% 概率建造"""
        return random.random() > 0.7

    def get_auction_bid(self, game_state: dict, tile_info: dict, current_bid: int) -> int | None:
        """50% 概率出价，最多出到购买价的 80%"""
        if random.random() > 0.5:
            return None
        max_bid = int((tile_info.get("price", 0) or 0) * 0.8)
        if current_bid >= max_bid:
            return None
        return min(current_bid + 10, max_bid)

    def should_mortgage(self, game_state: dict, tile_info: dict) -> bool:
        """现金低于 100 时随机抵押"""
        cash = game_state.get("cash", 0)
        if cash < 100:
            return random.random() > 0.5
        return False

    def choose_jail_action(self, game_state: dict, player_info: dict) -> str:
        """随机选择"""
        if player_info.get("get_out_of_jail_cards", 0) > 0:
            return random.choice(["card", "roll"])
        return random.choice(["bail", "roll"])


class MediumAI(BaseAIPlayer):
    """中等难度 AI — 基于简单规则的决策"""

    def should_buy_property(self, game_state: dict, property_info: dict) -> bool:
        """评估：现金占比、垄断潜力、保留应急资金(200)"""
        price = property_info.get("price", 0)
        cash = game_state.get("cash", 0)
        if cash < price + 200:  # 保留应急资金
            return False
        # 如果有同组地产，优先购买（垄断潜力）
        tile_group = property_info.get("tile_group")
        if tile_group:
            owned = game_state.get("owned_in_group", 0)
            total = game_state.get("total_in_group", 1)
            if owned >= total - 1:  # 差一张就垄断
                return True
        return cash >= price * 2  # 现金充裕才买

    def should_build_house(self, game_state: dict, tile_info: dict) -> bool:
        """优先升级有垄断的分组"""
        cash = game_state.get("cash", 0)
        build_cost = tile_info.get("build_cost", 0)
        has_monopoly = game_state.get("has_monopoly", False)
        if has_monopoly and cash >= build_cost + 200:
            return True
        return False

    def get_auction_bid(self, game_state: dict, tile_info: dict, current_bid: int) -> int | None:
        """基于地产价值评估出价，最多出到购买价的 100%"""
        price = tile_info.get("price", 0)
        max_bid = int(price)
        cash = game_state.get("cash", 0)
        if current_bid >= max_bid or cash < current_bid + 10 + 200:
            return None
        # 根据垄断潜力调整出价意愿
        bid = min(current_bid + 10, max_bid)
        return bid

    def should_mortgage(self, game_state: dict, tile_info: dict) -> bool:
        """现金低于 150 时考虑抵押"""
        cash = game_state.get("cash", 0)
        return cash < 150

    def choose_jail_action(self, game_state: dict, player_info: dict) -> str:
        """有免罪卡优先用，否则保释金"""
        if player_info.get("get_out_of_jail_cards", 0) > 0:
            return "card"
        cash = player_info.get("cash", 0)
        if cash > 200:
            return "bail"
        return "roll"


class HardAI(BaseAIPlayer):
    """困难难度 AI — 最优策略 / 蒙特卡洛模拟"""

    def should_buy_property(self, game_state: dict, property_info: dict) -> bool:
        """精算购买：几乎总是买，除非现金极度紧张"""
        price = property_info.get("price", 0)
        cash = game_state.get("cash", 0)
        if cash < price + 100:  # 困难 AI 保留更少的应急资金
            return False
        # 垄断潜力大增购买意愿
        tile_group = property_info.get("tile_group")
        if tile_group:
            owned = game_state.get("owned_in_group", 0)
            total = game_state.get("total_in_group", 1)
            if owned >= total - 1:
                return True  # 差一张垄断必买
        # 评估 ROI（简化：租金/价格比）
        rent = property_info.get("rent_0", 0)
        if rent and price:
            roi = rent / price
            if roi > 0.05:  # 租金回报率 > 5%
                return True
        return cash >= price * 1.5

    def should_build_house(self, game_state: dict, tile_info: dict) -> bool:
        """基于收益模拟选择最优操作"""
        cash = game_state.get("cash", 0)
        build_cost = tile_info.get("build_cost", 0)
        has_monopoly = game_state.get("has_monopoly", False)
        if not has_monopoly:
            return False
        if cash < build_cost + 100:
            return False
        # 评估升级后的租金增长
        current_level = tile_info.get("build_level", 0)
        next_rent_key = f"rent_{current_level + 1}"
        current_rent_key = f"rent_{current_level}"
        next_rent = tile_info.get(next_rent_key, 0)
        current_rent = tile_info.get(current_rent_key, 0)
        if build_cost > 0:
            rent_increase = next_rent - current_rent
            rounds_to_payoff = build_cost / max(rent_increase, 1)
            return rounds_to_payoff < 10  # 10 回合内回本
        return True

    def get_auction_bid(self, game_state: dict, tile_info: dict, current_bid: int) -> int | None:
        """模拟地产收益期望，可能超过购买价"""
        price = tile_info.get("price", 0)
        cash = game_state.get("cash", 0)
        # 困难 AI 可能出价超过购买价（如果 ROI 好）
        max_bid = int(price * 1.3)
        if current_bid >= max_bid or cash < current_bid + 10 + 100:
            return None
        # 每次只加最低价
        return current_bid + 10

    def should_mortgage(self, game_state: dict, tile_info: dict) -> bool:
        """现金低于 100 时果断抵押"""
        cash = game_state.get("cash", 0)
        return cash < 100

    def choose_jail_action(self, game_state: dict, player_info: dict) -> str:
        """最优出狱策略"""
        if player_info.get("get_out_of_jail_cards", 0) > 0:
            return "card"
        # 困难 AI 总是支付保释金以尽快移动
        return "bail"


# ─── 工厂方法 ───


_DIFFICULTY_MAP: dict[str, type[BaseAIPlayer]] = {
    "easy": EasyAI,
    "medium": MediumAI,
    "hard": HardAI,
}


class AIPlayerFactory:
    """AI 玩家工厂 — 根据难度创建 AI 实例"""

    @staticmethod
    def create(ai_index: int, difficulty: str = "easy") -> BaseAIPlayer:
        """创建 AI 玩家实例"""
        cls = _DIFFICULTY_MAP.get(difficulty)
        if cls is None:
            raise ValueError(f"未知的 AI 难度: {difficulty}，可选值: {list(_DIFFICULTY_MAP.keys())}")
        return cls(ai_index=ai_index, difficulty=difficulty)

    @staticmethod
    def create_batch(count: int, difficulty: str = "easy") -> list[BaseAIPlayer]:
        """批量创建 AI 玩家"""
        return [AIPlayerFactory.create(i, difficulty) for i in range(count)]

    @staticmethod
    def available_difficulties() -> list[str]:
        """返回所有可用的难度选项"""
        return list(_DIFFICULTY_MAP.keys())
