---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: ee1a9111a266e63ab5b365271262c0db_9855c38ab58511f19286525400638852
    ReservedCode1: WKDhjT5a98PHVliNeNcdpr+NX9d6oW1bB5/nNdaeDTW42EymdM7Mwv+unYeOZmA2mnEE08pKlrbKhrvRYF5dWHa6XkWIQtQbNWH9xKyufMZ3M1l7AH+14UYU67UT3O5kq5djlIobTXZE2Be1LN0zb59wqcTw74DyIqlRGEqfSTvZouG9MNalkVKiZ3g=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: ee1a9111a266e63ab5b365271262c0db_9855c38ab58511f19286525400638852
    ReservedCode2: WKDhjT5a98PHVliNeNcdpr+NX9d6oW1bB5/nNdaeDTW42EymdM7Mwv+unYeOZmA2mnEE08pKlrbKhrvRYF5dWHa6XkWIQtQbNWH9xKyufMZ3M1l7AH+14UYU67UT3O5kq5djlIobTXZE2Be1LN0zb59wqcTw74DyIqlRGEqfSTvZouG9MNalkVKiZ3g=
---

# GridGo（大富翁）

前后端分离的在线多人棋盘游戏：REST + WebSocket 实时对局，支持 1-8 人同房、AI 人机混战（easy / medium / hard）、拍卖、交易、回放与排行榜。应用版本 `0.1.0`。

| 组成 | 技术栈 | 目录 |
|------|--------|------|
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Element Plus + UnoCSS + Canvas/GSAP | `gridgo-web/` |
| 后端 | FastAPI + SQLAlchemy 2.0(async) + Alembic + Pydantic v2 + Redis | `gridgo-server/` |
| 存储 | PostgreSQL 16（持久化）、Redis 7（运行时房间与对局状态） | `docker-compose.yml` |

生产/开发环境、架构图、接口全表、数据库设计与字段口径见 [docs/PROJECT.md](docs/PROJECT.md)；对局流程见 [docs/GAME_FLOW.md](docs/GAME_FLOW.md)；技术选型见 [docs/TECH_STACK.md](docs/TECH_STACK.md)。

---

## 目录结构

```
E:\Project\GridGo\
├── gridgo-server\        # 后端（FastAPI，端口 8001）
├── gridgo-web\           # 前端（Vite，端口 3000）
├── docs\                 # 项目/流程/技术栈文档
├── docker\               # Docker 辅助配置（.env.docker、postgres/ 初始化目录）
├── docker-compose.yml    # postgres / redis / server / web 四服务编排
├── start.bat / stop.bat  # Windows 一键启停（本地模式）
└── clear8001.md          # 8001 端口占用处置（运维，内容已并入本文「常见问题」）
```

---

## 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.12+ |
| Node.js | 18+ |
| pnpm | 最新（`npm i -g pnpm`） |
| PostgreSQL | 16（本地或 Docker） |
| Redis | 7.x（本地或 Docker） |
| Docker + Docker Compose | 仅容器部署需要 |

---

## 快速开始（本地开发）

### 1. 准备数据库

本地 PostgreSQL 需存在库 `gridgo`，并同步修改 `gridgo-server\.env` 中的连接串：

```env
DATABASE_URL=postgresql+asyncpg://gridgo:gridgo123@127.0.0.1:3307/gridgo
REDIS_URL=redis://localhost:6379/0
```

### 2. 启动后端

```powershell
cd E:\Project\GridGo\gridgo-server
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 首次必须：建表 + 写入 classic 地图与卡牌种子
alembic upgrade head
python -m scripts.seed_classic_map

uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

- API 文档：http://localhost:8001/docs
- 健康检查：http://localhost:8001/api/v1/health

### 3. 启动前端

```powershell
cd E:\Project\GridGo\gridgo-web
pnpm install
pnpm dev          # http://localhost:3000
```

Vite 已配置代理：`/api` → `http://localhost:8001`，`/ws` → `ws://localhost:8001`（`ws: true`），前端无需额外配置跨域。

