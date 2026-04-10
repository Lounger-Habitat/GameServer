"""Anthropic 兼容 API 路由

提供与 Anthropic API 兼容的接口端点。
"""

import json
import logging
from typing import List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger("anthropic_api")
# 设置为 DEBUG 级别即可在终端看到调试信息。依赖于外部日志配置，如果没看到可以强制配置：
# logging.basicConfig(level=logging.DEBUG)

from .models import (
    AnthropicChatRequest,
    AnthropicChatResponse,
    AnthropicModelInfo,
)
from .service import (
    anthropic_chat,
    anthropic_stream_chat,
    list_anthropic_models,
    get_anthropic_model,
)

router = APIRouter()


@router.get("/")
async def anthropic_root():
    """Anthropic 兼容 API 根端点"""
    return {
        "message": "Anthropic Compatible API",
        "version": "1.0",
        "endpoints": [
            "POST /anthropic/messages - 对话补全（Anthropic 格式）",
            "GET /anthropic/models - 列出支持的模型（Anthropic 格式）",
            "GET /anthropic/models/{model_id} - 获取模型信息（Anthropic 格式）",
        ],
    }


@router.get("/models")
async def list_models():
    """列出所有支持的模型（Anthropic 格式）

    返回格式需要匹配 Anthropic SDK 的期望：
    {
        "data": [ModelInfo, ...],
        "object": "list"
    }
    """
    models = list_anthropic_models()
    return {"data": [model.model_dump() for model in models], "object": "list"}


@router.get("/models/{model_id}", response_model=AnthropicModelInfo)
async def get_model(model_id: str):
    """获取指定模型的详细信息（Anthropic 格式）

    - **model_id**: 模型 ID
    """
    model_info = get_anthropic_model(model_id)
    if not model_info:
        raise HTTPException(
            status_code=404,
            detail=f"模型 '{model_id}' 不存在，使用 GET /anthropic/models 查看支持的模型",
        )
    return model_info


@router.post("/messages", response_model=AnthropicChatResponse)
async def chat(request: AnthropicChatRequest):
    """对话补全接口（Anthropic 格式）"""
    logger.info(f"[Anthropic API] ---------- New Request: {request.model} ----------")
    try:
        # Debug incoming request
        logger.debug(
            f"[Anthropic API] Request Payload: {request.model_dump_json(indent=2)}"
        )

        if request.stream:
            logger.info("[Anthropic API] Stream Mode Enabled")

            # 流式响应
            async def stream_generator():
                try:
                    chunk_idx = 0
                    async for chunk in anthropic_stream_chat(request):
                        # 解析chunk获取事件类型
                        try:
                            import json

                            event_data = json.loads(chunk)
                            event_type = event_data.get("type", "unknown")
                            if chunk_idx == 0:
                                logger.debug(
                                    f"[Anthropic API] Stream First Chunk: {chunk}"
                                )
                            chunk_idx += 1
                            # Anthropic SSE格式: event: <type>\ndata: <json>\n\n
                            yield f"event: {event_type}\ndata: {chunk}\n\n"
                        except:
                            # 如果无法解析，使用默认格式
                            yield f"data: {chunk}\n\n"
                    logger.info(
                        f"[Anthropic API] ---------- Stream Completed (chunks: {chunk_idx}) ----------"
                    )
                except Exception as e:
                    import traceback

                    tb = traceback.format_exc()
                    logger.error(f"[Anthropic API] Stream Error: {str(e)}\n{tb}")
                    error_response = {
                        "type": "error",
                        "error": {"type": "api_error", "message": str(e)},
                    }
                    yield f"event: error\ndata: {json.dumps(error_response)}\n\n"

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        # 普通响应
        response = await anthropic_chat(request)
        logger.debug(
            f"[Anthropic API] Normal Response: {response.model_dump_json(indent=2)}"
        )
        logger.info("[Anthropic API] ---------- Request Completed ----------")
        return response

    except ValueError as e:
        logger.warning(f"[Anthropic API] Request Validation Warning: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        logger.error(f"[Anthropic API] Internal Error: {str(e)}\n{tb}")
        raise HTTPException(status_code=500, detail=f"LLM 调用失败: {str(e)}")


# ============== 兼容性端点 ==============


@router.post("/v1/messages")
async def chat_v1(request: AnthropicChatRequest):
    """兼容 Anthropic v1 API 的端点

    与 /anthropic/messages 相同，但路径为 /anthropic/v1/messages
    """
    return await chat(request)


@router.get("/v1/models")
async def list_models_v1():
    """兼容 Anthropic v1 API 的模型列表端点"""
    return await list_models()
