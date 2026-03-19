"""
协议适配器 - 支持多种标准协议接入
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ProtocolAdapter(ABC):
    """协议适配器基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """适配器名称"""
        pass
    
    @abstractmethod
    async def to_acp(self, message: Any) -> Optional[Dict]:
        """转换为ACP协议消息"""
        pass
    
    @abstractmethod
    async def from_acp(self, message: Dict) -> Any:
        """从ACP协议消息转换"""
        pass


@dataclass
class AdapterRegistration:
    """适配器注册信息"""
    adapter_id: str
    name: str
    description: str
    version: str
    adapter_class: type


class AdapterRegistry:
    """协议适配器注册中心"""
    
    def __init__(self):
        self._adapters: Dict[str, AdapterRegistration] = {}
    
    def register(self, adapter: ProtocolAdapter, adapter_id: str, description: str = "") -> None:
        """注册适配器"""
        reg = AdapterRegistration(
            adapter_id=adapter_id,
            name=adapter.name,
            description=description,
            version="1.0",
            adapter_class=type(adapter)
        )
        self._adapters[adapter_id] = reg
        logger.info(f"Registered adapter: {adapter.name}")
    
    def get(self, adapter_id: str) -> Optional[AdapterRegistration]:
        """获取适配器"""
        return self._adapters.get(adapter_id)
    
    def list_all(self) -> Dict[str, AdapterRegistration]:
        """列出所有适配器"""
        return self._adapters.copy()


# ==================== OpenAI Plugin 适配器 ====================

class OpenAIPluginAdapter(ProtocolAdapter):
    """
    OpenAI Plugin 格式适配器
    
    将 OpenAI Plugin Manifest 转换为 ACP Agent Card
    """
    
    @property
    def name(self) -> str:
        return "openai_plugin"
    
    async def to_acp(self, plugin_manifest: Dict) -> Optional[Dict]:
        """OpenAI Plugin -> ACP Agent Card"""
        try:
            # 解析 plugin_manifest.json
            return {
                "agent_id": f"openai_{plugin_manifest.get('name', 'unknown').replace(' ', '_')}",
                "name": plugin_manifest.get("name", "OpenAI Plugin"),
                "description": plugin_manifest.get("description", ""),
                "owner": plugin_manifest.get("author_name", ""),
                "capabilities": [
                    {
                        "name": "plugin_execute",
                        "description": f"Execute {plugin_manifest.get('name')} plugin",
                        "input_schema": plugin_manifest.get("parameters", {})
                    }
                ],
                "tags": ["openai", "plugin"],
                "endpoint": plugin_manifest.get("api", {}).get("base_url", ""),
                "acp_version": "1.0"
            }
        except Exception as e:
            logger.error(f"Failed to convert OpenAI plugin: {e}")
            return None
    
    async def from_acp(self, agent_card: Dict) -> Dict:
        """ACP Agent Card -> OpenAI Plugin Manifest"""
        # 这是一个单向转换，仅作参考
        return {
            "schema_version": "v1",
            "name_for_model": agent_card.get("name", ""),
            "name_for_human": agent_card.get("name", ""),
            "description_for_model": agent_card.get("description", ""),
            "description_for_human": agent_card.get("description", ""),
        }


# ==================== DIDComm 适配器 ====================

class DIDCommAdapter(ProtocolAdapter):
    """
    DIDComm 协议适配器
    
    支持 W3C DIDComm 消息格式
    https://didcomm.org/
    """
    
    @property
    def name(self) -> str:
        return "didcomm"
    
    async def to_acp(self, didcomm_msg: Dict) -> Optional[Dict]:
        """DIDComm -> ACP"""
        try:
            # DIDComm 消息格式
            # {
            #   "id": "unique-id",
            #   "type": "https://didcomm.org/message/1.0/problem-report",
            #   "body": { ... },
            #   "from": "did:example:alice",
            #   "to": "did:example:bob"
            # }
            
            # 映射到 ACP
            return {
                "id": didcomm_msg.get("id", ""),
                "type": self._map_type(didcomm_msg.get("type", "")),
                "protocol_version": "1.0",
                "from_agent": self._extract_did(didcomm_msg.get("from", "")),
                "to_agent": self._extract_did(didcomm_msg.get("to", "")),
                "payload": didcomm_msg.get("body", {}),
                "metadata": {
                    "original_type": didcomm_msg.get("type"),
                    "didcomm_version": "2.0"
                }
            }
        except Exception as e:
            logger.error(f"Failed to convert DIDComm message: {e}")
            return None
    
    async def from_acp(self, acp_msg: Dict) -> Dict:
        """ACP -> DIDComm"""
        # 提取 DID
        from_did = f"did:agent:marketplace:{acp_msg.get('from_agent', '')}"
        to_did = f"did:agent:marketplace:{acp_msg.get('to_agent', '')}"
        
        return {
            "id": acp_msg.get("id", ""),
            "type": self._map_type_reverse(acp_msg.get("type", "")),
            "from": from_did,
            "to": to_did,
            "body": acp_msg.get("payload", {}),
            "created_time": acp_msg.get("timestamp", "")
        }
    
    def _map_type(self, didcomm_type: str) -> str:
        """DIDComm type -> ACP type"""
        mapping = {
            "offer-invitation": "handshake.init",
            "request-policy": "discover.request",
            "propose-delegation": "task.request",
        }
        return mapping.get(didcomm_type, didcomm_type)
    
    def _map_type_reverse(self, acp_type: str) -> str:
        """ACP type -> DIDComm type"""
        mapping = {
            "handshake.init": "offer-invitation",
            "discover.request": "request-policy",
            "task.request": "propose-delegation",
        }
        return mapping.get(acp_type, acp_type)
    
    def _extract_did(self, did: str) -> str:
        """从 DID 提取 Agent ID"""
        # did:agent:marketplace:xxx -> xxx
        if ":" in did:
            return did.split(":")[-1]
        return did


