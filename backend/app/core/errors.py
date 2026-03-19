"""
Agent Marketplace V2 - 错误处理模块
统一错误码定义和错误响应格式
"""
from enum import Enum
from typing import Optional, Any, Dict
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class ErrorCode(str, Enum):
    """错误码枚举 - 格式: {模块}_{类型}_{序号}"""
    
    # 通用错误 (COMMON_xxx)
    COMMON_SUCCESS = "COMMON_SUCCESS"           # 成功
    COMMON_INVALID_REQUEST = "COMMON_INVALID_REQUEST"  # 无效请求
    COMMON_UNAUTHORIZED = "COMMON_UNAUTHORIZED"        # 未授权
    COMMON_FORBIDDEN = "COMMON_FORBIDDEN"              # 禁止访问
    COMMON_NOT_FOUND = "COMMON_NOT_FOUND"              # 资源不存在
    COMMON_INTERNAL_ERROR = "COMMON_INTERNAL_ERROR"    # 内部错误
    COMMON_SERVICE_UNAVAILABLE = "COMMON_SERVICE_UNAVAILABLE"  # 服务不可用
    COMMON_TIMEOUT = "COMMON_TIMEOUT"                  # 超时
    COMMON_RATE_LIMITED = "COMMON_RATE_LIMITED"        # 限流
    
    # 认证错误 (AUTH_xxx)
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"         # 无效Token
    AUTH_EXPIRED_TOKEN = "AUTH_EXPIRED_TOKEN"         # Token过期
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"  # 凭证错误
    
    # Agent错误 (AGENT_xxx)
    AGENT_NOT_FOUND = "AGENT_NOT_FOUND"               # Agent不存在
    AGENT_OFFLINE = "AGENT_OFFLINE"                   # Agent离线
    AGENT_BUSY = "AGENT_BUSY"                         # Agent忙碌
    AGENT_ALREADY_EXISTS = "AGENT_ALREADY_EXISTS"     # Agent已存在
    AGENT_REGISTRATION_FAILED = "AGENT_REGISTRATION_FAILED"  # 注册失败
    AGENT_CONNECTION_FAILED = "AGENT_CONNECTION_FAILED"      # 连接失败
    
    # 会话错误 (SESSION_xxx)
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"           # 会话不存在
    SESSION_EXPIRED = "SESSION_EXPIRED"               # 会话过期
    SESSION_ESTABLISHED = "SESSION_ESTABLISHED"       # 会话已建立
    SESSION_CLOSED = "SESSION_CLOSED"                 # 会话已关闭
    SESSION_HANDSHAKE_FAILED = "SESSION_HANDSHAKE_FAILED"  # 握手失败
    
    # 任务错误 (TASK_xxx)
    TASK_NOT_FOUND = "TASK_NOT_FOUND"                 # 任务不存在
    TASK_FAILED = "TASK_FAILED"                       # 任务执行失败
    TASK_TIMEOUT = "TASK_TIMEOUT"                     # 任务超时
    TASK_CANCELLED = "TASK_CANCELLED"                 # 任务取消
    
    # 协议错误 (PROTOCOL_xxx)
    PROTOCOL_INVALID_MESSAGE = "PROTOCOL_INVALID_MESSAGE"   # 无效消息格式
    PROTOCOL_UNSUPPORTED_VERSION = "PROTOCOL_UNSUPPORTED_VERSION"  # 不支持的协议版本
    PROTOCOL_INVALID_PAYLOAD = "PROTOCOL_INVALID_PAYLOAD"   # 无效载荷
    
    # 服务发现错误 (DISCOVER_xxx)
    DISCOVER_NO_RESULTS = "DISCOVER_NO_RESULTS"       # 未找到结果
    DISCOVER_QUERY_INVALID = "DISCOVER_QUERY_INVALID" # 查询无效


class APIError(Exception):
    """API错误基类"""
    
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }
    
    def to_websocket_message(self) -> Dict[str, Any]:
        """转换为WebSocket消息格式"""
        return {
            "type": "system.error",
            "payload": {
                "error_code": self.code.value,
                "message": self.message,
                "details": self.details
            }
        }


# ==================== 便捷错误创建函数 ====================

