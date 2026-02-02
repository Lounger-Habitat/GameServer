"""NPC Agent 路由

定义 NPC 相关的 Agent 端点
"""
from fastapi import APIRouter, HTTPException

from .models import NPCAgentRequest, NPCAgentResponse
from .service import npc_service

router = APIRouter()


@router.get("/")
async def npc_root():
    """NPC Agent 根端点"""
    return {
        "message": "NPC Agent API",
        "status": "待定义",
        "description": "NPC 相关功能端点将在此处定义"
    }


@router.post("/process", response_model=NPCAgentResponse)
async def process_npc(request: NPCAgentRequest):
    """NPC Agent 处理端点（占位符）
    
    TODO: 根据实际需求定义具体的 NPC 端点
    
    - **message**: 用户消息（必填）
    - **context**: 上下文信息（可选）
    """
    try:
        return await npc_service.process(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"NPC 处理失败: {str(e)}"
        )
