"""MengLong API 路由

提供 LLM 对话、模型列表等接口
"""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from datetime import datetime

# 直接使用 MengLong SDK 的类型
from menglong.schemas.chat import (
    Message,
    Response,
    StreamResponse,
    TextPart,
    ImagePart,
    DocumentPart,
    AudioPart,
    VideoPart,
    Action,
    Outcome,
)

from .models import MengLongModelInfo
from .config import get_model_info, list_all_models
from .service import get_service

router = APIRouter()


# ============== 请求模型 ==============


class ChatRequest(BaseModel):
    """Chat 请求（完整支持 SDK 多模态消息类型）"""

    model: str = Field(..., description="模型名称")
    messages: List[Dict[str, Any]] = Field(
        ..., description="对话消息列表 (支持多模态 ContentPart 结构)"
    )
    temperature: Optional[float] = Field(0.7, ge=0, le=2, description="温度参数")
    max_tokens: Optional[int] = Field(None, ge=1, description="最大生成 token 数")
    stream: Optional[bool] = Field(False, description="是否流式输出")
    tools: Optional[list] = Field(None, description="工具定义列表")
    tool_choice: Optional[str] = Field("auto", description="工具选择模式")


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
        ],
    }


@router.get("/models", response_model=List[MengLongModelInfo])
async def list_models():
    """列出所有支持的模型"""
    return list_all_models()


@router.get("/models/{model_id}", response_model=MengLongModelInfo)
async def get_model(model_id: str):
    """获取指定模型的详细信息

    - **model_id**: 模型 ID
    """
    model_info = get_model_info(model_id)
    if not model_info:
        raise HTTPException(
            status_code=404,
            detail=f"模型 '{model_id}' 不存在，使用 GET /menglong/models 查看支持的模型",
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

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 收到 MengLong Chat 请求: model={request.model}"
    )
    try:
        service = get_service()

        if request.stream:

            async def stream_generator():
                try:
                    async for chunk in service.stream_chat(
                        model=request.model,
                        messages=request.messages,
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        tools=request.tools,
                        tool_choice=request.tool_choice,
                    ):
                        # 强制确保返回的模型 ID 与请求的一致，避免上游 SDK/Provider 返回 base 名称导致客户端混淆
                        chunk.model = request.model
                        # 如果是最后一块，带上统计信息
                        yield f"data: {chunk.model_dump_json(exclude_none=True)}\n\n"
                except Exception as e:
                    import json

                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

                yield "data: [DONE]\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
            )

        # 普通响应：直接返回 MengLong Response
        response = await service.chat(
            model=request.model,
            messages=request.messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=request.tools,
            tool_choice=request.tool_choice,
        )
        # 强制确保返回的模型 ID 与请求的一致
        response.model = request.model
        return response

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        print(tb)
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")


# 注意：模型管理路由已移至顶级 /models 路径
# 原 /menglong/models 端点保持不变（只读模型列表）