def bad_request(message: str, code: ErrorCode = ErrorCode.COMMON_INVALID_REQUEST, **details) -> APIError:
    """400 - 无效请求"""
    return APIError(code, message, status.HTTP_400_BAD_REQUEST, details)


def unauthorized(message: str = "Unauthorized", code: ErrorCode = ErrorCode.COMMON_UNAUTHORIZED, **details) -> APIError:
    """401 - 未授权"""
    return APIError(code, message, status.HTTP_401_UNAUTHORIZED, details)


def forbidden(message: str = "Forbidden", code: ErrorCode = ErrorCode.COMMON_FORBIDDEN, **details) -> APIError:
    """403 - 禁止访问"""
    return APIError(code, message, status.HTTP_403_FORBIDDEN, details)


def not_found(resource: str, code: ErrorCode = ErrorCode.COMMON_NOT_FOUND, **details) -> APIError:
    """404 - 资源不存在"""
    message = f"{resource} not found"
    return APIError(code, message, status.HTTP_404_NOT_FOUND, details)


def internal_error(message: str = "Internal server error", code: ErrorCode = ErrorCode.COMMON_INTERNAL_ERROR, **details) -> APIError:
    """500 - 内部错误"""
    return APIError(code, message, status.HTTP_500_INTERNAL_SERVER_ERROR, details)


def service_unavailable(message: str = "Service unavailable", code: ErrorCode = ErrorCode.COMMON_SERVICE_UNAVAILABLE, **details) -> APIError:
    """503 - 服务不可用"""
    return APIError(code, message, status.HTTP_503_SERVICE_UNAVAILABLE, details)


# ==================== 特定业务错误 ====================

def agent_not_found(agent_id: str) -> APIError:
    """Agent不存在错误"""
    return not_found(f"Agent {agent_id}", ErrorCode.AGENT_NOT_FOUND, agent_id=agent_id)


def agent_offline(agent_id: str) -> APIError:
    """Agent离线错误"""
    return APIError(
        ErrorCode.AGENT_OFFLINE,
        f"Agent {agent_id} is currently offline",
        status.HTTP_400_BAD_REQUEST,
        agent_id=agent_id
    )


def agent_busy(agent_id: str) -> APIError:
    """Agent忙碌错误"""
    return APIError(
        ErrorCode.AGENT_BUSY,
        f"Agent {agent_id} is currently busy",
        status.HTTP_400_BAD_REQUEST,
        agent_id=agent_id
    )


def session_not_found(session_id: str) -> APIError:
    """会话不存在错误"""
    return not_found(f"Session {session_id}", ErrorCode.SESSION_NOT_FOUND, session_id=session_id)


def session_expired(session_id: str) -> APIError:
    """会话过期错误"""
    return APIError(
        ErrorCode.SESSION_EXPIRED,
        f"Session {session_id} has expired",
        status.HTTP_400_BAD_REQUEST,
        session_id=session_id
    )


def handshake_failed(reason: str, **details) -> APIError:
    """握手失败错误"""
    return APIError(
        ErrorCode.SESSION_HANDSHAKE_FAILED,
        f"Handshake failed: {reason}",
        status.HTTP_400_BAD_REQUEST,
        reason=reason,
        **details
    )


def invalid_token(reason: str = "Invalid token") -> APIError:
    """无效Token错误"""
    return unauthorized(reason, ErrorCode.AUTH_INVALID_TOKEN)


def expired_token(reason: str = "Token has expired") -> APIError:
    """Token过期错误"""
    return unauthorized(reason, ErrorCode.AUTH_EXPIRED_TOKEN)


# ==================== HTTP异常转换 ====================

def api_error_to_http(error: APIError) -> HTTPException:
    """将APIError转换为FastAPI HTTPException"""
    return HTTPException(
        status_code=error.status_code,
        detail=error.to_dict()
    )


# ==================== 错误响应格式化 ====================

def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """成功响应格式"""
    return {
        "success": True,
        "message": message,
        "data": data
    }


def error_response(error: APIError) -> Dict[str, Any]:
    """错误响应格式"""
    return {
        "success": False,
        "error": {
            "code": error.code.value,
            "message": error.message,
            "details": error.details
        }
    }
