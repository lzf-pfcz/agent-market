"""
Agent框架 - 基础抽象类
定义Agent的核心接口和行为
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import logging
import json
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentCapability(str, Enum):
    """Agent能力枚举"""
    # 理解能力
    UNDERSTAND = "understand"           # 理解用户意图
    REASON = "reason"                   # 推理能力
    PLAN = "plan"                       # 规划能力
    LEARN = "learn"                     # 学习能力
    
    # 行动能力
    SEARCH = "search"                    # 搜索能力
    EXECUTE = "execute"                 # 执行能力
    COMMUNICATE = "communicate"         # 沟通能力
    TOOL_USE = "tool_use"               # 工具使用能力


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Agent"
    description: str = ""
    owner_name: str = ""
    
    # 能力配置
    capabilities: List[AgentCapability] = field(default_factory=list)
    
    # 大模型配置
    llm_provider: Optional[str] = None      # openai | anthropic | local
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    # 行为配置
    max_retries: int = 3
    timeout: int = 30
    verbose: bool = True


@dataclass
class ConversationContext:
    """对话上下文"""
    session_id: str
    user_id: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """添加消息到历史"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的消息"""
        return self.history[-count:]
    
    def to_llm_format(self) -> List[Dict[str, str]]:
        """转换为大模型消息格式"""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self.history
        ]


class BaseAgent(ABC):
    """
    Agent基类 - 定义Agent的标准接口
    
    使用方式:
    1. 继承 BaseAgent
    2. 实现 process 方法
    3. 配置 capabilities
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self._initialized = False
        self._llm_client = None
        
        # 注册的工具
        self._tools: Dict[str, Callable] = {}
        
        # 事件回调
        self._event_handlers: Dict[str, List[Callable]] = {}
    
    @property
    def agent_id(self) -> str:
        return self.config.agent_id
    
    @property
    def name(self) -> str:
        return self.config.name
    
    @property
    def is_ready(self) -> bool:
        return self._initialized
    
    @abstractmethod
    async def process(self, input_text: str, context: Optional[ConversationContext] = None) -> Dict[str, Any]:
        """
        处理输入的核心方法 - 子类必须实现
        
        Args:
            input_text: 用户输入
            context: 对话上下文
            
        Returns:
            处理结果字典，包含:
            - response: 回复文本
            - action: 执行的动作 (可选)
            - data: 额外数据 (可选)
        """
        pass
    
    async def initialize(self) -> None:
        """初始化Agent - 可被重写"""
        if self.config.llm_provider:
            await self._init_llm()
        self._initialized = True
        logger.info(f"Agent {self.name} initialized")
    
    async def _init_llm(self) -> None:
        """初始化大模型客户端"""
        provider = self.config.llm_provider
        
        if provider == "openai":
            from openai import AsyncOpenAI
            self._llm_client = AsyncOpenAI(
                api_key=self.config.llm_api_key,
                base_url=self.config.llm_base_url
            )
        elif provider == "anthropic":
            import anthropic
            self._llm_client = anthropic.AsyncAnthropic(
                api_key=self.config.llm_api_key
            )
        elif provider == "local":
            # 可以接入本地模型，如 llama.cpp
            logger.info("Using local LLM (not implemented)")
        else:
            logger.warning(f"Unknown LLM provider: {provider}")
    
    async def chat(self, message: str, context: Optional[ConversationContext] = None) -> str:
        """
        对话接口 - 简单对话
        
        Args:
            message: 用户消息
            context: 对话上下文
            
        Returns:
            Agent回复
        """
        result = await self.process(message, context)
        return result.get("response", "")
    
    def register_tool(self, name: str, func: Callable, description: str = "") -> None:
        """
        注册工具
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
        """
        self._tools[name] = func
        logger.info(f"Registered tool: {name}")
    
    async def call_tool(self, name: str, **kwargs) -> Any:
        """
        调用已注册的工具
        
        Args:
            name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")
        
        tool = self._tools[name]
        if callable(tool):
            return await tool(**kwargs)
        return None
    
    def on(self, event: str, handler: Callable) -> None:
        """注册事件处理器"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def emit(self, event: str, data: Any) -> None:
        """触发事件"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
    
    async def think(self, prompt: str) -> str:
        """
        使用大模型思考 - 需要配置 LLM
        
        Args:
            prompt: 提示词
            
        Returns:
            模型输出
        """
        if not self._llm_client:
            return "LLM not configured"
        
        try:
            if self.config.llm_provider == "openai":
                response = await self._llm_client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens
                )
                return response.choices[0].message.content
            
            elif self.config.llm_provider == "anthropic":
                response = await self._llm_client.messages.create(
                    model=self.config.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens
                )
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return f"Error: {str(e)}"
        
        return "Unknown provider"
    
    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return [cap.value for cap in self.config.capabilities]
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """检查是否具有某能力"""
        return capability in self.config.capabilities
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式 - 用于Agent Card"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.config.description,
            "owner_name": self.config.owner_name,
            "capabilities": self.get_capabilities(),
            "llm_provider": self.config.llm_provider,
            "llm_model": self.config.llm_model,
        }


import asyncio
