# GridGo 后端镜像（生产部署用，构建上下文为仓库根）
# 构建: docker build -f deploy/server.Dockerfile -t gridgo-server .
#
# 要点：
#   - 数据库/Redis/JWT 等全部由 env_file（deploy/gridgo.env）注入，绝不写进镜像
#   - CMD 先跑 alembic 迁移（幂等）→ 经典地图种子（幂等）→ 再启动 uvicorn；
#     任一步失败容器即退出，由 restart: unless-stopped 自动重试，
#     故容器 healthy 隐含「迁移 + 种子 + 服务」三者都成功
#   - 数据库为外部复用（deploy-postgres-1），不在此镜像内做任何初始化
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 国内 Debian 源（海外服务器可删掉本行）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# gcc：编译 bcrypt 等需要本地编译的包
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing gcc && \
    rm -rf /var/lib/apt/lists/*

# 国内 pip 源（海外服务器可删掉本段）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 先拷依赖清单，利用 Docker 层缓存
COPY gridgo-server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 拷贝后端代码（根 .dockerignore 已排除 .venv / node_modules / __pycache__ / .env 等）
COPY gridgo-server/ /app/

EXPOSE 8001

# 健康检查：slim 镜像无 curl，用 urllib 打内置 /health
HEALTHCHECK --interval=10s --timeout=5s --retries=10 --start-period=30s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3).status==200 else 1)"

CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_classic_map && exec uvicorn app.main:app --host 0.0.0.0 --port 8001"]
