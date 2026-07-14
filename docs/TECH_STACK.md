# GridGo - 大富翁游戏技术选型文档

## 一、项目概述

| 项目 | 说明 |
|------|------|
| 项目名称 | GridGo（大富翁） |
| 项目类型 | 前后端分离的 Web 在线棋盘游戏 |
| 核心玩法 | 经典大富翁：掷骰子、买地、收租、事件卡、建造升级 |
| 游戏模式 | 在线多人实时联机 + 本地单人（vs AI） |
| 玩家规模 | 1-8 人（支持不同难度 AI 人机） |
| 部署方式 | 先本地开发，后续 Docker 容器化部署 |

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
                          │     MySQL       │
                          │  (持久化存储)    │
                          └────────────────┘
```

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
| 框架 | **Vue 3** | 3.4+ | 组合式API更灵活、TypeScript支持好、生态成熟；相比React，模板语法更直观适合游戏UI |
| 语言 | **TypeScript** | 5.x | 类型安全，减少运行时错误，IDE支持优秀 |
| 构建工具 | **Vite** | 5.x | 极速HMR、开箱即用、Vue官方推荐 |
| 包管理器 | **pnpm** | 9.x | 节省磁盘空间、安装速度快、monorepo友好 |

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
| 代码规范 | **ESLint + Prettier** | 统一代码风格 |
| 提交规范 | **husky + lint-staged + commitlint** | 规范化提交 |
| 音效 | **Howler.js** | Web Audio API 封装，支持多格式音效播放 |

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
| 关系数据库 | **MySQL 8.0** | 生态成熟、运维成本低，支持JSON类型存储灵活的游戏配置，社区资源丰富 |
| ORM | **SQLAlchemy 2.0** | Python生态最成熟的ORM，2.0版本原生支持async |
| 数据库迁移 | **Alembic** | SQLAlchemy官方迁移工具 |
| 缓存 | **Redis 7** | 房间状态缓存、在线玩家管理、排行榜、会话存储 |

### 4.3 认证 & 安全

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| 认证方案 | **JWT (JSON Web Token)** | 无状态认证，适合前后端分离；配合Refresh Token机制 |
| JWT 库 | **PyJWT** | 轻量级JWT实现 |
| 密码加密 | **bcrypt (passlib)** | 行业标准密码哈希 |
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
>   "type": "game.action",
>   "data": { "action": "roll_dice" },
>   "seq": 42,
>   "timestamp": 1700000000
> }
> ```
>
> 核心消息类型：
> - `room.*` - 房间相关（创建/加入/离开/准备）
> - `game.*` - 游戏操作（掷骰子/买地/建造/使用道具）
> - `state.*` - 状态同步（完整快照/增量更新）
> - `chat.*` - 聊天消息
> - `system.*` - 系统通知（断线/重连/错误）

### 4.5 AI 人机

| 技术 | 选型 | 选型理由 |
|------|------|----------|
| AI 框架 | **自研策略引擎** | 大富翁AI核心是决策树+权重评估，无需ML框架 |
| 简单难度 | **随机策略** | 随机决策，适合新手 |
| 中等难度 | **规则引擎 + 启发式** | 基于规则的决策：优先买地、适度升级、保留现金 |
| 困难难度 | **蒙特卡洛模拟 / Minimax** | 模拟多步后的最优决策 |

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
| **GameRoom** | 游戏房间生命周期管理 |
| **GameBoard** | 棋盘数据模型（地块、价格、租金规则） |
| **GameEngine** | 核心游戏逻辑（回合制、骰子、移动、交易、事件） |
| **PlayerState** | 玩家状态（位置、现金、地产、道具、状态效果） |
| **EventManager** | 事件系统（机会卡、命运卡、税收等随机事件） |
| **TurnManager** | 回合管理（当前玩家、操作顺序、超时处理） |
| **TradeManager** | 交易管理（玩家间地产/现金交易） |

---

## 五、项目结构

### 5.1 前端项目结构

```
gridgo-web/
├── public/
│   └── assets/              # 静态资源（图片、音效）
├── src/
│   ├── api/                 # API 接口封装
│   │   ├── rest.ts          # REST API
│   │   └── ws.ts            # WebSocket 封装
│   ├── assets/              # 构建时资源
│   ├── components/          # 通用组件
│   │   ├── board/           # 棋盘相关组件
│   │   ├── player/          # 玩家信息组件
│   │   ├── card/            # 卡片/弹窗组件
│   │   └── common/          # 通用UI组件
│   ├── composables/         # 组合式函数
│   │   ├── useGame.ts       # 游戏逻辑
│   │   ├── useWebSocket.ts  # WebSocket连接
│   │   └── useAnimation.ts  # 动画控制
│   ├── game/                # 游戏核心
│   │   ├── renderer/        # Canvas 渲染器
│   │   ├── entities/        # 游戏实体（棋子、地块）
│   │   └── animations/      # 动画定义
│   ├── layouts/             # 布局组件
│   ├── pages/               # 页面
│   │   ├── Home.vue         # 首页/大厅
│   │   ├── Room.vue         # 房间/等待
│   │   └── Game.vue         # 游戏主界面
│   ├── router/              # 路由配置
│   ├── stores/              # Pinia 状态
│   │   ├── user.ts          # 用户状态
│   │   ├── room.ts          # 房间状态
│   │   └── game.ts          # 游戏状态
│   ├── styles/              # 全局样式
│   ├── types/               # TypeScript 类型定义
│   ├── utils/               # 工具函数
│   ├── App.vue
│   └── main.ts
├── index.html
├── vite.config.ts
├── tsconfig.json
├── uno.config.ts
└── package.json
```

