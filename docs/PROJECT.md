---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: ee1a9111a266e63ab5b365271262c0db_b28c3db9b58511f19ef152540024e231
    ReservedCode1: 4J3bgVMVgSFJWYk/RHyf+EPkdD76Aebo4PXoQltUYil+Kjg331S3g37941ORBpi4oKyuQKIxm2m+4/PKNOVBDPvzb4m5vA+y+F8jbMelLotEEQVDcP1W+xtAeT8QGcqxgVPLJ/Ge3tPFmHdaXvvLkz56xLOTUWtPdl5uZ0DeYXLGEZHcuUMCY6A8hcw=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: ee1a9111a266e63ab5b365271262c0db_b28c3db9b58511f19ef152540024e231
    ReservedCode2: 4J3bgVMVgSFJWYk/RHyf+EPkdD76Aebo4PXoQltUYil+Kjg331S3g37941ORBpi4oKyuQKIxm2m+4/PKNOVBDPvzb4m5vA+y+F8jbMelLotEEQVDcP1W+xtAeT8QGcqxgVPLJ/Ge3tPFmHdaXvvLkz56xLOTUWtPdl5uZ0DeYXLGEZHcuUMCY6A8hcw=
---

# GridGo 项目文档

> **版本口径**：统一使用 `APP_VERSION = "0.1.0"`（见 `gridgo-server/app/core/config.py`），全文不再出现 V1.0 / V1.5 / V2.0 等历史版本号。
> **最后更新**：2026-09-21
> **唯一依据**：本文档中的目录结构、接口路径、字段名、WS 消息类型、数据库表结构均逐项取自 `gridgo-server` / `gridgo-web` 当前源码；凡与代码冲突处，一律以代码为准。

---

## 目录

