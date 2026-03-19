# Agent Framework Exceptions
"""Agent框架异常定义"""


class AgentException(Exception):
    """Agent基础异常"""
    pass


class AgentNotReadyError(AgentException):
    """Agent未就绪异常"""
    pass


class ToolNotFoundError(AgentException):
    """工具未找到异常"""
    pass


class LLMCallError(AgentException):
    """LLM调用异常"""
    pass


class ContextError(AgentException):
    """上下文异常"""
    pass
