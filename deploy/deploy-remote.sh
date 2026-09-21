#!/bin/bash
# ==================== GridGo 远程部署脚本（在服务器上执行） ====================
# 目标服务器：与 OJ 同一台机器，**完全复用** OJ 已运行的 postgres / redis，本项目不新起数据库。
#
# 用法（在任意目录，脚本自身会定位仓库）：
#   bash /home/deploy/GridGo/deploy/deploy-remote.sh
#   PG_SUPERUSER=oj bash /home/deploy/GridGo/deploy/deploy-remote.sh   # 显式指定 PG 超级用户
#
# 前置条件：同一台服务器上 OJ 已部署并运行，从而存在：
#   - docker 网络 deploy_ojnet（OJ compose 项目网络）
#   - 容器 deploy-postgres-1（:5432）与 deploy-redis-1（:6379）
#
# 幂等：可重复执行；已存在的 env / 角色 / 库 / 容器都不会被破坏；不删除任何数据。
set -e

PROJECT_DIR="/home/deploy/GridGo"
REPO_URL="https://github.com/LSM-bit/Gridgo.git"
BRANCH="main"
OJ_ENV_FILE="/home/deploy/OJ/deploy/api.env"   # 仅用于探测 OJ 的 PG 超级用户名（只读 user 字段）

echo "========== GridGo 部署开始 =========="

# ────────────────────────── 1. Docker 环境 ──────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  echo "[1/7] 安装 Docker..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
else
  echo "[1/7] Docker 已安装：$(docker --version)"
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "      安装 Docker Compose 插件..."
  sudo apt-get update && sudo apt-get install -y docker-compose-plugin
fi

# ────────────────────────── 2. 获取代码 ──────────────────────────
echo "[2/7] 获取代码..."
if [ -d "$PROJECT_DIR/.git" ]; then
  cd "$PROJECT_DIR" && git fetch origin && git checkout "$BRANCH" && git pull --ff-only
else
  mkdir -p "$(dirname "$PROJECT_DIR")"
  cd "$(dirname "$PROJECT_DIR")"
  git clone --branch "$BRANCH" "$REPO_URL" "$PROJECT_DIR"
  cd "$PROJECT_DIR"
fi

# ────────────────────────── 3. 校验 OJ 基础设施 ──────────────────────────
echo "[3/7] 校验复用的 OJ 基础设施..."
if ! docker network inspect deploy_ojnet >/dev/null 2>&1; then
  echo "!! 未找到网络 deploy_ojnet —— 请先在同一台服务器上部署并运行 OJ（其 compose 会创建该网络）"
  exit 1
fi
for c in deploy-postgres-1 deploy-redis-1; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "!! 容器 $c 未在运行 —— 请先启动 OJ（cd /home/deploy/OJ/deploy && docker compose -f docker-compose.yml -f compose.prod.yml up -d）"
    exit 1
  fi
done
echo "      deploy_ojnet 网络正常，deploy-postgres-1 / deploy-redis-1 均在运行"

# ────────────────────────── 4. 生成 gridgo.env ──────────────────────────
echo "[4/7] 准备密钥文件 deploy/gridgo.env..."
cd "$PROJECT_DIR/deploy"
if [ ! -f gridgo.env ]; then
  cp gridgo.env.example gridgo.env
  PG_PASSWORD="$(openssl rand -hex 24)"
  JWT_SECRET="$(openssl rand -hex 32)"
  SERVER_IP="$(curl -fsS --max-time 5 ifconfig.me 2>/dev/null || echo 127.0.0.1)"
  sed -i "s|<POSTGRES_PASSWORD>|$PG_PASSWORD|g" gridgo.env
  sed -i "s|<openssl rand -hex 32>|$JWT_SECRET|g" gridgo.env
  sed -i "s|<服务器IP>|$SERVER_IP|g" gridgo.env
  chmod 600 gridgo.env
  echo "      gridgo.env 已生成（PG 密码 / JWT 密钥均为随机值，权限 600）"
else
  echo "      gridgo.env 已存在，跳过生成（轮换密钥请手工编辑后重新 up -d）"
fi

# ────────────────────────── 5. 幂等创建 PG 角色与库 ──────────────────────────
echo "[5/7] 在复用的 PostgreSQL（deploy-postgres-1）中创建 gridgo 库与用户..."
DB_USER="$(sed -n 's|^DATABASE_URL=postgresql+asyncpg://\([^:@]*\):.*|\1|p' gridgo.env | head -1)"
DB_PASS="$(sed -n 's|^DATABASE_URL=postgresql+asyncpg://[^:@]*:\([^@]*\)@.*|\1|p' gridgo.env | head -1)"
DB_NAME="$(sed -n 's|^DATABASE_URL=.*@[^/]*/\([^?]*\).*|\1|p' gridgo.env | head -1)"
if [ -z "$DB_USER" ] || [ -z "$DB_PASS" ] || [ -z "$DB_NAME" ]; then
  echo "!! 无法从 gridgo.env 的 DATABASE_URL 解析出库/用户/密码，请检查该行格式"
  exit 1
