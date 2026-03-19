"""
LLM Agent - 基于大模型的智能Agent
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentConfig, ConversationContext, AgentCapability

logger = logging.getLogger(__name__)


class LLMAgent(BaseAgent):
    """
    大模型Agent - 使用LLM理解用户意图
    
    特点:
    - 真正理解自然语言
    - 支持多轮对话
    - 可调用工具
    - 可自定义系统提示词
    """
    
    def __init__(self, config: AgentConfig, system_prompt: str = ""):
        super().__init__(config)
        
        # 默认系统提示词
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # 对话历史缓存
        self._conversation_history: Dict[str, List[Dict]] = {}
        
        # 添加默认能力
        if not config.capabilities:
            config.capabilities = [
                AgentCapability.UNDERSTAND,
                AgentCapability.REASON,
                AgentCapability.COMMUNICATE,
            ]
    
    def _default_system_prompt(self) -> str:
        """默认系统提示词"""
        return f"""你是 {self.config.name}，一个智能AI助手。

你的能力：
- 理解用户意图
- 进行推理和规划
- 提供有用的帮助

请用清晰、准确的语言回复用户。
如果不确定某事，请如实说明。"""
    
    def set_system_prompt(self, prompt: str) -> None:
        """设置系统提示词"""
        self.system_prompt = prompt
    
    def add_tool(self, name: str, description: str, parameters: Dict):
        """
        添加工具定义（用于LLM调用）
        
        Args:
            name: 工具名称
            description: 工具描述
            parameters: 参数schema (JSON Schema)
        """
        if not hasattr(self, '_tools_schema'):
            self._tools_schema = []
        
        self._tools_schema.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
    
    async def process(self, input_text: str, context: Optional[ConversationContext] = None) -> Dict[str, Any]:
        """
        处理用户输入
        
        流程:
        1. 理解用户意图
        2. 决定是否需要调用工具
        3. 生成回复
        """
        if not self._initialized:
            await self.initialize()
        
        session_id = context.session_id if context else "default"
        
        # 获取或创建对话历史
        if session_id not in self._conversation_history:
            self._conversation_history[session_id] = []
        
        history = self._conversation_history[session_id]
        
        # 添加用户消息
        history.append({
            "role": "user",
            "content": input_text
        })
        
        try:
            # 构建消息列表
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(history[-10:])  # 最近10条
            
            # 调用LLM
            response_text = await self._chat_with_llm(messages)
            
            # 添加助手回复到历史
            history.append({
                "role": "assistant", 
                "content": response_text
            })
            
            # 限制历史长度
            if len(history) > 20:
                self._conversation_history[session_id] = history[-20:]
            
            return {
                "response": response_text,
                "intent": self._extract_intent(input_text),
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error processing input: {e}")
            return {
                "response": f"处理您的问题时出现错误: {str(e)}",
                "error": str(e)
            }
    
    async def _chat_with_llm(self, messages: List[Dict[str, str]]) -> str:
        """调用LLM生成回复"""
        if not self._llm_client:
            # 无LLM时的降级处理
            return self._fallback_response(messages)
        
        provider = self.config.llm_provider
        
        try:
            if provider == "openai":
                response = await self._llm_client.chat.completions.create(
                    model=self.config.llm_model,
                    messages=messages,
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens
                )
                return response.choices[0].message.content
            
            elif provider == "anthropic":
                # 转换消息格式
                anthropic_messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in messages if m["role"] != "system"
                ]
                system = next((m["content"] for m in messages if m["role"] == "system"), "")
                
                response = await self._llm_client.messages.create(
                    model=self.config.llm_model,
                    system=system,
                    messages=anthropic_messages,
                    temperature=self.config.llm_temperature,
                    max_tokens=self.config.llm_max_tokens
                )
                return response.content[0].text
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return self._fallback_response(messages)
        
        return "未知错误"
    
    def _fallback_response(self, messages: List[Dict]) -> str:
        """无LLM时的降级回复"""
        last_message = messages[-1]["content"] if messages else ""
        
        # 简单的关键词匹配
        if "天气" in last_message:
            return "我目前无法查询天气，请配置LLM后使用此功能。"
        elif "航班" in last_message or "机票" in last_message:
            return "我目前无法查询航班，请配置LLM后使用此功能。"
        elif "新闻" in last_message or "热点" in last_message:
            return "我目前无法查询新闻，请配置LLM后使用此功能。"
        else:
            return f"我已收到您的消息: {last_message}。当前为演示模式，请配置LLM API以启用智能对话功能。"
    
    def _extract_intent(self, text: str) -> Dict[str, Any]:
        """提取用户意图（简化版）"""
        intents = []
        
        keywords = {
            "查询": ["查询", "查一下", "搜索", "找"],
            "预订": ["预订", "订", "预约", "买"],
            "咨询": ["了解", "什么是", "怎么", "如何"],
            "推荐": ["推荐", "建议", "有什么好"]
        }
        
        for intent, kws in keywords.items():
            if any(kw in text for kw in kws):
                intents.append(intent)
        
        return {
            "intents": intents,
            "raw_text": text
        }
    
    async def initialize(self) -> None:
        """初始化 - 包含LLM初始化"""
        await super().initialize()
        logger.info(f"LLM Agent {self.name} ready (provider: {self.config.llm_provider or 'none'})")
    
    def clear_history(self, session_id: str = "default") -> None:
        """清除对话历史"""
        if session_id in self._conversation_history:
            del self._conversation_history[session_id]
    
    def get_history(self, session_id: str = "default") -> List[Dict]:
        """获取对话历史"""
        return self._conversation_history.get(session_id, [])


class SmartUserAgent(LLMAgent):
    """
    智能用户Agent - 理解用户需求，自动寻找服务
    
    这是对原 user_agent.py 的智能化升级版本
    """
    
    def __init__(self, config: AgentConfig):
        system_prompt = """你是用户的智能助理，能够：
