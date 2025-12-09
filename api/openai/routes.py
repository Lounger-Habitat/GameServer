"""OpenAI 兼容 API 路由"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


# 数据模型
class Model(BaseModel):
    """模型信息"""
    id: str
    object: str = "model"
    created: int
    owned_by: str


class ModelList(BaseModel):
    """模型列表"""
    object: str = "list"
    data: List[Model]


class ChatMessage(BaseModel):
    """聊天消息"""
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    """聊天补全请求"""
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class ChatCompletionChoice(BaseModel):
    """聊天补全选择"""
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionResponse(BaseModel):
    """聊天补全响应"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]


# API 端点
@router.get("/models", response_model=ModelList)
async def list_models():
    """列出可用模型"""
    return ModelList(
        data=[
            Model(
                id="gpt-3.5-turbo",
                created=int(datetime.now().timestamp()),
                owned_by="openai"
            ),
            Model(
                id="gpt-4",
                created=int(datetime.now().timestamp()),
                owned_by="openai"
            ),
        ]
    )


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(request: ChatCompletionRequest):
    """创建聊天补全（示例实现）"""
    # 这里是示例响应，实际应该调用 LLM 服务
    return ChatCompletionResponse(
        id="chatcmpl-123",
        created=int(datetime.now().timestamp()),
        model=request.model,
        choices=[
            ChatCompletionChoice(
                index=0,
                message=ChatMessage(
                    role="assistant",
                    content="这是一个示例响应。实际实现需要连接到 LLM 服务。"
                ),
                finish_reason="stop"
            )
        ]
    )


@router.get("/")
async def openai_root():
    """OpenAI API 根端点"""
    return {
        "message": "OpenAI Compatible API",
        "version": "v1",
        "endpoints": ["/v1/models", "/v1/chat/completions"]
    }