fi

# 超级用户优先级：环境变量 PG_SUPERUSER > OJ 的 api.env 中 POSTGRES_USER > postgres
if [ -z "${PG_SUPERUSER:-}" ] && [ -f "$OJ_ENV_FILE" ]; then
  PG_SUPERUSER="$(sed -n 's|^POSTGRES_USER=\(.*\)|\1|p' "$OJ_ENV_FILE" | tr -d '\r' | head -1)"
fi
PG_SUPERUSER="${PG_SUPERUSER:-postgres}"
echo "      目标库：$DB_NAME / 角色：$DB_USER / 超级用户：$PG_SUPERUSER"

PSQL="docker exec -i deploy-postgres-1 psql -v ON_ERROR_STOP=1"

# 角色（不存在则创建；存在则同步密码，保证与 gridgo.env 一致）
if $PSQL -U "$PG_SUPERUSER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
  $PSQL -U "$PG_SUPERUSER" -d postgres -c "ALTER ROLE \"$DB_USER\" LOGIN PASSWORD '$DB_PASS'" >/dev/null
  echo "      角色 $DB_USER 已存在（已同步密码）"
else
  $PSQL -U "$PG_SUPERUSER" -d postgres -c "CREATE ROLE \"$DB_USER\" LOGIN PASSWORD '$DB_PASS'" >/dev/null
  echo "      角色 $DB_USER 已创建"
fi

# 数据库（不存在则创建；owner 为 gridgo）
if $PSQL -U "$PG_SUPERUSER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
  echo "      数据库 $DB_NAME 已存在，跳过创建（数据保留）"
else
  $PSQL -U "$PG_SUPERUSER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\" ENCODING 'UTF8'" >/dev/null
  echo "      数据库 $DB_NAME 已创建（owner=$DB_USER）"
fi

# public schema 归属：PG15+ 的 public schema 属 pg_database_owner，显式改写更稳妥（幂等）
$PSQL -U "$PG_SUPERUSER" -d "$DB_NAME" -c "ALTER SCHEMA public OWNER TO \"$DB_USER\"" >/dev/null
$PSQL -U "$PG_SUPERUSER" -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO \"$DB_USER\"" >/dev/null

# 连通性自检（容器内直连 127.0.0.1）
echo "      连通性自检："
docker exec deploy-postgres-1 psql "postgresql://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME" -tAc "SELECT current_database() || ' / ' || current_user"

# Redis db1 自检（与 OJ 的 db0 隔离；同一个 redis 实例）
if docker exec deploy-redis-1 redis-cli -n 1 ping >/dev/null 2>&1; then
  echo "      Redis db1 可用（deploy-redis-1，与 OJ 的 db0 隔离）"
else
  echo "      !! Redis db1 无法访问，请检查 deploy-redis-1 是否正常运行"
fi

# ────────────────────────── 6. 构建并启动 ──────────────────────────
echo "[6/7] 构建并启动 GridGo 服务（首次需下载依赖，约 3~10 分钟）..."
docker rm -f deploy-server-1 deploy-web-1 gridgo-server gridgo-web 2>/dev/null || true
docker compose -f docker-compose.yml -f compose.prod.yml up -d --build

# ────────────────────────── 7. 验证 ──────────────────────────
echo "[7/7] 等待服务就绪并验证..."
sleep 20
docker compose -f docker-compose.yml -f compose.prod.yml ps
echo ""
echo "--- 服务健康检查 ---"
docker exec deploy-gridgo-server python -c "import urllib.request;print('server /health ->', urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=5).read().decode())" || echo "!! 后端健康检查失败，查看日志：docker logs deploy-gridgo-server"
docker exec deploy-gridgo-web wget -qO- http://server:8001/health >/dev/null 2>&1 && echo "web → server 内网连通 OK" || echo "!! web 容器无法访问 server，请检查网络与后端日志"
echo "--- 站点入口 ---"
curl -s -o /dev/null -w "http://127.0.0.1:81/ -> HTTP %{http_code}\n" http://127.0.0.1:81/ || true

echo ""
echo "========== 部署完成 =========="
echo "站点：http://$(curl -fsS --max-time 5 ifconfig.me 2>/dev/null || echo '<服务器IP>'):81/"
echo "日志：docker logs -f deploy-gridgo-server    /    docker logs -f deploy-gridgo-web"
echo "更新：cd $PROJECT_DIR && bash deploy/update.sh"
echo "注意：服务器防火墙/安全组需放行 81/tcp（80 已由 OJ 占用）"
