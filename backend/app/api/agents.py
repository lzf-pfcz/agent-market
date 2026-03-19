"""
Agent管理API - 注册、查询、更新Agent
"""
import uuid
import secrets
import logging
from typing import List, Optional
from datetime import datetime
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, and_

from app.core.database import get_db
from app.core.security import generate_agent_token
from app.models.models import Agent, ActivityLog
from app.services.connection_manager import connection_manager
from app.services.event_broadcaster import event_broadcaster

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


# ==================== Pydantic Models ====================

class AgentCapabilityInput(BaseModel):
    """Agent能力描述 - 用于输入验证"""
    name: str = Field(..., description="能力名称，如 flight_search")
    description: str = Field(..., description="能力描述")
    input_schema: dict = Field(default_factory=dict, description="输入参数JSON Schema")
    output_schema: dict = Field(default_factory=dict, description="输出参数JSON Schema")
    examples: List[dict] = Field(default_factory=list, description="使用示例")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.replace('_', '').isalnum():
            raise ValueError('Name must be alphanumeric with optional underscores')
        return v


class AgentRegisterRequest(BaseModel):
    """Agent注册请求"""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    owner_name: str
    avatar: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    capabilities: List[AgentCapabilityInput] = Field(default_factory=list)
    is_public: bool = True


class AgentRegisterResponse(BaseModel):
    agent_id: str
    secret_key: str
    token: str
    message: str
    warning: Optional[str] = None


class AgentInfo(BaseModel):
    id: str
    name: str
    description: str
    owner_name: str
    avatar: Optional[str]
    tags: List[str]
    capabilities: List[dict]
    status: str
    is_public: bool
    total_calls: int
    success_calls: int
    created_at: str


class PaginatedAgentsResponse(BaseModel):
    """分页Agent列表响应"""
    items: List[AgentInfo]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== 在线状态缓存 ====================

class OnlineStatusCache:
    """在线状态缓存 - 减少频繁调用"""
    
    def __init__(self, cache_ttl: int = 5):
        self._cache: Optional[set] = None
        self._cache_time: float = 0
        self._cache_ttl = cache_ttl
    
    def get_online_ids(self, force_refresh: bool = False) -> set:
        """获取在线Agent ID缓存"""
        import time
        now = time.time()
        
        if self._cache is None or force_refresh or (now - self._cache_time) > self._cache_ttl:
            self._cache = set(connection_manager.get_online_agents())
            self._cache_time = now
            logger.debug(f"Refreshed online cache: {len(self._cache)} agents")
        
        return self._cache


# 全局缓存实例
_online_cache = OnlineStatusCache(cache_ttl=5)


# ==================== 异步日志记录 ====================

async def log_activity_async(
    event_type: str,
    agent_id: str,
    description: str,
    target_agent_id: str = None,
    extra_data: dict = None
):
    """异步记录活动日志"""
    try:
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            log = ActivityLog(
                event_type=event_type,
                agent_id=agent_id,
                target_agent_id=target_agent_id,
                description=description,
                extra_data=extra_data or {}
            )
            db.add(log)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")


# ==================== API Endpoints ====================

