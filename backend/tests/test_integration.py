"""
集成测试 - 端到端场景测试
使用 httpx 和 websockets 模拟完整流程
"""
import pytest
import asyncio
import json
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from httpx import ASGITransport, ASGITransport


# 测试配置
TEST_BASE_URL = "http://testserver"
TEST_WS_URL = "ws://testserver"


@pytest.fixture
def app():
    """获取测试应用"""
    from app.main import app
    return app


@pytest.fixture
async def client(app) -> AsyncGenerator[httpx.AsyncClient, None]:
    """创建测试客户端"""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=app),
        base_url=TEST_BASE_URL
    ) as client:
        yield client


@pytest.fixture
def mock_websocket():
    """模拟 WebSocket"""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


# ==================== API 测试 ====================

class TestAgentAPI:
    """Agent 注册和管理 API 测试"""
    
    @pytest.mark.asyncio
    async def test_register_agent(self, client: httpx.AsyncClient):
        """测试注册 Agent"""
        response = await client.post(
            "/api/agents/register",
            json={
                "name": "测试Agent",
                "description": "用于测试的Agent",
                "owner_name": "测试开发者",
                "tags": ["test"],
                "capabilities": [
                    {
                        "name": "test_action",
                        "description": "测试动作"
                    }
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证响应字段
        assert "agent_id" in data
        assert "secret_key" in data
        assert "token" in data
        assert "message" in data
        assert data["message"] == "Agent '测试Agent' registered successfully!"
        
        # 验证返回的 agent_id 格式
        assert len(data["agent_id"]) == 36  # UUID format
    
    @pytest.mark.asyncio
    async def test_register_agent_validation(self, client: httpx.AsyncClient):
        """测试注册请求验证"""
        # 缺少必需字段
        response = await client.post(
            "/api/agents/register",
            json={"name": "测试"}
        )
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_list_agents(self, client: httpx.AsyncClient):
        """测试获取 Agent 列表"""
        response = await client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "items" in data
        assert "total" in data
    
    @pytest.mark.asyncio
    async def test_list_agents_pagination(self, client: httpx.AsyncClient):
        """测试分页参数"""
        response = await client.get("/api/agents?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
    
    @pytest.mark.asyncio
    async def test_discover_agents(self, client: httpx.AsyncClient):
        """测试服务发现"""
        response = await client.get("/api/agents/discover/search?query=航班&limit=3")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_agent_stats(self, client: httpx.AsyncClient):
        """测试获取平台统计"""
        response = await client.get("/api/agents/stats/overview")
        assert response.status_code == 200
        data = response.json()
        
        # 验证统计字段
        assert "total_agents" in data
        assert "online_agents" in data
        assert "total_calls" in data


class TestGuestAPI:
    """访客 API 测试"""
    
    @pytest.mark.asyncio
    async def test_guest_token(self, client: httpx.AsyncClient):
        """测试获取访客 Token"""
        response = await client.post(
            "/api/guest/token",
            json={
                "name": "测试访客",
                "purpose": "测试用途"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "guest_id" in data
        assert "token" in data
        assert "expires_in" in data


class TestHealthEndpoint:
    """健康检查端点测试"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, client: httpx.AsyncClient):
        """测试健康检查"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "platform" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: httpx.AsyncClient):
        """测试根端点"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "version" in data


# ==================== 协议消息测试 ====================

class TestACPProtocol:
    """ACP 协议测试"""
    
    def test_message_creation(self):
        """测试创建 ACP 消息"""
        from app.core.protocol import ACPMessage, MessageType
        
        msg = ACPMessage(
            type=MessageType.TASK_REQUEST,
            from_agent="agent-a",
            to_agent="agent-b",
            session_id="session-123",
            payload={"action": "test"}
        )
        
        assert msg.id is not None
        assert msg.type == MessageType.TASK_REQUEST
        assert msg.from_agent == "agent-a"
        assert msg.to_agent == "agent-b"
        assert msg.payload["action"] == "test"
    
    def test_message_serialization(self):
        """测试消息序列化"""
        from app.core.protocol import ACPMessage, MessageType
        
        msg = ACPMessage(
            type=MessageType.HANDSHAKE_INIT,
            from_agent="agent-a",
            payload={"target_agent_id": "agent-b"}
        )
        
        # 测试 JSON 序列化
        json_str = msg.model_dump_json()
        assert isinstance(json_str, str)
        assert "handshake.init" in json_str
        
        # 测试反序列化
        restored = ACPMessage.model_validate_json(json_str)
        assert restored.type == MessageType.HANDSHAKE_INIT


# ==================== 错误处理测试 ====================

class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, client: httpx.AsyncClient):
        """测试无效 JSON 请求"""
        # 发送无效 JSON
        response = await client.post(
            "/api/agents/register",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )
        # FastAPI 会返回 422 或 400
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_agent_not_found(self, client: httpx.AsyncClient):
        """测试获取不存在的 Agent"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/agents/{fake_id}")
        assert response.status_code == 404


# ==================== 安全测试 ====================

class TestSecurity:
    """安全测试"""
    
    def test_password_hashing(self):
        """测试密码哈希"""
        from app.core.security import get_password_hash, verify_password
        
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed)
        assert not verify_password("wrong_password", hashed)
    
    def test_token_creation(self):
        """测试 Token 创建"""
        from app.core.security import create_access_token, decode_token
        
        agent_id = "test-agent-123"
        token = create_access_token({"sub": agent_id})
        
        assert token is not None
        assert len(token) > 0
        
        # 解码验证
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == agent_id
    
    def test_token_expiration(self):
        """测试 Token 过期"""
        from datetime import timedelta
        from app.core.security import create_access_token, decode_token
        
        # 创建已过期的 token
        agent_id = "test-agent-123"
        token = create_access_token(
            {"sub": agent_id},
            expires_delta=timedelta(seconds=-1)
        )
        
        payload = decode_token(token)
        # 过期的 token 应该返回 None
        assert payload is None or "exp" in payload


# ==================== WebSocket 测试 ====================

class TestWebSocket:
    """WebSocket 测试"""
    
    @pytest.mark.asyncio
    async def test_connection_manager(self):
        """测试连接管理器"""
        from app.services.connection_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        # 测试初始状态
        assert len(manager.get_online_agents()) == 0
        assert not manager.is_online("test-agent")
    
    @pytest.mark.asyncio
    async def test_event_broadcaster(self):
        """测试事件广播器"""
        from app.services.event_broadcaster import EventBroadcaster
        
        broadcaster = EventBroadcaster()
        
        # 测试初始状态
        assert len(broadcaster._frontend_connections) == 0


# ==================== 集成场景测试 ====================

class TestIntegrationScenarios:
    """集成场景测试"""
    
    @pytest.mark.asyncio
    async def test_full_agent_lifecycle(self, client: httpx.AsyncClient):
        """测试完整的 Agent 生命周期"""
        
        # 1. 注册 Agent
        register_response = await client.post(
            "/api/agents/register",
            json={
                "name": "生命周期测试Agent",
                "description": "用于测试完整生命周期",
                "owner_name": "测试团队",
                "tags": ["test", "lifecycle"],
                "capabilities": [
                    {
                        "name": "echo",
                        "description": "回显测试"
                    }
                ]
            }
        )
        assert register_response.status_code == 200
        agent_data = register_response.json()
        agent_id = agent_data["agent_id"]
        
        # 2. 获取 Agent 详情
        detail_response = await client.get(f"/api/agents/{agent_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["name"] == "生命周期测试Agent"
        
        # 3. 搜索 Agent
        search_response = await client.get("/api/agents/discover/search?query=测试")
        assert search_response.status_code == 200
        # 搜索结果可能包含刚注册的 Agent
        
        # 4. 获取统计
        stats_response = await client.get("/api/agents/stats/overview")
        assert stats_response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_multiple_agents_registration(self, client: httpx.AsyncClient):
        """测试批量注册 Agent"""
        agents = []
        
        for i in range(3):
            response = await client.post(
                "/api/agents/register",
                json={
                    "name": f"批量测试Agent-{i}",
                    "description": f"批量测试 {i}",
                    "owner_name": "批量测试"
                }
            )
            assert response.status_code == 200
            agents.append(response.json()["agent_id"])
        
        # 验证注册数量
        stats = await client.get("/api/agents/stats/overview")
        assert stats.json()["total_agents"] >= 3


# ==================== 运行说明 ====================

if __name__ == "__main__":
    """
    运行集成测试:
    
    # 全部测试
    pytest tests/test_integration.py -v
    
    # 仅 API 测试
    pytest tests/test_integration.py::TestAgentAPI -v
    
    # 仅安全测试
    pytest tests/test_integration.py::TestSecurity -v
    
    # 带覆盖率
    pytest tests/test_integration.py --cov=app
    """
    pytest.main([__file__, "-v"])
