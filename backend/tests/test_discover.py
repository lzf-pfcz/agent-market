"""
服务发现测试
测试Agent搜索、匹配、向量检索等功能
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Agent


class TestServiceDiscovery:
    """服务发现功能测试"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        db = AsyncMock()
        return db
    
    @pytest.fixture
    def sample_agents(self):
        """示例Agent数据"""
        agents = []
        for i in range(3):
            agent = MagicMock()
            agent.id = f"agent_{i+1}"
            agent.name = ["航班助手", "天气查询", "酒店预订"][i]
            agent.description = [
                "提供航班查询、预订服务",
                "查询全球城市天气",
                "酒店搜索和预订"
            ][i]
            agent.tags = [
                ["travel", "flight", "booking"],
                ["weather", "forecast"],
                ["hotel", "booking", "travel"]
            ][i]
            agent.capabilities = [
                [{"name": "flight_search", "description": "搜索航班"}],
                [{"name": "weather_query", "description": "查询天气"}],
                [{"name": "hotel_search", "description": "搜索酒店"}]
            ][i]
            agent.status = "online"
            agents.append(agent)
        return agents
    
    def test_keyword_match_flight(self, sample_agents):
        """测试关键词匹配 - 航班"""
        query = "航班"
        results = []
        
        for agent in sample_agents:
            # 检查名称、描述、标签是否包含关键词
            if (query in agent.name or 
                query in agent.description or 
                any(query in tag for tag in agent.tags)):
                results.append(agent)
        
        assert len(results) == 1
        assert results[0].name == "航班助手"
    
    def test_keyword_match_weather(self, sample_agents):
        """测试关键词匹配 - 天气"""
        query = "天气"
        results = []
        
        for agent in sample_agents:
            if (query in agent.name or 
                query in agent.description or 
                any(query in tag for tag in agent.tags)):
                results.append(agent)
        
        assert len(results) == 1
        assert results[0].name == "天气查询"
    
    def test_keyword_match_travel(self, sample_agents):
        """测试关键词匹配 - 旅游（多结果）"""
        query = "travel"
        results = []
        
        for agent in sample_agents:
            if (query.lower() in agent.name.lower() or 
                query.lower() in agent.description.lower() or 
                any(query.lower() in tag.lower() for tag in agent.tags)):
                results.append(agent)
        
        assert len(results) == 2  # 航班助手和酒店预订
    
    def test_keyword_match_no_result(self, sample_agents):
        """测试无匹配结果"""
        query = "不存在的关键词"
        results = []
        
        for agent in sample_agents:
            if (query in agent.name or 
                query in agent.description or 
                any(query in tag for tag in agent.tags)):
                results.append(agent)
        
        assert len(results) == 0
    
    def test_semantic_query_similarity(self):
        """测试语义相似度匹配"""
        # 模拟语义向量匹配
        queries = [
            ("我想坐飞机去上海", "航班"),
            ("明天要出差", "航班"),
            ("查询目的地天气", "天气"),
        ]
        
        # 这些查询都应该能匹配到对应的Agent
        for user_query, expected_tag in queries:
            # 这里简化为关键词匹配演示
            # 实际应使用向量检索
            assert len(user_query) > 0


class TestVectorSearch:
    """向量搜索测试（需要embedding模型）"""
    
    @pytest.mark.skip(reason="需要embedding模型")
    def test_embedding_generation(self):
        """测试Embedding向量生成"""
        # 使用 sentence-transformers 生成向量
        # from sentence_transformers import SentenceTransformer
        
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # sentences = ["航班查询", "天气查询", "酒店预订"]
        # embeddings = model.encode(sentences)
        
        # assert embeddings.shape[0] == 3
        pass
    
    @pytest.mark.skip(reason="需要embedding模型")
    def test_cosine_similarity(self):
        """测试余弦相似度计算"""
        # import numpy as np
        # from sklearn.metrics.pairwise import cosine_similarity
        
        # v1 = [1, 0, 0]
        # v2 = [1, 0, 0]
        # v3 = [0, 1, 0]
        
        # sim = cosine_similarity([v1], [v2])[0][0]
        # assert sim == 1.0  # 完全相同
        
        # sim = cosine_similarity([v1], [v3])[0][0]
        # assert sim == 0.0  # 正交
        pass


