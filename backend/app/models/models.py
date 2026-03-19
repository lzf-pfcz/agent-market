from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String(100))
    avatar = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("Agent", back_populates="owner_user")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_id = Column(String, ForeignKey("users.id"))
    owner_name = Column(String(100))           # 冗余字段，便于查询
    avatar = Column(String)
    tags = Column(JSON, default=list)          # ["travel", "booking"]
    capabilities = Column(JSON, default=list)  # AgentCapability列表
    secret_key = Column(String, nullable=False) # Agent鉴权密钥
    status = Column(String(20), default="offline")  # online/offline/busy
    endpoint = Column(String)                  # WebSocket endpoint
    is_public = Column(Boolean, default=True)
    total_calls = Column(Integer, default=0)
    success_calls = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime)

    owner_user = relationship("User", back_populates="agents")
    sessions_as_initiator = relationship("Session", foreign_keys="Session.initiator_id", back_populates="initiator")
    sessions_as_responder = relationship("Session", foreign_keys="Session.responder_id", back_populates="responder")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    initiator_id = Column(String, ForeignKey("agents.id"))
    responder_id = Column(String, ForeignKey("agents.id"))
    status = Column(String(20), default="pending")  # pending/established/closed/failed
    challenge = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    established_at = Column(DateTime)
    closed_at = Column(DateTime)

    initiator = relationship("Agent", foreign_keys=[initiator_id], back_populates="sessions_as_initiator")
    responder = relationship("Agent", foreign_keys=[responder_id], back_populates="sessions_as_responder")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    from_agent_id = Column(String)
    to_agent_id = Column(String)
    message_type = Column(String(50))
    payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    session = relationship("Session", back_populates="messages")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50))            # register/handshake/task/discover
    agent_id = Column(String)
    target_agent_id = Column(String)
    description = Column(Text)
    extra_data = Column(JSON)                  # 额外数据（metadata是SQLAlchemy保留字）
    created_at = Column(DateTime, default=datetime.utcnow)
