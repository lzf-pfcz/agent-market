"""
事件广播服务 - 向前端推送实时事件
"""
import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class EventBroadcaster:
    """向前端监控页面广播平台事件"""

    def __init__(self):
        self.frontend_connections: List[WebSocket] = []

    async def connect_frontend(self, websocket: WebSocket):
        await websocket.accept()
        self.frontend_connections.append(websocket)
        logger.info(f"Frontend monitor connected. Total: {len(self.frontend_connections)}")

    def disconnect_frontend(self, websocket: WebSocket):
        if websocket in self.frontend_connections:
            self.frontend_connections.remove(websocket)

    async def broadcast_event(self, event_type: str, data: Dict[str, Any]):
        """广播平台事件给所有前端"""
        if not self.frontend_connections:
            return
        message = json.dumps({"event": event_type, "data": data})
        disconnected = []
        for ws in self.frontend_connections:
            try:
                await ws.send_text(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect_frontend(ws)

    async def emit_agent_online(self, agent_id: str, agent_name: str):
        await self.broadcast_event("agent.online", {"agent_id": agent_id, "name": agent_name})

    async def emit_agent_offline(self, agent_id: str, agent_name: str):
        await self.broadcast_event("agent.offline", {"agent_id": agent_id, "name": agent_name})

    async def emit_handshake(self, session_id: str, initiator: str, responder: str, status: str):
        await self.broadcast_event("handshake", {
            "session_id": session_id,
            "initiator": initiator,
            "responder": responder,
            "status": status
        })

    async def emit_task(self, session_id: str, from_agent: str, to_agent: str, task_type: str, detail: str):
        await self.broadcast_event("task", {
            "session_id": session_id,
            "from": from_agent,
            "to": to_agent,
            "task_type": task_type,
            "detail": detail
        })

    async def emit_activity(self, description: str, agent_id: str = None):
        await self.broadcast_event("activity", {
            "description": description,
            "agent_id": agent_id
        })


# 全局单例
event_broadcaster = EventBroadcaster()
