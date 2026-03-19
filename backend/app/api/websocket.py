"""
WebSocket通信中枢 - 处理Agent间的实时通信
改进版：统一会话管理、原子操作、统一错误处理
"""
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from datetime import datetime

from app.core.database import get_db, AsyncSessionLocal
from app.core.protocol import ACPMessage, MessageType
from app.core.security import decode_token, create_audit_log
from app.core.errors import APIError, ErrorCode, agent_not_found, agent_offline
from app.models.models import Agent, Session, Message, ActivityLog
from app.services.connection_manager import connection_manager
from app.services.event_broadcaster import event_broadcaster
from app.services.handshake import handshake_handler

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


async def send_error(agent_id: str, error: APIError) -> None:
    """
    统一发送错误消息
    
    将 APIError 转换为 system.error 消息格式发送
    """
    error_msg = ACPMessage(
        type=MessageType.SYSTEM_ERROR,
        from_agent="platform",
        to_agent=agent_id,
        payload={
            "error_code": error.code.value,
            "message": error.message,
            "details": error.details
        }
    )
    await connection_manager.send_to_agent(agent_id, error_msg)


async def handle_agent_message(msg: ACPMessage) -> None:
    """
    消息路由中心 - 统一数据库会话管理
    
    所有数据库操作在同一个会话中完成，最后统一提交
    """
    async with AsyncSessionLocal() as db:
        try:
            # 记录消息到数据库
            if msg.session_id:
                db_msg = Message(
                    id=msg.id,
                    session_id=msg.session_id,
                    from_agent_id=msg.from_agent,
                    to_agent_id=msg.to_agent,
                    message_type=msg.type,
                    payload=msg.payload
                )
                db.add(db_msg)

            # 根据消息类型分发处理
            if msg.type == MessageType.HANDSHAKE_INIT:
                await handshake_handler.handle_handshake_init(msg, db)

            elif msg.type == MessageType.HANDSHAKE_RESPONSE:
                await handshake_handler.handle_handshake_response(msg, db)

            elif msg.type == MessageType.DISCOVER_REQUEST:
                await handle_discover(msg, db)

            elif msg.type in [MessageType.TASK_REQUEST, MessageType.TASK_RESULT,
                              MessageType.TASK_ACK, MessageType.TASK_PROGRESS, MessageType.TASK_ERROR]:
                await handle_task_message(msg, db)

            elif msg.type == MessageType.SESSION_HEARTBEAT:
                # 使用原子操作更新心跳
                await db.execute(
                    update(Agent)
                    .where(Agent.id == msg.from_agent)
                    .values(last_active=datetime.utcnow())
                )

            elif msg.type == MessageType.SESSION_CLOSE:
                await handle_session_close(msg, db)

            # 统一提交
            await db.commit()

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await db.rollback()
            # 发送错误消息
            await send_error(msg.from_agent, APIError(
                ErrorCode.COMMON_INTERNAL_ERROR,
                f"Message handling error: {str(e)}"
            ))


async def handle_discover(msg: ACPMessage, db: AsyncSession):
    """处理Agent服务发现请求"""
    query_text = msg.payload.get("query", "")

    result = await db.execute(
        select(Agent).where(
            and_(
                Agent.is_public == True,
                Agent.id != msg.from_agent
            )
        )
    )
    agents = result.scalars().all()
    
    # 内存中过滤（更高效）
    online_ids = set(connection_manager.get_online_agents())
    
    # 关键词匹配
    query_lower = query_text.lower()
    discovered = []
    for a in agents:
        if (query_lower in a.name.lower() or 
            query_lower in (a.description or "").lower() or
            any(query_lower in tag.lower() for tag in (a.tags or []))):
            discovered.append({
                "agent_id": a.id,
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities or [],
                "tags": a.tags or [],
                "status": "online" if a.id in online_ids else a.status,
                "endpoint": f"/ws/agent/{a.id}"
            })

    response = ACPMessage(
        type=MessageType.DISCOVER_RESPONSE,
        from_agent="platform",
        to_agent=msg.from_agent,
        payload={
            "query": query_text,
            "results": discovered,
            "count": len(discovered)
        }
    )
    await connection_manager.send_to_agent(msg.from_agent, response)
    
    # 记录活动日志
    log = ActivityLog(
        event_type="discover",
        agent_id=msg.from_agent,
        description=f"搜索服务: '{query_text}'，找到 {len(discovered)} 个Agent",
        extra_data={"query": query_text, "count": len(discovered)}
    )
    db.add(log)


