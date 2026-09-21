---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: ee1a9111a266e63ab5b365271262c0db_b4605bffb58511f19286525400638852
    ReservedCode1: dKedjF3ZBlygZChIcV57nfiYtlGQfqytL34D0eILwlZmhEJ8zQ5QvpcYX66OjHh63jogEnnp8YzkzD2u2qXOQu4ckcFF4gZsEpHoZSZzI7MxTNwFR93GRXP3WxOxsgDIfRRx5MIElCBxt02Kk4TXH5LJYUET8j8fkAbNDP31ikzxenQoebuNNh9lUfo=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: ee1a9111a266e63ab5b365271262c0db_b4605bffb58511f19286525400638852
    ReservedCode2: dKedjF3ZBlygZChIcV57nfiYtlGQfqytL34D0eILwlZmhEJ8zQ5QvpcYX66OjHh63jogEnnp8YzkzD2u2qXOQu4ckcFF4gZsEpHoZSZzI7MxTNwFR93GRXP3WxOxsgDIfRRx5MIElCBxt02Kk4TXH5LJYUET8j8fkAbNDP31ikzxenQoebuNNh9lUfo=
---

# GridGo - 大富翁游戏技术选型文档

## 一、项目概述

| 项目 | 说明 |
|------|------|
| 项目名称 | GridGo（大富翁） |
| 项目类型 | 前后端分离的 Web 在线棋盘游戏 |
| 核心玩法 | 经典大富翁：掷骰子、买地、收租、事件卡、建造升级 |
| 游戏模式 | 在线多人实时联机（同房 AI 人机混战 + 观战） |
| 玩家规模 | 1-8 人（支持不同难度 AI 人机） |
| 部署方式 | 本地开发（venv + pnpm）与 Docker Compose 双形态，均已可用 |

---

## 二、系统架构

```
┌─────────────────────────────────────────────────────┐
│                     Nginx                            │
│              (反向代理 / 静态资源)                     │
└──────────────┬──────────────────┬───────────────────┘
               │                  │
       ┌───────▼───────┐  ┌──────▼────────┐
       │   Frontend     │  │   Backend      │
       │   (Vue 3 SPA)  │  │  (FastAPI)     │
       │                │  │                │
       │  - Canvas 渲染  │◄►│  - REST API    │
       │  - 状态管理     │  │  - WebSocket   │
       │  - 游戏逻辑同步 │  │  - 游戏引擎    │
       └───────────────┘  │  - AI 逻辑     │
                          └───────┬────────┘
                                  │
                          ┌───────▼────────┐
                          │    Redis        │
                          │  (房间/状态缓存) │
                          └───────┬────────┘
                                  │
                          ┌───────▼────────┐
                          │   PostgreSQL    │
                          │  (持久化存储)    │
                          └────────────────┘
```

> 上图为容器部署形态；本地开发时前端由 Vite dev server（3000）承担静态资源与 `/api`、`/ws` 代理，无独立 Nginx 进程。

### 架构模式

- **前端**：SPA 单页应用，Canvas 2D 渲染游戏画面
- **后端**：FastAPI 提供REST API + WebSocket 双协议通信
- **通信模式**：
  - REST API：用户认证、房间管理、历史记录等非实时操作
  - WebSocket：游戏内实时状态同步（掷骰子、移动、交易等）
- **状态管理**：后端为游戏状态的唯一权威源（Server Authoritative），前端仅做渲染和操作预测

---

## 三、前端技术选型

### 3.1 核心框架

| 技术 | 选型 | 版本 | 选型理由 |
|------|------|------|----------|
| 框架 | **Vue 3** | 3.5.39（来源 `package.json`） | 组合式API更灵活、TypeScript支持好、生态成熟；相比React，模板语法更直观适合游戏UI |
| 语言 | **TypeScript** | ~6.0.2 | 类型安全，减少运行时错误，IDE支持优秀 |
| 构建工具 | **Vite** | ^8.1.1 | 极速HMR、开箱即用、Vue官方推荐 |
| 包管理器 | **pnpm** | `pnpm-lock.yaml` 已提交 | 节省磁盘空间、安装速度快、monorepo友好 |

