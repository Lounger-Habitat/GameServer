"""Anthropic 兼容 API 数据模型

定义 Anthropic API 格式的请求和响应模型。
"""

from typing import List, Optional, Union, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


# ============== Anthropic 消息内容类型 ==============


class TextContent(BaseModel):
    """文本内容块"""

    type: str = "text"
    text: str


class ThinkingContent(BaseModel):
    """思维/推理内容块（对应 Anthropic thinking block 格式）"""

    type: str = "thinking"
    thinking: str


class ImageContentSource(BaseModel):
    """图像内容源"""

    type: str = "base64"
    media_type: str = Field(
        ..., description="媒体类型，如 image/jpeg, image/png, image/gif, image/webp"
    )
    data: str = Field(..., description="Base64 编码的图像数据")


class ImageContent(BaseModel):
    """图像内容块"""

    type: str = "image"
    source: ImageContentSource


ContentBlock = Union[TextContent, ThinkingContent, ImageContent, Dict[str, Any]]


# ============== Anthropic 消息 ==============


class AnthropicMessage(BaseModel):
    """Anthropic 格式的消息"""

    role: str = Field(..., description="角色：user 或 assistant")
    content: Any = Field(..., description="消息内容")

    # 允许额外的字段以兼容未来的 API
    model_config = {"extra": "allow"}


# ============== 请求模型 ==============


class AnthropicChatRequest(BaseModel):
    """Anthropic 格式的聊天请求"""

    model: str = Field(..., description="模型名称")
    messages: List[AnthropicMessage] = Field(..., description="对话消息列表")
    max_tokens: Optional[int] = Field(4096, description="最大生成 token 数")
    temperature: Optional[float] = Field(1.0, description="温度参数")
    top_p: Optional[float] = Field(1.0, description="Top-p 采样参数")
    top_k: Optional[int] = Field(None, description="Top-k 采样参数")
    stream: Optional[bool] = Field(False, description="是否流式输出")
    stop_sequences: Optional[List[str]] = Field(None, description="停止序列")
    system: Any = Field(None, description="系统提示")
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="工具定义列表")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        None, description="工具选择模式"
    )

    # 允许额外的字段，例如 metadata 等
    model_config = {"extra": "allow"}


# ============== 响应模型 ==============


class Usage(BaseModel):
    """Token 使用统计"""

    input_tokens: int = Field(..., description="输入 token 数")
    output_tokens: int = Field(..., description="输出 token 数")
    cache_read_input_tokens: int = Field(0, description="缓存输入 token 数")
    cache_creation_input_tokens: int = Field(0, description="缓存创建输入 token 数")


class AnthropicChatResponse(BaseModel):
    """Anthropic 格式的聊天响应"""

    id: str = Field(..., description="消息 ID")
    type: str = Field("message", description="类型，固定为 'message'")
    role: str = Field("assistant", description="角色，固定为 'assistant'")
    content: List[ContentBlock] = Field(..., description="响应内容")
    model: str = Field(..., description="使用的模型")
    stop_reason: Optional[str] = Field(
        None, description="停止原因：end_turn, max_tokens, stop_sequence"
    )
    stop_sequence: Optional[str] = Field(None, description="触发的停止序列")
    usage: Usage = Field(..., description="Token 使用统计")


class AnthropicStreamResponse(BaseModel):
    """Anthropic 格式的流式响应块"""

    type: str = Field(
        ...,
        description="类型：message_start, content_block_start, content_block_delta, content_block_stop, message_delta, message_stop, error",
    )
    message: Optional[AnthropicChatResponse] = Field(
        None, description="完整消息（仅 message_start 时）"
    )
    content_block: Optional[Dict[str, Any]] = Field(None, description="内容块信息")
    delta: Optional[Dict[str, Any]] = Field(None, description="增量内容")
    index: Optional[int] = Field(None, description="索引")
    usage: Optional[Usage] = Field(None, description="使用统计（仅 message_delta 时）")
    error: Optional[Dict[str, Any]] = Field(
        None, description="错误信息（仅 error 事件时）"
    )


# ============== 模型信息 ==============


class AnthropicModelInfo(BaseModel):
    """Anthropic 格式的模型信息"""

    id: str = Field(..., description="模型 ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    display_name: str = Field(..., description="显示名称")
    # type: str = Field("model", description="类型，固定为 'model'")
    # 可选字段，保持向后兼容
    name: Optional[str] = Field(None, description="模型名称（兼容字段）")
    max_tokens: Optional[int] = Field(4096, description="最大 token 数")
    supports: Optional[Dict[str, bool]] = Field(
        {"streaming": True, "image": False, "audio": False, "file": False},
        description="能力支持",
    )
    price: Optional[Dict[str, float]] = Field(
        {"input": 0.0, "output": 0.0}, description="模型价格"
    )
