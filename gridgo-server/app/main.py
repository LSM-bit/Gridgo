"""
GridGo 后端应用入口
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.access_log import AccessLogMiddleware
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.friend import router as friend_router
from app.api.v1.game import router as game_router
from app.api.v1.leaderboard import router as leaderboard_router
from app.api.v1.room import router as room_router
from app.api.v1.user import router as user_router
from app.api.ws.game_ws import router as ws_router
from app.core.config import settings
from app.core.logging import app_logger
from app.core.redis import close_redis, init_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    app_logger.info("%s v%s starting...", settings.APP_NAME, settings.APP_VERSION)
    await init_redis()
    yield
    # 关闭时
    await close_redis()
    app_logger.info("%s shutting down...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="GridGo - 大富翁游戏后端 API",
    lifespan=lifespan,
)

# 请求日志中间件（必须在 CORS 之前注册，才能拦截到所有请求）
app.add_middleware(AccessLogMiddleware)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 REST API 路由
app.include_router(auth_router, prefix="/api/v1")
app.include_router(room_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(game_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(friend_router, prefix="/api/v1")
app.include_router(leaderboard_router, prefix="/api/v1")

# 注册 WebSocket 路由
app.include_router(ws_router, prefix="/ws")


@app.get("/")
async def root():
    """健康检查"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}
