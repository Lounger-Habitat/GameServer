"""Interview Agent 数据模型

定义面试相关 Agent 的请求和响应模型
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============== Eval Agent ==============

class EvalAgentRequest(BaseModel):
    """评估 Agent 请求"""
    transcript: str = Field(..., description="面试对话记录")
    resume: Optional[str] = Field(None, description="候选人简历")
    job_description: Optional[str] = Field(None, description="职位描述")
    evaluation_criteria: Optional[List[str]] = Field(
        None, 
        description="评估维度（如：聪明度、勤奋度、目标感等）"
    )


class EvalAgentResponse(BaseModel):
    """评估 Agent 响应"""
    evaluation: Dict[str, Any] = Field(..., description="评估结果")
    summary: str = Field(..., description="评估总结")
    scores: Optional[Dict[str, float]] = Field(None, description="各维度评分")


# ============== Interviewer Agent ==============

class InterviewerAgentRequest(BaseModel):
    """面试官 Agent 请求"""
    conversation_history: List[Dict[str, str]] = Field(
        ..., 
        description="对话历史"
    )
    job_description: Optional[str] = Field(None, description="职位描述")
    candidate_resume: Optional[str] = Field(None, description="候选人简历")
    interview_stage: Optional[str] = Field("initial", description="面试阶段")


class InterviewerAgentResponse(BaseModel):
    """面试官 Agent 响应"""
    question: str = Field(..., description="面试官提问")
    reasoning: Optional[str] = Field(None, description="提问理由")
    follow_up_suggestions: Optional[List[str]] = Field(
        None, 
        description="后续问题建议"
    )


# ============== Candidate Agent ==============

class CandidateAgentRequest(BaseModel):
    """候选人 Agent 请求"""
    question: str = Field(..., description="面试官的问题")
    resume: str = Field(..., description="候选人简历")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None, 
        description="对话历史"
    )
    personality_traits: Optional[Dict[str, Any]] = Field(
        None, 
        description="性格特征设定"
    )


class CandidateAgentResponse(BaseModel):
    """候选人 Agent 响应"""
    answer: str = Field(..., description="候选人回答")
    confidence_level: Optional[float] = Field(
        None, 
        ge=0, 
        le=1, 
        description="回答信心度"
    )
    internal_thought: Optional[str] = Field(None, description="内心想法（调试用）")
