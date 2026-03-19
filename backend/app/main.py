"""
FastAPI主应用入口
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.background import BackgroundTasks
import logging
import asyncio

from app.core.config import settings
from app.core.database import init_db
from app.api.agents import router as agents_router
from app.api.guest_agents import router as guest_router
from app.api.websocket import router as ws_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_database_with_retry(max_retries: int = 3, retry_delay: float = 2.0) -> bool:
    """
    带重试的数据库初始化
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    """
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Database initialization attempt {attempt}/{max_retries}...")
            await init_db()
            logger.info("Database initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Database initialization attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
            else:
                logger.critical(f"Database initialization failed after {max_retries} attempts")
                raise
    return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库（带重试）
    logger.info("Starting AgentMarketplace platform...")
    
    try:
        await init_database_with_retry()
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}")
        # 不抛出异常，让应用继续启动以便调试
    
    logger.info(f"AgentMarketplace v{settings.APP_VERSION} is ready!")
    
    yield
    
    logger.info("Shutting down AgentMarketplace platform...")


# 创建应用
app = FastAPI(
    title=settings.APP_NAME,
    description="AI智能体开放集市平台 - 基于ACP协议的Agent互联互通平台",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件挂载（如果目录存在）
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Mounted static files from: {static_dir}")
else:
    logger.info("Static directory not found, skipping mount")

# 注册路由
app.include_router(agents_router, prefix="/api")
app.include_router(guest_router, prefix="/api")
app.include_router(ws_router)

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "platform": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "debug": settings.DEBUG
    }

@app.get("/")
async def root():
    """根路径"""
    return {
        "name": settings.APP_NAME,
        "description": "AI智能体开放集市平台",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时的额外初始化"""
    logger.info(f"Environment: {'Production' if not settings.DEBUG else 'Development'}")
    logger.info(f"Database: {settings.DATABASE_URL.split('://')[0]}")
    if settings.REDIS_URL:
        logger.info(f"Redis: {settings.REDIS_URL.split('@')[1] if '@' in settings.REDIS_URL else 'configured'}")


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info("Performing cleanup...")
    # 可以在这里关闭数据库连接池等
    logger.info("Cleanup completed")