- [一、项目概述](#一项目概述)
- [二、功能清单（已实现 / 规划中）](#二功能清单已实现--规划中)
- [三、系统架构](#三系统架构)
- [四、目录结构](#四目录结构)
- [五、REST API 路径表](#五rest-api-路径表)
- [六、WebSocket 协议](#六websocket-协议)
- [七、数据库设计](#七数据库设计)
- [八、枚举与字段口径](#八枚举与字段口径)
- [九、环境变量](#九环境变量)
- [十、运行与部署](#十运行与部署)
- [十一、测试](#十一测试)
- [十二、已知限制与规划项](#十二已知限制与规划项)

---

## 一、项目概述

| 项目 | 说明 |
|------|------|
| 项目名称 | GridGo（大富翁） |
| 应用版本 | `0.1.0` |
| 项目类型 | 前后端分离的 Web 在线棋盘游戏 |
| 核心玩法 | 掷骰子、买地、收租、建造升级、抵押赎回、拍卖、事件卡、玩家交易 |
| 游戏模式 | 在线多人实时联机（REST + WebSocket），支持 AI 人机混战与观战 |
| 玩家规模 | 单房 1-8 人（`max_players` 默认 8，`GAME_MAX_PLAYERS=8`），AI 难度 easy / medium / hard |
| 单局上限 | `GAME_MAX_TURNS=100` 回合 |
| 部署方式 | 本地开发（venv + pnpm）与 Docker Compose（postgres / redis / server / web）双形态 |

---

## 二、功能清单（已实现 / 规划中）

> 判定标准：**已实现** = 代码中存在对应路由/服务/模型且接线完成；**规划中** = 代码中不存在实现（或仅存在数据表/依赖而无调用链）。

### 2.1 账号与用户（已实现）

| 功能 | 状态 | 实现位置 |
|------|:----:|----------|
| 注册 / 登录 / 刷新 Token / 登出 / 当前用户 | 已实现 | `app/api/v1/auth.py`、`app/services/auth.py`、`app/services/token.py` |
| 个人资料查询与修改、修改密码 | 已实现 | `app/api/v1/user.py` |
| 我的统计 / 我的对局 / 他人统计与对局 / 单局详情 | 已实现 | `app/api/v1/user.py`、`app/services/stats.py` |
| 好友列表 / 好友申请（发起、列表、同意拒绝、删除） | 已实现 | `app/api/v1/friend.py`、`app/services/friends.py` |
| 排行榜（按 `user_stats.score` 排序，分页） | 已实现 | `app/api/v1/leaderboard.py` |

### 2.2 房间（已实现）

| 功能 | 状态 | 说明 |
|------|:----:|------|
| 创建房间 / 房间列表 / 房间详情 | 已实现 | 房间状态以内存 + Redis 为运行权威源，`rooms` 表为写穿透镜像 |
| 6 位房间码查询（`/rooms/by-code/{code}`） | 已实现 | 房间码 `room_code` 唯一 |
| 加入（支持房号、密码校验）/ 离开 | 已实现 | 房主离开销毁房间 |
| 准备 / 取消准备 | 已实现 | 房主无需准备 |
| 切换角色（玩家 ↔ 观战者） | 已实现 | `is_spectator` 落库于 `room_players` |
| 房间设置（`PATCH /settings`，`PUT /config` 为兼容别名） | 已实现 | 同一 `UpdateRoomRequest` 模型 |
| 开始游戏（校验人数与准备状态） | 已实现 | 触发 `GameService.init_game` |
| 房间重置（回到等待态） | 已实现 | |

### 2.3 对局与回放（已实现）

| 功能 | 状态 | 说明 |
|------|:----:|------|
| 对局信息 / 完整状态（调试用）/ 对局日志 | 已实现 | `app/api/v1/game.py` |
| 投降结束对局 | 已实现 | `POST /games/{room_id}/surrender` |
| 回放数据获取（`GET /games/replay/{game_id}`） | 已实现 | `actions` 为压缩编码操作序列，见 `app/game/replay.py` |
| 用户历史对局 | 已实现 | `GET /games/history/{user_id}` |

### 2.4 游戏引擎（已实现）

| 功能 | 状态 | 说明 |
|------|:----:|------|
| 掷骰 / 双数再掷 / 连续 3 次双数入狱（speed_trap） | 已实现 | `app/game/engine.py` |
| 移动与经过起点奖励（`GAME_PASS_GO_BONUS=200`） | 已实现 | `game.pass_go` 单播给该玩家 |
| 地块效果：买地 / 放弃购买 / 跳过 | 已实现 | PROPERTY / STATION / UTILITY |
| 租金计算（垄断同组 ×2、车站按持有数、设施按骰子倍率） | 已实现 | `GameState.calculate_rent` |
| 拍卖（起拍、竞价、倒计时、成交/流拍） | 已实现 | `AuctionState`、`game.auction_*` 消息 |
| 建造 / 拆除 / 抵押 / 赎回 | 已实现 | 等级 0-5（`max_build_level=5`） |
| 税收格（固定额与百分比两种） | 已实现 | `tax_amount` / `tax_is_percent` |
| 机会卡 10 张（C01-C10）、命运卡 10 张（F01-F10） | 已实现 | 卡片数据见 `scripts/seed_classic_map.py`，效果见 `_execute_card_effect` |
| 监狱（保释金 50 / 免罪卡 / 双数出狱 / 回合数） | 已实现 | `jail_bail=50` |
| 破产判定、对局结算与统计更新 | 已实现 | `game.player_bankrupt`、`game.over`；破产为**直接出局结算**，无变卖资产自救流程 |
| 玩家间交易（现金 + 地块的报价、接受、拒绝、过期） | 已实现 | `TradeOffer`、`pending_trades` |
| 回合超时（`GAME_TURN_TIMEOUT=30` 秒）与超时自动动作 | 已实现 | engine 内部 asyncio 定时器 |
| AI 三种难度（EasyAI / MediumAI / HardAI） | 已实现 | `app/game/ai/player.py`、`AIPlayerFactory` |
| 断线重连（玩家连接/离线标记、重连恢复） | 已实现 | `system.player_reconnected` 等消息 |
| 对局结束原因：last_standing / turn_limit | 已实现 | `EndReason` 枚举；`vote_end` 仅枚举预留，当前无触发入口 |

### 2.5 实时通信（已实现）

| 功能 | 状态 | 说明 |
|------|:----:|------|
| 游戏 WebSocket（玩家与观战者共用端点） | 已实现 | `ws://<host>/ws/game?token=<access_token>` |
| 心跳（客户端 `system.ping` → 服务端 `system.pong`） | 已实现 | 单播回复，非广播 |
| 观战者只读限制（16 类操作被拦截） | 已实现 | `SPECTATOR_BLOCKED_TYPES` |
| 聊天（REST 拉取/发送 + WS 实时 `chat.send` / `chat.message`） | 已实现 | WS 发送后广播 `chat.message` |

### 2.6 前端（已实现）

| 功能 | 状态 | 说明 |
|------|:----:|------|
| 9 个页面（Home / Room / Game / Login / Register / Profile / Friends / Leaderboard / Replay） | 已实现 | `gridgo-web/src/pages` |
| Canvas 棋盘渲染 + GSAP 动画 | 已实现 | `src/game/renderer.ts`、`src/game/animations.ts` |
| Pinia 状态管理（user / room / game / replay） | 已实现 | `src/stores` |
| Element Plus + UnoCSS 界面体系 | 已实现 | `main.ts` 全量注册 Element Plus |
| 回放播放页（基于 `replayEngine.ts`） | 已实现 | `src/pages/Replay.vue` |
| 音效播放 | 规划中 | `howler` 依赖已安装，但 `src` 内无实际调用与音频资源 |
| 道具系统、赛季/段位、成就体系 | 规划中 | 后端无对应模型与接口 |
| 多地图拓展（city / island 等） | 规划中 | 表结构与 `map_id` 链路已就绪，当前仅内置 `classic` 一张地图数据（`scripts/seed_classic_map.py`），其余地图 ID 仅出现在模型注释示例中 |

---

## 三、系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                     浏览器（Vue 3 SPA）                       │
│   Canvas 2D 棋盘渲染 · Pinia 状态 · Axios(REST) · WS 客户端    │
└───────────────┬──────────────────────────────┬───────────────┘
                │ /api/**                      │ /ws/game
        ┌───────▼────────┐             ┌───────▼────────┐
        │ 本地：Vite 3000 │             │ 同左（proxy ws）│
        │ 容器：Nginx 80  │             │                │
        └───────┬────────┘             └───────┬────────┘
                │ 反向代理 /api、/ws            │
        ┌───────▼──────────────────────────────▼────────┐
        │        FastAPI（uvicorn，端口 8001）            │
        │  api/v1（REST）   api/ws（WebSocket）          │
        │  services（业务） game（引擎/AI/回放）          │
        └───────┬──────────────────────────────┬────────┘
                │ SQLAlchemy 2.0 (asyncpg)     │ redis-py (async)
        ┌───────▼────────┐             ┌───────▼────────┐
        │ PostgreSQL 16  │             │  Redis 7.x     │
        │  5432 / 3307   │             │  6379 / 6380   │
        │  持久化存储      │             │ 运行时房间与对局状态 │
        └────────────────┘             └────────────────┘
```

**架构要点**

- **权威服务器**：对局状态以后端为唯一真源，前端只负责渲染与发送操作意图。
- **运行时状态放 Redis**：`game:{room_id}` 存 `GameState`（JSON），`room:{id}` 存房间运行时数据；PostgreSQL 承担用户、房间镜像、对局记录与统计的持久化。
- **双协议分工**：REST 负责认证、用户、房间、历史与回放查询；WebSocket 负责对局内的实时操作与广播。
- **Docker 拓扑**：`web`（Nginx，80）反代 `/api/`、`/ws/` 到 `server`（8001）；本地开发由 Vite dev server（3000）代理到 8001。

---

## 四、目录结构

### 4.1 仓库根目录

```
E:\Project\GridGo\
├── README.md                 # 快速上手（环境变量、启动、端点简表、WS 示例）
├── clear8001.md              # 8001 端口占用排查与清理说明（运维）
├── docker-compose.yml        # 四服务编排：postgres / redis / server / web
├── docker/
│   ├── .env.docker           # Docker 环境变量模板
│   └── postgres/             # PostgreSQL 初始化目录（建库由镜像自动完成）
├── docs/
│   ├── PROJECT.md            # 本文档（项目主文档）
│   ├── GAME_FLOW.md          # 完整对局流程
│   └── TECH_STACK.md         # 技术选型
├── gridgo-server/            # 后端（FastAPI）
├── gridgo-web/               # 前端（Vue 3 + Vite）
├── start.bat                 # 一键本地启动（后端 8001 + 前端 3000）
└── stop.bat                  # 一键停止本地服务
```

### 4.2 后端 `gridgo-server`

```
gridgo-server/
├── alembic/
│   └── versions/             # 5 个迁移版本（users → rooms/stats/friends → map → game_records → actions/settlement）
├── alembic.ini
├── app/
│   ├── main.py               # FastAPI 实例、路由注册（prefix=/api/v1）、中间件、健康检查
│   ├── api/
│   │   ├── middleware/access_log.py
│   │   ├── v1/               # auth.py / chat.py / friend.py / game.py / leaderboard.py / room.py / user.py
│   │   └── ws/game_ws.py     # 游戏 WebSocket 端点与消息路由
│   ├── core/                 # config.py / database.py / deps.py / logging.py / redis.py / security.py
│   ├── game/
│   │   ├── engine.py         # 游戏主引擎（回合机、地块、拍卖、交易、破产、结算）
│   │   ├── events.py         # WebSocket 连接管理与广播
│   │   ├── replay.py         # 操作序列压缩编码 / 回放
│   │   ├── schemas.py        # GameState / PlayerState / TileState / 枚举
│   │   └── ai/player.py      # BaseAIPlayer / EasyAI / MediumAI / HardAI / AIPlayerFactory
│   ├── models/               # user.py / room.py / stats.py / friend.py / game_record.py / map.py
│   ├── schemas/              # 各模块 Pydantic 请求响应模型
│   ├── services/             # auth / chat / friends / game / map / room / stats / token
│   └── utils/
├── scripts/seed_classic_map.py   # classic 地图与卡片数据种子
├── tests/
│   ├── unit/                 # 引擎规则、重连、交易结算契约、回合日志、WS 协议契约、迁移
│   └── integration/test_ai_full_game.py
├── requirements.txt
├── pyproject.toml
├── .env.example
└── Dockerfile
```

### 4.3 前端 `gridgo-web`

```
gridgo-web/
├── src/
│   ├── api/                  # rest.ts / ws.ts / auth.ts / room.ts / chat.ts / friend.ts / user.ts / leaderboard.ts / replay.ts
│   ├── assets/
│   ├── components/
│   │   ├── board/            # GameBoard.vue / TileDetailDialog.vue
│   │   ├── card/             # AuctionPanel.vue / ChanceCard.vue / DicePanel.vue
│   │   ├── common/           # ChatPanel / EmptyState / GameOverDialog / LogPanel / PageHeader / StatCard
│   │   └── player/           # PlayerPanel.vue / TradePanel.vue
│   ├── composables/          # useGame / useChat / useWebSocket / useAnimation
│   ├── game/                 # renderer.ts / entities.ts / board.ts / animations.ts / replayEngine.ts
│   ├── layouts/              # DefaultLayout.vue / GameLayout.vue
│   ├── pages/                # Home / Room / Game / Login / Register / Profile / Friends / Leaderboard / Replay .vue
│   ├── router/index.ts
│   ├── stores/               # user.ts / room.ts / game.ts / replay.ts
│   ├── styles/               # index.css / theme.css
│   ├── types/                # api.ts / game.ts / index.ts
│   ├── utils/                # format.ts / ws.ts
│   ├── App.vue
│   ├── env.d.ts              # Vite 类型声明
│   └── main.ts
├── index.html
├── nginx.conf                # 容器 Nginx 配置（反代 /api、/ws）
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── uno.config.ts
├── vite.config.ts
├── vitest.config.ts
└── Dockerfile
```

> **构建约定**：`src` 下 `*.vue` 与 `*.ts` 为唯一源码形态，不保留 `.js` 编译产物；所有内部导入统一使用 `@/` 别名或省略扩展名的相对路径，避免模块解析优先级歧义。

---

## 五、REST API 路径表

**Base URL**

| 场景 | 前缀 |
|------|------|
| 直连后端 | `http://localhost:8001/api/v1` |
| 本地前端（Vite 代理） | `http://localhost:3000/api/v1` |
| Docker（Nginx 代理） | `http://localhost/api/v1` |

**鉴权**：除标注「公开」外，均需请求头 `Authorization: Bearer <access_token>`。

### 5.1 认证 `/auth`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| POST | `/auth/register` | 注册（201） | 公开 |
| POST | `/auth/login` | 登录，返回 access + refresh | 公开 |
| POST | `/auth/refresh` | 刷新 Token | 公开（凭 refresh_token） |
| POST | `/auth/logout` | 登出（Token 加入黑名单） | 需要 |
| GET | `/auth/me` | 当前用户简要信息 | 需要 |

### 5.2 用户 `/users`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/users/me` | 当前用户详细资料 | 需要 |
| PATCH | `/users/me` | 修改昵称 / 头像 / 邮箱 | 需要 |
| POST | `/users/me/change-password` | 修改密码 | 需要 |
| GET | `/users/me/stats` | 我的统计 | 需要 |
| GET | `/users/me/records` | 我的对局记录（`limit` ≤100，`offset`） | 需要 |
| GET | `/users/records/{game_id}` | 单局详情（含各玩家结算） | 需要 |
| GET | `/users/{user_id}/stats` | 指定用户统计 | 公开 |
| GET | `/users/{user_id}/records` | 指定用户对局记录 | 公开 |

### 5.3 房间 `/rooms`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/rooms` | 等待中的房间列表 | 公开 |
| POST | `/rooms` | 创建房间（201） | 需要 |
| GET | `/rooms/by-code/{code}` | 按 6 位房间码查询 | 公开 |
| GET | `/rooms/{room_id}` | 房间详情 | 公开 |
| POST | `/rooms/join` | 加入房间（房号或房间 ID，可带密码） | 需要 |
| POST | `/rooms/{room_id}/leave` | 离开房间（房主离开销毁房间） | 需要 |
| POST | `/rooms/{room_id}/ready` | 准备 / 取消准备 | 需要 |
| POST | `/rooms/{room_id}/switch-role` | 切换玩家 ↔ 观战者 | 需要 |
| PATCH | `/rooms/{room_id}/settings` | 更新房间设置 | 需要（房主） |
| PUT | `/rooms/{room_id}/config` | 兼容别名，语义同 `PATCH /settings` | 需要（房主） |
| POST | `/rooms/{room_id}/start` | 开始游戏 | 需要（房主） |
| POST | `/rooms/{room_id}/reset` | 重置房间到等待态 | 需要（房主） |

> **路由匹配注意**：`GET /rooms/by-code/{code}` 先于 `GET /rooms/{room_id}` 注册，房间码查询不会落入房间 ID 分支。

### 5.4 对局 `/games`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/games/{room_id}` | 对局信息 | 公开 |
| GET | `/games/{room_id}/state` | 完整游戏状态（调试用） | 公开 |
| GET | `/games/{room_id}/log` | 对局日志（读已结束对局的 `game_records`） | 公开 |
| POST | `/games/{room_id}/surrender` | 投降 | 需要 |
| GET | `/games/replay/{game_id}` | 回放数据（配置快照 + 操作序列 + 最终快照） | 公开 |
| GET | `/games/history/{user_id}` | 用户历史对局（`limit` 默认 20） | 公开 |

### 5.5 聊天 `/rooms/{room_id}/chat`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/rooms/{room_id}/chat` | 拉取消息，游标 `before`（消息 ID） | 公开 |
| POST | `/rooms/{room_id}/chat` | 发送消息（201） | 需要 |

### 5.6 好友 `/friends`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/friends` | 好友列表 | 需要 |
| GET | `/friends/requests` | 待处理好友申请 | 需要 |
| POST | `/friends/requests` | 发起好友申请（201） | 需要 |
| POST | `/friends/requests/{request_id}/respond` | 同意 / 拒绝申请 | 需要 |
| DELETE | `/friends/{friend_id}` | 删除好友 | 需要 |

### 5.7 排行榜 `/leaderboard`

| 方法 | 路径 | 说明 | 鉴权 |
|------|------|------|------|
| GET | `/leaderboard` | 榜单（`limit` 1-100 默认 50，`offset`） | 公开 |

---

## 六、WebSocket 协议

### 6.1 端点与握手

| 场景 | 地址 |
|------|------|
| 直连后端 | `ws://localhost:8001/ws/game?token=<access_token>` |
| 本地前端（Vite 代理，ws:true） | `ws://localhost:3000/ws/game?token=<access_token>` |
| Docker（Nginx 代理） | `ws://localhost/ws/game?token=<access_token>` |

握手流程（与 `app/api/ws/game_ws.py` 实现一致）：

1. 客户端携带 `token` 查询参数发起连接；服务端通过 `AuthService.get_current_user` 鉴权，失败即以关闭码 `4001` 断开。
2. 服务端 `accept` 后等待客户端**首帧消息**，首帧 JSON 必须包含 `room_id` 字段（服务端只取该字段，不校验 `type`）；格式错误 → `4002`，缺少 `room_id` → `4003`。
3. 服务端调用 `GameService.ensure_game_initialized` 确保对局已初始化：初始化失败 → `4004`（携带异常文案），对局状态不存在 → `4005`。
4. 连接注册进房间广播组，随后**单播**下发首帧 `state.snapshot`（`data` 内含 `is_spectator` 标识）。
5. 复位玩家连接标记并恢复后台任务（AI 回合、超时计时器等），广播 `system.player_connected` / `system.spectator_connected`（排除自身）。
6. 断线时广播 `system.player_disconnected` / `system.spectator_disconnected`，并记录离线时刻用于重连档位判定。

**关闭码**

| 码 | 含义 |
|----|------|
| 4001 | 认证失败（Token 无效） |
| 4002 | 初始化消息格式错误 |
| 4003 | 首帧缺少 `room_id` |
| 4004 | 对局初始化失败（如房间未开始） |
| 4005 | 游戏状态不存在 |

### 6.2 上行消息（客户端 → 服务端）

| 类型 | 说明 |
|------|------|
| `system.ping` | 心跳，服务端单播回 `system.pong` |
| `game.roll_dice` | 掷骰子 |
| `game.buy_property` | 购买当前地块 |
| `game.decline_property` | 放弃购买（别名 `game.decline_buy`） |
| `game.skip_property` | 跳过当前地块 |
| `game.auction_bid` | 拍卖出价 |
| `game.auction_start` | 兼容占位：服务端忽略（拍卖由服务端在玩家放弃购买后自动广播） |
| `game.build` | 建造升级 |
| `game.demolish` | 拆除建筑 |
| `game.mortgage` | 抵押地产 |
| `game.redeem` | 赎回地产 |
| `game.end_turn` | 结束回合 |
| `game.jail_pay_bail` | 支付保释金（别名 `game.jail_pay`） |
| `game.jail_use_card` | 使用免罪卡 |
| `game.trade_offer` | 发起交易报价 |
| `game.trade_accept` | 接受交易 |
| `game.trade_reject` | 拒绝交易 |
| `chat.send` | 发送聊天消息 |

**文档历史别名归一**（`ALIAS_TYPES`，服务端统一映射到规范类型）：

| 历史别名 | 规范类型 |
|----------|----------|
| `game.decline_buy` | `game.decline_property` |
| `game.jail_pay` | `game.jail_pay_bail` |

**观战者被拦截的操作类型**（`SPECTATOR_BLOCKED_TYPES`，共 16 项）：
`game.roll_dice`、`game.buy_property`、`game.decline_property`、`game.skip_property`、`game.auction_bid`、`game.build`、`game.demolish`、`game.mortgage`、`game.redeem`、`game.end_turn`、`game.jail_pay_bail`、`game.jail_use_card`、`game.trade_offer`、`game.trade_accept`、`game.trade_reject`、`chat.send`。

### 6.3 下行消息（服务端 → 客户端）

| 类型 | 说明 | 发送方式 |
|------|------|----------|
| `state.snapshot` | 连接建立后的首帧完整状态（含 `is_spectator`） | 单播 |
| `state.update` | 每次状态落盘后广播的完整状态 | 广播 |
| `game.turn_change` | 回合切换：`current_player_id` / `current_player_nickname` / `turn_number` / `is_ai` | 广播 |
| `game.dice_result` | 掷骰结果：`player_id` / `dice` / `total` / `is_double`（三连双入狱时附 `speed_trap=true`） | 广播 |
| `game.extra_roll` | 双数获得额外掷骰：`player_id` / `reason="double"` | 广播 |
| `game.player_moved` | 移动结果：`player_id` / `from` / `to` / `steps` / `passed_go` | 广播 |
| `game.pass_go` | 经过起点奖励（单播给受益玩家） | 单播 |
| `game.tile_event` | 停在无主/可操作地块，等待决策 | 广播 |
| `game.property_bought` | 购地成功 | 广播 |
| `game.property_declined` / `game.property_skipped` | 放弃购买 / 跳过地块 | 广播 |
| `game.rent_paid` | 支付租金 | 广播 |
| `game.tax_paid` | 缴纳税款 | 广播 |
| `game.card_drawn` | 抽到机会/命运卡（含 `effect_type` / 描述） | 广播 |
| `game.get_out_of_jail_card` | 获得免罪卡 | 广播 |
| `game.jail_sent` | 入狱 | 广播 |
| `game.jail_released` | 出狱 | 广播 |
| `game.money_change` | 现金变动（含 `amount` / `cash` / `reason`） | 广播 |
| `game.building_built` / `game.building_demolished` | 建造 / 拆除 | 广播 |
| `game.property_mortgaged` / `game.property_redeemed` | 抵押 / 赎回 | 广播 |
| `game.auction_start` / `game.auction_update` / `game.auction_end` | 拍卖开始 / 出价更新 / 结束 | 广播 |
| `game.trade_offer` | 交易报价（广播给全房） | 广播 |
| `game.trade_received` | 交易报价定向投递给被报价方 | 单播 |
| `game.trade_accept` / `game.trade_reject` / `game.trade_completed` | 交易接受 / 拒绝 / 完成 | 广播 |
| `game.player_bankrupt` | 玩家破产 | 广播 |
| `game.over` | 对局结束：`end_reason` / `winner_id` / `rankings` / `total_turns` / `game_record_id` | 广播 |
| `chat.message` | 聊天消息（WS 发送后由服务端广播） | 广播 |
| `system.player_connected` / `system.player_disconnected` | 玩家上线 / 掉线 | 广播 |
| `system.player_reconnected` | 玩家重连（此前被判离线） | 广播 |
| `system.spectator_connected` / `system.spectator_disconnected` | 观战者进入 / 离开 | 广播 |
| `system.pong` | 心跳响应 | 单播 |
| `system.error` | 错误通知（前端已订阅） | 广播 |

> 消息信封统一为 `{"type": "...", "data": {...}, "timestamp": <毫秒>}`；服务端不产生 `seq` 字段。

### 6.4 连接示例（wscat / wscat 兼容客户端）

```
# 1. 登录取得 access_token 后建立连接
ws://localhost:8001/ws/game?token=eyJhbGciOi...

# 2. 首帧：声明加入哪个房间（只校验 room_id）
{"type": "join", "data": {"room_id": "75873edb9a92"}}

# 3. 服务端首帧回包
{"type": "state.snapshot", "data": {"game_id": "...", "phase": "TURN_START", "is_spectator": false, "players": [...], "tiles": [...]}, "timestamp": 1758380000000}

# 4. 心跳
{"type": "system.ping", "data": {}}
{"type": "system.pong", "data": {}, "timestamp": 1758380001000}

# 5. 掷骰（当前回合玩家）
{"type": "game.roll_dice", "data": {}}
{"type": "game.dice_result", "data": {"player_id": 8, "dice": [3, 5], "total": 8, "is_double": false}, "timestamp": 1758380001200}
```

---

## 七、数据库设计

**迁移管理**：Alembic，`alembic/versions` 共 5 个版本，按序为：

| 顺序 | 版本文件 | 内容 |
|:----:|----------|------|
| 1 | `f114bfc602d4_create_users_table.py` | `users` |
| 2 | `b7c1d9e4a2f8_create_rooms_stats_friends_tables.py` | `rooms` / `room_players` / `user_stats` / `friendships` |
| 3 | `234927b3e0cc_create_map_tables.py` | `maps` / `map_tiles` / `map_station_rent` / `map_utility_rent` / `map_cards` |
| 4 | `36c5dd26aae6_create_game_records_tables.py` | `game_records` / `game_players` / `game_turn_logs` |
| 5 | `a1b2c3d4e5f6_add_actions_and_settlement_to_game_records.py` | `game_records.actions`、`game_players.settlement_amount` |

### 7.1 用户与统计

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `users` | `id`(BIGINT PK) / `username`(唯一) / `password_hash` / `nickname` / `avatar` / `email`(唯一) / `status`(0=正常 1=禁用) / `created_at` / `updated_at` | 账号主表 |
| `user_stats` | `user_id`(PK) / `total_games` / `total_wins` / `total_bankruptcies` / `total_rent_collected` / `total_rent_paid` / `best_rank` / `win_streak` / `best_win_streak` / `score` / `updated_at` | 排行榜排序依据为 `score` |

### 7.2 房间

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `rooms` | `id`(VARCHAR(32) PK) / `room_code`(唯一，6 位) / `name` / `host_id` / `password_hash` / `max_players`(默认 8) / `map_id`(默认 classic) / `ai_count` / `ai_difficulty` / `status`(0=等待 1=游戏中 2=已结束) / `config`(JSON) / 时间戳 | Redis 运行时状态的写穿透镜像；索引 `ix_rooms_status` |
| `room_players` | `id` / `room_id` / `user_id`(AI 为负数) / `nickname` / `is_host` / `is_ready` / `is_ai` / `ai_difficulty` / `is_spectator` / `joined_at` | 唯一约束 `(room_id, user_id)`，索引 `ix_room_players_room_id` |

### 7.3 对局与结算

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `game_records` | `id` / `room_id` / `map_id` / `total_turns` / `player_count` / `winner_id`(AI 为负) / `end_reason`(last_standing / turn_limit / vote_end) / `config_snapshot` / `actions`(压缩编码) / `final_snapshot` / `created_at` | 单局主记录 |
| `game_players` | `id` / `game_id` / `user_id` / `nickname` / `rank` / `total_assets` / `settlement_amount`(正=盈利 负=亏损) / `is_bankrupt` / `is_ai` / `ai_difficulty` | 单局内每位玩家结算 |
| `game_turn_logs` | `id` / `game_id` / `turn_number` / `player_id` / `action_type` / `action_data`(JSON) / `dice_values`(如 `3,5`) / `created_at` | 回合级操作日志 |

### 7.4 好友

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `friendships` | `id` / `user_id`(发起方) / `friend_id`(接收方) / `status`(SmallInteger) / `created_at` / `updated_at` | 唯一约束 `(user_id, friend_id)`，索引 `ix_friendships_friend_id` |

### 7.5 地图（数据驱动）

| 表 | 关键字段 | 说明 |
|----|----------|------|
| `maps` | `id`(PK，如 classic) / `name` / `description` / `tile_count`(默认 40) / `start_bonus`(默认 200) / `jail_bail`(默认 50) / `max_build_level`(默认 5) / `is_active` | 地图模板 |
| `map_tiles` | `map_id`(FK) / `position`(0-39) / `name` / `tile_type` / `tile_group` / `group_color` / `price` / `build_cost` / `rent_0`…`rent_5` / `tax_amount` / `tax_is_percent` / `icon` / `description` | 唯一约束 `(map_id, position)` |
| `map_station_rent` | `map_id` / `owned_count`(1-4) / `rent` | 唯一约束 `(map_id, owned_count)` |
| `map_utility_rent` | `map_id` / `owned_count`(1-2) / `dice_multiplier` | 唯一约束 `(map_id, owned_count)` |
| `map_cards` | `map_id` / `card_type`(CHANCE / FATE) / `card_id`(如 C01、F05) / `name` / `effect_type` / `effect_value` / `description` | 唯一约束 `(map_id, card_type, card_id)` |

**Redis 键命名**（运行时状态）

| 键 | 内容 |
|----|------|
| `room:{room_id}` | 房间运行时状态 |
| `room:code:{room_code}` | 房间码 → 房间 ID 映射 |
| `room:pwd:{room_id}` | 房间密码校验 |
| `room:list` | 等待中房间列表 |
| `game:{room_id}` | `GameState` 完整状态（JSON） |
| `game:{room_id}:cards` | 本局卡组 |
| `chat:{room_id}` / `chat:{room_id}:seq` | 房间聊天消息与序号 |
| `map:{map_id}` | 地图模板缓存 |
| `token:access:{jti}` / `token:refresh:{user_id}` / `token:blacklist:{jti}` | Token 会话与黑名单 |

---

## 八、枚举与字段口径

### 8.1 对局阶段 `GamePhase`

`TURN_START`、`WAIT_ROLL`、`ROLLING`、`MOVING`、`TILE_EFFECT`、`WAIT_DECISION`、`FREE_ACTION`、`TURN_END`、`AUCTION`、`BANKRUPTCY`、`GAME_OVER`

> 代码中**不存在** `RESOLVED` 阶段，决策结果直接由 `WAIT_DECISION` 流转至 `FREE_ACTION` / `TURN_END`。

### 8.2 地块类型 `TileType`

`START`、`PROPERTY`、`STATION`、`UTILITY`、`CHANCE`、`FATE`、`TAX`、`JAIL`、`PARKING`、`GO_TO_JAIL`

### 8.3 结束原因 `EndReason`

| 值 | 含义 |
|----|------|
| `last_standing` | 仅剩一名未破产玩家 |
| `turn_limit` | 达到回合上限（`max_turns` 默认 100） |
| `vote_end` | 投票结束（枚举预留，当前无触发入口；投降走破产结算，不产生该值） |

### 8.4 AI 难度与玩家标识

| 字段 | 取值 | 说明 |
|------|------|------|
| `ai_difficulty` | `easy` / `medium` / `hard` | 对应 `EasyAI` / `MediumAI` / `HardAI`，工厂 `AIPlayerFactory.available_difficulties()` |
| `user_id` | 正数=真人，负数=AI | `game_records.winner_id`、`game_players.user_id` 同口径 |
| `is_spectator` | 布尔 | 观战者仅接收，不能发送被拦截的 16 类操作 |

### 8.5 卡片效果 `effect_type`

| 值 | 语义 | 参数 |
|----|------|------|
| `move_to_position` | 移动到指定格（可收过路费） | `effect_value` = 目标 position |
| `move_forward` | 前进 N 格 | N |
| `move_backward` | 后退 N 格（不收过路费） | N |
| `move_to_nearest_station` | 移动到最近车站，需付双倍租金 | — |
| `gain_money` | 从银行获得 | 金额 |
| `lose_money` | 向银行支付 | 金额 |
| `pay_per_house` | 按房屋/酒店数量支付 | 单栋金额（酒店按更高档） |
| `gain_from_all` | 其他每位玩家支付给本人 | 单人金额 |
| `go_to_jail` | 直接入狱 | — |
| `get_out_of_jail` | 获得免罪卡 | — |

**内置卡组**：机会卡 `C01`-`C10`、命运卡 `F01`-`F10`（名称、效果与数值以 `scripts/seed_classic_map.py` 为准）。

### 8.6 租金与资产口径

- **垄断加成**：拥有同组全部地块且建筑等级为 0 时，租金 ×2。
- **车站**：按持有数量查 `map_station_rent`。
- **设施**：租金 = 骰子点数 × `map_utility_rent.dice_multiplier`（1 座 ×4、2 座 ×10）。
- **总资产**：`calculate_total_assets = 现金 + 地产价值 + 建筑投入`（已抵押地产按规则折价），用于排名与结算。
- **结算金额**：`settlement_amount = 最终总资产 - 初始资金(1500)`，正值盈利、负值亏损。

---

## 九、环境变量

### 9.1 后端（`gridgo-server/.env`，模板见 `.env.example`）

| 变量 | 代码默认值（`app/core/config.py`） | 说明 |
|------|-----------------------------------|------|
| `APP_NAME` | `GridGo` | 应用名 |
| `APP_VERSION` | `0.1.0` | 版本口径（文档与前端展示统一使用） |
| `DEBUG` | `True` | 调试开关 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `8001` | 服务端口 |
| `DATABASE_URL` | `postgresql+asyncpg://gridgo:gridgo123@127.0.0.1:3307/gridgo` | PostgreSQL 连接串 |
| `DATABASE_ECHO` | `False` | SQL 回显 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `JWT_SECRET_KEY` | `gridgo-secret-key-change-in-production` | 生产必须修改 |
| `JWT_ALGORITHM` | `HS256` | 签名算法 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440`（1 天） | 注意 `.env.example` 示例值为 `60`，以实际 `.env` 为准 |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | 刷新 Token 有效期 |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | 允许来源（JSON 数组） |
| `GAME_INITIAL_CASH` | `1500` | 初始现金 |
| `GAME_PASS_GO_BONUS` | `200` | 经过起点奖励 |
| `GAME_TURN_TIMEOUT` | `30` | 回合超时（秒） |
| `GAME_MAX_PLAYERS` | `8` | 单房最大玩家数 |
| `GAME_MAX_TURNS` | `100` | 单局最大回合数 |

### 9.2 Docker（`docker/.env.docker`）

| 变量 | 值 | 说明 |
|------|-----|------|
| `POSTGRES_PASSWORD` | `gridgo123` | PostgreSQL 密码 |
| `POSTGRES_PORT` | `3307` | 宿主机映射端口（宿主 3307 → 容器 5432） |
| `REDIS_PORT` | `6380` | 宿主机映射端口（避开本机 6379） |
| `SERVER_PORT` | `8001` | 后端映射端口 |
| `WEB_PORT` | `80` | 前端 Nginx 映射端口 |
| `JWT_*` | 同后端 | 容器内 JWT 配置 |
| `CORS_ORIGINS` | `["http://localhost","http://localhost:80","http://localhost:3000"]` | 容器场景来源 |
| `GAME_*` | 同后端 | 游戏参数 |

### 9.3 前端

前端通过相对路径 `/api`、`/ws` 访问后端，**无需环境变量**；开发环境由 `vite.config.ts` 代理到 `http://localhost:8001`，容器环境由 Nginx 反代。

---

## 十、运行与部署

完整命令与环境要求见仓库根目录 [README.md](../README.md)，此处仅列形态：

| 形态 | 入口 | 说明 |
|------|------|------|
| 本地一键启动 | `start.bat` | 检查 Python/Node/pnpm → 建 venv 装依赖 → 并行启动后端（8001）与前端（3000） |
| 本地一键停止 | `stop.bat` | 结束 8001 / 3000 端口进程 |
| 手动后端 | `uvicorn app.main:app --reload --port 8001` | 需先执行 Alembic 迁移与地图种子 |
| 手动前端 | `pnpm dev` | 默认 3000 |
| Docker | `docker compose up -d --build` | 四服务：postgres / redis / server / web；后端容器启动即执行 `alembic upgrade head` + 地图种子 + uvicorn |
| 端口占用排查 | `clear8001.md` | 8001 端口被占用时的查杀步骤（运维说明） |

---

## 十一、测试

| 层 | 框架 | 位置 / 命令 |
|----|------|-------------|
| 后端单元测试 | pytest / pytest-asyncio | `gridgo-server/tests/unit`（引擎拍卖规则、重连、交易结算契约、回合日志与租金统计、WS 协议契约、迁移） |
| 后端集成测试 | pytest | `gridgo-server/tests/integration/test_ai_full_game.py`（AI 全流程对局） |
| 前端测试 | Vitest（jsdom） | `gridgo-web`：`pnpm test`（单次）/ `pnpm test:watch` |
| 代码检查 | Ruff（Python） | `ruff check .` |

---

## 十二、已知限制与规划项

| 项 | 现状 | 影响 / 后续 |
|----|------|-------------|
| 内置地图仅 `classic` | 数据驱动链路完整，但 `seed_classic_map.py` 只写入 classic | 新增地图需补种子数据（规划中） |
| 音效未落地 | `howler` 已装未使用 | 规划中 |
| 观战者不可发言 | `chat.send` 属被拦截类型 | 设计如此，如需开放需调整拦截表 |
| `game.pass_go` 为单播消息 | 仅过路玩家可见 | 前端如需全局可见，改为广播并同步文档 |
| 8001 端口占用 | 已有 `clear8001.md` 处置流程 | 端口被占时后端无法启动 |
| `.env.example` 与代码默认值差异 | access token 有效期示例为 60 分钟，代码默认 1440 分钟 | 以实际 `.env` 为准，建议统一 |
| 对局状态依赖 Redis | `game:{room_id}` 为运行权威源 | Redis 清空会丢失进行中对局（前端需重连恢复或重开） |
*（内容由AI生成，仅供参考）*
