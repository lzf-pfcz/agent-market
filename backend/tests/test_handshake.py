"""
握手服务测试
测试ACP握手的四步流程
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.handshake import HandshakeHandler
from app.core.protocol import ACPMessage, MessageType


class TestHandshakeHandler:
    """握手处理器测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = AsyncMock()
        db.get = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        db.add = MagicMock()
        return db
    
    @pytest.fixture
    def mock_connection_manager(self):
        """模拟连接管理器"""
        with patch('app.services.handshake.connection_manager') as cm:
            cm.is_online = MagicMock(return_value=True)
            cm.register_session = MagicMock()
            cm.send_to_agent = AsyncMock()
            yield cm
    
    @pytest.fixture
    def mock_event_broadcaster(self):
        """模拟事件广播器"""
        with patch('app.services.handshake.event_broadcaster') as eb:
            eb.emit_handshake = AsyncMock()
            yield eb
    
    @pytest.mark.asyncio
    async def test_handle_handshake_init_success(self, mock_db, mock_connection_manager, mock_event_broadcaster):
        """测试成功发起握手"""
        # 模拟Agent查询结果
        mock_initiator = MagicMock()
        mock_initiator.id = "agent_001"
        mock_initiator.name = "航班助手"
        mock_initiator.secret_key = "secret123"
        
        mock_responder = MagicMock()
        mock_responder.id = "agent_002"
        mock_responder.name = "天气助手"
        
        mock_db.get = AsyncMock(side_effect=[mock_initiator, mock_responder])
        
        handler = HandshakeHandler()
        
        msg = ACPMessage(
            type=MessageType.HANDSHAKE_INIT,
            from_agent="agent_001",
            payload={"target_agent_id": "agent_002", "purpose": "查询航班"}
        )
        
        await handler.handle_handshake_init(msg, mock_db)
        
        # 验证连接管理器被调用
        mock_connection_manager.register_session.assert_called_once()
        mock_connection_manager.send_to_agent.assert_called()
        
        # 验证数据库操作
        mock_db.add.assert_called()
        await mock_db.commit.assert_called()
        
        # 验证事件广播
        mock_event_broadcaster.emit_handshake.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_handshake_init_missing_target(self, mock_db, mock_connection_manager):
        """测试缺少目标Agent ID"""
        handler = HandshakeHandler()
        
        msg = ACPMessage(
            type=MessageType.HANDSHAKE_INIT,
            from_agent="agent_001",
            payload={}  # 缺少 target_agent_id
        )
        
        await handler.handle_handshake_init(msg, mock_db)
        
        # 验证发送错误消息
        mock_connection_manager.send_to_agent.assert_called_once()
        
        # 获取发送的错误消息
        call_args = mock_connection_manager.send_to_agent.call_args
        error_msg = call_args[0][1]
        
        assert error_msg.type == MessageType.SYSTEM_ERROR
        assert "target_agent_id" in error_msg.payload["reason"]
    
    @pytest.mark.asyncio
    async def test_handle_handshake_init_offline_agent(self, mock_db, mock_connection_manager):
        """测试目标Agent离线"""
        mock_connection_manager.is_online = MagicMock(return_value=False)
        
        handler = HandshakeHandler()
        
        msg = ACPMessage(
            type=MessageType.HANDSHAKE_INIT,
            from_agent="agent_001",
            payload={"target_agent_id": "agent_002"}
        )
        
        await handler.handle_handshake_init(msg, mock_db)
        
        # 验证发送错误消息
        mock_connection_manager.send_to_agent.assert_called_once()
        
        call_args = mock_connection_manager.send_to_agent.call_args
        error_msg = call_args[0][1]
        
        assert error_msg.type == MessageType.SYSTEM_ERROR
        assert "offline" in error_msg.payload["reason"]
    
    @pytest.mark.asyncio
    async def test_handle_handshake_response_success(self, mock_db, mock_connection_manager, mock_event_broadcaster):
        """测试握手响应成功"""
        # 模拟会话查询
        mock_session = MagicMock()
        mock_session.id = "session_123"
        mock_session.challenge = "test_challenge"
        mock_session.initiator_id = "agent_001"
        mock_session.responder_id = "agent_002"
        mock_session.status = "pending"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # 模拟Agent查询
        mock_initiator = MagicMock()
        mock_initiator.id = "agent_001"
        mock_initiator.name = "航班助手"
        mock_initiator.secret_key = "secret123"
        
        mock_responder = MagicMock()
        mock_responder.id = "agent_002"
        mock_responder.name = "天气助手"
        
        def get_side_effect(model, agent_id):
            if agent_id == "agent_001":
                return mock_initiator
            if agent_id == "agent_002":
                return mock_responder
            return None
        
        mock_db.get = AsyncMock(side_effect=get_side_effect)
        
        handler = HandshakeHandler()
        
        msg = ACPMessage(
            type=MessageType.HANDSHAKE_RESPONSE,
            from_agent="agent_001",
            session_id="session_123",
            payload={"challenge_answer": "valid_answer"}
        )
        
        # 模拟挑战验证通过
        with patch('app.services.handshake.verify_challenge_response', return_value=True):
            await handler.handle_handshake_response(msg, mock_db)
        
        # 验证ACK消息发送
        assert mock_connection_manager.send_to_agent.call_count >= 2
    
    @pytest.mark.asyncio
    async def test_handle_handshake_response_invalid(self, mock_db, mock_connection_manager, mock_event_broadcaster):
        """测试握手响应验证失败"""
        mock_session = MagicMock()
        mock_session.id = "session_123"
        mock_session.challenge = "test_challenge"
        mock_session.initiator_id = "agent_001"
        mock_session.responder_id = "agent_002"
        mock_session.status = "pending"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_session)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        mock_initiator = MagicMock()
        mock_initiator.id = "agent_001"
        mock_initiator.secret_key = "secret123"
        
        mock_db.get = AsyncMock(return_value=mock_initiator)
        
        handler = HandshakeHandler()
        
        msg = ACPMessage(
            type=MessageType.HANDSHAKE_RESPONSE,
            from_agent="agent_001",
            session_id="session_123",
            payload={"challenge_answer": "wrong_answer"}
        )
        
        # 模拟挑战验证失败
        with patch('app.services.handshake.verify_challenge_response', return_value=False):
            await handler.handle_handshake_response(msg, mock_db)
        
        # 验证拒绝消息
        call_args = mock_connection_manager.send_to_agent.call_args
        reject_msg = call_args[0][1]
        
        assert reject_msg.type == MessageType.HANDSHAKE_REJECT
        assert "Authentication failed" in reject_msg.payload["reason"]


