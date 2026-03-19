"""
Agent注册中心 - 管理所有在线Agent的连接
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Set
from fastapi import WebSocket
from app.core.protocol import ACPMessage, MessageType

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器 - 维护所有Agent的实时连接"""

    def __init__(self):
        # agent_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # agent_id -> Set[session_id]
        self.agent_sessions: Dict[str, Set[str]] = {}
        # session_id -> (agent_id, agent_id)
        self.sessions: Dict[str, tuple] = {}

    async def connect(self, agent_id: str, websocket: WebSocket):
        """Agent上线"""
        await websocket.accept()
        self.active_connections[agent_id] = websocket
        self.agent_sessions.setdefault(agent_id, set())
        logger.info(f"Agent {agent_id} connected. Total online: {len(self.active_connections)}")

    def disconnect(self, agent_id: str):
        """Agent下线"""
        if agent_id in self.active_connections:
            del self.active_connections[agent_id]
        if agent_id in self.agent_sessions:
            del self.agent_sessions[agent_id]
        logger.info(f"Agent {agent_id} disconnected. Total online: {len(self.active_connections)}")

    def is_online(self, agent_id: str) -> bool:
        return agent_id in self.active_connections

    def get_online_agents(self) -> list:
        return list(self.active_connections.keys())

    async def send_to_agent(self, agent_id: str, message: ACPMessage) -> bool:
        """发送消息给指定Agent"""
        if agent_id not in self.active_connections:
            logger.warning(f"Agent {agent_id} is offline, cannot deliver message")
            return False
        try:
            ws = self.active_connections[agent_id]
            await ws.send_text(message.model_dump_json())
            return True
        except Exception as e:
            logger.error(f"Failed to send message to agent {agent_id}: {e}")
            self.disconnect(agent_id)
            return False

    async def send_raw(self, agent_id: str, data: dict) -> bool:
        """发送原始JSON数据"""
        if agent_id not in self.active_connections:
            return False
        try:
            ws = self.active_connections[agent_id]
            await ws.send_text(json.dumps(data))
            return True
        except Exception as e:
            logger.error(f"Failed to send raw message to agent {agent_id}: {e}")
            self.disconnect(agent_id)
            return False

    async def broadcast_to_all(self, message: ACPMessage):
        """广播消息给所有在线Agent"""
        disconnected = []
        for agent_id, ws in self.active_connections.items():
            try:
                await ws.send_text(message.model_dump_json())
            except Exception:
                disconnected.append(agent_id)
        for agent_id in disconnected:
            self.disconnect(agent_id)

    def register_session(self, session_id: str, initiator_id: str, responder_id: str):
        """注册握手会话"""
        self.sessions[session_id] = (initiator_id, responder_id)
        self.agent_sessions.setdefault(initiator_id, set()).add(session_id)
        self.agent_sessions.setdefault(responder_id, set()).add(session_id)

    def close_session(self, session_id: str):
        """关闭会话"""
        if session_id in self.sessions:
            initiator_id, responder_id = self.sessions[session_id]
            self.agent_sessions.get(initiator_id, set()).discard(session_id)
            self.agent_sessions.get(responder_id, set()).discard(session_id)
            del self.sessions[session_id]


# 全局单例
connection_manager = ConnectionManager()
