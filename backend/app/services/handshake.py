"""
握手协议处理器 - 实现ACP握手四步流程
"""
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.protocol import ACPMessage, MessageType
from app.core.security import generate_challenge, verify_challenge_response
from app.models.models import Agent, Session, ActivityLog
from app.services.connection_manager import connection_manager
from app.services.event_broadcaster import event_broadcaster

logger = logging.getLogger(__name__)


class HandshakeHandler:
    """
    ACP握手四步流程：
    1. initiator -> platform: HANDSHAKE_INIT (我要联系 responder)
    2. platform -> initiator: HANDSHAKE_CHALLENGE (这是挑战码)
    3. initiator -> platform: HANDSHAKE_RESPONSE (这是我的答案 + responder转发)
    4. platform -> both: HANDSHAKE_ACK / HANDSHAKE_REJECT
    """

    async def handle_handshake_init(self, msg: ACPMessage, db: AsyncSession) -> None:
        """处理握手发起"""
        initiator_id = msg.from_agent
        responder_id = msg.payload.get("target_agent_id")

        if not responder_id:
            await self._send_error(initiator_id, msg.id, "Missing target_agent_id")
            return

        # 检查目标Agent是否在线
        if not connection_manager.is_online(responder_id):
            await self._send_error(initiator_id, msg.id, f"Agent {responder_id} is offline")
            return

        # 查询双方Agent信息
        initiator = await db.get(Agent, initiator_id)
        responder = await db.get(Agent, responder_id)
        if not initiator or not responder:
            await self._send_error(initiator_id, msg.id, "Agent not found")
            return

        # 创建握手会话
        import uuid
        session_id = str(uuid.uuid4())
        challenge = generate_challenge()

        new_session = Session(
            id=session_id,
            initiator_id=initiator_id,
            responder_id=responder_id,
            status="pending",
            challenge=challenge
        )
        db.add(new_session)
        await db.commit()

        connection_manager.register_session(session_id, initiator_id, responder_id)

        # 向发起方发送挑战码
        challenge_msg = ACPMessage(
            type=MessageType.HANDSHAKE_CHALLENGE,
            from_agent="platform",
            to_agent=initiator_id,
            session_id=session_id,
            payload={
                "challenge": challenge,
                "responder_id": responder_id,
                "responder_name": responder.name,
                "session_id": session_id
            }
        )
        await connection_manager.send_to_agent(initiator_id, challenge_msg)

        # 通知responder有人要握手
        notify_msg = ACPMessage(
            type=MessageType.HANDSHAKE_INIT,
            from_agent=initiator_id,
            to_agent=responder_id,
            session_id=session_id,
            payload={
                "initiator_id": initiator_id,
                "initiator_name": initiator.name,
                "initiator_description": initiator.description,
                "purpose": msg.payload.get("purpose", ""),
                "session_id": session_id
            }
        )
        await connection_manager.send_to_agent(responder_id, notify_msg)

        # 广播事件
        await event_broadcaster.emit_handshake(
            session_id, initiator.name, responder.name, "initiating"
        )

        # 记录日志
        log = ActivityLog(
            event_type="handshake_init",
            agent_id=initiator_id,
            target_agent_id=responder_id,
            description=f"{initiator.name} 向 {responder.name} 发起握手",
            extra_data={"session_id": session_id}
        )
        db.add(log)
        await db.commit()

        logger.info(f"Handshake initiated: {initiator_id} -> {responder_id}, session: {session_id}")

    async def handle_handshake_response(self, msg: ACPMessage, db: AsyncSession) -> None:
        """处理握手挑战响应"""
        initiator_id = msg.from_agent
        session_id = msg.session_id
        challenge_answer = msg.payload.get("challenge_answer")

        if not session_id or not challenge_answer:
            await self._send_error(initiator_id, msg.id, "Missing session_id or challenge_answer")
            return

        # 查询会话
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if not session or session.status != "pending":
            await self._send_error(initiator_id, msg.id, "Session not found or invalid state")
            return

        # 验证挑战响应
        initiator = await db.get(Agent, initiator_id)
        if not initiator:
            await self._send_error(initiator_id, msg.id, "Initiator not found")
            return

        is_valid = verify_challenge_response(session.challenge, initiator.secret_key, challenge_answer)

        if not is_valid:
            # 握手失败
            await db.execute(
                update(Session).where(Session.id == session_id).values(status="failed")
            )
            await db.commit()

            reject_msg = ACPMessage(
                type=MessageType.HANDSHAKE_REJECT,
                from_agent="platform",
                to_agent=initiator_id,
                session_id=session_id,
                payload={"reason": "Authentication failed"}
            )
            await connection_manager.send_to_agent(initiator_id, reject_msg)
            await event_broadcaster.emit_handshake(session_id, initiator_id, session.responder_id, "rejected")
            return

        # 握手成功！
        await db.execute(
            update(Session).where(Session.id == session_id).values(
                status="established",
                established_at=datetime.utcnow()
            )
        )
        await db.commit()

        responder = await db.get(Agent, session.responder_id)

        # 向双方发送ACK
        ack_payload = {
            "session_id": session_id,
            "established_at": datetime.utcnow().isoformat(),
            "message": "Handshake successful! Secure channel established."
        }

        ack_to_initiator = ACPMessage(
            type=MessageType.HANDSHAKE_ACK,
            from_agent="platform",
            to_agent=initiator_id,
            session_id=session_id,
            payload={**ack_payload, "peer_id": session.responder_id, "peer_name": responder.name if responder else ""}
        )
        ack_to_responder = ACPMessage(
            type=MessageType.HANDSHAKE_ACK,
            from_agent="platform",
            to_agent=session.responder_id,
            session_id=session_id,
            payload={**ack_payload, "peer_id": initiator_id, "peer_name": initiator.name}
        )

        await connection_manager.send_to_agent(initiator_id, ack_to_initiator)
        await connection_manager.send_to_agent(session.responder_id, ack_to_responder)

        await event_broadcaster.emit_handshake(
            session_id, initiator.name, responder.name if responder else session.responder_id, "established"
        )

        # 记录日志
        log = ActivityLog(
            event_type="handshake_established",
            agent_id=initiator_id,
            target_agent_id=session.responder_id,
            description=f"{initiator.name} 与 {responder.name if responder else session.responder_id} 握手成功，建立安全通道",
            extra_data={"session_id": session_id}
        )
        db.add(log)
        await db.commit()

        logger.info(f"Handshake established: session {session_id}")

    async def _send_error(self, agent_id: str, ref_id: str, reason: str):
        error_msg = ACPMessage(
            type=MessageType.SYSTEM_ERROR,
            from_agent="platform",
            to_agent=agent_id,
            payload={"reason": reason, "ref_id": ref_id}
        )
        await connection_manager.send_to_agent(agent_id, error_msg)


handshake_handler = HandshakeHandler()
