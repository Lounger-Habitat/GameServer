"""MengLong API 路由

提供 LLM 对话、模型列表等接口
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# 直接使用 MengLong SDK 的类型
from menglong.schemas.chat import Message, Response, StreamResponse

from .models import ModelInfo
from .config import get_model_info, list_all_models
from .service import get_service

router = APIRouter()


# ============== 请求模型 ==============

class ChatRequest(BaseModel):
    """Chat 请求（使用 MengLong SDK 的 Message 类型）"""
    model: str = Field(..., description="模型名称")
    messages: List[Message] = Field(..., description="对话消息列表")
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, description="最大生成 token 数")
    stream: Optional[bool] = Field(False, description="是否流式输出")


# ============== API 端点 ==============

@router.get("/")
async def menglong_root():
    """MengLong API 根端点"""
    return {
        "message": "MengLong API",
        "version": "1.0",
        "endpoints": [
            "POST /menglong/chat - 对话补全",
            "GET /menglong/models - 列出支持的模型",
            "GET /menglong/models/{model_id} - 获取模型信息",
        ]
    }


@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """列出所有支持的模型"""
    return list_all_models()


@router.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    """获取指定模型的详细信息
    
    - **model_id**: 模型 ID
    """
    model_info = get_model_info(model_id)
    if not model_info:
        raise HTTPException(
            status_code=404,
            detail=f"模型 '{model_id}' 不存在，使用 GET /menglong/models 查看支持的模型"
        )
    return model_info


@router.post("/chat", response_model=Response)
async def chat(request: ChatRequest):
    """对话补全接口
    
    向 LLM 发送对话消息并获取回复。返回 MengLong SDK 的 Response 格式。
    
    - **model**: 使用的模型 ID
    - **messages**: 对话历史消息列表（MengLong SDK Message 类型）
    - **temperature**: 生成温度 (0-2)
    - **max_tokens**: 最大生成 token 数
    - **stream**: 是否流式输出（返回 StreamResponse）
    """
    try:
        service = get_service()
        
        # 流式响应
        if request.stream:
            async def stream_generator():
                async for chunk in service.stream_chat(
            # def stream_generator():
            #     for chunk in service.stream_chat(
                    model=request.model,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                ):
                    # 直接返回 StreamResponse 的 JSON
                    yield chunk.model_dump_json() + "\n"
            
            return StreamingResponse(
                stream_generator(),
                media_type="application/x-ndjson",
            )
        
        # 普通响应：直接返回 MengLong Response
        return await service.chat(
            model=request.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM 调用失败: {str(e)}"
        )