"""
Redis缓存服务
提高热点数据访问性能
"""
import json
import logging
from typing import Any, Optional, List
from dataclasses import dataclass
import redis.asyncio as redis
from app.core.config import settings

logger = logging.getLogger(__name__)


# 缓存键前缀
CACHE_PREFIX = "agent_marketplace"


@dataclass
class CacheConfig:
    """缓存配置"""
    default_ttl: int = 300        # 默认TTL (秒)
    agent_list_ttl: int = 60      # Agent列表缓存时间
    session_ttl: int = 3600       # 会话缓存时间
    stats_ttl: int = 30           # 统计数据缓存时间


class RedisCache:
    """
    Redis缓存服务
    
    功能:
    - 热点数据缓存
    - 会话状态存储
    - 分布式锁
    - 消息队列
    """
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.get_redis_url()
        self._client: Optional[redis.Redis] = None
        self.config = CacheConfig()
    
    async def connect(self) -> None:
        """连接到Redis"""
        if not self.redis_url:
            logger.warning("Redis URL not configured, caching disabled")
            return
        
        try:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self._client.ping()
            logger.info(f"Connected to Redis: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None
    
    async def close(self) -> None:
        """关闭连接"""
        if self._client:
            await self._client.close()
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._client is not None
    
    # ==================== 基础操作 ====================
    
    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        if not self._client:
            return None
        
        try:
            return await self._client.get(f"{CACHE_PREFIX}:{key}")
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置值"""
        if not self._client:
            return False
        
        try:
            ttl = ttl or self.config.default_ttl
            await self._client.setex(
                f"{CACHE_PREFIX}:{key}",
                ttl,
                value
            )
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除键"""
        if not self._client:
            return False
        
        try:
            await self._client.delete(f"{CACHE_PREFIX}:{key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self._client:
            return False
        
        try:
            return await self._client.exists(f"{CACHE_PREFIX}:{key}") > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    # ==================== JSON操作 ====================
    
    async def get_json(self, key: str) -> Optional[Any]:
        """获取JSON值"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON for key: {key}")
        return None
    
    async def set_json(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """设置JSON值"""
        try:
            json_str = json.dumps(value)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.error(f"Cache set_json error: {e}")
            return False
    
    # ==================== Agent缓存 ====================
    
    async def cache_agent_list(self, agents: List[dict]) -> bool:
        """缓存Agent列表"""
        return await self.set_json("agents:list", agents, self.config.agent_list_ttl)
    
    async def get_cached_agent_list(self) -> Optional[List[dict]]:
        """获取缓存的Agent列表"""
        return await self.get_json("agents:list")
    
    async def cache_agent(self, agent_id: str, agent_data: dict) -> bool:
        """缓存单个Agent"""
        return await self.set_json(
            f"agent:{agent_id}", 
            agent_data, 
            self.config.agent_list_ttl
        )
    
    async def get_cached_agent(self, agent_id: str) -> Optional[dict]:
        """获取缓存的Agent"""
        return await self.get_json(f"agent:{agent_id}")
    
    async def invalidate_agent_list(self) -> bool:
        """使Agent列表缓存失效"""
        return await self.delete("agents:list")
    
    async def invalidate_agent(self, agent_id: str) -> bool:
        """使Agent缓存失效"""
        return await self.delete(f"agent:{agent_id}")
    
    # ==================== 在线状态 ====================
    
    async def set_agent_online(self, agent_id: str) -> bool:
        """设置Agent在线状态"""
        if not self._client:
            return False
        
        try:
            # 使用Hash存储在线Agent
            await self._client.hset(
                f"{CACHE_PREFIX}:agents:online",
                agent_id,
                json.dumps({"status": "online", "timestamp": __import__("time").time()})
            )
            return True
        except Exception as e:
            logger.error(f"Cache set_agent_online error: {e}")
            return False
    
    async def set_agent_offline(self, agent_id: str) -> bool:
        """设置Agent离线状态"""
        if not self._client:
            return False
        
        try:
            await self._client.hdel(f"{CACHE_PREFIX}:agents:online", agent_id)
            return True
        except Exception as e:
            logger.error(f"Cache set_agent_offline error: {e}")
            return False
    
    async def get_online_agents(self) -> List[str]:
        """获取所有在线Agent"""
        if not self._client:
            return []
        
        try:
            agents = await self._client.hgetall(f"{CACHE_PREFIX}:agents:online")
            return list(agents.keys())
        except Exception as e:
            logger.error(f"Cache get_online_agents error: {e}")
            return []
    
    # ==================== 会话缓存 ====================
    
    async def cache_session(self, session_id: str, session_data: dict) -> bool:
        """缓存会话"""
        return await self.set_json(
            f"session:{session_id}",
            session_data,
            self.config.session_ttl
        )
    
    async def get_cached_session(self, session_id: str) -> Optional[dict]:
        """获取缓存的会话"""
        return await self.get_json(f"session:{session_id}")
    
    # ==================== 统计数据 ====================
    
    async def cache_stats(self, stats: dict) -> bool:
        """缓存统计数据"""
        return await self.set_json(
            "platform:stats",
            stats,
            self.config.stats_ttl
        )
    
    async def get_cached_stats(self) -> Optional[dict]:
        """获取缓存的统计数据"""
        return await self.get_json("platform:stats")
    
    # ==================== 分布式锁 ====================
    
    async def acquire_lock(
        self, 
        lock_name: str, 
        timeout: int = 10
    ) -> bool:
        """获取分布式锁"""
        if not self._client:
            return False
        
        try:
            # SET NX with expiry
            result = await self._client.set(
                f"{CACHE_PREFIX}:lock:{lock_name}",
                "1",
                nx=True,
                ex=timeout
            )
            return result is not None
        except Exception as e:
            logger.error(f"Cache acquire_lock error: {e}")
            return False
    
    async def release_lock(self, lock_name: str) -> bool:
        """释放分布式锁"""
        if not self._client:
            return False
        
        try:
            await self._client.delete(f"{CACHE_PREFIX}:lock:{lock_name}")
            return True
        except Exception as e:
            logger.error(f"Cache release_lock error: {e}")
            return False


# 全局实例
_cache: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """获取缓存实例"""
    global _cache
    
    if _cache is None:
        _cache = RedisCache()
        await _cache.connect()
    
    return _cache
