"""
监控和运维服务
提供指标收集、健康检查、日志聚合
"""
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """指标数据"""
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """健康状态"""
    component: str
    status: str  # healthy, degraded, unhealthy
    message: str = ""
    last_check: float = field(default_factory=time.time)


class MetricsCollector:
    """
    指标收集器
    
    收集:
    - 连接数
    - 消息吞吐量
    - 响应延迟
    - 错误率
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        
        # 统计
        self._request_times: List[float] = []
        self._error_count = 0
        self._total_requests = 0
    
    def increment(self, name: str, value: float = 1) -> None:
        """增加计数器"""
        self._counters[name] += value
    
    def gauge(self, name: str, value: float) -> None:
        """设置仪表值"""
        self._gauges[name] = value
    
    def record_request(self, duration_ms: float, success: bool = True) -> None:
        """记录请求"""
        self._request_times.append(duration_ms)
        self._total_requests += 1
        if not success:
            self._error_count += 1
        
        # 保持最近1000条记录
        if len(self._request_times) > 1000:
            self._request_times = self._request_times[-1000:]
    
    def record_message(self, msg_type: str) -> None:
        """记录消息"""
        self.increment(f"messages.{msg_type}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取当前指标"""
        # 计算统计数据
        if self._request_times:
            sorted_times = sorted(self._request_times)
            avg_latency = sum(self._request_times) / len(self._request_times)
            p50_latency = sorted_times[len(sorted_times) // 2]
            p95_latency = sorted_times[int(len(sorted_times) * 0.95)]
            p99_latency = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_latency = p50_latency = p95_latency = p99_latency = 0
        
        error_rate = (
            self._error_count / self._total_requests 
            if self._total_requests > 0 else 0
        )
        
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "latency": {
                "avg_ms": round(avg_latency, 2),
                "p50_ms": round(p50_latency, 2),
                "p95_ms": round(p95_latency, 2),
                "p99_ms": round(p99_latency, 2),
            },
            "errors": {
                "count": self._error_count,
                "rate": round(error_rate * 100, 2)
            },
            "total_requests": self._total_requests
        }
    
    def reset(self) -> None:
        """重置统计"""
        self._request_times.clear()
        self._error_count = 0
        self._total_requests = 0


class HealthChecker:
    """
    健康检查器
    
    检查:
    - 数据库连接
    - Redis连接
    - Agent连接状态
    - 系统资源
    """
    
    def __init__(self):
        self._components: Dict[str, HealthStatus] = {}
        self._check_interval = 30  # 秒
        self._running = False
    
    def register_component(self, name: str) -> None:
        """注册组件"""
        self._components[name] = HealthStatus(
            component=name,
            status="unknown"
        )
    
    async def check_database(self) -> HealthStatus:
        """检查数据库"""
        try:
            from app.core.database import AsyncSessionLocal
            from sqlalchemy import text
            
            async with AsyncSessionLocal() as db:
                await db.execute(text("SELECT 1"))
            
            return HealthStatus(
                component="database",
                status="healthy",
                message="Database connection OK"
            )
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return HealthStatus(
                component="database",
                status="unhealthy",
                message=str(e)
            )
    
    async def check_redis(self) -> HealthStatus:
        """检查Redis"""
        try:
            from app.services.cache import get_cache
            cache = await get_cache()
            
            if not cache.is_connected:
                return HealthStatus(
                    component="redis",
                    status="degraded",
                    message="Redis not configured"
                )
            
            return HealthStatus(
                component="redis",
                status="healthy",
                message="Redis connection OK"
            )
        except Exception as e:
            return HealthStatus(
                component="redis",
                status="unhealthy",
                message=str(e)
            )
    
    async def check_agents(self) -> HealthStatus:
        """检查Agent连接"""
        try:
            from app.services.connection_manager import connection_manager
            
            online_count = len(connection_manager.get_online_agents())
            
            return HealthStatus(
                component="agents",
                status="healthy" if online_count > 0 else "degraded",
                message=f"{online_count} agents online"
            )
        except Exception as e:
            return HealthStatus(
                component="agents",
                status="unhealthy",
                message=str(e)
            )
    
    async def check_system(self) -> HealthStatus:
        """检查系统资源"""
        try:
            import psutil
            
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # 判断状态
            if cpu > 90 or memory.percent > 90:
                status = "degraded"
            elif cpu > 80 or memory.percent > 80:
                status = "healthy"
            else:
                status = "healthy"
            
            return HealthStatus(
                component="system",
                status=status,
                message=f"CPU: {cpu}%, Memory: {memory.percent}%"
            )
        except ImportError:
            return HealthStatus(
                component="system",
                status="unknown",
                message="psutil not installed"
            )
        except Exception as e:
            return HealthStatus(
                component="system",
                status="unhealthy",
                message=str(e)
            )
    
    async def check_all(self) -> Dict[str, HealthStatus]:
        """执行所有健康检查"""
        checks = [
            self.check_database(),
            self.check_redis(),
            self.check_agents(),
            self.check_system()
        ]
        
        results = {}
        for check in asyncio.as_completed(checks):
            result = await check
            results[result.component] = result
            self._components[result.component] = result
        
        return results
    
    def get_overall_status(self, statuses: Dict[str, HealthStatus]) -> str:
        """获取整体健康状态"""
        if not statuses:
            return "unknown"
        
        has_unhealthy = any(s.status == "unhealthy" for s in statuses.values())
        has_degraded = any(s.status == "degraded" for s in statuses.values())
        
        if has_unhealthy:
            return "unhealthy"
        elif has_degraded:
            return "degraded"
        else:
            return "healthy"


# 结构化日志
class StructuredLogger:
    """结构化日志 - 便于ELK检索"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log(
        self,
        level: str,
        message: str,
        agent_id: str = None,
        session_id: str = None,
        **kwargs
    ) -> None:
        """记录结构化日志"""
        extra = {
            "agent_id": agent_id,
            "session_id": session_id,
            **kwargs
        }
        extra = {k: v for k, v in extra.items() if v is not None}
        
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(message, extra=extra)


# 全局实例
metrics_collector = MetricsCollector()
health_checker = HealthChecker()


# ==================== 指标端点 ====================

async def get_metrics() -> Dict[str, Any]:
    """获取平台指标"""
    return metrics_collector.get_metrics()


async def get_health() -> Dict[str, Any]:
    """获取健康状态"""
    statuses = await health_checker.check_all()
    overall = health_checker.get_overall_status(statuses)
    
    return {
        "status": overall,
        "components": {
            name: {
                "status": hs.status,
                "message": hs.message,
                "last_check": datetime.fromtimestamp(hs.last_check).isoformat()
            }
            for name, hs in statuses.items()
        }
    }
