"""认证相关API接口。"""

from fastapi import APIRouter, Depends, HTTPException
from gameserver.utils.auth import get_current_active_user

router = APIRouter()

@router.get("/verify")
async def verify_token(current_user = Depends(get_current_active_user)):
    """验证API Key是否有效"""
    return {
        "status": "success",
        "message": "API Key有效",
        "user": {
            "username": current_user.username,
        }
    }
