"""
对局回放记录模块

负责：
  1. 实时记录游戏中的每一步操作（掷骰、移动、购买、建造等）
  2. 将操作序列压缩编码为紧凑字符串
  3. 解析压缩编码，还原操作序列
  4. 生成完整的回放数据（初始状态 + 动作序列 + 结束状态）

════════════════════════════════════════════════════════════
压缩编码方案
════════════════════════════════════════════════════════════

整体格式（actions 字段）:
  "T1|P0R35;P1R24;P0B12;P0E|T2|P1R16;P1D;P1E|..."

每回合以 T<回合号> 开头，内含该回合所有动作，以 ; 分隔。
回合之间用 | 分隔。

单个动作格式:
  P<玩家序号><动作码>[参数]

动作码对照表:
  R<d1><d2>      掷骰子（两个点数，0-9，双数加 D 后缀）
  M<位置>        移动到指定位置（0-39）
  B<位置>        购买地产
  X              放弃/跳过购买
  S<位置>        拍卖出价（位置隐含在当前拍卖上下文）
  H<位置>        建造房屋
  G<位置>        拆除房屋
  O<位置>        抵押地产
  N<位置>        赎回地产
  E              结束回合
  J<方式>        监狱操作（b=保释金, c=免罪卡, r=掷骰）
  A<金额>        拍卖出价（金额）
  K<位置>        跳过地产（不购买也不拍卖）
  W<卡类型><卡ID> 抽卡（C=机会, F=命运, 后跟卡ID用hex编码）
  L<金额>        金钱变化（正数获得，负数支付，金额用hex）
  C<位置>        收租金

参数说明:
  - 位置: 0-39（地图格子数）
  - 点数: 单个数字 1-6
  - 金额: 十六进制无符号，0-FFFF (0-65535)
  - 卡ID: 十六进制编码

示例:
  "T1|P0R35M18B18E|T2|P1R24M6E|T3|P0R52D;P0M9WC3A;P0L-1E"
  解读:
    T1 回合: P0 掷出 3+5=8, 移动到18, 购买18号地产, 结束回合
    T2 回合: P1 掷出 2+4=6, 移动到6, 结束回合
    T3 回合: P0 掷出 5+2=7(双数!), P0 移动到9, 抽机会卡3A, P0 支付金钱(hex 1=1), 结束回合
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ─── 动作类型枚举 ───


class ReplayAction(str, Enum):
    """回放动作类型 — 与压缩编码中的动作码一一对应"""

    ROLL = "R"          # 掷骰子
    MOVE = "M"          # 移动
    BUY = "B"           # 购买地产
    DECLINE = "X"       # 放弃购买
    SKIP = "K"          # 跳过地产
    BUILD = "H"         # 建造房屋
    DEMOLISH = "G"      # 拆除房屋
    MORTGAGE = "O"      # 抵押
    REDEEM = "N"        # 赎回
    END_TURN = "E"      # 结束回合
    JAIL = "J"          # 监狱操作
    AUCTION_BID = "A"   # 拍卖出价
    CARD = "W"          # 抽卡
    MONEY = "L"         # 金钱变化
    RENT = "C"          # 支付租金
    EXTRA_ROLL = "D"    # 双数再掷标记


# ─── 单步动作 ───


@dataclass
class ReplayStep:
    """
    回放中的一个原子操作

    Attributes:
        player_idx:  玩家在 players 列表中的索引（0-7）
        action:      动作类型
        params:      动作参数（具体含义取决于 action 类型）
                     ROLL:   [d1, d2] 两个骰子点数
                     MOVE:   [position] 目标位置
                     BUY:    [position] 地产位置
                     DECLINE: []
                     SKIP:   [position]
                     BUILD:  [position]
                     DEMOLISH: [position]
                     MORTGAGE: [position]
                     REDEEM: [position]
                     END_TURN: []
                     JAIL:   [method] 'b'=保释, 'c'=免罪卡, 'r'=掷骰
                     AUCTION_BID: [amount]
                     CARD:   [card_type, card_id] 'C'/'F', 卡ID
                     MONEY:  [amount] 正=获得, 负=支付
                     RENT:   [position]
                     EXTRA_ROLL: []
    """

    player_idx: int
    action: ReplayAction
    params: list[int | str] = field(default_factory=list)


# ─── 回合 ───


@dataclass
class ReplayTurn:
    """一个回合的所有操作"""

    turn_number: int
    steps: list[ReplayStep] = field(default_factory=list)


# ─── 完整回放数据 ───


@dataclass
class ReplayData:
    """
    完整的回放数据

    Attributes:
        init_state:  初始状态快照（游戏开始时的玩家顺序、地图配置等）
        turns:       所有回合的操作列表
        final_state: 结束状态快照（排名、结算金额等）
        actions_encoded: 压缩编码后的动作序列字符串
    """

    init_state: dict[str, Any]
    turns: list[ReplayTurn] = field(default_factory=list)
    final_state: dict[str, Any] = field(default_factory=dict)
    actions_encoded: str = ""


# ═══════════════════════════════════════════════════════════
# 编码器 — 将 ReplayStep / ReplayTurn 编码为压缩字符串
# ═══════════════════════════════════════════════════════════


class ReplayEncoder:
    """将操作序列编码为压缩字符串"""

    @staticmethod
    def encode_step(step: ReplayStep) -> str:
        """编码单个操作为紧凑字符串

        格式: P<idx><ActionCode><params>
        """
        parts = [f"P{step.player_idx}{step.action.value}"]

        if step.action == ReplayAction.ROLL:
            # R<d1><d2>  两个骰子点数
            d1, d2 = step.params[0], step.params[1]
            parts.append(f"{d1}{d2}")

        elif step.action == ReplayAction.MOVE:
            # M<位置>
            parts.append(str(step.params[0]))

        elif step.action in (ReplayAction.BUY, ReplayAction.DECLINE,
                             ReplayAction.SKIP, ReplayAction.BUILD,
                             ReplayAction.DEMOLISH, ReplayAction.MORTGAGE,
                             ReplayAction.REDEEM, ReplayAction.RENT):
            # 带位置参数: B/X/K/H/G/O/N/C<position>
            if step.params:
                parts.append(str(step.params[0]))

        elif step.action == ReplayAction.END_TURN:
            # 无参数
            pass

        elif step.action == ReplayAction.JAIL:
            # J<方式>  b=保释, c=免罪卡, r=掷骰
            parts.append(str(step.params[0]))

        elif step.action == ReplayAction.AUCTION_BID:
            # A<金额hex>
            parts.append(ReplayEncoder._encode_amount(int(step.params[0])))

        elif step.action == ReplayAction.CARD:
            # W<卡类型C/F><卡ID hex>
            card_type = step.params[0]  # 'C' or 'F'
            card_id = step.params[1]
            parts.append(f"{card_type}{ReplayEncoder._encode_card_id(str(card_id))}")

        elif step.action == ReplayAction.MONEY:
            # L<金额hex>  (有符号，用补码表示负数)
            parts.append(ReplayEncoder._encode_amount(int(step.params[0])))

        elif step.action == ReplayAction.EXTRA_ROLL:
            # 无参数
            pass

        return "".join(parts)

    @staticmethod
    def encode_turn(turn: ReplayTurn) -> str:
        """编码一个回合的所有操作，以 ; 分隔"""
        return ";".join(ReplayEncoder.encode_step(s) for s in turn.steps)

    @staticmethod
    def encode(turns: list[ReplayTurn]) -> str:
        """编码所有回合，回合间以 | 分隔"""
        return "|".join(
            f"T{t.turn_number}|{ReplayEncoder.encode_turn(t)}"
            for t in turns
        )

    @staticmethod
    def _encode_amount(amount: int) -> str:
        """编码金额为十六进制（有符号，负数用 - 前缀）"""
        if amount < 0:
            return f"-{hex(-amount)[2:]}"
        return hex(amount)[2:]

    @staticmethod
    def _encode_card_id(card_id: str) -> str:
        """编码卡ID为十六进制字符串"""
        # 卡ID通常是 "C01" "F03" 之类，提取数字部分
        try:
            num = int("".join(c for c in card_id if c.isdigit()))
            return hex(num)[2:]
        except ValueError:
            # 无法解析的卡ID，直接用原字符串的hex
            return card_id.encode("utf-8").hex()


# ═══════════════════════════════════════════════════════════
# 解码器 — 将压缩字符串解析为 ReplayStep / ReplayTurn
# ═══════════════════════════════════════════════════════════


class ReplayDecoder:
    """将压缩字符串解析为操作序列"""

    @staticmethod
    def decode(encoded: str) -> list[ReplayTurn]:
        """解析完整的压缩动作序列

        Args:
            encoded: "T1|P0R35;P0B18;P0E|T2|P1R24;P1E|..." 格式的字符串

        Returns:
            按回合组织的操作列表
        """
        if not encoded or not encoded.strip():
            return []

        turns: list[ReplayTurn] = []

        # 按 | 分割，但要注意 T 前缀
        segments = encoded.split("|")
        current_turn: ReplayTurn | None = None

        for seg in segments:
            if not seg:
                continue

            if seg.startswith("T"):
                # 新回合标记
                try:
                    turn_num = int(seg[1:])
                except ValueError:
                    logger.warning(f"[ReplayDecoder] Invalid turn number: {seg}")
                    continue
                current_turn = ReplayTurn(turn_number=turn_num)
                turns.append(current_turn)
            elif current_turn is not None:
                # 操作步骤
                steps = seg.split(";")
                for step_str in steps:
                    if not step_str.strip():
                        continue
                    step = ReplayDecoder._decode_step(step_str)
                    if step:
                        current_turn.steps.append(step)

        return turns

    @staticmethod
    def _decode_step(step_str: str) -> ReplayStep | None:
        """解析单个操作字符串

        格式: P<idx><ActionCode><params>
        """
        if not step_str or not step_str.startswith("P"):
            logger.warning(f"[ReplayDecoder] Invalid step: {step_str}")
            return None

        try:
            # 找到动作码位置: P<digits><ActionCode>
            idx_end = 1
            while idx_end < len(step_str) and step_str[idx_end].isdigit():
                idx_end += 1

            player_idx = int(step_str[1:idx_end])
            action_code = step_str[idx_end]
            params_str = step_str[idx_end + 1:]

            # 查找动作类型
            action = None
            for a in ReplayAction:
                if a.value == action_code:
                    action = a
                    break

            if action is None:
                logger.warning(f"[ReplayDecoder] Unknown action code: {action_code}")
                return None

            # 解析参数
            params = ReplayDecoder._decode_params(action, params_str)

            return ReplayStep(player_idx=player_idx, action=action, params=params)

        except Exception as e:
            logger.warning(f"[ReplayDecoder] Failed to decode step '{step_str}': {e}")
            return None

    @staticmethod
    def _decode_params(action: ReplayAction, params_str: str) -> list[int | str]:
        """根据动作类型解析参数字符串"""
        if action == ReplayAction.ROLL:
            # R<d1><d2>  两个数字
            if len(params_str) >= 2:
                return [int(params_str[0]), int(params_str[1])]
            return [0, 0]

        elif action == ReplayAction.MOVE:
            return [int(params_str)] if params_str else [0]

        elif action in (ReplayAction.BUY, ReplayAction.BUILD,
                        ReplayAction.DEMOLISH, ReplayAction.MORTGAGE,
                        ReplayAction.REDEEM, ReplayAction.RENT,
                        ReplayAction.SKIP):
            return [int(params_str)] if params_str else [0]

        elif action == ReplayAction.DECLINE:
            return []

        elif action == ReplayAction.END_TURN:
            return []

        elif action == ReplayAction.EXTRA_ROLL:
            return []

        elif action == ReplayAction.JAIL:
            return [params_str] if params_str else ["r"]

        elif action == ReplayAction.AUCTION_BID:
            return [ReplayDecoder._decode_amount(params_str)]

        elif action == ReplayAction.CARD:
            # W<type C/F><card_id hex>
            if len(params_str) >= 2:
                card_type = params_str[0]  # C or F
                card_id_hex = params_str[1:]
                try:
                    card_num = int(card_id_hex, 16)
                    card_id = f"{card_type}{card_num:02d}"
                except ValueError:
                    card_id = card_id_hex
                return [card_type, card_id]
            return ["C", "00"]

        elif action == ReplayAction.MONEY:
            return [ReplayDecoder._decode_amount(params_str)]

        return []

    @staticmethod
    def _decode_amount(hex_str: str) -> int:
        """解码十六进制金额（支持负数 - 前缀）"""
        if not hex_str:
            return 0
        try:
            if hex_str.startswith("-"):
                return -int(hex_str[1:], 16)
            return int(hex_str, 16)
        except ValueError:
            return 0


# ═══════════════════════════════════════════════════════════
# 回放记录器 — 在游戏过程中实时记录操作
# ═══════════════════════════════════════════════════════════


class ReplayRecorder:
    """
    对局记录器 — 游戏引擎中挂载，实时记录每步操作

    用法:
        recorder = ReplayRecorder()
        recorder.set_init_state(game_state)
        recorder.record_roll(player_idx, 3, 5)
        recorder.record_move(player_idx, 18)
        recorder.record_buy(player_idx, 18)
        recorder.record_end_turn(player_idx)
        ...
        replay_data = recorder.finalize(game_state, ranking_data)
    """

    def __init__(self) -> None:
        self._init_state: dict[str, Any] = {}
        self._turns: list[ReplayTurn] = []
        self._current_turn: ReplayTurn | None = None
        self._started: bool = False

    def set_init_state(self, state: Any) -> None:
        """设置初始状态快照（游戏开始时调用一次）

        Args:
            state: GameState 对象或其 model_dump() 结果
        """
        if hasattr(state, "model_dump"):
            state_dict = state.model_dump()
        else:
            state_dict = dict(state)

        # 只保存回放需要的关键信息，减少体积
        self._init_state = {
            "map_id": state_dict.get("map_id", ""),
            "initial_cash": state_dict.get("initial_cash", 1500),
            "start_bonus": state_dict.get("start_bonus", 200),
            "jail_bail": state_dict.get("jail_bail", 50),
            "max_turns": state_dict.get("max_turns", 100),
            "players": [
                {
                    "idx": i,
                    "user_id": p.get("user_id", 0),
                    "nickname": p.get("nickname", ""),
                    "is_ai": p.get("is_ai", False),
                    "start_position": p.get("position", 0),
                }
                for i, p in enumerate(state_dict.get("players", []))
            ],
            "tiles": [
                {
                    "pos": t.get("position", 0),
                    "name": t.get("name", ""),
                    "type": t.get("tile_type", ""),
                    "group": t.get("tile_group"),
                    "price": t.get("price"),
                }
                for t in state_dict.get("tiles", [])
            ],
        }
        self._started = True

    def _ensure_turn(self, turn_number: int) -> ReplayTurn:
        """确保当前回合存在"""
        if self._current_turn is None or self._current_turn.turn_number != turn_number:
            self._current_turn = ReplayTurn(turn_number=turn_number)
            self._turns.append(self._current_turn)
        return self._current_turn

    def _add_step(self, turn_number: int, player_idx: int,
                  action: ReplayAction, params: list[int | str] | None = None) -> None:
        """添加一个操作步骤"""
        turn = self._ensure_turn(turn_number)
        turn.steps.append(ReplayStep(
            player_idx=player_idx,
            action=action,
            params=params or [],
        ))

    # ─── 记录方法（由引擎调用） ───

    def record_roll(self, turn_number: int, player_idx: int, d1: int, d2: int) -> None:
        """记录掷骰子"""
        self._add_step(turn_number, player_idx, ReplayAction.ROLL, [d1, d2])

    def record_extra_roll(self, turn_number: int, player_idx: int) -> None:
        """记录双数再掷"""
        self._add_step(turn_number, player_idx, ReplayAction.EXTRA_ROLL)

    def record_move(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录移动"""
        self._add_step(turn_number, player_idx, ReplayAction.MOVE, [position])

    def record_buy(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录购买地产"""
        self._add_step(turn_number, player_idx, ReplayAction.BUY, [position])

    def record_decline(self, turn_number: int, player_idx: int) -> None:
        """记录放弃购买"""
        self._add_step(turn_number, player_idx, ReplayAction.DECLINE)

    def record_skip(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录跳过地产"""
        self._add_step(turn_number, player_idx, ReplayAction.SKIP, [position])

    def record_build(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录建造房屋"""
        self._add_step(turn_number, player_idx, ReplayAction.BUILD, [position])

    def record_demolish(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录拆除房屋"""
        self._add_step(turn_number, player_idx, ReplayAction.DEMOLISH, [position])

    def record_mortgage(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录抵押"""
        self._add_step(turn_number, player_idx, ReplayAction.MORTGAGE, [position])

    def record_redeem(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录赎回"""
        self._add_step(turn_number, player_idx, ReplayAction.REDEEM, [position])

    def record_end_turn(self, turn_number: int, player_idx: int) -> None:
        """记录结束回合"""
        self._add_step(turn_number, player_idx, ReplayAction.END_TURN)

    def record_jail(self, turn_number: int, player_idx: int, method: str) -> None:
        """记录监狱操作 (b=保释, c=免罪卡, r=掷骰)"""
        self._add_step(turn_number, player_idx, ReplayAction.JAIL, [method])

    def record_auction_bid(self, turn_number: int, player_idx: int, amount: int) -> None:
        """记录拍卖出价"""
        self._add_step(turn_number, player_idx, ReplayAction.AUCTION_BID, [amount])

    def record_card(self, turn_number: int, player_idx: int,
                    card_type: str, card_id: str) -> None:
        """记录抽卡 (card_type: 'C'=机会, 'F'=命运)"""
        self._add_step(turn_number, player_idx, ReplayAction.CARD, [card_type, card_id])

    def record_money(self, turn_number: int, player_idx: int, amount: int) -> None:
        """记录金钱变化 (正=获得, 负=支付)"""
        self._add_step(turn_number, player_idx, ReplayAction.MONEY, [amount])

    def record_rent(self, turn_number: int, player_idx: int, position: int) -> None:
        """记录支付租金"""
        self._add_step(turn_number, player_idx, ReplayAction.RENT, [position])

    # ─── 最终生成 ───

    def finalize(self, final_state: Any, ranking_data: list[dict]) -> ReplayData:
        """
        生成完整的回放数据

        Args:
            final_state:   游戏结束时的 GameState
            ranking_data:  排名数据列表

        Returns:
            ReplayData 包含初始状态、操作序列、结束状态
        """
        # 编码动作序列
        actions_encoded = ReplayEncoder.encode(self._turns)

        # 生成结束状态快照
        if hasattr(final_state, "model_dump"):
            state_dict = final_state.model_dump()
        else:
            state_dict = dict(final_state)

        final_snapshot = {
            "turn_number": state_dict.get("turn_number", 0),
            "end_reason": ranking_data[0] if ranking_data else "",
            "rankings": ranking_data,
            "players": [
                {
                    "idx": i,
                    "user_id": p.get("user_id", 0),
                    "nickname": p.get("nickname", ""),
                    "cash": p.get("cash", 0),
                    "position": p.get("position", 0),
                    "is_bankrupt": p.get("is_bankrupt", False),
                    "is_in_jail": p.get("is_in_jail", False),
                    "properties": p.get("properties", []),
                    "get_out_of_jail_cards": p.get("get_out_of_jail_cards", 0),
                    "is_ai": p.get("is_ai", False),
                }
                for i, p in enumerate(state_dict.get("players", []))
            ],
            "tiles": [
                {
                    "pos": t.get("position", 0),
                    "name": t.get("name", ""),
                    "type": t.get("tile_type", ""),
                    "group": t.get("tile_group"),
                    "price": t.get("price"),
                    "owner_id": t.get("owner_id"),
                    "build_level": t.get("build_level", 0),
                    "is_mortgaged": t.get("is_mortgaged", False),
                }
                for t in state_dict.get("tiles", [])
            ],
        }

        return ReplayData(
            init_state=self._init_state,
            turns=self._turns,
            final_state=final_snapshot,
            actions_encoded=actions_encoded,
        )

    def to_json(self) -> str:
        """将回放数据序列化为 JSON 字符串（用于存入数据库）"""
        data = self.finalize.__wrapped__ if hasattr(self.finalize, "__wrapped__") else {}
        # 直接构建
        return json.dumps({
            "init_state": self._init_state,
            "actions": ReplayEncoder.encode(self._turns),
            "turns_count": len(self._turns),
        }, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════
# 便捷函数 — 解析数据库中存储的回放数据
# ═══════════════════════════════════════════════════════════


def parse_replay_data(init_snapshot_json: str | None,
                      actions_encoded: str,
                      final_snapshot_json: str | None) -> dict:
    """
    解析数据库中存储的回放数据，返回可读的结构化结果

    Args:
        init_snapshot_json:   初始状态快照 JSON 字符串
        actions_encoded:      压缩编码的动作序列字符串
        final_snapshot_json:  结束状态快照 JSON 字符串

    Returns:
        {
            "init_state": {...},
            "turns": [
                {
                    "turn_number": 1,
                    "steps": [
                        {"player_idx": 0, "action": "ROLL", "params": [3, 5], "description": "掷骰子 3+5=8"},
                        {"player_idx": 0, "action": "MOVE", "params": [18], "description": "移动到 18号地块"},
                        ...
                    ]
                },
                ...
            ],
            "final_state": {...}
        }
    """
    # 解析初始状态
    init_state = {}
    if init_snapshot_json:
        try:
            init_state = json.loads(init_snapshot_json)
        except (json.JSONDecodeError, TypeError):
            init_state = {}

    # 解析动作序列
    turns = ReplayDecoder.decode(actions_encoded)

    # 解析结束状态
    final_state = {}
    if final_snapshot_json:
        try:
            final_state = json.loads(final_snapshot_json)
        except (json.JSONDecodeError, TypeError):
            final_state = {}

    # 转换为可读结构
    result_turns = []
    for turn in turns:
        steps = []
        for step in turn.steps:
            step_dict = {
                "player_idx": step.player_idx,
                "action": step.action.name,
                "params": step.params,
                "description": _describe_step(step),
            }
            steps.append(step_dict)
        result_turns.append({
            "turn_number": turn.turn_number,
            "steps": steps,
        })

    return {
        "init_state": init_state,
        "turns": result_turns,
        "final_state": final_state,
    }


def _describe_step(step: ReplayStep) -> str:
    """为操作生成人类可读的描述"""
    if step.action == ReplayAction.ROLL:
        d1, d2 = step.params[0], step.params[1]
        total = int(d1) + int(d2)
        return f"掷骰子 {d1}+{d2}={total}"

    elif step.action == ReplayAction.EXTRA_ROLL:
        return "双数！再掷一次"

    elif step.action == ReplayAction.MOVE:
        return f"移动到 {step.params[0]} 号地块"

    elif step.action == ReplayAction.BUY:
        return f"购买 {step.params[0]} 号地产"

    elif step.action == ReplayAction.DECLINE:
        return "放弃购买"

    elif step.action == ReplayAction.SKIP:
        return f"跳过 {step.params[0]} 号地产"

    elif step.action == ReplayAction.BUILD:
        return f"在 {step.params[0]} 号地产建造房屋"

    elif step.action == ReplayAction.DEMOLISH:
        return f"拆除 {step.params[0]} 号地产房屋"

    elif step.action == ReplayAction.MORTGAGE:
        return f"抵押 {step.params[0]} 号地产"

    elif step.action == ReplayAction.REDEEM:
        return f"赎回 {step.params[0]} 号地产"

    elif step.action == ReplayAction.END_TURN:
        return "结束回合"

    elif step.action == ReplayAction.JAIL:
        method_map = {"b": "支付保释金", "c": "使用免罪卡", "r": "掷骰出狱"}
        return method_map.get(str(step.params[0]), "监狱操作")

    elif step.action == ReplayAction.AUCTION_BID:
        return f"拍卖出价 ¥{step.params[0]}"

    elif step.action == ReplayAction.CARD:
        type_map = {"C": "机会卡", "F": "命运卡"}
        card_type = type_map.get(str(step.params[0]), "卡片")
        return f"抽取 {card_type} {step.params[1]}"

    elif step.action == ReplayAction.MONEY:
        amount = int(step.params[0])
        if amount > 0:
            return f"获得 ¥{amount}"
        return f"支付 ¥{abs(amount)}"

    elif step.action == ReplayAction.RENT:
        return f"支付 {step.params[0]} 号地产租金"

    return f"未知操作 {step.action.value}"
