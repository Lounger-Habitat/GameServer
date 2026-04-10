"""MengLong API 数据模型

直接使用 MengLong SDK 的 schema 类型
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

# 直接从 MengLong SDK 导入所有需要的类型
from menglong.schemas.chat import (
    Message,  # 消息类型
    Response,  # 响应类型
    StreamResponse,  # 流式响应类型
    Usage,  # Token 使用统计
    Output,  # 输出类型
    Delta,  # 流式增量
)

# 也可以使用便捷的消息构造器
from menglong import User, Assistant, System


# ============== 额外的 API 模型（仅用于 API 层） ==============


class MengLongModelInfo(BaseModel):
    """模型信息"""

    id: str = Field(..., description="模型 ID")
    name: str = Field(..., description="模型显示名称")
    provider: Optional[str] = Field(None, description="模型提供商")
    description: Optional[str] = Field(None, description="模型描述")
    max_tokens: Optional[int] = Field(None, description="最大 token 数")
    supports: Dict[str, bool] = Field(
        {"streaming": True, "image": True, "audio": True, "file": True, "video": True, "tools": True},
        description="能力支持",
    )
    price: Optional[Dict[str, float]] = Field(
        {"input": 0.0, "cache_input": 0.0, "output": 0.0}, description="模型价格"
    )
