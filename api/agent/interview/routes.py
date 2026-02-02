"""Interview Agent 路由

定义面试相关的 Agent 端点
"""
from fastapi import APIRouter, HTTPException

from .models import (
    EvalAgentRequest, EvalAgentResponse,
    InterviewerAgentRequest, InterviewerAgentResponse,
    CandidateAgentRequest, CandidateAgentResponse
)
from .service import interview_service

router = APIRouter()


@router.get("/")
async def interview_root():
    """Interview Agent 根端点"""
    return {
        "message": "Interview Agent API",
        "endpoints": [
            "POST /eval_agent - 评估面试表现",
            "POST /interviewer_agent - 面试官 Agent",
            "POST /candidate_agent - 候选人 Agent",
        ]
    }


@router.post("/eval_agent", response_model=EvalAgentResponse)
async def eval_agent(request: EvalAgentRequest):
    """评估面试表现
    
    根据面试对话记录、简历和职位描述，评估候选人的表现。
    
    - **transcript**: 面试对话记录（必填）
    - **resume**: 候选人简历（可选）
    - **job_description**: 职位描述（可选）
    - **evaluation_criteria**: 评估维度列表（可选）
    """
    try:
        return await interview_service.eval_agent(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"评估失败: {str(e)}"
        )


@router.post("/interviewer_agent", response_model=InterviewerAgentResponse)
async def interviewer_agent(request: InterviewerAgentRequest):
    """面试官 Agent
    
    根据对话历史、职位描述和候选人简历，生成下一个面试问题。
    
    - **conversation_history**: 对话历史（必填）
    - **job_description**: 职位描述（可选）
    - **candidate_resume**: 候选人简历（可选）
    - **interview_stage**: 面试阶段（可选，默认为 initial）
    """
    try:
        return await interview_service.interviewer_agent(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成问题失败: {str(e)}"
        )


@router.post("/candidate_agent", response_model=CandidateAgentResponse)
async def candidate_agent(request: CandidateAgentRequest):
    """候选人 Agent
    
    根据面试官的问题和候选人简历，生成候选人的回答。
    
    - **question**: 面试官的问题（必填）
    - **resume**: 候选人简历（必填）
    - **conversation_history**: 对话历史（可选）
    - **personality_traits**: 性格特征设定（可选）
    """
    try:
        return await interview_service.candidate_agent(request)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"生成回答失败: {str(e)}"
        )
