"""
错误处理装饰器和异常处理器
"""
import logging
import traceback
from functools import wraps
from typing import Callable, Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import APIError, ErrorCode

logger = logging.getLogger(__name__)


def handle_api_error(func: Callable) -> Callable:
    """API错误处理装饰器 - 用于自动捕获和处理APIError"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        except APIError as e:
            logger.warning(f"API Error in {func.__name__}: {e.message}")
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict()
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            logger.debug(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content=APIError(
                    ErrorCode.COMMON_INTERNAL_ERROR,
                    "An unexpected error occurred",
                    details={"function": func.__name__}
                ).to_dict()
            )
    return wrapper


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """全局错误处理中间件"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
            return response
        except APIError as e:
            logger.warning(f"API Error: {e.message}")
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict()
            )
        except Exception as e:
            logger.error(f"Unhandled exception: {str(e)}")
            logger.debug(traceback.format_exc())
            return JSONResponse(
                status_code=500,
                content=APIError(
                    ErrorCode.COMMON_INTERNAL_ERROR,
                    "An unexpected error occurred",
                    details={"path": str(request.url)}
                ).to_dict()
            )


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """FastAPI异常处理器 - 处理APIError"""
    logger.warning(f"API Error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=APIError(
            ErrorCode.COMMON_INTERNAL_ERROR,
            "An unexpected error occurred",
            details={"path": str(request.url)}
        ).to_dict()
    )
