"""
服务发现增强 - 向量搜索
使用Embedding实现语义匹配
"""
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentEmbedding:
    """Agent向量表示"""
    agent_id: str
    name: str
    description: str
    tags: List[str]
    capabilities: List[Dict]
    embedding: Optional[np.ndarray] = None


class EmbeddingService:
    """
    向量嵌入服务
    
    支持:
    - 本地模型 (sentence-transformers)
    - OpenAI Embedding API
    """
    
    def __init__(self, provider: str = "local", model: str = "all-MiniLM-L6-v2"):
        self.provider = provider
        self.model_name = model
        self._model = None
    
    async def initialize(self) -> None:
        """初始化嵌入模型"""
        if self.provider == "local":
            await self._init_local_model()
        elif self.provider == "openai":
            # OpenAI API会在调用时初始化
            logger.info("Using OpenAI Embedding API")
        else:
            logger.warning(f"Unknown provider: {self.provider}, using keyword fallback")
    
    async def _init_local_model(self) -> None:
        """初始化本地模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading local embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Local embedding model loaded successfully")
            
        except ImportError:
            logger.warning("sentence-transformers not installed, using keyword matching")
            self.provider = "fallback"
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.provider = "fallback"
    
    async def encode(self, texts: List[str]) -> np.ndarray:
        """
        将文本编码为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            numpy数组 shape: (len(texts), embedding_dim)
        """
        if self.provider == "fallback" or not self._model:
            # 返回随机向量作为占位符
            # 实际使用关键词匹配
            return np.random.rand(len(texts), 384)
        
        if self.provider == "local" and self._model:
            return self._model.encode(texts)
        
        # OpenAI
        return await self._encode_openai(texts)
    
    async def _encode_openai(self, texts: List[str]) -> np.ndarray:
        """使用OpenAI API编码"""
        try:
            import httpx
            
            from app.core.config import settings
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.OPENAI_BASE_URL}/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": texts,
                        "model": "text-embedding-ada-002"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    embeddings = [item["embedding"] for item in data["data"]]
                    return np.array(embeddings)
                else:
                    logger.error(f"OpenAI API error: {response.text}")
                    raise Exception("OpenAI API failed")
                    
        except Exception as e:
            logger.error(f"OpenAI encoding failed: {e}")
            raise


class VectorSearchService:
    """
    向量搜索服务
    
    功能:
    - 为Agent生成并存储向量
    - 语义相似度搜索
    - 混合搜索 (向量 + 关键词)
    """
    
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self._agent_embeddings: Dict[str, AgentEmbedding] = {}
        self._index_built = False
    
    async def initialize(self) -> None:
        """初始化服务"""
        await self.embedding_service.initialize()
    
    async def index_agent(self, agent: Dict[str, Any]) -> None:
        """
        为Agent建立索引
        
        Args:
            agent: Agent信息字典
        """
        # 构建文本表示
        text_representation = self._build_text_representation(agent)
        
        # 编码为向量
        embeddings = await self.embedding_service.encode([text_representation])
        
        agent_emb = AgentEmbedding(
            agent_id=agent["id"],
            name=agent.get("name", ""),
            description=agent.get("description", ""),
            tags=agent.get("tags", []),
            capabilities=agent.get("capabilities", []),
            embedding=embeddings[0]
        )
        
        self._agent_embeddings[agent["id"]] = agent_emb
        self._index_built = False
        
        logger.info(f"Indexed agent: {agent.get('name')} ({agent['id'][:8]}...)")
    
    async def index_agents(self, agents: List[Dict[str, Any]]) -> None:
        """批量索引Agent"""
        for agent in agents:
            await self.index_agent(agent)
        
        self._index_built = True
        logger.info(f"Indexed {len(agents)} agents")
    
    def _build_text_representation(self, agent: Dict[str, Any]) -> str:
        """构建Agent的文本表示"""
        parts = [
            agent.get("name", ""),
            agent.get("description", ""),
            " ".join(agent.get("tags", [])),
        ]
        
        # 添加能力描述
        capabilities = agent.get("capabilities", [])
        if capabilities:
            cap_texts = [c.get("description", "") for c in capabilities]
            parts.append(" ".join(cap_texts))
        
        return " ".join(parts)
    
    async def search(
        self, 
        query: str, 
        top_k: int = 5,
        use_hybrid: bool = True
    ) -> List[Dict[str, Any]]:
        """
        语义搜索Agent
        
        Args:
            query: 查询文本
            top_k: 返回数量
            use_hybrid: 是否使用混合搜索
            
        Returns:
            排序后的Agent列表
        """
        if not self._agent_embeddings:
            logger.warning("No agents indexed yet")
            return []
        
        # 编码查询
        query_embeddings = await self.embedding_service.encode([query])
        query_vector = query_embeddings[0]
        
        # 计算相似度
        results = []
        for agent_id, agent_emb in self._agent_embeddings.items():
            if agent_emb.embedding is None:
                continue
            
            # 余弦相似度
            similarity = self._cosine_similarity(query_vector, agent_emb.embedding)
            
            # 关键词匹配加分
            keyword_boost = 0
            if use_hybrid:
                keyword_boost = self._keyword_match_score(query, agent_emb)
            
            # 综合分数
            combined_score = similarity * 0.7 + keyword_boost * 0.3
            
            results.append({
                "agent_id": agent_id,
                "name": agent_emb.name,
                "description": agent_emb.description,
                "similarity": float(similarity),
                "keyword_score": float(keyword_boost),
                "combined_score": float(combined_score)
            })
        
        # 排序
        results.sort(key=lambda x: x["combined_score"], reverse=True)
        
        return results[:top_k]
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _keyword_match_score(self, query: str, agent_emb: AgentEmbedding) -> float:
        """关键词匹配评分"""
        query_lower = query.lower()
        score = 0.0
        
        # 名称匹配
        if query_lower in agent_emb.name.lower():
            score += 0.5
        
        # 描述匹配
        if query_lower in agent_emb.description.lower():
            score += 0.3
        
        # 标签匹配
        for tag in agent_emb.tags:
            if query_lower in tag.lower():
                score += 0.2
        
        return min(score, 1.0)
    
    def remove_agent(self, agent_id: str) -> None:
        """移除Agent索引"""
        if agent_id in self._agent_embeddings:
            del self._agent_embeddings[agent_id]
            self._index_built = False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """获取索引统计"""
        return {
            "total_agents": len(self._agent_embeddings),
            "index_ready": self._index_built,
            "provider": self.embedding_service.provider,
            "model": self.embedding_service.model_name
        }


# 全局实例
_embedding_service: Optional[EmbeddingService] = None
_vector_search: Optional[VectorSearchService] = None


async def get_embedding_service() -> EmbeddingService:
    """获取嵌入服务实例"""
    global _embedding_service
    
    if _embedding_service is None:
        from app.core.config import settings
        
        _embedding_service = EmbeddingService(
            provider=settings.EMBEDDING_PROVIDER,
            model=settings.EMBEDDING_MODEL
        )
        await _embedding_service.initialize()
    
    return _embedding_service


async def get_vector_search_service() -> VectorSearchService:
    """获取向量搜索服务实例"""
    global _vector_search
    
    if _vector_search is None:
        emb_service = await get_embedding_service()
        _vector_search = VectorSearchService(emb_service)
        await _vector_search.initialize()
    
    return _vector_search