### 3.2 游戏渲染

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 渲染引擎 | **HTML5 Canvas 2D** | 棋盘游戏2D渲染足够，性能优于DOM操作；无需引入重量级3D引擎 |
| 动画库 | **GSAP** | 轻量高性能的动画库，适合骰子翻转、棋子移动等动画 |
| 备选方案 | **PixiJS** | 若后续需要更丰富的视觉效果（粒子、滤镜），可平滑迁移 |

> **为什么不用 Three.js？** 大富翁是2D棋盘游戏，Canvas 2D完全满足需求，引入3D引擎会增加包体积和复杂度，无必要。

### 3.3 状态管理 & 路由

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 状态管理 | **Pinia** | Vue 3官方推荐，TypeScript支持优秀，轻量直观 |
| 路由 | **Vue Router 4** | Vue 3配套路由，支持路由守卫和懒加载 |

### 3.4 UI 组件库

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 组件库 | **Element Plus** | Vue 3生态最成熟的中后台组件库，表单/弹窗/通知等开箱即用 |
| 样式方案 | **UnoCSS** | 原子化CSS，按需生成，体积小；支持快捷方式自定义 |
| 图标 | **Iconify** | 统一图标方案，支持多图标集按需引入 |

### 3.5 网络通信

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| HTTP 客户端 | **Axios** | 拦截器机制完善，请求/响应统一处理 |
| WebSocket | **原生 WebSocket + 封装** | 游戏通信协议简单，原生足够；封装重连、心跳、消息分发 |
| 备选方案 | **Socket.IO Client** | 若需自动重连、房间、命名空间等高级功能可升级 |

### 3.6 其他工具

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 类型检查 | **tsc** | `pnpm build` 前置执行 `tsc`；当前无 ESLint / Prettier / husky 配置 |
| 单元测试 | **Vitest + @vue/test-utils + jsdom** | `pnpm test` / `pnpm test:watch` |
| 音效 | **Howler.js** | 依赖已安装；音效资源与调用尚未落地（规划中） |

---

## 四、后端技术选型

### 4.1 核心框架

| 技术 | 选型 | 版本 | 选型理由 |
|------|------|------|----------|
| Web 框架 | **FastAPI** | 0.110+ | 异步高性能，原生支持WebSocket，自动生成OpenAPI文档，类型提示完善 |
| ASGI 服务器 | **Uvicorn** | 0.29+ | 高性能ASGI服务器，支持热重载 |
| 语言 | **Python 3.12+** | - | 性能提升，match-case语法，类型提示增强 |

> **为什么选 FastAPI 而非 Django/Flask？**
> - Django：重量级，同步框架，WebSocket支持需额外配置，不适合实时游戏
> - Flask：同步框架，WebSocket需用Flask-SocketIO（基于gevent），异步支持弱
> - FastAPI：原生异步 + WebSocket，性能优异，开发效率高

### 4.2 数据库

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 关系数据库 | **PostgreSQL 16** | 原生 JSONB 存储灵活的游戏配置，事务与并发能力强，社区资源丰富 |
| ORM | **SQLAlchemy 2.0** | Python生态最成熟的ORM，2.0版本原生支持async |
| 数据库迁移 | **Alembic** | SQLAlchemy官方迁移工具 |
| 缓存 | **Redis 7** | 房间状态缓存、在线玩家管理、排行榜、会话存储 |

### 4.3 认证 & 安全

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 认证方案 | **JWT (JSON Web Token)** | 无状态认证，适合前后端分离；配合Refresh Token机制 |
| JWT 库 | **PyJWT** | 轻量级JWT实现 |
| 密码加密 | **bcrypt** | 行业标准密码哈希（直接使用 `bcrypt` 库，无 passlib） |
| CORS | **FastAPI 内置 CORSMiddleware** | 开箱即用 |
| 数据校验 | **Pydantic V2** | FastAPI内置，请求/响应数据验证 |

