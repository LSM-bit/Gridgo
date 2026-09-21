#!/bin/bash
# GridGo 服务器更新脚本：拉代码 → 重建并启动 GridGo 服务
# 用法（在仓库目录 GridGo/ 下执行）：
#   bash deploy/update.sh
#
# 说明：
#   - deploy/gridgo.env 不在 git 内，pull 不会覆盖它（缺失时请先跑一次 deploy-remote.sh 生成）
#   - 只重建 GridGo 自身容器（deploy-gridgo-server / deploy-gridgo-web）；
#     OJ 的 deploy-postgres-1 / deploy-redis-1 完全不受影响：本脚本不 down、不加 -v，
#     也不会碰 OJ 项目里的任何容器
#   - 需要重建数据库结构时无需额外操作：server 容器每次启动都会执行
#     alembic upgrade head（幂等）+ 经典地图种子（幂等）
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> [1/4] 拉取最新代码"
git pull --ff-only

echo "==> [2/4] 检查外部网络（由 OJ 提供）"
if ! docker network inspect deploy_ojnet >/dev/null 2>&1; then
  echo "!! 找不到网络 deploy_ojnet：请先在同一台服务器上部署并运行 OJ（其 compose 会创建该网络）"
  exit 1
fi

echo "==> [3/4] 检查密钥文件"
if [ ! -f deploy/gridgo.env ]; then
  echo "!! deploy/gridgo.env 不存在：先执行一次 bash deploy/deploy-remote.sh 生成密钥并创建库/用户"
  exit 1
fi

echo "==> [4/4] 重建并启动服务"
cd deploy
# 一次性兼容清理（之后为空操作）：清理历史自动名容器与本地（根 compose）容器名，
# 它们若存在会与显式名容器抢占 8100/81 端口或网络别名。
# 不带 -v、不 down：不影响外部 postgres/redis，也不会丢数据。
docker rm -f deploy-server-1 deploy-web-1 gridgo-server gridgo-web 2>/dev/null || true
docker compose -f docker-compose.yml -f compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f compose.prod.yml ps
