"""
重试机制 - 自动重试和熔断
"""
import asyncio
import logging
from typing import Callable, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import random

logger = logging.getLogger(__name__)


class RetryStrategy(str, Enum):
    """重试策略"""
    FIXED = "fixed"           # 固定间隔
    LINEAR = "linear"         # 线性递增
    EXPONENTIAL = "exponential"  # 指数退避
    FIBONACCI = "fibonacci"   # 斐波那契


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 3           # 最大尝试次数
    initial_delay: float = 1.0       # 初始延迟(秒)
    max_delay: float = 30.0         # 最大延迟(秒)
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True             # 是否添加随机抖动
    jitter_range: float = 0.3       # 抖动范围 (0-1)
    
    # 可重试的错误
    retryable_errors: List[str] = field(default_factory=lambda: [
        "ConnectionError",
        "TimeoutError", 
        "TemporaryFailure"
    ])


@dataclass
class CircuitState:
    """熔断器状态"""
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    
    # 配置
    failure_threshold: int = 5      # 触发熔断的失败次数
    recovery_timeout: int = 60       # 恢复超时(秒)
    half_open_requests: int = 0     # 半开状态的请求数


class RetryableError(Exception):
    """可重试的错误"""
    def __init__(self, message: str, error_type: str = "TemporaryFailure"):
        super().__init__(message)
        self.error_type = error_type


class NonRetryableError(Exception):
    """不可重试的错误"""
    pass


class CircuitBreakerOpen(Exception):
    """熔断器已打开"""
    pass


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    带退避的重试装饰器/函数
    
    Args:
        func: 要执行的异步函数
        config: 重试配置
        
    Returns:
        函数执行结果
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
            
        except NonRetryableError:
            # 不可重试的错误直接抛出
            raise
            
        except Exception as e:
            last_exception = e
            error_type = type(e).__name__
            
            # 检查是否可重试
            if error_type not in config.retryable_errors:
                logger.warning(f"Non-retryable error: {error_type}")
                raise
            
            # 计算延迟
            delay = calculate_delay(attempt, config)
            
            logger.warning(
                f"Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            
            if attempt < config.max_attempts - 1:
                await asyncio.sleep(delay)
    
    # 所有尝试都失败
    logger.error(f"All {config.max_attempts} attempts failed")
    raise last_exception


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """计算重试延迟"""
    if config.strategy == RetryStrategy.FIXED:
        delay = config.initial_delay
        
    elif config.strategy == RetryStrategy.LINEAR:
        delay = config.initial_delay * (attempt + 1)
        
    elif config.strategy == RetryStrategy.EXPONENTIAL:
        delay = config.initial_delay * (2 ** attempt)
        
    elif config.strategy == RetryStrategy.FIBONACCI:
        # 斐波那契数列
        fib = [1, 1, 2, 3, 5, 8, 13, 21]
        idx = min(attempt, len(fib) - 1)
        delay = config.initial_delay * fib[idx]
    
    # 添加抖动
    if config.jitter:
        jitter_amount = delay * config.jitter_range
        delay = delay + random.uniform(-jitter_amount, jitter_amount)
    
    # 限制最大延迟
    return min(delay, config.max_delay)


class CircuitBreaker:
    """
    熔断器
    
    状态:
    - closed: 正常，允许请求通过
    - open: 熔断，拒绝请求
    - half-open: 半开，允许部分请求通过用于探测
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.state = CircuitState(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        self.half_open_max_calls = half_open_max_calls
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """执行带熔断保护的调用"""
        
        # 检查是否可以执行
        if not self._can_execute():
            raise CircuitBreakerOpen(
                f"Circuit breaker is open. State: {self.state.state}"
            )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except Exception as e:
            self._on_failure()
            raise
    
    def _can_execute(self) -> bool:
        """检查是否可以执行请求"""
        
        if self.state.state == "closed":
            return True
        
        if self.state.state == "open":
            # 检查是否超时
            if self.state.last_failure_time:
                elapsed = (datetime.utcnow() - self.state.last_failure_time).total_seconds()
                if elapsed >= self.state.recovery_timeout:
                    logger.info("Circuit breaker transitioning to half-open")
                    self.state.state = "half-open"
                    self.state.half_open_requests = 0
                    return True
            return False
        
        if self.state.state == "half-open":
            # 半开状态限制请求数
            return self.state.half_open_requests < self.half_open_max_calls
        
        return False
    
    def _on_success(self) -> None:
        """成功回调"""
        if self.state.state == "half-open":
            self.state.half_open_requests += 1
            
            # 连续成功，关闭熔断器
            if self.state.half_open_requests >= self.half_open_max_calls:
                logger.info("Circuit breaker closed after successful recovery")
                self.state.state = "closed"
                self.state.failures = 0
        
        elif self.state.state == "closed":
            # 成功时减少失败计数
            self.state.failures = max(0, self.state.failures - 1)
    
    def _on_failure(self) -> None:
        """失败回调"""
        self.state.failures += 1
        self.state.last_failure_time = datetime.utcnow()
        
        if self.state.state == "half-open":
            # 半开状态失败，重新打开
            logger.warning("Circuit breaker re-opened after half-open failure")
            self.state.state = "open"
            
        elif self.state.state == "closed":
            # 达到阈值，打开熔断器
            if self.state.failures >= self.state.failure_threshold:
                logger.warning(f"Circuit breaker opened after {self.state.failures} failures")
                self.state.state = "open"
    
    def get_state(self) -> dict:
        """获取熔断器状态"""
        return {
            "state": self.state.state,
            "failures": self.state.failures,
            "last_failure": self.state.last_failure_time.isoformat() if self.state.last_failure_time else None
        }
    
    def reset(self) -> None:
        """手动重置熔断器"""
        self.state = CircuitState()
        logger.info("Circuit breaker manually reset")


class FallbackManager:
    """
    降级管理器
    
    当主服务不可用时，自动切换到备用服务
    """
    
    def __init__(self):
        self._fallbacks: Dict[str, List[Callable]] = {}
    
    def register_fallback(self, service_name: str, fallback_func: Callable) -> None:
        """注册降级函数"""
        if service_name not in self._fallbacks:
            self._fallbacks[service_name] = []
        self._fallbacks[service_name].append(fallback_func)
    
    async def execute_with_fallback(
        self,
        service_name: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """执行主函数，失败时调用降级"""
        try:
            return await primary_func(*args, **kwargs)
            
        except Exception as e:
            logger.warning(f"Primary service {service_name} failed: {e}")
            
            if service_name in self._fallbacks:
                # 尝试降级函数
                for fallback in self._fallbacks[service_name]:
                    try:
                        return await fallback(*args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback failed: {fallback_error}")
            
            # 所有都失败
            raise


from typing import Dict
