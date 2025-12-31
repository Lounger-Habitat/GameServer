"""API Key 管理路由"""
from fastapi import APIRouter, HTTPException, status

from .models import ApiKeyCreate, ApiKeyInfo, ApiKeyResponse
from .storage import get_key_store

router = APIRouter()


@router.get("/")
async def auth_root():
    """鉴权模块"""
    return {
        "message": "API Key 鉴权已启用",
        "note": "目前处于测试阶段，联系管理员获取 API Key",
    }

#     return {
#         "message": "API Key 鉴权模块",
#         "endpoints": [
#             "POST /auth/keys - 创建新 Key",
#             "GET /auth/keys - 列出所有 Keys",
#             "DELETE /auth/keys/{name} - 删除指定 Key",
#         ]
#     }


# @router.post("/keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
# async def create_api_key(request: ApiKeyCreate):
#     """创建新的 API Key
    
#     - **name**: Key 的唯一名称标识
#     - **expires_in_days**: 可选，有效天数（1-365），不设置则永久有效
    
#     返回完整的 API Key，请妥善保存，Key 只会显示一次。
#     """
#     try:
#         key_store = get_key_store()
#         api_key = key_store.create_key(request)
        
#         return ApiKeyResponse(
#             name=api_key.name,
#             key=api_key.key,
#             created_at=api_key.created_at,
#             expires_at=api_key.expires_at,
#         )
#     except ValueError as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(e)
#         )


# @router.get("/keys", response_model=list[ApiKeyInfo])
# async def list_api_keys():
#     """列出所有 API Keys
    
#     返回所有已创建的 Key 信息，Key 值仅显示前缀预览。
#     """
#     key_store = get_key_store()
#     return key_store.list_keys()


# @router.delete("/keys/{name}", status_code=status.HTTP_200_OK)
# async def delete_api_key(name: str):
#     """删除指定的 API Key
    
#     - **name**: 要删除的 Key 名称
#     """
#     key_store = get_key_store()
    
#     if not key_store.delete_key(name):
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=f"未找到名为 '{name}' 的 API Key"
#         )
    
#     return {
#         "success": True,
#         "message": f"已删除 API Key: {name}"
#     }