### 4.4 实时通信

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| WebSocket | **FastAPI 原生 WebSocket** | 无需额外依赖，与FastAPI深度集成 |
| 消息格式 | **JSON** | 可读性好，调试方便；游戏消息量小，无需二进制协议 |
| 心跳机制 | **自定义 Ping/Pong** | 30秒间隔，检测连接存活 |
| 断线重连 | **游戏状态快照** | 重连后发送完整状态快照，恢复游戏 |

> **通信协议设计（WebSocket消息格式）**：
> ```json
> {
>   "type": "game.roll_dice",
>   "data": {},
>   "timestamp": 1758380001200
> }
> ```
>
> 信封固定为 `{type, data, timestamp}`，**不含 `seq`**（前后端均不产生、不校验序号）。
>
> 核心消息类型（与 `app/api/ws/game_ws.py` 一致）：
> - `state.*` - 状态同步（`state.snapshot` 首帧 / `state.update`）
> - `game.*` - 对局操作与广播（掷骰、买地、建造、拍卖、交易等）
> - `chat.*` - 聊天（`chat.send` 上行 / `chat.message` 广播）
> - `system.*` - 系统通知（心跳 `system.ping` / `system.pong`、上下线、重连、错误）
>
> 房间相关操作走 REST（`/api/v1/rooms`），WebSocket 不承载 `room.*` 消息。

### 4.5 AI 人机

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| AI 框架 | **自研策略引擎** | 大富翁AI核心是决策树+权重评估，无需ML框架 |
| 简单难度 | **随机策略** | 随机决策，适合新手 |
| 中等难度 | **规则引擎 + 启发式** | 基于规则的决策：优先买地、适度升级、保留现金 |
| 困难难度 | **ROI 规则评估** | 按租金回报率（> 5%）与回本回合数（< 10）决策；**不含蒙特卡洛 / Minimax 模拟** |

> **AI 决策流程**：
> ```
> AI输入 → 状态评估 → 策略选择 → 动作输出
>   │           │           │           │
>   │     资产/现金/     买入/卖出/    具体操作
>   │     位置/概率      升级/跳过
>   └──────────────────────────────────────┘
> ```

### 4.6 游戏引擎核心

| 模块 | 说明 |
|------|------|
| `app/game/engine.py` | `GameEngine`：回合机、骰子与移动、地块效果、拍卖、交易、破产与结算 |
| `app/game/schemas.py` | `GameState` / `PlayerState` / `TileState` / `AuctionState` / `TradeOffer` / 枚举定义 |
| `app/game/events.py` | WebSocket 连接管理与房间广播（`ws_manager`） |
| `app/game/replay.py` | 操作序列压缩编码与回放 |
| `app/game/ai/player.py` | `BaseAIPlayer` / `EasyAI` / `MediumAI` / `HardAI` / `AIPlayerFactory` |
| `app/services/game.py` | 对局服务（初始化、操作分发、聊天、回放查询） |
| `app/services/room.py` | 房间生命周期与 Redis 运行时状态 |
| `app/services/map.py` | 地图模板加载与缓存 |

---

## 五、项目结构

### 5.1 前端项目结构

```
gridgo-web/
├── src/
│   ├── api/                 # rest.ts / ws.ts / auth.ts / room.ts / chat.ts / friend.ts / user.ts / leaderboard.ts / replay.ts
│   ├── assets/              # 构建时资源
│   ├── components/          # 通用组件
│   │   ├── board/           # 棋盘相关组件
│   │   ├── player/          # 玩家信息组件
│   │   ├── card/            # 卡片/弹窗组件
│   │   └── common/          # 通用UI组件
│   ├── composables/         # useGame.ts / useChat.ts / useWebSocket.ts / useAnimation.ts
│   ├── game/                # renderer.ts / entities.ts / board.ts / animations.ts / replayEngine.ts
│   ├── layouts/             # 布局组件
│   ├── pages/               # Home / Room / Game / Login / Register / Profile / Friends / Leaderboard / Replay .vue
│   ├── router/              # 路由配置
│   ├── stores/              # Pinia：user.ts / room.ts / game.ts / replay.ts
│   ├── styles/              # 全局样式
│   ├── types/               # TypeScript 类型定义
│   ├── utils/               # 工具函数
│   ├── App.vue
│   └── main.ts
├── index.html
├── nginx.conf               # 容器 Nginx 配置（反代 /api、/ws）
├── package.json
├── pnpm-lock.yaml
├── tsconfig.json
├── uno.config.ts
├── vite.config.ts
├── vitest.config.ts
└── Dockerfile
```