### 4. 一键启停（可选）

| 脚本 | 行为 |
|------|------|
| `start.bat` | 检查 Python / Node / pnpm → 不存在 `.env` 时从 `.env.example` 复制 → 创建 venv 并装依赖 → 装前端依赖（无 `node_modules` 时）→ 先后台启动后端 8001 与前端 3000 |
| `stop.bat` | 结束占用 8001 / 3000 端口的进程 |

> 注意：`start.bat` 只负责拉起进程，**不会**执行 Alembic 迁移与地图种子；首次使用请先按第 2 步手动执行 `alembic upgrade head` 与 `python -m scripts.seed_classic_map`。

---

## Docker 部署

```powershell
cd E:\Project\GridGo
Copy-Item docker\.env.docker .env      # 按需修改端口与密码
docker compose up -d --build
```

| 服务 | 容器名 | 镜像/构建 | 宿主机端口 | 说明 |
|------|--------|-----------|-----------|------|
| postgres | gridgo-postgres | postgres:16-alpine | 3307 → 5432 | 镜像按 POSTGRES_DB=gridgo 自动建库；健康检查 pg_isready |
| redis | gridgo-redis | redis:7-alpine | 6380 → 6379 | 开启 AOF（`--appendonly yes`） |
| server | gridgo-server | 构建 `./gridgo-server` | 8001 → 8001 | 容器启动即执行 `alembic upgrade head` + 地图种子 + uvicorn；依赖 postgres/redis 健康 |
| web | gridgo-web | 构建 `./gridgo-web` | 80 → 80 | Nginx 托管静态资源并反代 `/api`、`/ws` 到 `server:8001` |

- 访问入口：http://localhost
- 数据卷：`gridgo-postgres-data`、`gridgo-redis-data`；网络：`gridgo-network`
- 容器内连接串由 compose 注入：`DATABASE_URL=postgresql+asyncpg://gridgo:<密码>@postgres:5432/gridgo`、`REDIS_URL=redis://redis:6379/0`
- 重建后端（代码升级后）：

```powershell
docker compose up -d --build server
```

---

## 环境变量

### 后端 `gridgo-server\.env`（模板：`.env.example`）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_NAME` | `GridGo` | 应用名 |
| `DEBUG` | `True` | 调试模式 |
| `HOST` / `PORT` | `0.0.0.0` / `8001` | 监听地址与端口 |
| `DATABASE_URL` | `postgresql+asyncpg://gridgo:gridgo123@127.0.0.1:3307/gridgo` | PostgreSQL 连接串 |
| `DATABASE_ECHO` | `False` | SQL 回显 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接串 |
| `JWT_SECRET_KEY` | `gridgo-secret-key-change-in-production` | **生产必须修改** |
| `JWT_ALGORITHM` | `HS256` | 签名算法 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | access token 有效期（分钟），`.env.example` 示例为 60 |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | refresh token 有效期（天） |
| `CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | JSON 数组 |
| `GAME_INITIAL_CASH` | `1500` | 初始现金 |
| `GAME_PASS_GO_BONUS` | `200` | 经过起点奖励 |
| `GAME_TURN_TIMEOUT` | `30` | 回合超时（秒） |
| `GAME_MAX_PLAYERS` | `8` | 单房最大玩家数 |
| `GAME_MAX_TURNS` | `100` | 单局最大回合数 |

### Docker `docker\.env.docker`（根目录 `.env`）

| 变量 | 值 | 说明 |
|------|-----|------|
| `POSTGRES_PASSWORD` | `gridgo123` | PostgreSQL 密码 |
| `POSTGRES_PORT` | `3307` | 宿主机映射端口（宿主 3307 → 容器 5432） |
| `REDIS_PORT` | `6380` | Redis 映射端口（避开本机 6379） |
| `SERVER_PORT` | `8001` | 后端映射端口 |
| `WEB_PORT` | `80` | 前端映射端口 |
| `JWT_*` / `GAME_*` | 同上 | 容器内配置 |

前端不读取环境变量：开发经 Vite 代理、容器经 Nginx 反代访问 `/api` 与 `/ws`。

---

## REST 端点简表

Base：本地直连 `http://localhost:8001/api/v1`；前端开发 `http://localhost:3000/api/v1`；Docker `http://localhost/api/v1`。除标注「公开」外均需 `Authorization: Bearer <access_token>`。

