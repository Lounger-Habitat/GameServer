"""API Key 数据模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ApiKey(BaseModel):
    """API Key 完整信息"""
    name: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True

    def is_valid(self) -> bool:
        """检查 Key 是否有效"""
        if not self.is_active:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True


class ApiKeyCreate(BaseModel):
    """创建 API Key 请求"""
    name: str = Field(..., min_length=1, max_length=64, description="Key 名称，用于标识")
    expires_in_days: Optional[int] = Field(
        None, 
        ge=1, 
        le=365,
        description="有效天数，不设置则永久有效"
    )


class ApiKeyResponse(BaseModel):
    """API Key 响应（创建时返回完整 key）"""
    name: str
    key: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    message: str = "请妥善保存此 Key，它只会显示一次"


class ApiKeyInfo(BaseModel):
    """API Key 信息（列表时返回，隐藏完整 key）"""
    name: str
    key_preview: str  # 只显示前8位
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    is_expired: bool
