"""User model for authentication and authorization."""

import os
import yaml
from typing import Dict, List, Optional

from pydantic import BaseModel

# 用户存储路径
STORAGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage")
USER_STORAGE_PATH = os.path.join(STORAGE_BASE_PATH, "users")
USER_FILE = os.path.join(USER_STORAGE_PATH, "users.yaml")

# 确保目录存在
os.makedirs(USER_STORAGE_PATH, exist_ok=True)


class User(BaseModel):
    """简化的用户模型"""
    username: str
    display_name: Optional[str] = None


def load_users() -> Dict[str, User]:
    """从文件加载用户信息"""
    if not os.path.exists(USER_FILE):
        return {}
    
    try:
        with open(USER_FILE, 'r', encoding='utf-8') as f:
            user_data = yaml.safe_load(f) or {}
            return {username: User(**data) for username, data in user_data.items()}
    except Exception as e:
        print(f"加载用户信息失败: {e}")
        return {}


def save_user(user: User) -> None:
    """保存用户信息到文件"""
    users = load_users()
    users[user.username] = user
    
    # 转换为可序列化的字典
    user_dict = {username: user.dict() for username, user in users.items()}
    
    with open(USER_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(user_dict, f, allow_unicode=True)


def get_user_by_username(username: str) -> Optional[User]:
    """通过用户名获取用户"""
    users = load_users()
    return users.get(username)


def create_user(username: str, display_name: Optional[str] = None) -> User:
    """创建新用户"""
    user = User(username=username, display_name=display_name or username)
    save_user(user)
    return user


def get_all_users() -> List[User]:
    """获取所有用户"""
    return list(load_users().values())


def user_exists(username: str) -> bool:
    """检查用户是否存在"""
    return get_user_by_username(username) is not None


def delete_user(username: str) -> bool:
    """删除用户"""
    users = load_users()
    if username in users:
        del users[username]
        
        # 转换为可序列化的字典
        user_dict = {username: user.dict() for username, user in users.items()}
        
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(user_dict, f, allow_unicode=True)
        
        return True
    
    return False