| 模块 | 方法与路径 | 说明 |
|------|-----------|------|
| 认证 | `POST /auth/register`、`POST /auth/login`、`POST /auth/refresh` | 公开：注册、登录、刷新 |
| 认证 | `POST /auth/logout`、`GET /auth/me` | 登出、当前用户 |
| 用户 | `GET /users/me`、`PATCH /users/me`、`POST /users/me/change-password` | 资料读写、改密 |
| 用户 | `GET /users/me/stats`、`GET /users/me/records`、`GET /users/records/{game_id}` | 我的统计、我的对局、单局详情 |
| 用户 | `GET /users/{user_id}/stats`、`GET /users/{user_id}/records` | 公开：他人统计与对局 |
| 房间 | `GET /rooms`、`POST /rooms`、`GET /rooms/by-code/{code}`、`GET /rooms/{room_id}` | 列表、创建、房间码查询、详情 |
| 房间 | `POST /rooms/join`、`POST /rooms/{room_id}/leave`、`POST /rooms/{room_id}/ready`、`POST /rooms/{room_id}/switch-role` | 加入、离开、准备、切换玩家/观战 |
| 房间 | `PATCH /rooms/{room_id}/settings`（`PUT .../config` 别名）、`POST /rooms/{room_id}/start`、`POST /rooms/{room_id}/reset` | 设置、开始、重置（房主） |
| 对局 | `GET /games/{room_id}`、`GET /games/{room_id}/state`、`GET /games/{room_id}/log` | 对局信息、完整状态、日志 |
| 对局 | `POST /games/{room_id}/surrender`、`GET /games/replay/{game_id}`、`GET /games/history/{user_id}` | 投降、回放、历史 |
| 聊天 | `GET /rooms/{room_id}/chat`、`POST /rooms/{room_id}/chat` | 游标拉取、发送 |
| 好友 | `GET /friends`、`GET /friends/requests`、`POST /friends/requests`、`POST /friends/requests/{request_id}/respond`、`DELETE /friends/{friend_id}` | 好友与申请 |
| 排行 | `GET /leaderboard` | 公开：`limit` 1-100（默认 50）、`offset` |

---

## WebSocket 握手与消息示例

**端点**：`ws://localhost:8001/ws/game?token=<access_token>`（前端开发走 `ws://localhost:3000/ws/game?token=...`，Docker 走 `ws://localhost/ws/game?token=...`）

**握手约定**

1. `token` 查询参数必填，鉴权失败服务端以关闭码 `4001` 断开。
2. 连接后客户端**首帧**必须发送含 `room_id` 的 JSON（服务端只取 `room_id`，不校验 `type`）。
3. 服务端随后单播 `state.snapshot`（含 `is_spectator`），并广播 `system.player_connected` / `system.spectator_connected`。

**关闭码**：`4001` 认证失败、`4002` 首帧格式错误、`4003` 缺少 `room_id`、`4004` 初始化失败、`4005` 状态不存在。

**示例**