@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(
    request: AgentRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    注册新Agent到平台
    
    注意：secret_key 只返回一次，请妥善保管！
    """
    agent_id = str(uuid.uuid4())
    secret_key = secrets.token_hex(32)
    token = generate_agent_token(agent_id)

    # 转换capabilities为dict列表
    capabilities_list = [cap.model_dump() for cap in request.capabilities] if request.capabilities else []

    agent = Agent(
        id=agent_id,
        name=request.name,
        description=request.description,
        owner_name=request.owner_name,
        avatar=request.avatar,
        tags=request.tags,
        capabilities=capabilities_list,
        secret_key=secret_key,
        is_public=request.is_public,
        status="offline"
    )
    db.add(agent)
    
    log = ActivityLog(
        event_type="register",
        agent_id=agent_id,
        description=f"新Agent '{request.name}' 注册到平台",
        extra_data={"owner": request.owner_name, "capabilities": len(capabilities_list)}
    )
    db.add(log)
    await db.commit()

    # 异步广播活动
    background_tasks.add_task(
        event_broadcaster.emit_activity,
        f"新Agent '{request.name}' 已注册到平台",
        agent_id
    )
    
    # 异步记录详细日志
    background_tasks.add_task(
        log_activity_async,
        "agent_registered",
        agent_id,
        f"Agent '{request.name}' registered",
        extra_data={"owner": request.owner_name}
    )

    return AgentRegisterResponse(
        agent_id=agent_id,
        secret_key=secret_key,
        token=token,
        message=f"Agent '{request.name}' registered successfully!",
        warning="⚠️ secret_key 只返回一次，请妥善保存！"
    )


@router.get("/", response_model=PaginatedAgentsResponse)
async def list_agents(
    search: Optional[str] = Query(None, description="搜索关键词"),
    tag: Optional[str] = Query(None, description="按标签过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取Agent列表（支持搜索和分页）
    
    - search: 搜索名称或描述
    - tag: 按标签过滤
    - status: 按状态过滤 (online/offline)
    - page: 页码
    - page_size: 每页数量
    """
    # 构建查询条件
    conditions = [Agent.is_public == True]
    
    if search:
        conditions.append(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%")
            )
        )
    
    if status:
        conditions.append(Agent.status == status)
    
    # 查询总数
    count_query = select(func.count(Agent.id)).where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 查询分页数据
    query = (
        select(Agent)
        .where(and_(*conditions))
        .order_by(Agent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    agents = result.scalars().all()
    
    # 使用缓存获取在线状态
    online_ids = _online_cache.get_online_ids()
    
    # 构建响应
    items = []
    for agent in agents:
        # tag过滤在Python层处理（因为SQLite JSON支持有限）
        if tag and tag not in (agent.tags or []):
            continue
        
        live_status = "online" if agent.id in online_ids else agent.status
        items.append(AgentInfo(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            owner_name=agent.owner_name or "",
            avatar=agent.avatar,
            tags=agent.tags or [],
            capabilities=agent.capabilities or [],
            status=live_status,
            is_public=agent.is_public,
            total_calls=agent.total_calls,
            success_calls=agent.success_calls,
            created_at=agent.created_at.isoformat() if agent.created_at else ""
        ))
    
    return PaginatedAgentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0
    )


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个Agent详情"""
    agent = await db.get(Agent, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 使用缓存获取在线状态
    online_ids = _online_cache.get_online_ids()
    live_status = "online" if agent.id in online_ids else agent.status

    return AgentInfo(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        owner_name=agent.owner_name or "",
        avatar=agent.avatar,
        tags=agent.tags or [],
        capabilities=agent.capabilities or [],
        status=live_status,
        is_public=agent.is_public,
        total_calls=agent.total_calls,
        success_calls=agent.success_calls,
        created_at=agent.created_at.isoformat() if agent.created_at else ""
    )


@router.get("/discover/search")
async def discover_agents(
    query: str = Query(..., description="搜索关键词或能力描述"),
    limit: int = Query(10, ge=1, le=50, description="返回数量限制"),
    db: AsyncSession = Depends(get_db)
):
    """
    Agent服务发现接口 - 供Agent调用
    
    返回匹配的Agent列表
    """
    search_query = (
        select(Agent)
        .where(
            and_(
                Agent.is_public == True,
                or_(
                    Agent.name.ilike(f"%{query}%"),
                    Agent.description.ilike(f"%{query}%")
                )
            )
        )
        .limit(limit)
    )
    result = await db.execute(search_query)
    agents = result.scalars().all()

    # 使用缓存
    online_ids = _online_cache.get_online_ids()

    return [
        {
            "agent_id": a.id,
            "name": a.name,
            "description": a.description,
            "capabilities": a.capabilities or [],
            "tags": a.tags or [],
            "status": "online" if a.id in online_ids else a.status,
            "endpoint": f"/ws/agent/{a.id}"
        }
        for a in agents
    ]


@router.get("/stats/overview")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """平台统计数据"""
    # Agent总数
    total_result = await db.execute(select(func.count(Agent.id)))
    total_agents = total_result.scalar() or 0
    
    # 使用缓存的在线数
    online_count = len(_online_cache.get_online_ids())
    
    # 会话统计
    from app.models.models import Session
    sessions_result = await db.execute(
        select(func.count(Session.id)).where(Session.status == "established")
    )
    active_sessions = sessions_result.scalar() or 0
    
    total_sessions_result = await db.execute(select(func.count(Session.id)))
    total_sessions = total_sessions_result.scalar() or 0
    
    # 计算成功率
    agents_result = await db.execute(
        select(func.sum(Agent.total_calls), func.sum(Agent.success_calls))
    )
    row = agents_result.one()
    total_calls = row[0] or 0
    success_calls = row[1] or 0
    success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0

    return {
        "total_agents": total_agents,
        "online_agents": online_count,
        "active_sessions": active_sessions,
        "total_sessions": total_sessions,
        "total_calls": total_calls,
        "success_calls": success_calls,
        "success_rate": round(success_rate, 2)
    }


@router.post("/refresh-online-cache")
async def refresh_online_cache():
    """手动刷新在线状态缓存"""
    online_ids = _online_cache.get_online_ids(force_refresh=True)
    return {
        "status": "success",
        "online_count": len(online_ids)
    }