# ==================== MCP (Model Context Protocol) 适配器 ====================

class MCPAdapter(ProtocolAdapter):
    """
    MCP (Model Context Protocol) 适配器
    
    Anthropic's Model Context Protocol
    """
    
    @property
    def name(self) -> str:
        return "mcp"
    
    async def to_acp(self, mcp_msg: Dict) -> Optional[Dict]:
        """MCP -> ACP"""
        # MCP 消息类型
        # - tools/list, tools/call
        # - resources/list, resources/read
        # - prompts/list, prompts/get
        
        msg_type = mcp_msg.get("jsonrpc", "")
        
        if "tools/list" in str(mcp_msg):
            return {
                "type": "discover.request",
                "from_agent": mcp_msg.get("params", {}).get("agent_id", ""),
                "payload": {"query": ""}
            }
        
        return {
            "type": "task.request",
            "from_agent": mcp_msg.get("params", {}).get("agent_id", ""),
            "payload": mcp_msg.get("params", {})
        }
    
    async def from_acp(self, acp_msg: Dict) -> Dict:
        """ACP -> MCP"""
        return {
            "jsonrpc": "2.0",
            "id": acp_msg.get("id", ""),
            "result": acp_msg.get("payload", {})


# ==================== Anthropic Messages 适配器 ====================

class AnthropicAdapter(ProtocolAdapter):
    """
    Anthropic Messages API 适配器
    
    让 Claude 可以调用平台上的 Agent
    """
    
    @property
    def name(self) -> str:
        return "anthropic_messages"
    
    async def to_acp(self, anthropic_msg: Dict) -> Optional[Dict]:
        """Anthropic Message -> ACP Task"""
        # Anthropic tool_use 消息
        tools = anthropic_msg.get("tools", [])
        
        if not tools:
            return None
        
        # 转换为任务请求
        return {
            "type": "task.request",
            "from_agent": "anthropic_claude",
            "payload": {
                "task_type": "tool_call",
                "tools": tools,
                "message": anthropic_msg.get("message", {})
            }
        }
    
    async def from_acp(self, acp_msg: Dict) -> Dict:
        """ACP Task Result -> Anthropic Tool Result"""
        return {
            "type": "tool_result",
            "tool_use_id": acp_msg.get("metadata", {}).get("tool_use_id"),
            "result": acp_msg.get("payload", {}).get("result")
        }


# ==================== 全局适配器注册 ====================

_adapters = {
    "openai_plugin": OpenAIPluginAdapter,
    "didcomm": DIDCommAdapter,
    "mcp": MCPAdapter,
    "anthropic": AnthropicAdapter,
}

_adapter_registry = AdapterRegistry()


def get_adapter(protocol: str) -> Optional[ProtocolAdapter]:
    """获取协议适配器"""
    adapter_class = _adapters.get(protocol)
    if adapter_class:
        return adapter_class()
    return None


def register_adapter(protocol: str, adapter: ProtocolAdapter) -> None:
    """注册自定义适配器"""
    _adapter_registry.register(adapter, protocol)


def convert_to_acp(protocol: str, message: Any) -> Optional[Dict]:
    """通用转换接口"""
    adapter = get_adapter(protocol)
    if adapter:
        return adapter.to_acp(message)
    return None


def convert_from_acp(protocol: str, message: Dict) -> Any:
    """通用反向转换接口"""
    adapter = get_adapter(protocol)
    if adapter:
        return adapter.from_acp(message)
    return None
