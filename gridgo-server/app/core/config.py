"""
GridGo 后端配置管理
使用 pydantic-settings 从环境变量加载配置
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # 应用
    APP_NAME: str = "GridGo"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 服务器
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # 数据库 - PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://gridgo:gridgo123@127.0.0.1:3307/gridgo"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "gridgo-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 天
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # 雪花 ID（64 位整数，见 app/utils/snowflake.py）
    SNOWFLAKE_WORKER_ID: int = 0  # 节点 ID（0-1023），多实例部署时区分

    # 游戏
    GAME_INITIAL_CASH: int = 1500 # 初始现金
    GAME_PASS_GO_BONUS: int = 200 # 过路费
    GAME_TURN_TIMEOUT: int = 30 # 回合超时时间
    GAME_MAX_PLAYERS: int = 8 # 最大玩家数
    GAME_MAX_TURNS: int = 100 # 最大回合数

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