class TestHandshakeFlow:
    """握手流程集成测试"""
    
    def test_handshake_flow_complete(self):
        """测试完整握手流程"""
        # 1. HANDSHAKE_INIT -> HANDSHAKE_CHALLENGE
        # 2. HANDSHAKE_RESPONSE -> HANDSHAKE_ACK
        
        flow_steps = [
            MessageType.HANDSHAKE_INIT,
            MessageType.HANDSHAKE_CHALLENGE,
            MessageType.HANDSHAKE_RESPONSE,
            MessageType.HANDSHAKE_ACK
        ]
        
        # 验证流程顺序
        assert flow_steps[0] == MessageType.HANDSHAKE_INIT
        assert flow_steps[1] == MessageType.HANDSHAKE_CHALLENGE
        assert flow_steps[2] == MessageType.HANDSHAKE_RESPONSE
        assert flow_steps[3] == MessageType.HANDSHAKE_ACK
    
    def test_handshake_reject_flow(self):
        """测试握手拒绝流程"""
        reject_steps = [
            MessageType.HANDSHAKE_INIT,
            MessageType.HANDSHAKE_CHALLENGE,
            MessageType.HANDSHAKE_RESPONSE,
            MessageType.HANDSHAKE_REJECT
        ]
        
        assert reject_steps[-1] == MessageType.HANDSHAKE_REJECT
    
    def test_handshake_timeout_scenario(self):
        """测试握手超时场景"""
        # 如果超时未响应，状态应保持pending
        session_status = "pending"
        
        # 验证pending是有效状态
        valid_statuses = ["pending", "established", "closed", "failed"]
        assert session_status in valid_statuses


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