### 5.2 后端项目结构

```
gridgo-server/
├── alembic/                  # 数据库迁移
├── app/
│   ├── api/                  # API 路由
│   │   ├── v1/
│   │   │   ├── auth.py       # 认证接口
│   │   │   ├── room.py       # 房间接口
│   │   │   ├── game.py       # 游戏接口
│   │   │   └── user.py       # 用户接口
│   │   └── ws/
│   │       ├── game_ws.py    # 游戏 WebSocket
│   │       └── chat_ws.py    # 聊天 WebSocket
│   ├── core/                 # 核心配置
│   │   ├── config.py         # 配置管理
│   │   ├── security.py       # 安全/认证
│   │   └── events.py         # 事件定义
│   ├── game/                 # 游戏引擎
│   │   ├── engine.py         # 游戏主引擎
│   │   ├── board.py          # 棋盘模型
│   │   ├── player.py         # 玩家状态
│   │   ├── turn.py           # 回合管理
│   │   ├── events.py         # 事件/卡片系统
│   │   ├── trade.py          # 交易系统
│   │   └── ai/               # AI 模块
│   │       ├── base.py       # AI 基类
│   │       ├── easy.py       # 简单 AI
│   │       ├── medium.py     # 中等 AI
│   │       └── hard.py       # 困难 AI
│   ├── models/               # 数据库模型
│   │   ├── user.py
│   │   ├── room.py
│   │   └── game_record.py
│   ├── schemas/              # Pydantic 模型
│   ├── services/             # 业务逻辑层
│   ├── utils/                # 工具函数
│   └── main.py               # 应用入口
├── tests/                    # 测试
│   ├── unit/
│   └── integration/
├── requirements.txt
├── pyproject.toml
└── Dockerfile
```

---

## 六、关键技术决策

### 6.1 游戏状态同步策略

| 策略 | 说明 |
|------|------|
| **权威服务器** | 后端是唯一状态源，前端只负责渲染和发送操作 |
| **增量同步** | 正常游戏时仅推送变化的字段（位置、现金等），减少带宽 |
| **全量快照** | 关键时刻（回合开始、重连）推送完整游戏状态 |
| **操作确认** | 前端操作需等待服务器确认后才生效，防止作弊 |

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
| Python 环境 | uv（极速Python包管理器） |
| Node 环境 | nvm + pnpm |
| IDE | VS Code / Cursor |
| API 调试 | FastAPI 自带 Swagger UI |
| WebSocket 调试 | Postman / wscat |

### 7.2 Docker 部署（后续）

```yaml
# docker-compose.yml 预览
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: [./nginx.conf:/etc/nginx/nginx.conf]

  backend:
    build: ./gridgo-server
    environment:
      - DATABASE_URL=mysql+aiomysql://...
      - REDIS_URL=redis://redis:6379
    depends_on: [mysql, redis]

  frontend:
    build: ./gridgo-web
    # 构建后静态文件由 nginx 托管

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=gridgo
    volumes: [mysqldata:/var/lib/mysql]

  redis:
    image: redis:7-alpine
    volumes: [redisdata:/data]
```

### 7.3 CI/CD（后续）

| 阶段 | 工具 |
|------|------|
| 代码检查 | Ruff (Python) + ESLint (TypeScript) |
| 单元测试 | pytest + Vitest |
| 构建 | Docker multi-stage build |
| 部署 | Docker Compose → 后续可迁移 Kubernetes |

---

## 八、技术选型总结

| 层次 | 技术 | 作用 |
|------|------|------|
| **前端框架** | Vue 3 + TypeScript + Vite | 应用框架 |
| **前端渲染** | Canvas 2D + GSAP | 游戏画面渲染和动画 |
| **前端UI** | Element Plus + UnoCSS | 界面组件和样式 |
| **前端状态** | Pinia | 状态管理 |
| **后端框架** | FastAPI + Uvicorn | Web服务和WebSocket |
| **数据库** | MySQL 8.0 + SQLAlchemy 2.0 | 持久化存储 |
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

| 阶段 | 内容 | 预计周期 |
|------|------|----------|
| **MVP** | 单人vs AI、基础棋盘、买地/收租、掷骰子 | 2-3 周 |
| **V1.0** | 在线多人、房间系统、建造升级、事件卡 | 3-4 周 |
| **V1.5** | 交易系统、聊天、断线重连、排行榜 | 2-3 周 |
| **V2.0** | 多地图、道具系统、赛季、Docker部署 | 3-4 周 |
