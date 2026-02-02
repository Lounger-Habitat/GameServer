"""NPC Agent 数据模型

定义 NPC 相关 Agent 的请求和响应模型
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============== 占位符模型 ==============
# TODO: 根据实际需求定义 NPC Agent 的数据模型

class NPCAgentRequest(BaseModel):
    """NPC Agent 请求（占位符）"""
    message: str = Field(..., description="用户消息")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")


class NPCAgentResponse(BaseModel):
    """NPC Agent 响应（占位符）"""
    response: str = Field(..., description="NPC 响应")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
