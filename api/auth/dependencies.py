"""FastAPI 鉴权依赖项"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from .models import ApiKey
from .storage import get_key_store
from utils.config import settings

# 支持两种认证方式
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key_from_header(
    bearer: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    x_api_key: Optional[str] = Depends(api_key_header),
) -> Optional[str]:
    """从 Header 中提取 API Key
    
    支持两种方式:
    1. Authorization: Bearer <key>
    2. X-API-Key: <key>
    """
    if bearer and bearer.credentials:
        return bearer.credentials
    if x_api_key:
        return x_api_key
    return None


async def verify_api_key(
    request: Request,
    api_key: Optional[str] = Depends(get_api_key_from_header),
) -> ApiKey:
    """验证 API Key 依赖项
    
    用法:
        @router.get("/protected")
        async def protected_route(api_key: ApiKey = Depends(verify_api_key)):
            return {"user": api_key.name}
    """

    
    # 检查是否启用鉴权
    if not settings.auth.enabled:
        # 鉴权未启用，返回一个虚拟 Key
        from datetime import datetime
        return ApiKey(
            name="anonymous",
            key="disabled",
            created_at=datetime.now(),
            is_active=True
        )
    
    # 检查白名单路径
    path = request.url.path
    for allowed_path in settings.auth.allow_no_auth_paths:
        if path.startswith(allowed_path):
            from datetime import datetime
            return ApiKey(
                name="anonymous",
                key="whitelisted",
                created_at=datetime.now(),
                is_active=True
            )
    
    # 需要验证 Key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供 API Key，请在 Header 中添加 'Authorization: Bearer <key>' 或 'X-API-Key: <key>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 验证 Key
    key_store = get_key_store()
    validated_key = key_store.validate_key(api_key)
    
    if not validated_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key 无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return validated_key


async def optional_api_key(
    api_key: Optional[str] = Depends(get_api_key_from_header),
) -> Optional[ApiKey]:
    """可选的 API Key 验证（不强制要求）"""
    if not api_key:
        return None
    
    key_store = get_key_store()
    return key_store.validate_key(api_key)