```js
const ws = new WebSocket(`ws://localhost:8001/ws/game?token=${accessToken}`);
ws.onopen = () => {
  ws.send(JSON.stringify({ type: 'join', data: { room_id: '75873edb9a92' } }));   // 首帧
  setInterval(() => ws.send(JSON.stringify({ type: 'system.ping', data: {} })), 20000);
};
ws.onmessage = (e) => {
  const { type, data } = JSON.parse(e.data);
  if (type === 'state.snapshot') console.log('初始状态', data);      // {game_id, phase, tiles, players, ...}
  if (type === 'game.turn_change') console.log('轮到', data.current_player_nickname);
  if (type === 'game.dice_result') console.log('点数', data.dice, '总和', data.total);
  if (type === 'game.over') console.log('结束', data.end_reason, data.rankings);
};
// 掷骰
ws.send(JSON.stringify({ type: 'game.roll_dice', data: {} }));
```

**上行类型**：`system.ping`、`game.roll_dice`、`game.buy_property`、`game.decline_property`（别名 `game.decline_buy`）、`game.skip_property`、`game.auction_bid`、`game.auction_start`（服务端忽略）、`game.build`、`game.demolish`、`game.mortgage`、`game.redeem`、`game.end_turn`、`game.jail_pay_bail`（别名 `game.jail_pay`）、`game.jail_use_card`、`game.trade_offer`、`game.trade_accept`、`game.trade_reject`、`chat.send`

**下行类型**：`state.snapshot`、`state.update`、`game.turn_change`、`game.dice_result`、`game.extra_roll`、`game.player_moved`、`game.pass_go`（单播）、`game.tile_event`、`game.property_bought`、`game.property_declined`、`game.property_skipped`、`game.rent_paid`、`game.tax_paid`、`game.card_drawn`、`game.get_out_of_jail_card`、`game.jail_sent`、`game.jail_released`、`game.money_change`、`game.building_built`、`game.building_demolished`、`game.property_mortgaged`、`game.property_redeemed`、`game.auction_start`、`game.auction_update`、`game.auction_end`、`game.trade_offer`、`game.trade_received`（单播）、`game.trade_accept`、`game.trade_reject`、`game.trade_completed`、`game.player_bankrupt`、`game.over`、`chat.message`、`system.player_connected`、`system.player_disconnected`、`system.player_reconnected`、`system.spectator_connected`、`system.spectator_disconnected`、`system.pong`（单播）、`system.error`

> 观战者被服务端拦截的上行操作共 16 类（含 `chat.send`），详见 [docs/PROJECT.md](docs/PROJECT.md) 第 6.2 节。消息信封为 `{type, data, timestamp}`，无 `seq` 字段。

---

## 前端命令与测试

```powershell
cd E:\Project\GridGo\gridgo-web
pnpm dev            # 开发服务器（3000）
pnpm build          # tsc && vite build
pnpm preview        # 预览构建产物
pnpm test           # Vitest 单次运行
pnpm test:watch     # Vitest 监听模式
```

后端测试与检查：

```powershell
cd E:\Project\GridGo\gridgo-server
pytest tests -q      # 单元 + 集成（AI 全流程对局）
ruff check .
```

---

## 常见问题

### 1. 后端接口 502 / 前端所有请求失败

优先确认 8001 端口是否有进程监听（后端容器曾以 ExitCode 137 退出会导致代理不可达）：

```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen
docker ps -a --filter "name=gridgo-server"
```

容器方式修复：`docker start gridgo-server`；若镜像过旧（缺少新路由），使用 `docker compose up -d --build server` 重建。

### 2. 8001 端口被占用（清理步骤，原 `clear8001.md`）

```powershell
# 查看 8001 端口的进程
Get-NetTCPConnection -LocalPort 8001
# 只杀掉占用 8001 端口的进程（按监听端口精确定位 PID，避免误杀其它 python 进程）
Get-NetTCPConnection -LocalPort 8001 -State Listen | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force }
# 然后重新启动
```

### 3. 数据库表不存在 / 地图数据缺失

```powershell
cd E:\Project\GridGo\gridgo-server
alembic upgrade head
python -m scripts.seed_classic_map
```

### 4. 前端需要确认后端地址

不要硬编码域名：开发环境统一使用相对路径 `/api`、`/ws`，由 `vite.config.ts` 代理；容器环境由 `gridgo-web/nginx.conf`（构建进 `web` 镜像）反代。
*（内容由AI生成，仅供参考）*
