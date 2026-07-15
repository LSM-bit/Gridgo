FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai

# 换用国内 Debian 镜像源（解决网络不稳定问题）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖（gcc 用于编译 bcrypt 等包）
RUN apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing gcc default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*

# 换用国内 pip 镜像源
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.trusted-host mirrors.aliyun.com

# 先复制依赖文件，利用 Docker 缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8001

# 启动命令（先运行数据库迁移，再启动服务）
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_classic_map && uvicorn app.main:app --host 0.0.0.0 --port 8001"]
