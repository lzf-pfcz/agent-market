"""
Rule-Based Agent - 基于规则的Agent
适用于简单场景或需要确定性行为的场景
"""
import re
import logging
from typing import Any, Dict, List, Optional, Callable

from .base import BaseAgent, AgentConfig, ConversationContext, AgentCapability

logger = logging.getLogger(__name__)


class Rule:
    """规则定义"""
    
    def __init__(
        self, 
        pattern: str, 
        response: str | Callable,
        action: Optional[Callable] = None,
        priority: int = 0
    ):
        self.pattern = pattern
        self.response = response
        self.action = action
        self.priority = priority
        self._regex = re.compile(pattern, re.IGNORECASE)
    
    def match(self, text: str) -> bool:
        """检查是否匹配"""
        return bool(self._regex.search(text))
    
    def get_response(self, text: str, context: Optional[ConversationContext] = None) -> str:
        """获取响应"""
        if callable(self.response):
            return self.response(text, context)
        return self.response


class RuleBasedAgent(BaseAgent):
    """
    规则引擎Agent - 基于预定义规则响应
    
    适用于:
    - 简单FAQ场景
    - 命令行接口
    - 需要确定性行为的场景
    """
    
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        
        self._rules: List[Rule] = []
        self._default_response = "抱歉，我不明白您的意思。"
        
        # 默认能力
        if not config.capabilities:
            config.capabilities = [
                AgentCapability.COMMUNICATE,
            ]
    
    def add_rule(
        self, 
        pattern: str, 
        response: str | Callable,
        action: Optional[Callable] = None,
        priority: int = 0
    ) -> 'RuleBasedAgent':
        """
        添加规则
        
        Args:
            pattern: 匹配模式 (正则表达式)
            response: 响应文本或函数
            action: 触发的动作函数
            priority: 优先级 (数字越大越优先)
            
        Returns:
            self (支持链式调用)
        """
        rule = Rule(pattern, response, action, priority)
        self._rules.append(rule)
        
        # 按优先级排序
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        
        return self
    
    def set_default_response(self, response: str) -> None:
        """设置默认响应"""
        self._default_response = response
    
    def add_faq(self, question_pattern: str, answer: str) -> None:
        """快速添加FAQ"""
        self.add_rule(
            pattern=question_pattern,
            response=answer,
            priority=0
        )
    
    def add_intent(
        self, 
        intent_name: str, 
        patterns: List[str], 
        handler: Callable
    ) -> None:
        """添加意图处理器"""
        pattern = "|".join(f"({p})" for p in patterns)
        self.add_rule(
            pattern=pattern,
            response=f"[Action: {intent_name}]",
            action=handler,
            priority=10
        )
    
    async def process(self, input_text: str, context: Optional[ConversationContext] = None) -> Dict[str, Any]:
        """处理输入"""
        if not self._initialized:
            await self.initialize()
        
        # 匹配规则
        for rule in self._rules:
            if rule.match(input_text):
                # 执行动作
                if rule.action:
                    try:
                        result = await rule.action(input_text, context)
                        return {
                            "response": rule.get_response(input_text, context),
                            "action_executed": True,
                            "action_result": result,
                            "matched_rule": rule.pattern
                        }
                    except Exception as e:
                        logger.error(f"Action execution failed: {e}")
                        return {
                            "response": f"执行动作时出错: {str(e)}",
                            "error": str(e)
                        }
                
                # 返回响应
                return {
                    "response": rule.get_response(input_text, context),
                    "matched_rule": rule.pattern
                }
        
        # 未匹配任何规则
        return {
            "response": self._default_response,
            "matched": False
        }
    
    async def initialize(self) -> None:
        """初始化 - 添加默认规则"""
        await super().initialize()
        
        # 如果没有规则，添加一些默认FAQ
        if not self._rules:
            self._add_default_rules()
        
        logger.info(f"Rule-Based Agent {self.name} initialized with {len(self._rules)} rules")
    
    def _add_default_rules(self) -> None:
        """添加默认规则"""
        self.add_rule(
            pattern=r"(你好|hi|hello|嗨)",
            response="您好！有什么可以帮助您的吗？"
        )
        
        self.add_rule(
            pattern=r"(帮助|help|帮助信息)",
            response="我可以帮您：\n1. 查询航班信息\n2. 查询天气\n3. 查询热点新闻\n4. 预订服务\n\n请告诉我您的需求。"
        )
        
        self.add_rule(
            pattern=r"(再见|bye|结束|退出)",
            response="再见！有任何需要随时找我。"
        )
    
    def get_rules_count(self) -> int:
        """获取规则数量"""
        return len(self._rules)


class HybridAgent(RuleBasedAgent):
    """
    混合Agent - 结合规则和LLM
    
    规则优先匹配，匹配失败则调用LLM
    """
    
    def __init__(self, config: AgentConfig, fallback_to_llm: bool = True):
        super().__init__(config)
        self.fallback_to_llm = fallback_to_llm
    
    async def process(self, input_text: str, context: Optional[ConversationContext] = None) -> Dict[str, Any]:
        """处理输入 - 规则优先，LLM兜底"""
        result = await super().process(input_text, context)
        
        # 如果没有匹配规则，且配置了LLM，则使用LLM
        if not result.get("matched") and self.fallback_to_llm and self._llm_client:
            llm_response = await self.think(input_text)
            result["response"] = llm_response
            result["source"] = "llm"
        else:
            result["source"] = "rule"
        
        return result
