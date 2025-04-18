"""Authentication utilities for the GameServer."""

import os
import yaml
from datetime import datetime
from typing import Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from jose import jwt, JWTError
from pydantic import BaseModel

from gameserver.models.user import get_user_by_username, user_exists, create_user

# API Key存储路径
STORAGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
USER_STORAGE_PATH = os.path.join(STORAGE_BASE_PATH, "users")
API_KEY_FILE = os.path.join(USER_STORAGE_PATH, "api_keys.yaml")

# 确保目录存在
os.makedirs(USER_STORAGE_PATH, exist_ok=True)

# 配置API Key认证头
api_key_header = APIKeyHeader(name="Authorization", scheme_name="Bearer")

# JWT配置
SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", "insecure_secret_key_for_development_only"
)
ALGORITHM = "HS256"


class TokenData(BaseModel):
    """Token数据模型"""
    username: str


def load_api_keys() -> Dict[str, Dict]:
    """从文件加载API Keys"""
    if not os.path.exists(API_KEY_FILE):
        return {}
    
    try:
        with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"加载API Keys失败: {e}")
        return {}


# def save_api_keys(api_keys: Dict[str, Dict]) -> None:
#     """保存API Keys到文件"""
#     with open(API_KEY_FILE, 'w', encoding='utf-8') as f:
#         yaml.dump(api_keys, f, allow_unicode=True)


def create_api_key(username: str) -> str:
    """创建新的API Key (永久有效)"""
    # 确保用户存在
    if not user_exists(username):
        create_user(username)
    
    # 创建JWT数据
    data = {
        "sub": username
    }
    
    # 生成JWT令牌 (不设置过期时间，使其永久有效)
    api_key = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)
    
    # 保存API Key
    # api_keys = load_api_keys()
    # api_keys[api_key] = {
    #     "username": username
    # }
    # save_api_keys(api_keys)
    
    return api_key


def get_user_by_api_key(api_key: str) -> Optional[TokenData]:
    """通过API Key获取用户信息"""
    # 尝试解析JWT令牌
    try:
        payload = jwt.decode(api_key, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        username = payload.get("sub")
        
        if username and user_exists(username):
            return TokenData(username=username)
    except JWTError:
        pass
    
    # 如果JWT解析失败，检查静态API Key
    api_keys = load_api_keys()
    if api_key in api_keys:
        user_data = api_keys[api_key]
        if user_exists(user_data["username"]):
            return TokenData(**user_data)
    
    return None


async def get_current_user(api_key: str = Depends(api_key_header)):
    """验证API Key并返回用户信息"""
    # 移除Bearer前缀(如果有)
    if api_key.startswith("Bearer "):
        api_key = api_key[7:]
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的API Key",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_data = get_user_by_api_key(api_key)
    if token_data is None:
        raise credentials_exception
    
    return token_data


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)):
    """获取当前活跃用户"""
    return current_user


# def revoke_api_key(api_key: str) -> bool:
#     """撤销API Key"""
#     api_keys = load_api_keys()
#     if api_key in api_keys:
#         del api_keys[api_key]
#         save_api_keys(api_keys)
#         return True
#     return False
