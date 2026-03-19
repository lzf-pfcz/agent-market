"""
访客Agent API - 支持用完即走的用户Agent
访客Agent不需要注册，直接临时接入平台使用服务
"""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.core.security import generate_agent_token
from app.models.models import Agent
from app.services.connection_manager import connection_manager

router = APIRouter(prefix="/guest", tags=["guest-agents"])


class GuestTokenRequest(BaseModel):
    """访客Agent临时Token请求"""
    name: str  # 访客名称
    purpose: str  # 访问目的


class GuestTokenResponse(BaseModel):
    """访客Agent临时Token响应"""
    guest_id: str
    token: str
    message: str
    expires_in: int  # Token有效期（秒）


class AgentServiceInfo(BaseModel):
    """Agent服务信息"""
    agent_id: str
    name: str
    description: str
    capabilities: List[dict]
    tags: List[str]
    status: str
    stats: dict


# 存储访客Token的简单内存缓存（生产环境应使用Redis）
GUEST_TOKENS = {}  # {token: {"guest_id": str, "name": str, "expires": datetime}}


@router.post("/token", response_model=GuestTokenResponse)
async def create_guest_token(request: GuestTokenRequest):
    """
    为访客Agent创建临时Token
    
    访客Agent无需注册，通过此接口获取临时Token即可接入平台
    Token有效期为1小时，过期自动失效
    """
    guest_id = str(uuid.uuid4())
    token = generate_agent_token(guest_id)
    
    # Token有效期1小时
    expires = datetime.utcnow() + timedelta(hours=1)
    
    GUEST_TOKENS[token] = {
        "guest_id": guest_id,
        "name": request.name,
        "purpose": request.purpose,
        "expires": expires
    }
    
    return GuestTokenResponse(
        guest_id=guest_id,
        token=token,
        message=f"访客Token已创建，有效期1小时",
        expires_in=3600
    )


@router.get("/services")
async def list_available_services(
    search: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    列出所有可用的服务Agent
    
    访客Agent通过此接口发现平台上的服务Agent
    """
    query = select(Agent).where(Agent.is_public == True)
    
    if search:
        query = query.where(
            or_(
                Agent.name.ilike(f"%{search}%"),
                Agent.description.ilike(f"%{search}%")
            )
        )
    
    result = await db.execute(query)
    agents = result.scalars().all()
    
    # 过滤tag
    if tag:
        agents = [a for a in agents if tag in (a.tags or [])]
    
    # 实时更新在线状态
    online_ids = set(connection_manager.get_online_agents())
    
    return [
        {
            "agent_id": a.id,
            "name": a.name,
            "description": a.description,
            "capabilities": a.capabilities or [],
            "tags": a.tags or [],
            "status": "online" if a.id in online_ids else "offline",
            "stats": {
                "total_calls": a.total_calls,
                "success_calls": a.success_calls,
                "success_rate": f"{(a.success_calls / a.total_calls * 100):.1f}%" if a.total_calls > 0 else "0%"
            },
            "endpoint": f"/ws/agent/{a.id}"
        }
        for a in agents
    ]


@router.get("/services/discover")
async def discover_services(
    query: str = Query(..., description="搜索关键词"),
    db: AsyncSession = Depends(get_db)
):
    """
    服务发现 - 根据关键词查找合适的Agent
    
    这是访客Agent最常用的接口，用于寻找能提供所需服务的Agent
    """
    search_query = select(Agent).where(
        Agent.is_public == True,
        or_(
            Agent.name.ilike(f"%{query}%"),
            Agent.description.ilike(f"%{query}%"),
            # 在tags中搜索（SQLite JSON兼容性处理）
        )
    )
    
    result = await db.execute(search_query)
    agents = result.scalars().all()
    
    # 进一步过滤tags和capabilities
    filtered_agents = []
    for agent in agents:
        tags = agent.tags or []
        capabilities = agent.capabilities or []
        
        # 在tags中匹配
        if any(query.lower() in str(tag).lower() for tag in tags):
            filtered_agents.append(agent)
            continue
        
        # 在capabilities中匹配
        for cap in capabilities:
            if query.lower() in str(cap.get("name", "")).lower() or \
               query.lower() in str(cap.get("description", "")).lower():
                filtered_agents.append(agent)
                break
    
    # 实时更新在线状态
    online_ids = set(connection_manager.get_online_agents())
    
    return [
        {
            "agent_id": a.id,
            "name": a.name,
            "description": a.description,
            "capabilities": a.capabilities or [],
            "tags": a.tags or [],
            "status": "online" if a.id in online_ids else "offline",
            "match_score": calculate_match_score(a, query)
        }
        for a in filtered_agents
    ]


def calculate_match_score(agent: Agent, query: str) -> float:
    """计算匹配分数（0-1之间）"""
    score = 0.0
    query_lower = query.lower()
    
    # 名称匹配
    if query_lower in agent.name.lower():
        score += 0.5
    
    # 描述匹配
    if query_lower in agent.description.lower():
        score += 0.3
    
    # 标签匹配
    if agent.tags:
        for tag in agent.tags:
            if query_lower in str(tag).lower():
                score += 0.2
                break
    
    return min(score, 1.0)


@router.delete("/token/{token}")
async def revoke_guest_token(token: str):
    """
    撤销访客Token
    
    访客Agent使用完服务后，应主动撤销Token（用完即走）
    """
    if token in GUEST_TOKENS:
        del GUEST_TOKENS[token]
        return {"message": "Token已撤销"}
    else:
        raise HTTPException(status_code=404, detail="Token不存在")
