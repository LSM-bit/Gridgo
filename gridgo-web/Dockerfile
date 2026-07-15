# ===== 阶段1: 构建前端 =====
FROM node:22-alpine AS builder

# 设置国内 npm 镜像（corepack 和 pnpm 都会使用）
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com
RUN corepack enable && corepack prepare pnpm@9 --activate

# pnpm 也用国内镜像
RUN pnpm config set registry https://registry.npmmirror.com

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存
COPY package.json pnpm-lock.yaml ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源代码
COPY . .

# 构建生产版本
RUN pnpm build

# ===== 阶段2: Nginx 服务 =====
FROM nginx:alpine

# 设置时区
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && cp /usr/share/zoneinfo/$TZ /etc/localtime

# 复制构建产物到 Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
