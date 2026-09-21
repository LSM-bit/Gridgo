# GridGo 前端镜像（多阶段：node 构建 → nginx 托管，构建上下文为仓库根）
# 构建: docker build -f deploy/web.Dockerfile -t gridgo-web .
#
# 要点：
#   - 前端构建配置不改（沿用 gridgo-web/ 现有 vite/uno 配置）；前端请求走相对路径
#     （REST baseURL=/api/v1，WS 同源 /ws/game），因此站点挂根路径即可，无需 build 参数
#   - nginx 配置用 deploy/nginx/default.conf，把 /api/、/ws/ 反代到 compose 服务名 server:8001
#     （与 gridgo-web/nginx.conf 的逻辑一致，仅代理目标改为生产服务名）
FROM node:22-alpine AS builder

# 国内 npm 镜像（corepack / pnpm 都用它；海外服务器可删掉这两行 ENV/RUN 中的 registry 设置）
ENV COREPACK_NPM_REGISTRY=https://registry.npmmirror.com
RUN corepack enable && corepack prepare pnpm@9 --activate && \
    pnpm config set registry https://registry.npmmirror.com

WORKDIR /app

# 先拷依赖清单，利用 Docker 层缓存
COPY gridgo-web/package.json gridgo-web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 拷贝前端源码并构建（根 .dockerignore 已排除 node_modules / dist）
COPY gridgo-web/ ./
RUN pnpm build

# ===== 阶段2：nginx 托管产物 =====
FROM nginx:alpine

ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && cp /usr/share/zoneinfo/$TZ /etc/localtime

# 站点 nginx 配置（根路径托管 + /api/、/ws/ 反代，见 deploy/nginx/default.conf）
COPY deploy/nginx/default.conf /etc/nginx/conf.d/default.conf

# 构建产物直接挂根路径
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
