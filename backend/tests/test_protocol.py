"""
ACP协议测试
测试消息格式、类型解析、消息构建等核心功能
"""
import pytest
from datetime import datetime
import json

from app.core.protocol import (
    ACPMessage, 
    MessageType, 
    AgentCapability, 
    AgentCard
)


class TestACPMessage:
    """ACP消息测试"""
    
    def test_message_creation(self):
        """测试创建基本消息"""
        msg = ACPMessage(
            type=MessageType.SYSTEM_REGISTER,
            from_agent="agent_001",
            to_agent="platform",
            payload={"name": "Test Agent"}
        )
        
        assert msg.id is not None
        assert msg.type == MessageType.SYSTEM_REGISTER
        assert msg.from_agent == "agent_001"
        assert msg.to_agent == "platform"
        assert msg.payload["name"] == "Test Agent"
        assert msg.protocol_version == "1.0"
    
    def test_message_serialization(self):
        """测试消息序列化"""
        msg = ACPMessage(
            type=MessageType.TASK_REQUEST,
            from_agent="agent_001",
            to_agent="agent_002",
            session_id="session_123",
            payload={"action": "book_flight", "params": {"from": "Beijing", "to": "Shanghai"}}
        )
        
        # 测试字典转换
        msg_dict = msg.model_dump()
        assert isinstance(msg_dict, dict)
        assert msg_dict["type"] == "task.request"
        assert msg_dict["from_agent"] == "agent_001"
        
    def test_message_timestamp(self):
        """测试时间戳自动生成"""
        before = datetime.utcnow().isoformat()
        msg = ACPMessage(
            type=MessageType.SYSTEM_HEARTBEAT,
            from_agent="agent_001"
        )
        after = datetime.utcnow().isoformat()
        
        assert msg.timestamp is not None
        assert before <= msg.timestamp <= after
    
    def test_message_json_roundtrip(self):
        """测试JSON往返序列化"""
        original = ACPMessage(
            type=MessageType.DISCOVER_REQUEST,
            from_agent="agent_001",
            payload={"query": "航班查询"}
        )
        
        # 序列化为JSON
        json_str = original.model_dump_json()
        assert isinstance(json_str, str)
        
        # 反序列化
        restored = ACPMessage.model_validate_json(json_str)
        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.payload["query"] == "航班查询"


class TestMessageType:
    """消息类型枚举测试"""
    
    def test_all_message_types_defined(self):
        """测试所有消息类型都已定义"""
        expected_types = [
            "handshake.init",
            "handshake.challenge", 
            "handshake.response",
            "handshake.ack",
            "handshake.reject",
            "session.open",
            "session.close",
            "session.heartbeat",
            "discover.request",
            "discover.response",
            "task.request",
            "task.ack",
            "task.progress",
            "task.result",
            "task.error",
            "system.register",
            "system.heartbeat",
            "system.error"
        ]
        
        for expected in expected_types:
            msg_type = MessageType(expected)
            assert msg_type.value == expected
    
    def test_message_type_from_string(self):
        """测试从字符串创建消息类型"""
        msg_type = MessageType("handshake.init")
        assert msg_type == MessageType.HANDSHAKE_INIT


class TestAgentCapability:
    """Agent能力描述测试"""
    
    def test_capability_creation(self):
        """测试创建Agent能力"""
        cap = AgentCapability(
            name="flight_booking",
            description="预订国内和国际航班机票",
            input_schema={
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                    "date": {"type": "string"}
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "booking_id": {"type": "string"}
                }
            }
        )
        
        assert cap.name == "flight_booking"
        assert "航班" in cap.description
        assert "from_city" in cap.input_schema["properties"]
    
    def test_capability_with_examples(self):
        """测试带示例的能力描述"""
        cap = AgentCapability(
            name="weather_query",
            description="查询天气",
            examples=[
                {"input": {"city": "北京"}, "output": {"temp": 20, "weather": "晴"}},
                {"input": {"city": "上海"}, "output": {"temp": 25, "weather": "多云"}}
            ]
        )
        
        assert len(cap.examples) == 2
        assert cap.examples[0]["input"]["city"] == "北京"


class TestAgentCard:
    """Agent名片测试"""
    
    def test_agent_card_creation(self):
        """测试创建Agent名片"""
        card = AgentCard(
            agent_id="agent_001",
            name="航班助手",
            description="提供航班查询和预订服务",
            owner="航空科技公司",
            tags=["travel", "booking", "flight"],
            endpoint="ws://localhost:8000/ws/agent/agent_001",
            capabilities=[
                AgentCapability(
                    name="flight_search",
                    description="搜索航班"
                )
            ]
        )
        
        assert card.agent_id == "agent_001"
        assert card.name == "航班助手"
        assert "flight" in card.tags
        assert len(card.capabilities) == 1
    
    def test_agent_card_defaults(self):
        """测试默认值"""
        card = AgentCard(
            agent_id="agent_002",
            name="测试Agent",
            description="测试用",
            owner="测试",
            endpoint="ws://localhost:8000"
        )
        
        assert card.status == "online"
        assert card.acp_version == "1.0"
        assert card.avatar is None
        assert card.public_key is None
        assert card.capabilities == []
        assert card.tags == []


class TestProtocolValidation:
    """协议验证测试"""
    
    def test_invalid_message_type(self):
        """测试无效消息类型"""
        with pytest.raises(ValueError):
            ACPMessage(
                type="invalid_type",  # type: ignore
                from_agent="agent_001"
            )
    
    def test_missing_required_field(self):
        """测试缺少必需字段"""
        # from_agent 是可选的（但实际业务中应该需要）
        msg = ACPMessage(type=MessageType.SYSTEM_HEARTBEAT)
        assert msg.from_agent is None
    
    def test_payload_validation(self):
        """测试payload内容验证"""
        msg = ACPMessage(
            type=MessageType.TASK_REQUEST,
            from_agent="agent_001",
            payload={"action": "test"}
        )
        
        # payload 应该是字典
        assert isinstance(msg.payload, dict)
        assert msg.payload["action"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
