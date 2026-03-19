"""
应用配置 - 支持环境变量和 .env 文件
"""
import os
import secrets
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 忽略额外的环境变量
    )

    # ==================== 应用配置 ====================
    APP_NAME: str = "AgentMarketplace"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    
    # 基础路径
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # ==================== 安全配置 ====================
    # 注意：生产环境必须设置固定的 SECRET_KEY
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天
    
    # JWT刷新令牌过期时间 (天)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ==================== 数据库配置 ====================
    DATABASE_URL: str = "sqlite+aiosqlite:///./agent_marketplace.db"
    
    # ==================== Redis配置 ====================
    REDIS_URL: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None

    # ==================== CORS配置 ====================
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000", 
        "http://localhost:5173", 
        "http://127.0.0.1:5173"
    ]

    # ==================== WebSocket配置 ====================
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_URL: str = "ws://localhost:8000/ws"
    
    # TLS证书路径 (生产环境)
    SSL_CERT_FILE: Optional[str] = None
    SSL_KEY_FILE: Optional[str] = None

    # ==================== Agent协议配置 ====================
    ACP_VERSION: str = "1.0"
    HANDSHAKE_TIMEOUT: int = 30
    SESSION_TIMEOUT: int = 3600
    
    # ==================== 外部API配置 (可选) ====================
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = "https://api.openai.com/v1"
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # ==================== 向量搜索配置 ====================
    EMBEDDING_PROVIDER: str = "local"  # local | openai
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    
    # ==================== 日志配置 ====================
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # ==================== 监控配置 ====================
    ENABLE_METRICS: bool = False
    METRICS_PORT: int = 9090

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_config()
    
    def _validate_config(self):
        """验证配置有效性"""
        # 生产环境检查
        if not self.DEBUG:
            # SECRET_KEY 检查
            if not self.SECRET_KEY or self.SECRET_KEY == "":
                # 检查是否使用了自动生成的默认值
                logger.warning(
                    "⚠️ 生产环境未配置 SECRET_KEY！"
                    "请在 .env 文件中设置 SECRET_KEY=your-secure-random-key"
                )
                # 不抛出异常，但记录警告
            
            # WS_URL 检查
            if self.WS_URL.startswith("ws://") and not self.WS_URL.startswith("ws://localhost"):
                logger.warning(
                    "⚠️ 生产环境 WebSocket 使用明文 ws://！"
                    "请使用 wss:// 协议确保通信安全"
                )
                
            # 数据库检查
            if self.DATABASE_URL.startswith("sqlite"):
                logger.warning(
                    "⚠️ 生产环境建议使用 PostgreSQL 而非 SQLite"
                )
    
    def get_secret_key(self) -> str:
        """获取 SECRET_KEY，如果是空的则生成一个临时密钥"""
        if not self.SECRET_KEY:
            # 开发环境生成临时密钥
            logger.info("使用自动生成的临时 SECRET_KEY（仅限开发环境）")
            return secrets.token_urlsafe(32)
        return self.SECRET_KEY
    
    def get_database_url(self) -> str:
        """获取数据库URL"""
        return self.DATABASE_URL
    
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.DEBUG
    
    def get_redis_url(self) -> Optional[str]:
        """获取Redis URL"""
        if self.REDIS_URL:
            if self.REDIS_PASSWORD:
                return self.REDIS_URL.replace("redis://", f"redis://:{self.REDIS_PASSWORD}@")
            return self.REDIS_URL
        return None
    
    def get_ws_url(self) -> str:
        """获取 WebSocket URL（带协议检查）"""
        if not self.DEBUG and not self.WS_URL.startswith("wss://"):
            # 生产环境强制使用 WSS
            logger.warning("生产环境强制使用 WSS 协议")
            return self.WS_URL.replace("ws://", "wss://", 1)
        return self.WS_URL


# 全局配置实例
settings = Settings()


def get_settings() -> Settings:
    """获取配置实例 (用于依赖注入)"""
    return settings
