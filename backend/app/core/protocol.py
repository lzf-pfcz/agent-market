"""
Agent Communication Protocol (ACP) v1.0
标准化的Agent间握手与通信协议
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


class MessageType(str, Enum):
    # 握手阶段
    HANDSHAKE_INIT = "handshake.init"          # 发起握手
    HANDSHAKE_CHALLENGE = "handshake.challenge" # 挑战码
    HANDSHAKE_RESPONSE = "handshake.response"   # 回应挑战
    HANDSHAKE_ACK = "handshake.ack"             # 确认建立
    HANDSHAKE_REJECT = "handshake.reject"       # 拒绝握手

    # 会话管理
    SESSION_OPEN = "session.open"
    SESSION_CLOSE = "session.close"
    SESSION_HEARTBEAT = "session.heartbeat"

    # 服务发现
    DISCOVER_REQUEST = "discover.request"       # 搜索Agent
    DISCOVER_RESPONSE = "discover.response"     # 返回结果

    # 任务执行
    TASK_REQUEST = "task.request"               # 发起任务请求
    TASK_ACK = "task.ack"                       # 确认收到任务
    TASK_PROGRESS = "task.progress"             # 任务进度
    TASK_RESULT = "task.result"                 # 任务结果
    TASK_ERROR = "task.error"                   # 任务失败

    # 系统消息
    SYSTEM_REGISTER = "system.register"         # Agent注册到平台
    SYSTEM_HEARTBEAT = "system.heartbeat"       # 平台心跳
    SYSTEM_ERROR = "system.error"


class ACPMessage(BaseModel):
    """ACP标准消息格式"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    protocol_version: str = "1.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    from_agent: Optional[str] = None           # 发送方Agent ID
    to_agent: Optional[str] = None             # 接收方Agent ID
    session_id: Optional[str] = None           # 会话ID
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentCapability(BaseModel):
    """Agent能力描述"""
    name: str                                   # 能力名称，如 "flight_booking"
    description: str                            # 人类可读描述
    input_schema: Dict[str, Any] = {}          # 输入参数JSON Schema
    output_schema: Dict[str, Any] = {}         # 输出参数JSON Schema
    examples: List[Dict[str, Any]] = []        # 使用示例


class AgentCard(BaseModel):
    """Agent名片 - 类似 .well-known/agent.json"""
    agent_id: str
    name: str
    description: str
    owner: str                                  # 所有者（公司/个人）
    avatar: Optional[str] = None
    capabilities: List[AgentCapability] = []
    tags: List[str] = []
    endpoint: str                               # WebSocket连接地址
    public_key: Optional[str] = None           # 公钥（用于加密通信）
    acp_version: str = "1.0"
    status: str = "online"                      # online/offline/busy
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class HandshakeSession(BaseModel):
    """握手会话状态"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    initiator_id: str                           # 发起方
    responder_id: str                           # 响应方
    challenge: Optional[str] = None            # 挑战码
    status: str = "pending"                     # pending/established/closed/failed
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    established_at: Optional[str] = None
