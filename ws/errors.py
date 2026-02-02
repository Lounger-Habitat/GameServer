"""Monitor API 错误定义"""
from fastapi import HTTPException
from typing import Optional, Dict, Any


class MonitorAPIError(HTTPException):
    """Monitor API 基础错误"""
    
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details or {}
                }
            }
        )


class ClientNotFoundError(MonitorAPIError):
    """客户端不存在"""
    
    def __init__(self, client_id: str):
        super().__init__(
            status_code=404,
            error_code="CLIENT_NOT_FOUND",
            message=f"Client '{client_id}' not found",
            details={"client_id": client_id}
        )


class EnvironmentNotFoundError(MonitorAPIError):
    """环境不存在"""
    
    def __init__(self, env_id: str):
        super().__init__(
            status_code=404,
            error_code="ENVIRONMENT_NOT_FOUND",
            message=f"Environment '{env_id}' not found",
            details={"env_id": env_id}
        )


class InvalidParameterError(MonitorAPIError):
    """参数错误"""
    
    def __init__(self, parameter: str, message: str):
        super().__init__(
            status_code=400,
            error_code="INVALID_PARAMETER",
            message=message,
            details={"parameter": parameter}
        )


class RateLimitExceededError(MonitorAPIError):
    """超过速率限制"""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            details={"limit": limit, "window": window}
        )


class InternalError(MonitorAPIError):
    """内部服务器错误"""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message=message,
            details={}
        )