1. 理解用户的自然语言需求
2. 将需求分解为具体任务
3. 自动寻找合适的服务Agent
4. 协调完成多轮对话

当用户提出需求时，你应该：
- 理解用户的真实意图
- 提取关键信息（时间、地点、对象等）
- 规划执行步骤
- 返回结构化的任务描述"""

        super().__init__(config, system_prompt)
        
        # 注册服务发现回调
        self._on_discover_callback = None
        self._on_task_complete_callback = None
    
    def set_discovery_handler(self, handler):
        """设置服务发现处理器"""
        self._on_discover_callback = handler
    
    def set_task_complete_handler(self, handler):
        """设置任务完成处理器"""
        self._on_task_complete_callback = handler
    
    async def process(self, input_text: str, context: Optional[ConversationContext] = None) -> Dict[str, Any]:
        """处理用户需求"""
        result = await super().process(input_text, context)
        
        # 智能分析用户需求
        intent_analysis = await self._analyze_intent(input_text)
        result["intent_analysis"] = intent_analysis
        
        # 如果需要调用外部服务
        if intent_analysis.get("needs_service"):
            service_query = intent_analysis.get("service_query")
            if service_query and self._on_discover_callback:
                # 发现服务
                agents = await self._on_discover_callback(service_query)
                result["discovered_agents"] = agents
        
        return result
    
    async def _analyze_intent(self, text: str) -> Dict[str, Any]:
        """分析用户意图"""
        # 简单意图分析
        analysis = {
            "raw_text": text,
            "needs_service": False,
            "service_query": None,
            "entities": {}
        }
        
        # 航班相关
        if any(kw in text for kw in ["航班", "机票", "飞机", "飞"]):
            analysis["needs_service"] = True
            analysis["service_query"] = "航班"
            # 提取实体
            import re
            cities = re.findall(r"([\u4e00-\u9fa5]+)", text)
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", text)
            
            if cities:
                analysis["entities"]["cities"] = cities
            if dates:
                analysis["entities"]["dates"] = dates
        
        # 天气相关
        elif any(kw in text for kw in ["天气", "气温", "温度"]):
            analysis["needs_service"] = True
            analysis["service_query"] = "天气"
        
        # 新闻相关
        elif any(kw in text for kw in ["新闻", "热点", "热搜"]):
            analysis["needs_service"] = True
            analysis["service_query"] = "热点新闻"
        
        return analysis