async def handle_task_message(msg: ACPMessage, db: AsyncSession):
    """中继任务消息（平台作为中间人转发）"""
    target_id = msg.to_agent
    
    # 检查目标是否在线
    if not target_id or not connection_manager.is_online(target_id):
        await send_error(msg.from_agent, APIError(
            ErrorCode.AGENT_OFFLINE,
            f"Target agent {target_id or 'unknown'} is offline",
            agent_id=target_id
        ))
        return

    # 转发消息
    await connection_manager.send_to_agent(target_id, msg)

    # 更新统计 - 使用原子操作
    if msg.type == MessageType.TASK_REQUEST:
        # 原子递增 total_calls
        await db.execute(
            update(Agent)
            .where(Agent.id == target_id)
            .values(total_calls=Agent.total_calls + 1)
        )

        from_agent = await db.get(Agent, msg.from_agent)
        to_agent = await db.get(Agent, target_id)
        from_name = from_agent.name if from_agent else msg.from_agent
        to_name = to_agent.name if to_agent else target_id

        await event_broadcaster.emit_task(
            msg.session_id or "unknown",
            from_name, to_name,
            "request",
            msg.payload.get("task_description", "任务请求")
        )
        
        # 记录审计日志
        audit = create_audit_log(
            event="task_request",
            agent_id=msg.from_agent,
            action="send_task",
            result="success",
            details={"target": target_id, "task_type": msg.payload.get("task_type")}
        )
        logger.info(f"Audit: {audit}")

    elif msg.type == MessageType.TASK_RESULT:
        # 原子递增 success_calls
        await db.execute(
            update(Agent)
            .where(Agent.id == msg.from_agent)
            .values(success_calls=Agent.success_calls + 1)
        )

        from_agent = await db.get(Agent, msg.from_agent)
        to_agent = await db.get(Agent, target_id)
        
        await event_broadcaster.emit_task(
            msg.session_id or "unknown",
            from_agent.name if from_agent else msg.from_agent,
            to_agent.name if to_agent else target_id,
            "result",
            "任务完成，返回结果"
        )

        # 记录任务完成日志
        log = ActivityLog(
            event_type="task_complete",
            agent_id=msg.from_agent,
            target_agent_id=target_id,
            description=f"任务执行完成",
            extra_data={"session_id": msg.session_id}
        )
        db.add(log)


async def handle_session_close(msg: ACPMessage, db: AsyncSession):
    """处理会话关闭"""
    session_id = msg.session_id
    if not session_id:
        return

    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if session and session.status == "established":
        await db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(status="closed", closed_at=datetime.utcnow())
        )

        # 通知对方
        peer_id = session.responder_id if msg.from_agent == session.initiator_id else session.initiator_id
        close_msg = ACPMessage(
            type=MessageType.SESSION_CLOSE,
            from_agent=msg.from_agent,
            to_agent=peer_id,
            session_id=session_id,
            payload={"reason": msg.payload.get("reason", "Session closed by peer")}
        )
        await connection_manager.send_to_agent(peer_id, close_msg)
        connection_manager.close_session(session_id)

        from_agent = await db.get(Agent, msg.from_agent)
        
        # 记录日志
        log = ActivityLog(
            event_type="session_close",
            agent_id=msg.from_agent,
            target_agent_id=peer_id,
            description=f"会话结束: {from_agent.name if from_agent else msg.from_agent}",
            extra_data={"session_id": session_id}
        )
        db.add(log)


@router.websocket("/ws/agent/{agent_id}")
async def agent_websocket(
    websocket: WebSocket,
    agent_id: str,
    token: str = Query(...)
):
    """Agent WebSocket连接入口"""
    # 验证Token
    payload = decode_token(token)
    if not payload or payload.get("sub") != agent_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # 连接管理
    await connection_manager.connect(agent_id, websocket)

    # 更新Agent状态
    async with AsyncSessionLocal() as db:
        agent = await db.get(Agent, agent_id)
        if not agent:
            await websocket.close(code=4004, reason="Agent not found")
            return
        await db.execute(
            update(Agent).where(Agent.id == agent_id).values(
                status="online", last_active=datetime.utcnow()
            )
        )
        await db.commit()
        agent_name = agent.name

    await event_broadcaster.emit_agent_online(agent_id, agent_name)
    await event_broadcaster.emit_activity(f"🟢 {agent_name} 已上线", agent_id)

    # 发送欢迎消息
    welcome = ACPMessage(
        type=MessageType.SESSION_OPEN,
        from_agent="platform",
        to_agent=agent_id,
        payload={
            "message": f"Welcome to AgentMarketplace! You are now online.",
            "platform_version": "1.0",
            "online_agents": len(connection_manager.get_online_agents())
        }
    )
    await connection_manager.send_to_agent(agent_id, welcome)

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                msg = ACPMessage(**data)
                msg.from_agent = agent_id  # 强制设置发送方，防止伪造
            except Exception as e:
                logger.warning(f"Invalid message from {agent_id}: {e}")
                await send_error(agent_id, APIError(
                    ErrorCode.PROTOCOL_INVALID_MESSAGE,
                    f"Invalid message format: {str(e)}"
                ))
                continue

            # 分发消息处理（统一会话管理）
            await handle_agent_message(msg)

    except WebSocketDisconnect:
        logger.info(f"Agent {agent_id} disconnected")
    except Exception as e:
        logger.error(f"Error in agent websocket {agent_id}: {e}")
    finally:
        connection_manager.disconnect(agent_id)
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Agent).where(Agent.id == agent_id).values(status="offline")
            )
            await db.commit()
        await event_broadcaster.emit_agent_offline(agent_id, agent_name)
        await event_broadcaster.emit_activity(f"🔴 {agent_name} 已下线", agent_id)


@router.websocket("/ws/monitor")
async def monitor_websocket(websocket: WebSocket):
    """前端监控WebSocket - 推送平台实时事件"""
    await event_broadcaster.connect_frontend(websocket)
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        event_broadcaster.disconnect_frontend(websocket)


@router.get("/sessions/list")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """获取会话列表"""
    result = await db.execute(
        select(Session).order_by(Session.created_at.desc()).limit(50)
    )
    sessions = result.scalars().all()

    return [
        {
            "id": s.id,
            "initiator_id": s.initiator_id,
            "responder_id": s.responder_id,
            "status": s.status,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "established_at": s.established_at.isoformat() if s.established_at else None,
            "closed_at": s.closed_at.isoformat() if s.closed_at else None
        }
        for s in sessions
    ]


@router.get("/activity/logs")
async def get_activity_logs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """获取平台活动日志"""
    result = await db.execute(
        select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(limit)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "agent_id": log.agent_id,
            "target_agent_id": log.target_agent_id,
            "description": log.description,
            "metadata": log.extra_data,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]
