"""API Key 存储管理"""
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from utils.config import settings

from .models import ApiKey, ApiKeyCreate, ApiKeyInfo


class ApiKeyStore:
    """API Key 存储类 - 使用 JSON 文件持久化"""
    
    def __init__(self, keys_file: str = "api_keys.json"):
        self.keys_file = Path(keys_file)
        self._keys: dict[str, ApiKey] = {}
        self._load()
    
    def _load(self) -> None:
        """从文件加载 Keys"""
        if self.keys_file.exists():
            try:
                with open(self.keys_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, key_data in data.items():
                    # 转换时间字符串
                    key_data["created_at"] = datetime.fromisoformat(key_data["created_at"])
                    if key_data.get("expires_at"):
                        key_data["expires_at"] = datetime.fromisoformat(key_data["expires_at"])
                    self._keys[name] = ApiKey(**key_data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️  加载 API Keys 文件失败: {e}")
                self._keys = {}
    
    def _save(self) -> None:
        """保存 Keys 到文件"""
        data = {}
        for name, key in self._keys.items():
            key_dict = key.model_dump()
            key_dict["created_at"] = key_dict["created_at"].isoformat()
            if key_dict.get("expires_at"):
                key_dict["expires_at"] = key_dict["expires_at"].isoformat()
            data[name] = key_dict
        
        with open(self.keys_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_key(self, request: ApiKeyCreate) -> ApiKey:
        """创建新的 API Key"""
        if request.name in self._keys:
            raise ValueError(f"名称 '{request.name}' 已存在")
        
        # 生成安全的随机 Key
        key = f"sk-{secrets.token_urlsafe(32)}"
        
        # 计算过期时间
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.now() + timedelta(days=request.expires_in_days)
        
        api_key = ApiKey(
            name=request.name,
            key=key,
            created_at=datetime.now(),
            expires_at=expires_at,
            is_active=True
        )
        
        self._keys[request.name] = api_key
        self._save()
        
        return api_key
    
    def get_key(self, name: str) -> Optional[ApiKey]:
        """根据名称获取 Key"""
        return self._keys.get(name)
    
    def get_key_by_value(self, key_value: str) -> Optional[ApiKey]:
        """根据 Key 值查找"""
        for api_key in self._keys.values():
            if api_key.key == key_value:
                return api_key
        return None
    
    def list_keys(self) -> list[ApiKeyInfo]:
        """列出所有 Keys（隐藏完整 key）"""
        result = []
        for api_key in self._keys.values():
            result.append(ApiKeyInfo(
                name=api_key.name,
                key_preview=api_key.key[:12] + "...",
                created_at=api_key.created_at,
                expires_at=api_key.expires_at,
                is_active=api_key.is_active,
                is_expired=not api_key.is_valid() if api_key.is_active else False
            ))
        return result
    
    def delete_key(self, name: str) -> bool:
        """删除指定 Key"""
        if name in self._keys:
            del self._keys[name]
            self._save()
            return True
        return False
    
    def validate_key(self, key_value: str) -> Optional[ApiKey]:
        """验证 Key，返回有效的 ApiKey 或 None"""
        api_key = self.get_key_by_value(key_value)
        if api_key and api_key.is_valid():
            return api_key
        return None


# 全局存储实例
_key_store: Optional[ApiKeyStore] = None


def get_key_store() -> ApiKeyStore:
    """获取全局 Key 存储实例"""
    global _key_store
    if _key_store is None:
        _key_store = ApiKeyStore(settings.auth.keys_file)
    return _key_store