### 5.2 后端项目结构

```
gridgo-server/
├── alembic/                  # 数据库迁移
├── app/
│   ├── api/                  # API 路由
│   │   ├── middleware/access_log.py
│   │   ├── v1/               # auth.py / room.py / game.py / user.py / chat.py / friend.py / leaderboard.py
│   │   └── ws/game_ws.py     # 游戏 WebSocket（无独立 chat_ws）
│   ├── core/                 # config.py / database.py / deps.py / logging.py / redis.py / security.py
│   ├── game/                 # 游戏引擎
│   │   ├── engine.py         # 游戏主引擎
│   │   ├── events.py         # WebSocket 连接管理与广播
│   │   ├── replay.py         # 操作序列压缩编码 / 回放
│   │   ├── schemas.py        # 状态与枚举模型
│   │   └── ai/player.py      # AI 难度实现与工厂
│   ├── models/               # user.py / room.py / stats.py / friend.py / game_record.py / map.py
│   ├── schemas/              # Pydantic 模型
│   ├── services/             # 业务逻辑层
│   ├── utils/                # 工具函数
│   └── main.py               # 应用入口
├── scripts/seed_classic_map.py   # classic 地图与卡牌种子
├── tests/                    # 测试（unit / integration）
├── requirements.txt
├── pyproject.toml
├── .env.example
└── Dockerfile
```

---

## 六、关键技术决策

### 6.1 游戏状态同步策略

| 策略 | 说明 |
|------|------|
| **权威服务器** | 后端是唯一状态源，前端只负责渲染和发送操作 |
| **全量快照** | `state.snapshot`（连接首帧）与 `state.update`（每次状态落盘后）均为**完整状态**；当前未实现字段级增量同步 |
| **事件广播** | 具体操作另发细粒度事件（如 `game.dice_result`、`game.player_moved`）供前端播放动画 |
| **操作回执** | 无独立 ack 帧；服务端处理后以广播消息 + 新快照回执，非法/越权操作返回 `system.error` |

### 6.2 断线重连机制

```
玩家断线
    │
    ▼
服务器标记"断线中"，AI暂代操作
    │
    ▼
玩家重连 ──► 发送全量状态快照 ──► 前端恢复渲染
    │
    ▼
玩家恢复控制，AI停止暂代
```

### 6.3 并发 & 性能

| 问题 | 方案 |
|------|------|
| 游戏房间状态管理 | Redis 存储活跃房间状态，游戏结束后落库 |
| 并发控制 | 每个房间一个 asyncio 锁，防止同时操作冲突 |
| 定时器 | asyncio 协程实现回合超时（30秒未操作自动跳过/AI代打） |
| 内存管理 | 游戏结束后清理内存中的房间状态 |

---

## 七、开发 & 部署

### 7.1 开发环境

| 工具 | 选型 |
|------|------|
| 版本控制 | Git + GitHub/GitLab |
| Python 环境 | venv + pip（依赖见 `requirements.txt` / `pyproject.toml`） |
| Node 环境 | Node.js 18+ + pnpm |
| IDE | VS Code / Cursor |
| API 调试 | FastAPI 自带 Swagger UI |
| WebSocket 调试 | Postman / wscat |

### 7.2 Docker 部署（已落地）

`docker-compose.yml` 编排四个服务：

| 服务 | 镜像 / 构建 | 宿主端口 | 说明 |
|------|-------------|:--------:|------|
| `postgres` | `postgres:16-alpine` | 3307（→5432） | 镜像按 `POSTGRES_DB=gridgo` 自动建库；健康检查 `pg_isready` |
| `redis` | `redis:7-alpine` | 6380 | 运行时状态与会话 |
| `server` | 构建 `./gridgo-server` | 8001 | 启动即执行 `alembic upgrade head` + 地图种子 + uvicorn |
| `web` | 构建 `./gridgo-web` | 80 | 容器内 Nginx 托管静态资源并反代 `/api`、`/ws` 到 `server:8001` |

