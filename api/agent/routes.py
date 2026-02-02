"""Agent API 主路由

聚合 interview 和 npc 子路由
"""
from fastapi import APIRouter

# 导入子路由
from .interview.routes import router as interview_router
from .npc.routes import router as npc_router

router = APIRouter()

# 包含子路由
router.include_router(interview_router, prefix="/interview", tags=["Agent - Interview"])
router.include_router(npc_router, prefix="/npc", tags=["Agent - NPC"])


@router.get("/")
async def agent_root():
    """Agent API 根端点"""
    return {
        "message": "Agent API",
        "version": "1.0",
        "sub_modules": [
            {
                "path": "/agent/interview",
                "description": "面试相关 Agent",
                "endpoints": [
                    "POST /agent/interview/eval_agent - 评估面试表现",
                    "POST /agent/interview/interviewer_agent - 面试官 Agent",
                    "POST /agent/interview/candidate_agent - 候选人 Agent",
                ]
            },
            {
                "path": "/agent/npc",
                "description": "NPC 相关 Agent",
                "endpoints": [
                    "(待定义)"
                ]
            }
        ]
    }
