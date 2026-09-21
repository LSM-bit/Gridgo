---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: ee1a9111a266e63ab5b365271262c0db_b373d745b58511f19ef152540024e231
    ReservedCode1: qZofDLMIMF3apN9MwiVy9ot+Gu48z/p22cnNBYt2JKnK+zeyuuCjryOfxBPt+DTTjLrgP8zrzmoTkwUve7rXEZBKnZQ+ryTOQ9XomZpfX4SfyqDJaVC8+Xa3iDqJIxcqTQ+fenjLoFVhq4waEDIdnhalLxwi/2x2yC368zz9/yKLaNU2BzPkfGQ88UU=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: ee1a9111a266e63ab5b365271262c0db_b373d745b58511f19ef152540024e231
    ReservedCode2: qZofDLMIMF3apN9MwiVy9ot+Gu48z/p22cnNBYt2JKnK+zeyuuCjryOfxBPt+DTTjLrgP8zrzmoTkwUve7rXEZBKnZQ+ryTOQ9XomZpfX4SfyqDJaVC8+Xa3iDqJIxcqTQ+fenjLoFVhq4waEDIdnhalLxwi/2x2yC368zz9/yKLaNU2BzPkfGQ88UU=
---

# GridGo - 完整游戏流程

> 基于当前已实现的房间系统、AI 系统、聊天系统，描述从"开始游戏"到"游戏结束"的完整对局流程。
> 更新日期：2026-07-11

---

## 目录