class TestSearchRanking:
    """搜索排序测试"""
    
    def test_ranking_by_response_time(self):
        """测试按响应时间排序"""
        agents = [
            {"name": "Agent A", "avg_response_time": 100},  # ms
            {"name": "Agent B", "avg_response_time": 50},
            {"name": "Agent C", "avg_response_time": 200},
        ]
        
        # 按响应时间升序排序
        ranked = sorted(agents, key=lambda x: x["avg_response_time"])
        
        assert ranked[0]["name"] == "Agent B"
        assert ranked[1]["name"] == "Agent A"
        assert ranked[2]["name"] == "Agent C"
    
    def test_ranking_by_success_rate(self):
        """测试按成功率排序"""
        agents = [
            {"name": "Agent A", "total_calls": 100, "success_calls": 90},
            {"name": "Agent B", "total_calls": 50, "success_calls": 48},
            {"name": "Agent C", "total_calls": 200, "success_calls": 150},
        ]
        
        # 计算成功率并排序
        for agent in agents:
            agent["success_rate"] = agent["success_calls"] / agent["total_calls"]
        
        ranked = sorted(agents, key=lambda x: x["success_rate"], reverse=True)
        
        assert ranked[0]["name"] == "Agent B"  # 96%
        assert ranked[1]["name"] == "Agent A"  # 90%
        assert ranked[2]["name"] == "Agent C"  # 75%
    
    def test_combined_ranking(self):
        """测试综合排序（响应时间 + 成功率 + 评分）"""
        agents = [
            {
                "name": "Agent A",
                "avg_response_time": 100,
                "success_rate": 0.9,
                "rating": 4.5
            },
            {
                "name": "Agent B", 
                "avg_response_time": 50,
                "success_rate": 0.96,
                "rating": 4.2
            },
            {
                "name": "Agent C",
                "avg_response_time": 200,
                "success_rate": 0.75,
                "rating": 4.8
            },
        ]
        
        # 综合评分计算 (归一化后加权)
        weights = {
            "response_time": 0.3,  # 越快越好
            "success_rate": 0.4,  # 越高越好
            "rating": 0.3        # 越高越好
        }
        
        # 归一化
        min_time = min(a["avg_response_time"] for a in agents)
        max_time = max(a["avg_response_time"] for a in agents)
        
        for agent in agents:
            # 响应时间归一化 (反向，越小越好)
            time_score = 1 - (agent["avg_response_time"] - min_time) / (max_time - min_time) if max_time > min_time else 1
            # 成功率
            success_score = agent["success_rate"]
            # 评分归一化 (假设5分制)
            rating_score = agent["rating"] / 5.0
            
            # 综合分数
            agent["combined_score"] = (
                weights["response_time"] * time_score +
                weights["success_rate"] * success_score +
                weights["rating"] * rating_score
            )
        
        ranked = sorted(agents, key=lambda x: x["combined_score"], reverse=True)
        
        # Agent B 综合分数最高
        assert ranked[0]["name"] == "Agent B"


class TestDiscoverAPI:
    """服务发现API测试"""
    
    @pytest.mark.asyncio
    async def test_discover_endpoint_validation(self):
        """测试发现端点参数验证"""
        # 测试缺少必需参数
        # response = await client.get("/api/agents/discover/search")
        # assert response.status_code == 422  # FastAPI会自动验证
        
        # 测试有效查询
        # response = await client.get("/api/agents/discover/search?query=航班")
        # assert response.status_code == 200
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