启动命令 `docker compose up -d --build`，环境变量见 `docker/.env.docker`，完整步骤见仓库根 `README.md`。

> Nginx **不再作为独立服务**，而是打包进 `web` 镜像（配置文件 `gridgo-web/nginx.conf`）。

### 7.3 CI/CD（部分落地）

| 阶段 | 工具 |
|------|------|
| 代码检查 | Ruff（Python，配置见 `pyproject.toml`）；前端无 ESLint 配置，仅 `tsc` 类型检查 |
| 单元测试 | pytest（`tests/unit`、`tests/integration`）+ Vitest（`gridgo-web`） |
| 构建 | 分别构建 `gridgo-server` / `gridgo-web` 两个镜像 |
| 部署 | Docker Compose（Kubernetes 迁移仍为规划中） |

---

## 八、技术选型总结

| 层次 | 技术 | 作用 |
|------|------|------|
| **前端框架** | Vue 3 + TypeScript + Vite | 应用框架 |
| **前端渲染** | Canvas 2D + GSAP | 游戏画面渲染和动画 |
| **前端UI** | Element Plus + UnoCSS | 界面组件和样式 |
| **前端状态** | Pinia | 状态管理 |
| **后端框架** | FastAPI + Uvicorn | Web服务和WebSocket |
| **数据库** | PostgreSQL 16 + SQLAlchemy 2.0 | 持久化存储 |
| **缓存** | Redis | 房间状态、会话、排行榜 |
| **认证** | JWT + PyJWT | 用户认证 |
| **AI** | 自研策略引擎 | 人机对战 |
| **通信** | REST + WebSocket | 双协议通信 |
| **部署** | Docker Compose + Nginx | 容器化部署 |

---

## 九、风险与应对

| 风险 | 影响 | 应对方案 |
|------|------|----------|
| WebSocket连接不稳定 | 游戏中断 | 断线重连 + AI暂代 + 状态快照 |
| 游戏逻辑复杂度 | 开发周期长 | 分阶段迭代：先核心玩法→再扩展功能 |
| Canvas渲染性能 | 低端设备卡顿 | 脏矩形重绘、requestAnimationFrame、降帧策略 |
| 并发房间管理 | 状态混乱 | asyncio锁 + Redis原子操作 + 定期清理 |
| AI决策公平性 | 游戏体验差 | 难度分级、规则透明、AI不"读牌" |

---

## 十、迭代计划

版本口径统一为 `0.1.0`（见 `gridgo-server/app/core/config.py`），**不再使用 MVP / V1.0 / V1.5 / V2.0 等阶段版本号**；进展按下表标注（判定标准同 `docs/PROJECT.md`）。

| 能力 | 状态 | 说明 |
|------|:----:|------|
| 基础棋盘、掷骰、买地 / 收租 | 已实现 | `app/game/engine.py`、classic 地图种子 |
| 在线多人、房间系统 | 已实现 | REST `/api/v1/rooms` + Redis 运行时状态 |
| 建造升级、事件卡（机会 / 命运） | 已实现 | 建筑等级 0-5；机会卡 C01-C10、命运卡 F01-F10 |
| 交易、聊天、断线重连、排行榜 | 已实现 | `trade_*` 系列、`chat.*`、`player_reconnected`、`/api/v1/leaderboard` |
| AI 人机（easy / medium / hard） | 已实现 | `app/game/ai/player.py` |
| Docker 容器化部署 | 已实现 | `docker-compose.yml` 四服务 |
| 多地图拓展（city / island 等） | 规划中 | 表结构与 `map_id` 链路就绪，仅 classic 有种子数据 |
| 道具系统、赛季 / 段位、成就 | 规划中 | 无对应模型与接口 |
| 音效 | 规划中 | `howler` 已安装，无资源与调用 |
*（内容由AI生成，仅供参考）*