- [一、总体流程概览](#一总体流程概览)
- [二、阶段一：游戏初始化](#二阶段一游戏初始化)
- [三、阶段二：回合循环](#三阶段二回合循环)
  - [3.1 回合开始 (TURN_START)](#31-回合开始-turn_start)
  - [3.2 等待掷骰 (WAIT_ROLL)](#32-等待掷骰-wait_roll)
  - [3.3 掷骰中 (ROLLING)](#33-掷骰中-rolling)
  - [3.4 棋子移动 (MOVING)](#34-棋子移动-moving)
  - [3.5 地块效果 (TILE_EFFECT)](#35-地块效果-tile_effect)
  - [3.6 等待决策 (WAIT_DECISION)](#36-等待决策-wait_decision)
  - [3.7 自由行动 (FREE_ACTION)](#37-自由行动-free_action)
  - [3.8 回合结束 (TURN_END)](#38-回合结束-turn_end)
- [四、阶段三：游戏结束](#四阶段三游戏结束)
- [五、特殊机制详解](#五特殊机制详解)
  - [5.1 监狱机制](#51-监狱机制)
  - [5.2 破产机制](#52-破产机制)
  - [5.3 拍卖机制](#53-拍卖机制)
  - [5.4 卡片事件机制](#54-卡片事件机制)
  - [5.5 交易机制](#55-交易机制)
- [六、AI 决策流程](#六ai-决策流程)
- [七、WebSocket 消息流](#七websocket-消息流)
  - [7.2 心跳与断线](#72-心跳与断线)
  - [7.3 连接关闭码](#73-连接关闭码)
- [八、数据存储策略](#八数据存储策略)
- [九、异常与边界处理](#九异常与边界处理)

---

## 一、总体流程概览

```
房主点击"开始游戏"
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  阶段一：游戏初始化                                        │
│  ├─ 创建 GameState 存入 Redis                             │
│  ├─ 分配初始资金（默认 1500）                               │
│  ├─ 随机决定玩家顺序                                       │
│  ├─ 所有棋子放在起点 (Tile 0)                              │
│  ├─ 洗牌生成机会卡/命运卡堆                                │
│  └─ 广播 state.snapshot 给所有玩家                         │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  阶段二：回合循环                                          │
│                                                          │
│  ┌──► 第 N 回合（当前玩家 P）                              │
│  │    ├─ 回合开始 → 广播 game.turn_change                 │
│  │    ├─ 等待掷骰 / AI自动掷骰                             │
│  │    ├─ 骰子结果 → 广播 game.dice_result                  │
│  │    ├─ 棋子移动 → 广播 game.player_moved                 │
│  │    ├─ 触发地块效果                                      │
│  │    ├─ 自由行动阶段                                      │
│  │    ├─ 检查破产条件                                      │
│  │    └─ 回合结束 → 切换下一玩家                            │
│  │         │                                              │
│  │         ▼                                              │
│  │    检查游戏结束条件 ──否──► 回到回合开始                   │
│  │         │                                              │
│  │        是                                              │
│  └────────┼──────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────┐
│  阶段三：游戏结束                                          │
│  ├─ 广播 game.over（含最终排名、资产统计）                   │
│  ├─ 保存对局记录到 PostgreSQL                              │
│  ├─ 更新用户统计（胜场、积分等）                             │
│  ├─ 房间状态改为 finished                                   │
│  ├─ 清理 Redis 中的 GameState                              │
│  └─ 展示结算页 → 返回大厅/再来一局                          │
└──────────────────────────────────────────────────────────┘
```

---

## 二、阶段一：游戏初始化

当房主点击"开始游戏"且满足条件（所有非房主真人已准备、至少 2 名玩家），服务器执行以下初始化：

### 2.1 初始化步骤

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 创建 `GameState` | 包含棋盘、玩家列表、当前回合号等 |
| 2 | 分配初始资金 | 每人 `GAME_INITIAL_CASH=1500` |
| 3 | 随机玩家顺序 | 使用 `random.shuffle` 打乱玩家列表 |
| 4 | 棋子归零 | 所有玩家 `position = 0`（起点） |
| 5 | 初始化棋盘 | 加载地图配置，40 个地块状态初始化（无主、建筑等级 0） |
| 6 | 洗牌卡组 | 机会卡（10 张）和命运卡（10 张）分别洗牌 |
| 7 | 初始化 AI 实例 | 为每个 AI 玩家创建对应难度的 `BaseAIPlayer` 实例 |
| 8 | 存入 Redis | `game:{room_id}` → GameState JSON，TTL=24h |
| 9 | 更新房间状态 | `room.status = "playing"`，从 `room:list` 移除 |
| 10 | 广播快照 | 通过 WebSocket 推送 `state.snapshot` 给所有在线玩家 |

### 2.2 GameState 核心数据结构

```json
{
  "game_id": "75873edb9a92",
  "room_id": "75873edb9a92",
  "turn_number": 0,
  "current_player_index": 0,
  "phase": "TURN_START",
  "players": [
    {
      "user_id": 8,
      "nickname": "Lsm",
      "cash": 1500,
      "position": 0,
      "is_bankrupt": false,
      "is_in_jail": false,
      "jail_turns": 0,
      "properties": [],
      "get_out_of_jail_cards": 0,
      "is_ai": false,
      "is_connected": true
    },
    {
      "user_id": -1,
      "nickname": "阿尔法",
      "cash": 1500,
      "position": 0,
      "is_bankrupt": false,
      "is_in_jail": false,
      "jail_turns": 0,
      "properties": [],
      "get_out_of_jail_cards": 0,
      "is_ai": true,
      "ai_difficulty": "medium",
      "is_connected": true
    }
  ],
  "tiles": [
    {"position": 0, "name": "起点", "tile_type": "START", "owner_id": null, "build_level": 0, "is_mortgaged": false},
    {"position": 1, "name": "朝阳路", "tile_type": "PROPERTY", "tile_group": "brown", "price": 60, "owner_id": null, "build_level": 0, "is_mortgaged": false},
    "..."
  ],
  "chance_deck": ["C01", "C05", "C03", "..."],
  "fate_deck": ["F02", "F08", "F04", "..."],
  "dice": {"values": [0, 0], "total": 0, "is_double": false},
  "consecutive_doubles": 0,
  "auction": null,
  "pending_trades": [],
  "station_rent": {"...": "..."},
  "utility_multiplier": {"...": "..."},
  "initial_cash": 1500,
  "max_turns": 100,
  "turn_timeout": 30,
  "created_at": "2026-07-11T00:00:00Z"
}
```

> **字段口径**（`app/game/schemas.py::GameState`）：`game_id`、`room_id`、`map_id`、`turn_number`、`current_player_index`、`phase`、`players`、`tiles`、`dice`、`consecutive_doubles`、`chance_deck`、`fate_deck`、`chance_discard`、`fate_discard`、`auction`、`pending_trades`、`station_rent`、`utility_multiplier`、`start_bonus`、`jail_bail`、`max_build_level`、`initial_cash`、`max_turns`、`turn_timeout`、`created_at`。
> 地块为**扁平 `tiles` 数组**（元素字段 `position` / `name` / `tile_type` / `tile_group` / `group_color` / `price` / `build_cost` / `rent_0`…`rent_5` / `tax_amount` / `tax_is_percent` / `owner_id` / `build_level` / `is_mortgaged`），**不存在 `board` 嵌套层**。

### 2.3 前端跳转

```
Room.vue 检测到 room.status === "playing"
  → router.push(`/game/${room.id}`)
  → 加载 Game.vue
  → 建立 WebSocket 连接 ws://host/ws/game?token=<access_token>
  → 接收 state.snapshot → 渲染棋盘
```

---

## 三、阶段二：回合循环

### 回合状态机总览

```
                    ┌───────────┐
                    │TURN_START │
                    └─────┬─────┘
                          │
                    ┌─────▼─────┐
                    │ WAIT_ROLL  │◄──── 回合超时(自动掷骰)
                    └─────┬─────┘
                     掷骰子│
                    ┌─────▼─────┐
              ┌─────┤  ROLLING   ├─────┐
              │     └────────────┘     │
         双数│                    非双数│
              │                         │
         ┌────▼────┐            ┌──────▼──────┐
         │ 可再掷骰 │            │   MOVING     │
         └─────────┘            └──────┬──────┘
                                       │ 移动完成
                              ┌────────▼────────┐
                              │  TILE_EFFECT    │
                              └────────┬────────┘
                                       │
                         ┌─────────────▼─────────────┐
                         │ 需要玩家决策?              │
                         │ (买地/拍卖/出狱/支付保释)  │
                         └─────┬─────────────┬───────┘
                          是   │          否  │
                     ┌────────▼────┐   ┌─────▼──────┐
                     │WAIT_DECISION│   │ FREE_ACTION │
                     └────────┬────┘   └─────┬──────┘
                     玩家决策 │              │ 可选操作完成
                              └──────────────┘
                              │
                     ┌────────▼────┐
                     │  TURN_END   │
                     └────────┬────┘
                              │
                     ┌────────▼────┐
                     │  下一玩家    │
                     └─────────────┘
```

---

### 3.1 回合开始 (TURN_START)

```
服务器 → 广播 game.turn_change:
{
  "type": "game.turn_change",
  "data": {
    "current_player_id": 8,
    "current_player_nickname": "Lsm",
    "turn_number": 1,
    "is_ai": false
  }
}
```

- 更新 `turn_number += 1`
- 设置 `phase = "WAIT_ROLL"`
- 启动 30 秒回合计时器
- 如果当前玩家是 AI，延迟 1-2 秒后自动进入掷骰阶段

---

### 3.2 等待掷骰 (WAIT_ROLL)

**真人玩家：**
- 前端显示 [掷骰子] 按钮
- 倒计时显示（30 秒）
- 倒计时最后 5 秒高亮警告

**AI 玩家：**
- 服务器自动触发掷骰
- 统一延迟 1-2s（模拟真人思考，难度差异体现在决策策略而非速度）

**在监狱中的玩家：**
- 额外显示 [支付保释金 50] 和 [使用免罪卡] 按钮
- 选择掷骰时，判定是否掷出双数来出狱

**超时处理：**
- 30 秒未操作 → 自动掷骰
- 连续超时 3 次 → 标记断线，AI 暂代

---

### 3.3 掷骰中 (ROLLING)

```
客户端 → 服务器: game.roll_dice
服务器 → 广播 game.dice_result:
{
  "type": "game.dice_result",
  "data": {
    "player_id": 8,
    "dice": [3, 5],
    "total": 8,
    "is_double": false
  }
}
```

**前端动画：**
- 骰子 3D 翻滚动画（1.2s）
- 动画结束后显示点数

**服务器逻辑：**
1. 生成 2 个随机骰子值（1-6）
2. 判断是否双数 `dice[0] == dice[1]`
3. 如果双数：`consecutive_doubles += 1`
   - 连续 3 次双数 → 直接入狱（防作弊机制）
   - 否则 → 本次移动后可再掷一次
4. 如果非双数：`consecutive_doubles = 0`，正常移动

---

### 3.4 棋子移动 (MOVING)

```
服务器 → 广播 game.player_moved:
{
  "type": "game.player_moved",
  "data": {
    "player_id": 8,
    "from": 5,
    "to": 13,
    "steps": 8,
    "passed_go": true
  }
}
```

**移动逻辑：**
1. 计算新位置：`new_pos = (current_pos + dice_total) % 40`
2. 判断是否经过起点：如果 `new_pos < current_pos`（跨过 0），则经过起点
3. 经过起点 → 获得 `GAME_PASS_GO_BONUS=200`

**前端动画：**
- 棋子沿棋盘逐格跳动（0.3s/格）
- 经过起点时显示 "+200" 金币动画

**特殊情况：**
- 被送入监狱时不经过起点，不获得过路费
- 卡片效果移动（如"前进至起点"）经过起点时获得过路费

---

### 3.5 地块效果 (TILE_EFFECT)

到达目标地块后，根据地块类型触发效果：

| 地块类型 | 效果 | 是否需要决策 | 进入阶段 |
|----------|------|:----------:|----------|
| **START** | 无额外效果（过路费已在移动时发放） | 否 | FREE_ACTION |
| **PROPERTY** | 无主→可购买；己方→可升级；他方→付租金 | 是 | WAIT_DECISION |
| **STATION** | 同 PROPERTY，租金按拥有数量计算 | 是 | WAIT_DECISION |
| **UTILITY** | 同 PROPERTY，租金=骰子×4/×10 | 是 | WAIT_DECISION |
| **CHANCE** | 抽取机会卡并执行效果 | 视卡片 | FREE_ACTION |
| **FATE** | 抽取命运卡并执行效果 | 视卡片 | FREE_ACTION |
| **TAX** | 扣除税款（200 或 100） | 否 | FREE_ACTION |
| **JAIL** | 仅停留，无效果 | 否 | FREE_ACTION |
| **GO_TO_JAIL** | 直接送入监狱 | 否 | TURN_END |
| **PARKING** | 安全格，无效果 | 否 | FREE_ACTION |

---

### 3.6 等待决策 (WAIT_DECISION)

#### 场景 A：停在无主地产 — 购买/跳过

```
服务器 → 广播 game.tile_event:
{
  "type": "game.tile_event",
  "data": {
    "player_id": 8,
    "tile_id": 1,
    "tile_name": "朝阳路",
    "event_type": "property_unowned",
    "price": 60
  }
}
```

**真人玩家选项：**
- [购买 (¥60)] → 扣除现金，获得地产
- [放弃] → 不购买，直接进入自由行动

**AI 决策：**
- 调用 `ai.decide_buy_property(game_state, property_info)`
- 根据难度返回购买/放弃

#### 场景 B：停在他人地产 — 支付租金

```
服务器 → 广播 game.rent_paid:
{
  "type": "game.rent_paid",
  "data": {
    "from_id": 8,
    "to_id": -1,
    "amount": 20,
    "tile_id": 1,
    "tile_name": "朝阳路"
  }
}
```

- 自动计算并扣除租金
- 如果现金不足 → 进入破产处理流程
- 垄断加成：拥有同组全部地产且建筑等级=0时，租金 ×2

#### 场景 C：停在自己地产 — 可升级

- 提示是否建造房屋
- 需满足：拥有同组全部地产、均匀建造规则、现金充足

---

### 3.7 自由行动 (FREE_ACTION)

地块效果处理完毕后，玩家进入自由行动阶段，可选操作：

| 操作 | WebSocket 消息 | 说明 |
|------|---------------|------|
| 建造房屋 | `game.build` | 需拥有同组全部地产，均匀建造 |
| 拆除房屋 | `game.demolish` | 返还半价 |
| 抵押地产 | `game.mortgage` | 获得购买价一半的现金，停止收租 |
| 赎回地产 | `game.redeem` | 支付赎回费用（抵押额 + 10%） |
| 发起交易 | `game.trade_offer` | 与其他玩家交换现金/地产 |
| 使用免罪卡 | `game.jail_use_card` | 出狱（如果在监狱中） |
| 结束回合 | `game.end_turn` | 结束自由行动，进入 TURN_END |
| 聊天 | `chat.send` | 随时可用 |

**AI 自由行动：**
- 根据难度决定是否建造/抵押/交易
- 简单 AI：随机操作
- 中等 AI：优先升级有垄断的分组
- 困难 AI：基于收益模拟选择最优操作

---

### 3.8 回合结束 (TURN_END)

1. 检查破产条件
2. 检查游戏结束条件
3. 如果掷出双数且未入狱 → 返回 WAIT_ROLL（同一玩家再掷一次）
4. 否则 → 切换到下一个未破产玩家

---

## 四、阶段三：游戏结束

### 4.1 游戏结束条件

| 条件 | end_reason | 说明 |
|------|-----------|------|
| 仅剩 1 名未破产玩家 | `last_standing` | 经典模式，该玩家获胜 |
| 达到回合上限 | `turn_limit` | 资产最多的玩家获胜（默认 100 回合） |
| 全体投票结束 | `vote_end` | 超过半数玩家同意，按资产排名结算 |

### 4.2 结算流程

```
游戏结束条件触发
       │
       ▼
计算最终排名
  ├─ 按总资产降序排列（现金 + 地产价值 + 建筑价值 - 抵押）
  ├─ 破产玩家排最末（按破产先后排序）
  └─ 总资产相同则现金多者排前
       │
       ▼
广播 game.over:
{
  "type": "game.over",
  "data": {
    "end_reason": "last_standing",
    "winner_id": 8,
    "rankings": [
      {"rank": 1, "user_id": 8, "nickname": "Lsm", "total_assets": 5800, "is_ai": false},
      {"rank": 2, "user_id": -1, "nickname": "阿尔法", "total_assets": 2100, "is_ai": true}
    ]
  }
}
       │
       ▼
保存对局记录到 PostgreSQL (game_records + game_players)
  ├─ 记录对局配置快照
  ├─ 记录总回合数、胜者、结束原因
  ├─ 记录每位玩家的最终排名、资产、是否破产
  └─ 记录最终状态快照 (final_snapshot)
       │
       ▼
更新用户统计 (user_stats)
  ├─ 胜者：total_wins += 1, win_streak += 1, score += 30
  ├─ 败者：win_streak = 0, score -= 10
  ├─ 破产者：total_bankruptcies += 1
  └─ 所有玩家：total_games += 1
       │
       ▼
更新房间状态
  ├─ room.status = "finished"
  ├─ 保留聊天记录（玩家可能继续聊）
  └─ 延迟 5 分钟后自动清理 GameState 和 Room
       │
       ▼
前端展示结算页
  ├─ 排名列表 + 资产统计
  ├─ [返回大厅] 按钮
  └─ [再来一局] 按钮（创建新房间，保留原房间玩家）
```

---

## 五、特殊机制详解

### 5.1 监狱机制

```
进入监狱的途径:
  ├─ 停在 GO_TO_JAIL (Tile 30) → 直接入狱
  ├─ 连续 3 次掷出双数 → 速度陷阱入狱
  └─ 卡片效果（C10 前进至监狱 / F06 入狱）

出狱方式:
  ├─ 掷出双数 → 免费出狱，按点数移动
  ├─ 支付保释金 50 → 出狱后正常掷骰移动
  ├─ 使用免罪卡 → 免费出狱，不消耗回合
  └─ 连续 3 回合未掷出双数 → 强制支付 50 并移动

监狱中的权限:
  ├─ ✅ 收取租金
  ├─ ✅ 建造/拆除房屋
  ├─ ✅ 抵押/赎回地产
  ├─ ✅ 参与拍卖
  ├─ ✅ 聊天
  └─ ❌ 主动移动（只能选择出狱方式）
```

### 5.2 破产机制

```
当玩家现金 < 需支付金额时:
       │
       ▼
进入"资产处理"阶段 (phase = BANKRUPTCY)
  ├─ 可选操作（限时 60 秒）:
  │   ├─ 出售房屋（返还半价）
  │   ├─ 抵押地产（获得购买价一半）
  │   └─ 与其他玩家交易（换取现金）
  │
       ▼
处理完毕后检查:
  ├─ 现金 ≥ 需支付 → 破产解除，继续游戏
  └─ 现金仍不足 → 确认破产
       │
       ▼
确认破产:
  ├─ 债权人为其他玩家:
  │   ├─ 所有现金转给债权人
  │   ├─ 所有地产转给债权人
  │   └─ 抵押地产也转给债权人（需后续赎回）
  │
  └─ 债权人为银行（税收/卡片罚款）:
      ├─ 所有地产变为无主
      ├─ 房屋被拆除
      └─ 地产进入拍卖

破产玩家:
  ├─ is_bankrupt = true
  ├─ 变为观战者，可继续聊天
  └─ 出现在玩家列表中（置灰）
```

### 5.3 拍卖机制

```
触发条件: 玩家放弃购买无主地产

拍卖流程:
  ├─ 服务器广播 game.auction_start
  │   { tile_id, start_price: 购买价×50%, min_increment: 10 }
  │
  ├─ 所有未破产玩家可出价
  │   ├─ 最低加价: 10
  │   ├─ 每次出价后 15 秒倒计时
  │   └─ 倒计时内无人加价 → 拍卖结束
  │
  ├─ 广播 game.auction_update（每次出价）
  │   { tile_id, current_bid, bidder_id }
  │
  └─ 广播 game.auction_end
      { tile_id, winner_id, final_price }

AI 拍卖策略:
  ├─ 简单: 50% 概率出价，上限为购买价 ×0.8，每次加价 10
  ├─ 中等: 上限为购买价 ×1.0，且需保留 ≥200 现金
  └─ 困难: ROI 规则评估，上限为购买价 ×1.3，且需保留 ≥100 现金
```

### 5.4 卡片事件机制

```
触发: 停在 CHANCE (Tile 7, 22, 36) 或 FATE (Tile 2, 17, 33)

抽卡流程:
  ├─ 从牌堆顶部取一张卡
  ├─ 广播 game.card_drawn { card_id, card_name, effect }
  ├─ 立即执行卡片效果
  └─ 使用后的卡放入弃牌堆

牌堆耗尽时:
  └─ 弃牌堆重新洗牌，作为新牌堆

特殊卡片 - 免罪卡 (C06, F05):
  ├─ 获得后存入 player.get_out_of_jail_cards
  ├─ 在监狱中可选择使用
  └─ 使用后放回对应牌堆底部
```

### 5.5 交易机制

```
触发: 自由行动阶段，玩家 A 向玩家 B 发起交易（game.trade_offer）

提议载荷:
  {
    target_id: B,                      // 交易对象
    offer:   { cash: int, properties: [tile_id, ...] },   // A 付出
    request: { cash: int, properties: [tile_id, ...] }    // A 索取
  }

服务端校验（不通过则静默丢弃，不生成提议）:
  ├─ phase != GAME_OVER 且 A、B 均未破产，A != B
  ├─ A.cash >= offer.cash 且 B.cash >= request.cash
  ├─ offer.properties 全部归 A 所有
  └─ request.properties 全部归 B 所有

提议登记:
  ├─ 服务端生成 trade_id（12 位 hex），写入 GameState.pending_trades
  ├─ 同一对玩家（A→B）的旧提议自动失效，仅保留最新一条
  ├─ 广播 game.trade_offer { trade_id, from_id, to_id, offer }
  └─ 定向推送 game.trade_received { trade_id, from_id, offer } 给 B

响应:
  ├─ B 发送 game.trade_accept { trade_id }
  │   ├─ 二次校验现金与地产归属（提议可能已过期）
  │   │   ├─ 现金不足 → 自动拒绝（reason=insufficient_cash）
  │   │   └─ 地产易主 → 自动拒绝（reason=property_changed）
  │   ├─ 现金双向结算 + 地产双向过户 + 从 pending_trades 移除
  │   └─ 广播 game.trade_completed { trade_id, from_id, to_id, offer, cash }
  │             game.trade_accept   { trade_id, from_id, to_id }
  │
  └─ B 拒绝 或 A 撤回（game.trade_reject { trade_id }）
      ├─ 移除提议，写回合日志 trade_reject（含 reason）
      └─ 广播 game.trade_reject { trade_id, from_id, to_id, reason }

约束:
  ├─ 交易不改变回合归属，不受掷骰/移动阶段影响
  ├─ 观战者与破产玩家不可发起、不可响应
  └─ 交易提议不设超时，跟随 GameState 存续于 Redis（TTL 24h）
```

---

## 六、AI 决策流程

### 6.1 AI 回合总流程

```
AI 回合开始
  │
  ├─ 1. 判断是否在监狱
  │     ├─ 有免罪卡 → 使用出狱
  │     ├─ 现金 > 200 → 支付保释金
  │     └─ 否则 → 掷骰子尝试双数
  │
  ├─ 2. 掷骰子（自动）
  │
  ├─ 3. 地块效果决策
  │     ├─ 无主地产 → decide_buy_property()
  │     ├─ 他人地产 → 自动支付租金
  │     └─ 卡片效果 → 自动执行
  │
  ├─ 4. 自由行动决策
  │     ├─ 是否升级地产
  │     ├─ 是否抵押/赎回
  │     └─ AI 不主动发起交易（引擎未实现 AI 发起交易）
  │
  └─ 5. 结束回合
```

### 6.2 AI 操作延迟

所有难度统一延迟 1-2s，模拟真人操作节奏。**难度差异仅体现在决策策略的复杂度**，不影响操作速度。

| 操作 | 延迟 | 说明 |
|------|------|------|
| 掷骰子 | 1-2s | 模拟思考时间 |
| 购买/拍卖决策 | 1-2s | 模拟考虑时间 |
| 自由行动 | 1-2s | 模拟操作时间 |

### 6.3 AI 购买决策

| 难度 | 策略 |
|------|------|
| easy | 50% 概率购买，不考虑策略 |
| medium | 规则评估：现金占比、垄断潜力，保留应急资金 200 |
| hard | ROI 规则：租金回报率 > 5% 且回本 < 10 回合则购买（**无蒙特卡洛 / Minimax 模拟**） |

---

## 七、WebSocket 消息流

### 7.1 完整一回合的消息流示例

```
[回合开始]
S → All: game.turn_change    { current_player_id: 8, turn_number: 1 }

[真人玩家掷骰]
C → S:   game.roll_dice      {}
S → All: game.dice_result    { dice: [3,5], total: 8, is_double: false }

[棋子移动]
S → All: game.player_moved   { player_id: 8, from: 0, to: 8, passed_go: false }

[停在无主地产 - 南京路]
S → All: game.tile_event     { event_type: "property_unowned", tile_id: 8, price: 100 }

[玩家选择购买]
C → S:   game.buy_property   { tile_id: 8 }
S → All: game.property_bought { player_id: 8, tile_id: 8, price: 100 }

[自由行动 - 建造房屋]
C → S:   game.build          { tile_id: 8 }
S → All: game.building_built { player_id: 8, tile_id: 8, level: 1 }

[结束回合]
C → S:   game.end_turn       {}
S → All: game.turn_change    { current_player_id: -1, turn_number: 1 }

[AI 回合 - 自动掷骰]
S → All: game.dice_result    { dice: [2,4], total: 6, is_double: false }
S → All: game.player_moved   { player_id: -1, from: 0, to: 6 }
S → All: game.tile_event     { event_type: "property_unowned", tile_id: 6, price: 100 }
S → All: game.property_bought { player_id: -1, tile_id: 6, price: 100 }
S → All: game.turn_change    { current_player_id: 8, turn_number: 2 }
```

### 7.2 心跳与断线

```
[连接握手 - 建立连接后首帧]
C → S:   { "room_id": "75873edb9a92" }        // 必须首帧发送，缺失则 4003 关闭
S → C:   state.snapshot  { 完整游戏状态, is_spectator }

[心跳 - 每 30 秒]
C → S:   system.ping         {}
S → C:   system.pong         {}

[玩家断线]
S → All: system.player_disconnected { player_id: 8, mode: "offline" }
         → 记录离线时刻，AI 暂代该玩家操作

[玩家重连]
C → S:   建立新 WebSocket 连接 + 首帧 { "room_id": ... }
S → C:   state.snapshot     { 完整游戏状态 }
S → All: system.player_reconnected { player_id: 8, mode, offline_seconds }
```

### 7.3 连接关闭码

| 关闭码 | 触发条件 |
|--------|----------|
| 4001 | token 无效 / 鉴权失败 |
| 4002 | 首帧消息格式错误（非合法 JSON） |
| 4003 | 首帧缺少 room_id |
| 4004 | 对局初始化失败（房间未开局 / 玩家不在房中） |
| 4005 | 对局状态不存在 |

---

## 八、数据存储策略

### 8.1 Redis 存储（活跃数据）

| Key | 类型 | TTL | 说明 |
|-----|------|-----|------|
| `room:{id}` | String (JSON) | 4h | 房间运行时状态 |
| `room:code:{code}` | String | 4h | code → id 映射 |
| `room:pwd:{id}` | String | 4h | 房间密码哈希（有密码时写入） |
| `room:list` | Set | - | 等待中的房间 ID 集合 |
| `game:{id}` | String (JSON) | 24h | 游戏状态（GameState） |
| `game:{id}:cards` | String (JSON) | 24h | 本局卡组（含弃牌堆状态） |
| `map:{map_id}` | String (JSON) | 1h | 地图模板缓存 |
| `chat:{room_id}` | Sorted Set | 24h | 聊天消息 |
| `chat:{room_id}:seq` | String | 24h | 聊天消息自增序号 |

### 8.2 PostgreSQL 存储（持久数据）

| 表 | 写入时机 | 说明 |
|----|----------|------|
| `game_records` | 游戏结束时 | 对局记录（配置快照、胜者、回合数、结束原因） |
| `game_players` | 游戏结束时 | 每位玩家的最终排名、资产、是否破产 |
| `game_turn_logs` | 每回合操作时 | 回合日志（骰子、操作类型、操作详情） |
| `user_stats` | 游戏结束时 | 用户统计（胜场、积分等） |

### 8.3 数据流转

```
游戏进行中:
  Redis (game:{id}) ←→ GameEngine ←→ WebSocket

游戏结束:
  Redis GameState → 生成 game_records + game_players → PostgreSQL
  Redis GameState → 清理
  Redis room:{id} → status="finished" → 延迟清理
```

---

## 九、异常与边界处理

### 9.1 回合超时

| 超时场景 | 处理方式 |
|----------|----------|
| 掷骰超时 (30s) | 自动掷骰 |
| 购买决策超时 (15s) | 默认放弃购买 |
| 自由行动超时 (30s) | 自动结束回合 |
| 拍卖出价超时 (15s) | 视为放弃出价 |
| 连续超时 3 次 | 标记断线，AI 暂代 |

### 9.2 断线重连

| 断线时长 | 恢复档位（`mode`） | 处理方式 |
|----------|-------------------|----------|
| 从未断开 | `reconnect`（无广播） | 玩家本就在线，仅复位连接标记，不广播 `system.player_reconnected` |
| ≤ 30s | `resume_incremental` | 复位连接标记；重连首帧仍为 `state.snapshot` 全量快照（档位名沿用代码 `reconnect_mode`，未实现字段级增量推送） |
| 30s ~ 3min | `resume_snapshot` | AI 暂代操作，重连后发送全量快照恢复 |
| > 3min | `left_game` | 判定退出，AI 持续代打至游戏结束 |

> 阈值常量：`RECONNECT_INCREMENT_WINDOW = 30`（秒）、`RECONNECT_AI_WINDOW = 180`（秒）。
> 断线时服务端调用 `mark_disconnected` 记录离线时刻；重连时 `mark_connected` 依据离线时长返回上述档位，并广播
> `system.player_reconnected { player_id, mode, offline_seconds }`，同时写入 `game_turn_logs`（操作类型 `reconnect`）。

### 9.3 并发安全

- 每个游戏房间使用 `asyncio.Lock` 串行处理操作
- 消息信封为 `{type, data, timestamp}`，**不含 `seq` 字段**；同一房间的操作由房间锁串行处理，不依赖序号去乱序
- Redis 操作使用 pipeline 保证原子性

### 9.4 游戏异常结束

| 场景 | 处理方式 |
|------|----------|
| 所有真人玩家断线 | AI 对战至结束，或 5 分钟后强制结束 |
| 服务器崩溃 | 从 Redis 恢复 GameState（Redis 持久化） |
| 房主断线 | AI 暂代房主，不销毁房间 |

---

## 十、地图数据库存储

### 10.1 设计思路

地图数据分为两层：

| 层次 | 存储位置 | 数据 | 读写频率 |
|------|----------|------|----------|
| **地图模板** | PostgreSQL | 地图定义（地块配置、租金表等），由管理员维护 | 低（只在创建/修改地图时写入） |
| **游戏状态** | Redis | 每局游戏中地块的实时状态（归属、建筑等级、抵押） | 高（每个回合多次读写） |

地图模板是"蓝图"，游戏状态是"实例"。一局游戏开始时，从 PostgreSQL 加载地图模板，初始化为 Redis 中的 GameState；游戏进行中只操作 Redis；游戏结束后，最终状态落库到 PostgreSQL。

### 10.2 数据库表设计

#### 10.2.1 maps — 地图表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | VARCHAR(32) | PK | 地图 ID（如 `classic`, `city`, `island`） |
| name | VARCHAR(50) | NOT NULL | 地图显示名称 |
| description | TEXT | NULL | 地图描述 |
| tile_count | SMALLINT | NOT NULL, DEFAULT 40 | 地块总数 |
| start_bonus | INT | NOT NULL, DEFAULT 200 | 经过起点奖励金额 |
| jail_bail | INT | NOT NULL, DEFAULT 50 | 保释金金额 |
| max_build_level | SMALLINT | NOT NULL, DEFAULT 5 | 最大建筑等级（0=空地, 5=酒店） |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | 是否启用 |
| created_at | DATETIME | DEFAULT NOW | 创建时间 |
| updated_at | DATETIME | DEFAULT NOW | 更新时间 |

#### 10.2.2 map_tiles — 地块配置表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | - |
| map_id | VARCHAR(32) | FK→maps.id | 所属地图 |
| position | SMALLINT | NOT NULL | 地块在棋盘上的位置（0-39） |
| name | VARCHAR(50) | NOT NULL | 地块名称（如"朝阳路"） |
| tile_type | VARCHAR(20) | NOT NULL | 地块类型枚举：START / PROPERTY / STATION / UTILITY / CHANCE / FATE / TAX / JAIL / PARKING / GO_TO_JAIL |
| tile_group | VARCHAR(20) | NULL | 地产分组：brown / light_blue / pink / orange / red / yellow / green / blue（仅 PROPERTY 类型） |
| group_color | VARCHAR(20) | NULL | 分组颜色（前端渲染用，与 tile_group 一一对应） |
| price | INT | NULL | 购买价格（仅 PROPERTY / STATION / UTILITY） |
| build_cost | INT | NULL | 每级建筑升级费用（仅 PROPERTY） |
| rent_0 | INT | NULL | 空地租金（建筑等级=0） |
| rent_1 | INT | NULL | 1栋房屋租金 |
| rent_2 | INT | NULL | 2栋房屋租金 |
| rent_3 | INT | NULL | 3栋房屋租金 |
| rent_4 | INT | NULL | 4栋房屋租金 |
| rent_5 | INT | NULL | 酒店租金 |
| tax_amount | INT | NULL | 税收金额（仅 TAX 类型） |
| tax_is_percent | BOOLEAN | DEFAULT FALSE | 税收是否为百分比（如 10%） |
| icon | VARCHAR(50) | NULL | 图标标识（前端渲染用） |
| description | VARCHAR(200) | NULL | 地块描述/提示文字 |

**唯一约束：** `UNIQUE(map_id, position)` — 同一地图内位置不重复

#### 10.2.3 map_station_rent — 车站租金阶梯表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | - |
| map_id | VARCHAR(32) | FK→maps.id | 所属地图 |
| owned_count | SMALLINT | NOT NULL | 拥有车站数量（1-4） |
| rent | INT | NOT NULL | 对应租金 |

**唯一约束：** `UNIQUE(map_id, owned_count)`

#### 10.2.4 map_utility_rent — 公共设施租金规则表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | - |
| map_id | VARCHAR(32) | FK→maps.id | 所属地图 |
| owned_count | SMALLINT | NOT NULL | 拥有设施数量（1-2） |
| dice_multiplier | INT | NOT NULL | 骰子倍率（1座=×4, 2座=×10） |

**唯一约束：** `UNIQUE(map_id, owned_count)`

#### 10.2.5 map_cards — 卡片配置表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | - |
| map_id | VARCHAR(32) | FK→maps.id | 所属地图 |
| card_type | VARCHAR(10) | NOT NULL | 卡片类型：CHANCE / FATE |
| card_id | VARCHAR(10) | NOT NULL | 卡片编号（如 C01, F05） |
| name | VARCHAR(50) | NOT NULL | 卡片名称 |
| effect_type | VARCHAR(30) | NOT NULL | 效果类型（见下方枚举） |
| effect_value | INT | NULL | 效果数值（金额、步数等） |
| description | VARCHAR(200) | NOT NULL | 卡片描述文字 |

**唯一约束：** `UNIQUE(map_id, card_type, card_id)`

**effect_type 枚举：**

| effect_type | 说明 | effect_value |
|-------------|------|-------------|
| move_to_position | 移动到指定位置 | 目标 position |
| move_forward | 前进 N 步 | 步数 |
| move_backward | 后退 N 步 | 步数 |
| move_to_nearest_station | 移动到最近车站 | - |
| gain_money | 获得金钱 | 金额 |
| lose_money | 失去金钱 | 金额 |
| pay_per_house | 按房屋数支付 | 每栋房屋金额（酒店按 effect_value×4 计算） |
| gain_from_all | 所有其他玩家向你支付 | 每人支付金额 |
| go_to_jail | 入狱 | - |
| get_out_of_jail | 获得免罪卡 | - |

### 10.3 表关系 ER 图

```
┌──────────────┐
│     maps     │
│──────────────│
│ id (PK)      │
│ name         │
│ tile_count   │
│ start_bonus  │
│ jail_bail    │
└──────┬───────┘
       │
       │ 1:N
       ├──────────────────────┬───────────────────────┬──────────────────────┐
       │                      │                       │                      |
       ▼                      ▼                       ▼                      ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  map_tiles   │    │map_station_rent  │    │ map_utility_rent │    │   map_cards      │
│──────────────│    │──────────────────│    │──────────────────│    │──────────────────│
│ id (PK)      │    │ id (PK)          │    │ id (PK)          │    │ id (PK)          │
│ map_id (FK)  │    │ map_id (FK)      │    │ map_id (FK)      │    │ map_id (FK)      │
│ position     │    │ owned_count      │    │ owned_count      │    │ card_type        │
│ name         │    │ rent             │    │ dice_multiplier  │    │ card_id          │
│ tile_type    │    └──────────────────┘    └──────────────────┘    │ name             │
│ tile_group   │                                                     │ effect_type      │
│ price        │                                                     │ effect_value     │
│ rent_0~5     │                                                     │ description      │
│ build_cost   │                                                     └──────────────────┘
│ tax_amount   │
└──────────────┘
```

### 10.4 classic 地图数据示例

#### maps 表

| id | name | tile_count | start_bonus | jail_bail |
|----|------|-----------|-------------|-----------|
| classic | 经典地图 | 40 | 200 | 50 |

#### map_tiles 表（40 条记录，map_id 均为 classic）

| map_id | position | name | tile_type | tile_group | price | rent_0 | rent_1 | rent_2 | rent_3 | rent_4 | rent_5 | build_cost |
|--------|----------|------|-----------|-----------|-------|--------|--------|--------|--------|--------|--------|-----------|
| classic | 0 | 起点 | START | - | - | - | - | - | - | - | - | - |
| classic | 1 | 朝阳路 | PROPERTY | brown | 60 | 4 | 20 | 60 | 180 | 320 | 450 | 50 |
| classic | 2 | 命运卡 | FATE | - | - | - | - | - | - | - | - | - |
| classic | 3 | 朝阳大道 | PROPERTY | brown | 60 | 4 | 20 | 60 | 180 | 320 | 450 | 50 |
| classic | 4 | 所得税 | TAX | - | - | - | - | - | - | - | - | - |
| classic | 5 | 北京站 | STATION | - | 200 | - | - | - | - | - | - | - |
| classic | 6 | 长安街 | PROPERTY | light_blue | 100 | 6 | 30 | 90 | 270 | 400 | 550 | 50 |
| classic | 7 | 机会卡 | CHANCE | - | - | - | - | - | - | - | - | - |
| classic | 8 | 南京路 | PROPERTY | light_blue | 100 | 6 | 30 | 90 | 270 | 400 | 550 | 50 |
| classic | 9 | 淮海路 | PROPERTY | light_blue | 120 | 8 | 40 | 100 | 300 | 450 | 600 | 50 |
| classic | 10 | 监狱 | JAIL | - | - | - | - | - | - | - | - | - |
| classic | 11 | 王府井 | PROPERTY | pink | 140 | 10 | 50 | 150 | 450 | 625 | 750 | 100 |
| classic | 12 | 电力公司 | UTILITY | - | 150 | - | - | - | - | - | - | - |
| classic | 13 | 西单 | PROPERTY | pink | 140 | 10 | 50 | 150 | 450 | 625 | 750 | 100 |
| classic | 14 | 东单 | PROPERTY | pink | 160 | 12 | 60 | 180 | 500 | 700 | 900 | 100 |
| classic | 15 | 上海站 | STATION | - | 200 | - | - | - | - | - | - | - |
| classic | 16 | 春熙路 | PROPERTY | orange | 180 | 14 | 70 | 200 | 550 | 750 | 950 | 100 |
| classic | 17 | 命运卡 | FATE | - | - | - | - | - | - | - | - | - |
| classic | 18 | 步行街 | PROPERTY | orange | 180 | 14 | 70 | 200 | 550 | 750 | 950 | 100 |
| classic | 19 | 中山路 | PROPERTY | orange | 200 | 16 | 80 | 220 | 600 | 800 | 1000 | 100 |
| classic | 20 | 免费停车 | PARKING | - | - | - | - | - | - | - | - | - |
| classic | 21 | 解放路 | PROPERTY | red | 220 | 18 | 90 | 250 | 700 | 875 | 1050 | 150 |
| classic | 22 | 机会卡 | CHANCE | - | - | - | - | - | - | - | - | - |
| classic | 23 | 人民路 | PROPERTY | red | 220 | 18 | 90 | 250 | 700 | 875 | 1050 | 150 |
| classic | 24 | 建设路 | PROPERTY | red | 240 | 20 | 100 | 300 | 750 | 925 | 1100 | 150 |
| classic | 25 | 广州站 | STATION | - | 200 | - | - | - | - | - | - | - |
| classic | 26 | 天河路 | PROPERTY | yellow | 260 | 22 | 110 | 330 | 800 | 975 | 1150 | 150 |
| classic | 27 | 珠江路 | PROPERTY | yellow | 260 | 22 | 110 | 330 | 800 | 975 | 1150 | 150 |
| classic | 28 | 自来水公司 | UTILITY | - | 150 | - | - | - | - | - | - | - |
| classic | 29 | 体育西路 | PROPERTY | yellow | 280 | 24 | 120 | 360 | 850 | 1025 | 1200 | 150 |
| classic | 30 | 去监狱 | GO_TO_JAIL | - | - | - | - | - | - | - | - | - |
| classic | 31 | 科技园 | PROPERTY | green | 300 | 26 | 130 | 390 | 900 | 1100 | 1275 | 200 |
| classic | 32 | 软件大道 | PROPERTY | green | 300 | 26 | 130 | 390 | 900 | 1100 | 1275 | 200 |
| classic | 33 | 命运卡 | FATE | - | - | - | - | - | - | - | - | - |
| classic | 34 | 金融街 | PROPERTY | green | 320 | 28 | 150 | 450 | 1000 | 1200 | 1400 | 200 |
| classic | 35 | 深圳站 | STATION | - | 200 | - | - | - | - | - | - | - |
| classic | 36 | 机会卡 | CHANCE | - | - | - | - | - | - | - | - | - |
| classic | 37 | 滨海大道 | PROPERTY | blue | 350 | 35 | 175 | 500 | 1100 | 1300 | 1500 | 200 |
| classic | 38 | 奢侈品税 | TAX | - | - | - | - | - | - | - | - | - |
| classic | 39 | 前海路 | PROPERTY | blue | 400 | 50 | 200 | 600 | 1400 | 1700 | 2000 | 200 |

#### map_station_rent 表

| map_id | owned_count | rent |
|--------|-------------|------|
| classic | 1 | 25 |
| classic | 2 | 50 |
| classic | 3 | 75 |
| classic | 4 | 100 |

#### map_utility_rent 表

| map_id | owned_count | dice_multiplier |
|--------|-------------|-----------------|
| classic | 1 | 4 |
| classic | 2 | 10 |

#### map_tiles 特殊字段补充

| map_id | position | tax_amount | tax_is_percent | description |
|--------|----------|-----------|----------------|-------------|
| classic | 4 | 200 | false | 所得税，支付 200 |
| classic | 38 | 100 | false | 奢侈品税，支付 100 |

#### map_cards 表（20 条记录，map_id 均为 classic）

| map_id | card_type | card_id | name | effect_type | effect_value | description |
|--------|-----------|---------|------|-------------|-------------|-------------|
| classic | CHANCE | C01 | 前进至起点 | move_to_position | 0 | 移动到起点，获得过路费 |
| classic | CHANCE | C02 | 前进至最近的车站 | move_to_nearest_station | - | 移动到下一车站，需付双倍租金 |
| classic | CHANCE | C03 | 前进三格 | move_forward | 3 | 向前移动 3 格 |
| classic | CHANCE | C04 | 银行分红 | gain_money | 150 | 从银行获得 150 |
| classic | CHANCE | C05 | 修理费 | pay_per_house | 25 | 每栋房屋支付 25，每家酒店支付 100 |
| classic | CHANCE | C06 | 出狱卡 | get_out_of_jail | - | 获得免罪卡，可随时使用出狱 |
| classic | CHANCE | C07 | 后退一格 | move_backward | 1 | 向后移动 1 格 |
| classic | CHANCE | C08 | 前进至朝阳路 | move_to_position | 1 | 移动到朝阳路 |
| classic | CHANCE | C09 | 被罚款 | lose_money | 40 | 支付 40 |
| classic | CHANCE | C10 | 前进至监狱 | go_to_jail | - | 直接进入监狱 |
| classic | FATE | F01 | 银行利息 | gain_money | 100 | 从银行获得 100 |
| classic | FATE | F02 | 医疗费用 | lose_money | 50 | 支付 50 |
| classic | FATE | F03 | 生日快乐 | gain_from_all | 20 | 每位其他玩家向你支付 20 |
| classic | FATE | F04 | 遗产继承 | gain_money | 200 | 从银行获得 200 |
| classic | FATE | F05 | 出狱卡 | get_out_of_jail | - | 获得免罪卡 |
| classic | FATE | F06 | 入狱 | go_to_jail | - | 直接进入监狱 |
| classic | FATE | F07 | 补缴税款 | pay_per_house | 40 | 每栋房屋支付 40，每家酒店支付 115 |
| classic | FATE | F08 | 彩票中奖 | gain_money | 500 | 从银行获得 500 |
| classic | FATE | F09 | 咨询费 | lose_money | 25 | 支付 25 |
| classic | FATE | F10 | 前进至起点 | move_to_position | 0 | 移动到起点，获得过路费 |

### 10.5 数据加载流程

```
游戏开始
   │
   ▼
从 PostgreSQL 加载地图模板
  ├─ SELECT * FROM maps WHERE id = 'classic'
  ├─ SELECT * FROM map_tiles WHERE map_id = 'classic' ORDER BY position
  ├─ SELECT * FROM map_station_rent WHERE map_id = 'classic' ORDER BY owned_count
  ├─ SELECT * FROM map_utility_rent WHERE map_id = 'classic' ORDER BY owned_count
  └─ SELECT * FROM map_cards WHERE map_id = 'classic'
       │
       ▼
缓存到 Redis（避免每局重复查库）
  └─ map:classic → 地图模板整体 JSON（基本信息 + 地块 + 车站租金 + 设施租金 + 卡片；键名 `map:{map_id}`，TTL=1h）
       │
       ▼
初始化 GameState（每局游戏实例）
  ├─ 从地图模板复制地块配置
  ├─ 所有地块 owner_id = null, build_level = 0
  ├─ 洗牌卡组
  └─ 存入 game:{room_id}
```

### 10.6 多地图扩展

创建新地图只需往 PostgreSQL 插入数据，无需改代码：

```sql
-- 创建新地图 "城市风云"
INSERT INTO maps (id, name, tile_count, start_bonus, jail_bail)
VALUES ('city', '城市风云', 40, 200, 50);

-- 插入地块配置（40 条）
INSERT INTO map_tiles (map_id, position, name, tile_type, ...) VALUES
('city', 0, '起点', 'START', ...),
('city', 1, '华尔街', 'PROPERTY', ...),
...;

-- 插入车站租金、设施租金、卡片
INSERT INTO map_station_rent ...
INSERT INTO map_utility_rent ...
INSERT INTO map_cards ...
```

前端在创建房间时选择 `map_id`，后端根据 `map_id` 加载对应地图模板初始化游戏。

### 10.7 租金计算伪代码

```python
def calculate_rent(tile: MapTile, owner: Player, game_state: GameState, dice_total: int) -> int:
    """计算租金"""

    if tile.tile_type == "PROPERTY":
        base_rent = [tile.rent_0, tile.rent_1, tile.rent_2,
                     tile.rent_3, tile.rent_4, tile.rent_5][tile.build_level]
        # 垄断加成：拥有同组全部地产且建筑等级=0
        if tile.build_level == 0 and owns_full_group(owner, tile.tile_group, game_state):
            return base_rent * 2
        return base_rent

    elif tile.tile_type == "STATION":
        station_count = count_owned_stations(owner, game_state)
        return station_rent_table[station_count]  # 从 map_station_rent 查询

    elif tile.tile_type == "UTILITY":
        utility_count = count_owned_utilities(owner, game_state)
        multiplier = utility_multiplier_table[utility_count]  # 从 map_utility_rent 查询
        return dice_total * multiplier

    else:
        return 0  # 非可购买地块无租金
```
*（内容由AI生成，仅供参考）*
