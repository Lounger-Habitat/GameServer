"""Anthropic 兼容 API 服务层

处理 Anthropic 格式到 MengLong SDK 格式的转换，直接调用 MengLong SDK。
"""

import uuid
import json
import logging
import asyncio
from typing import List, Optional, Union, Dict, Any, AsyncIterator
from datetime import datetime

logger = logging.getLogger("anthropic_service")


# --- 专用调试日志配置 ---
def _setup_debug_logger():
    import os
    from logging.handlers import RotatingFileHandler

    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    debug_log = logging.getLogger("anthropic_debug")
    debug_log.setLevel(logging.DEBUG)

    # 避免重复添加 Handler
    if not debug_log.handlers:
        path = os.path.join(log_dir, "anthropic_api.log")
        handler = RotatingFileHandler(
            path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        debug_log.addHandler(handler)
    return debug_log


debug_log = _setup_debug_logger()
# -----------------------

# 直接导入 MengLong SDK
from menglong import Model
from menglong.schemas.chat import (
    Message as MengLongMessage,
    Response as MengLongResponse,
    StreamResponse as MengLongStreamResponse,
    Usage as MengLongUsage,
    Output,
    Delta,
    Action as MengLongAction,
    User,
    Assistant,
    System,
)

from .models import (
    AnthropicMessage,
    AnthropicChatRequest,
    AnthropicChatResponse,
    AnthropicStreamResponse,
    ContentBlock,
    TextContent,
    ThinkingContent,
    Usage,
    AnthropicModelInfo,
)


def convert_anthropic_to_menglong_messages(
    anthropic_messages: List[AnthropicMessage], system_prompt: Optional[str] = None
) -> List[MengLongMessage]:
    """将 Anthropic 格式的消息转换为 MengLong SDK 格式

    Args:
        anthropic_messages: Anthropic 格式的消息列表
        system_prompt: 可选的系统提示

    Returns:
        MengLong SDK 格式的消息列表
    """
    menglong_messages = []

    # 如果有系统提示，添加到消息列表开头
    if system_prompt:
        # system_prompt 可以是字符串或列表，这里为了简单统一处理
        system_content = (
            system_prompt if isinstance(system_prompt, str) else str(system_prompt)
        )
        menglong_messages.append(System(content=system_content))

    # 转换 Anthropic 消息
    for msg in anthropic_messages:
        role = msg.role

        # 即使端点放宽了限制，我们依然要把灵活的字典正确映射到 MengLong 的标准模型
        if role == "user":
            if isinstance(msg.content, str):
                menglong_messages.append(User(content=msg.content))
            else:
                content_parts = []
                for block in msg.content:
                    b = (
                        block
                        if isinstance(block, dict)
                        else dict(block)
                        if hasattr(block, "keys")
                        else getattr(block, "__dict__", {})
                    )
                    b_type = b.get("type", "")

                    if b_type == "text":
                        content_parts.append(
                            {"type": "text", "text": b.get("text", "")}
                        )
                    elif b_type == "image":
                        source = b.get("source", {})
                        if source.get("type") == "base64":
                            content_parts.append(
                                {
                                    "type": "image",
                                    "data": source.get("data"),
                                    "media_type": source.get("media_type"),
                                }
                            )
                    elif b_type == "document":
                        source = b.get("source", {})
                        if source.get("type") == "base64":
                            content_parts.append(
                                {
                                    "type": "document",
                                    "data": source.get("data"),
                                    "media_type": source.get("media_type")
                                    or "application/pdf",
                                }
                            )
                    elif b_type == "tool_result":
                        # 如果前面有累积的各类型内容，先发一条 User 消息
                        if content_parts:
                            menglong_messages.append(User(content=content_parts))
                            content_parts = []

                        # 工具响应转换为 Menglong 中 role=tool 的消息
                        tool_id = b.get("tool_use_id", "")
                        content = b.get("content", "")
                        if isinstance(content, list):
                            content = "\n".join(
                                str(c.get("text", ""))
                                for c in content
                                if isinstance(c, dict) and c.get("type") == "text"
                            )

                        from menglong.schemas.chat import Message as MLMessage

                        menglong_messages.append(
                            MLMessage(
                                role="tool",
                                tool_id=tool_id,
                                content=[
                                    {
                                        "type": "outcome",
                                        "id": tool_id,
                                        "result": str(content),
                                    }
                                ],
                            )
                        )

                # 发送剩余的内容
                if content_parts:
                    menglong_messages.append(User(content=content_parts))

        elif role == "assistant":
            if isinstance(msg.content, str):
                menglong_messages.append(Assistant(content=msg.content))
            else:
                text_parts = []
                tool_calls = []
                thinking_text = None
                for block in msg.content:
                    b = (
                        block
                        if isinstance(block, dict)
                        else dict(block)
                        if hasattr(block, "keys")
                        else getattr(block, "__dict__", {})
                    )
                    b_type = b.get("type", "")

                    if b_type == "text":
                        text_parts.append(b.get("text", ""))
                    elif b_type == "thinking":
                        thinking_text = b.get("thinking", "")
                    elif b_type == "tool_use":
                        # 必须传 Action 对象而非 dict，否则 Assistant() 内部的 action.id 会报 AttributeError
                        tool_calls.append(
                            MengLongAction(
                                id=b.get("id", ""),
                                name=b.get("name", ""),
                                arguments=b.get("input", {}) or {},
                            )
                        )

                content_str = "\n".join(text_parts) if text_parts else None
                menglong_messages.append(
                    Assistant(
                        content=content_str, actions=tool_calls, reasoning=thinking_text
                    )
                )
        else:
            # 兜底处理
            menglong_messages.append(
                MengLongMessage(role=role, content=str(msg.content))
            )

    if logger.isEnabledFor(logging.DEBUG):
        debug_msgs = [
            {
                "role": m.role,
                "content": str(m.content)[:200] + "..."
                if len(str(m.content)) > 200
                else m.content,
            }
            for m in menglong_messages
        ]
        logger.debug(
            f"[Anthropic API] Converted to MengLong Format: {json.dumps(debug_msgs, ensure_ascii=False, indent=2)}"
        )

    return menglong_messages


def convert_menglong_to_anthropic_response(
    menglong_response: MengLongResponse, model: str, request_id: Optional[str] = None
) -> AnthropicChatResponse:
    """将 MengLong SDK 响应转换为 Anthropic 格式

    Args:
        menglong_response: MengLong SDK 响应对象
        model: 使用的模型名称
        request_id: 可选的请求 ID

    Returns:
        Anthropic 格式的响应
    """
    # 生成消息 ID
    message_id = request_id or f"msg_{uuid.uuid4().hex[:16]}"

    # 提取响应内容
    content_text = ""
    reasoning_text = ""  # 思维/推理过程

    if hasattr(menglong_response, "output") and menglong_response.output:
        # 检查output对象是否有content属性
        if hasattr(menglong_response.output, "content"):
            # content可能是一个Content对象
            content_obj = menglong_response.output.content
            if hasattr(content_obj, "text"):
                content_text = content_obj.text or ""
            else:
                content_text = str(content_obj)
            # 提取 reasoning（思维过程），DeepSeek-thinking 等模型会填充此字段
            if hasattr(content_obj, "reasoning") and content_obj.reasoning:
                reasoning_text = content_obj.reasoning
        else:
            content_text = str(menglong_response.output)

    # 创建 Anthropic 格式的内容块
    # 按照 Anthropic 规范：thinking 块先于 text 块
    content_blocks = []
    if reasoning_text:
        content_blocks.append({"type": "thinking", "thinking": reasoning_text})
    if content_text:
        content_blocks.append({"type": "text", "text": content_text})

    # 提取生成的 tool_calls / actions
    if hasattr(menglong_response, "output") and menglong_response.output:
        actions = getattr(menglong_response.output, "actions", None)
        if actions:
            for act in actions:
                # attr or dict fallback
                act_dict = (
                    act
                    if isinstance(act, dict)
                    else vars(act)
                    if hasattr(act, "__dict__")
                    else {}
                )
                act_id = (
                    act_dict.get("id")
                    or getattr(act, "id", None)
                    or f"call_{uuid.uuid4().hex[:8]}"
                )
                act_name = act_dict.get("name") or getattr(act, "name", "")
                act_args = act_dict.get("arguments") or getattr(act, "arguments", {})

                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": act_id,
                        "name": act_name,
                        "input": act_args,
                    }
                )

    if not content_blocks:
        content_blocks.append(
            {
                "type": "text",
                "text": "Hello! I'm an AI assistant powered by MengLong SDK.",
            }
        )

    # 提取使用统计
    if hasattr(menglong_response, "usage"):
        input_tokens = menglong_response.usage.input_tokens
        output_tokens = menglong_response.usage.output_tokens
        cache_tokens = menglong_response.usage.cache_tokens

    usage = Usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_input_tokens=cache_tokens,
        cache_creation_input_tokens=0,
    )

    # 确定停止原因
    # MengLong SDK 将 OpenAI 的 finish_reason 存在 output.status 里
    raw_status = None
    if hasattr(menglong_response, "output") and menglong_response.output:
        raw_status = getattr(menglong_response.output, "status", None)

    if raw_status == "tool_calls":
        stop_reason = "tool_use"
    elif raw_status == "length":
        stop_reason = "max_tokens"
    elif raw_status in ("stop", "end_turn", None):
        # 兜底：如果响应里有 tool_use block，无论 status 如何都应为 tool_use
        has_tool_use = any(
            (b.get("type") if isinstance(b, dict) else getattr(b, "type", ""))
            == "tool_use"
            for b in content_blocks
        )
        stop_reason = "tool_use" if has_tool_use else "end_turn"
    else:
        # 直接映射其他未知状态
        stop_reason = "end_turn"

    return AnthropicChatResponse(
        id=message_id,
        type="message",
        role="assistant",
        content=content_blocks,
        model=model,
        stop_reason=stop_reason,
        stop_sequence=None,  # 目前不支持停止序列
        usage=usage,
    )


async def anthropic_chat(request: AnthropicChatRequest) -> AnthropicChatResponse:
    """处理 Anthropic 格式的聊天请求

    Args:
        request: Anthropic 格式的请求

    Returns:
        Anthropic 格式的响应

    Raises:
        ValueError: 模型不支持或请求参数无效
    """
    try:
        # 直接使用 MengLong SDK
        model = Model()

        # 转换消息格式
        menglong_messages = convert_anthropic_to_menglong_messages(
            request.messages, request.system
        )

        # 准备调用参数
        kwargs = {
            "model": request.model,
            "messages": menglong_messages,
            "temperature": request.temperature or 0.7,
        }

        if request.max_tokens is not None:
            # 动态获取模型信息的真实最大 Token 上限
            model_info = get_anthropic_model(request.model)
            max_model_tokens = (
                model_info.max_tokens if model_info and model_info.max_tokens else 8192
            )
            kwargs["max_tokens"] = min(request.max_tokens, max_model_tokens)

        if request.stop_sequences:
            kwargs["stop"] = request.stop_sequences

        if request.tools:
            # 将 Anthropic 格式 ({"name": "x", "input_schema": ...}) 转换为标准格式 ({"type": "function", "function": {"name": "x", "parameters": ...}})
            ml_tools = []
            for t in request.tools:
                if "type" in t and "function" in t:
                    ml_tools.append(t)
                else:
                    ml_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": t.get("name", ""),
                                "description": t.get("description", ""),
                                "parameters": t.get(
                                    "input_schema", {"type": "object", "properties": {}}
                                ),
                            },
                        }
                    )
            kwargs["tools"] = ml_tools

            # 处理 tool_choice 映射
            if request.tool_choice:
                tc = request.tool_choice
                if isinstance(tc, dict):
                    tc_type = tc.get("type", "auto")
                    if tc_type == "tool":
                        kwargs["tool_choice"] = {
                            "type": "tool",
                            "name": tc.get("name", ""),
                        }
                    else:
                        # 如 "auto", "any"
                        kwargs["tool_choice"] = {"type": tc_type}
                elif isinstance(tc, str):
                    # 字符串处理: "auto", "any" (即 required)
                    kwargs["tool_choice"] = {"type": tc}
                else:
                    kwargs["tool_choice"] = tc
            else:
                kwargs["tool_choice"] = {"type": "auto"}

        logger.debug(
            f"[Anthropic API] Invoking Model.chat with kwargs: {json.dumps({k: str(v) if k == 'messages' else v for k, v in kwargs.items()}, ensure_ascii=False, indent=2)}"
        )

        # 调用 MengLong SDK 的异步方法
        request_id = getattr(request, "id", None) or f"req_{uuid.uuid4().hex[:12]}"
        debug_log.info(f"[{request_id}] === NEW REQUEST === Model: {request.model}")
        debug_log.debug(
            f"[{request_id}] INPUT (Anthropic): {request.model_dump_json(ensure_ascii=False, indent=2)}"
        )
        debug_log.debug(
            f"[{request_id}] INTERMEDIATE (MengLong Kwargs): {json.dumps({k: str(v) if k == 'messages' else v for k, v in kwargs.items()}, ensure_ascii=False, indent=2)}"
        )

        menglong_response = await model.async_chat(**kwargs)

        if menglong_response is None:
            debug_log.error(f"[{request_id}] SDK returned None")
            raise ValueError("SDK 返回了空响应 (None)")

        logger.debug("[Anthropic API] Model response received")

        # 转换响应格式
        response = convert_menglong_to_anthropic_response(
            menglong_response,
            request.model,
        )

        debug_log.info(
            f"[{request_id}] SUCCESS: {response.model_dump_json(ensure_ascii=False, indent=2)}"
        )
        return response

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        # 即使在 try 外层定义的 request_id 也可以在这里用（如果是赋值后报错）
        rid = locals().get("request_id", "unknown")
        debug_log.error(f"[{rid}] FAILED: {str(e)}\n{error_details}")
        raise ValueError(f"LLM 调用失败: {e}\n{error_details}")


async def anthropic_stream_chat(request: AnthropicChatRequest) -> AsyncIterator[str]:
    """处理 Anthropic 格式的流式聊天请求

    Args:
        request: Anthropic 格式的请求

    Yields:
        Anthropic 格式的流式响应块（JSON 字符串）

    Raises:
        ValueError: 模型不支持或请求参数无效
    """
    try:
        model = Model()

        menglong_messages = convert_anthropic_to_menglong_messages(
            request.messages, request.system
        )

        request_id = f"msg_{uuid.uuid4().hex[:16]}"

        # 估算输入 token 数
        def _estimate_msg_length(msg):
            if isinstance(msg.content, str):
                return len(msg.content)
            elif isinstance(msg.content, list):
                return sum(
                    len(str(c.get("text", "")))
                    if isinstance(c, dict)
                    else len(getattr(c, "text", ""))
                    for c in msg.content
                )
            return len(str(msg.content))

        input_tokens = sum(_estimate_msg_length(msg) for msg in request.messages) // 4

        # 组装 SDK 调用参数
        kwargs: dict = {
            "model": request.model,
            "messages": menglong_messages,
            "temperature": request.temperature or 0.7,
        }

        if request.max_tokens is not None:
            model_info = get_anthropic_model(request.model)
            max_model_tokens = (
                model_info.max_tokens if model_info and model_info.max_tokens else 64000
            )
            kwargs["max_tokens"] = min(request.max_tokens, max_model_tokens)

        if request.stop_sequences:
            kwargs["stop"] = request.stop_sequences

        has_tools = bool(request.tools)
        if has_tools:
            ml_tools = []
            for t in request.tools:
                if "type" in t and "function" in t:
                    ml_tools.append(t)
                else:
                    ml_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": t.get("name", ""),
                                "description": t.get("description", ""),
                                "parameters": t.get(
                                    "input_schema", {"type": "object", "properties": {}}
                                ),
                            },
                        }
                    )
            kwargs["tools"] = ml_tools

            if request.tool_choice:
                tc = request.tool_choice
                if isinstance(tc, dict):
                    tc_type = tc.get("type", "auto")
                    if tc_type == "tool":
                        kwargs["tool_choice"] = {
                            "type": "tool",
                            "name": tc.get("name", ""),
                        }
                    else:
                        kwargs["tool_choice"] = {"type": tc_type}
                elif isinstance(tc, str):
                    kwargs["tool_choice"] = {"type": tc}
                else:
                    kwargs["tool_choice"] = tc
            else:
                kwargs["tool_choice"] = {"type": "auto"}

        debug_log.info(
            f"[{request_id}] === NEW STREAM REQUEST === Model: {request.model}"
        )
        debug_log.debug(
            f"[{request_id}] INPUT (Anthropic): {request.model_dump_json(ensure_ascii=False, indent=2)}"
        )
        debug_log.debug(
            f"[{request_id}] INTERMEDIATE (MengLong Kwargs): {json.dumps({k: str(v) if k == 'messages' else v for k, v in kwargs.items()}, ensure_ascii=False, indent=2)}"
        )

        logger.debug(
            f"[Anthropic Stream] kwargs: {json.dumps({k: str(v) if k == 'messages' else v for k, v in kwargs.items()}, ensure_ascii=False, indent=2)}"
        )

        # ── 辅助：发送各类 SSE 事件 ─────────────────────────────────────────

        def _make_message_start(in_tokens: int) -> str:
            return AnthropicStreamResponse(
                type="message_start",
                message=AnthropicChatResponse(
                    id=request_id,
                    type="message",
                    role="assistant",
                    content=[],
                    model=request.model,
                    stop_reason=None,
                    stop_sequence=None,
                    usage=Usage(input_tokens=in_tokens, output_tokens=0),
                ),
            ).model_dump_json()

        def _make_cb_start(index: int, block: dict) -> str:
            return AnthropicStreamResponse(
                type="content_block_start",
                content_block=block,
                index=index,
            ).model_dump_json()

        def _make_cb_delta(index: int, delta: dict) -> str:
            return AnthropicStreamResponse(
                type="content_block_delta",
                delta=delta,
                index=index,
            ).model_dump_json()

        def _make_cb_stop(index: int) -> str:
            return AnthropicStreamResponse(
                type="content_block_stop",
                index=index,
            ).model_dump_json()

        def _make_message_delta(
            stop_reason: str, out_tokens: int, cache_tokens: Optional[int] = 0
        ) -> str:
            return json.dumps(
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                    "usage": {
                        "output_tokens": out_tokens,
                        "cache_read_input_tokens": cache_tokens,
                        "cache_creation_input_tokens": 0,
                    },
                }
            )

        # ────────────────────────────────────────────────────────────────────
        # 分支 A：有工具 → 使用非流式内部调用，然后模拟完整的 SSE 事件序列
        #   （必须如此，因为 MengLong StreamResponse 不携带 tool_call 数据）
        #   关键：message_start 推迟到 async_chat 返回后再发，以便使用真实 Usage
        # ────────────────────────────────────────────────────────────────────
        if has_tools:
            try:
                menglong_resp = await model.async_chat(**kwargs)
            except Exception as e:
                import traceback

                # 调用失败时先发 message_start（用估算值），再发 error，保持协议完整性
                yield _make_message_start(input_tokens)
                yield AnthropicStreamResponse(
                    type="error",
                    error={
                        "type": "api_error",
                        "message": f"LLM 调用失败: {e}\n{traceback.format_exc()}",
                    },
                ).model_dump_json()
                return

            anthropic_resp = convert_menglong_to_anthropic_response(
                menglong_resp, request.model, request_id
            )

            # 从模型响应中提取真实 Usage（in + out 均以模型返回为准）
            real_in_tokens = (
                anthropic_resp.usage.input_tokens
                if anthropic_resp.usage
                else input_tokens
            )
            real_out_tokens = (
                anthropic_resp.usage.output_tokens if anthropic_resp.usage else 0
            )
            # 现在就在此处透传 cache_creation_input_tokens / cache_read_input_tokens

            cache_creation_input_tokens = (
                anthropic_resp.usage.cache_creation_input_tokens
                if anthropic_resp.usage
                else 0
            )
            cache_read_input_tokens = (
                anthropic_resp.usage.cache_read_input_tokens
                if anthropic_resp.usage
                else 0
            )

            # 现在才发 message_start，携带真实 input_tokens
            yield _make_message_start(real_in_tokens)

            # 按 Anthropic 规范，逐块发送 content_block_* 事件
            for i, block in enumerate(anthropic_resp.content):
                b = (
                    block
                    if isinstance(block, dict)
                    else (
                        block.model_dump()
                        if hasattr(block, "model_dump")
                        else vars(block)
                    )
                )
                b_type = b.get("type", "")

                if b_type == "thinking":
                    thinking = b.get("thinking", "")
                    yield _make_cb_start(i, {"type": "thinking", "thinking": ""})
                    if thinking:
                        yield _make_cb_delta(
                            i, {"type": "thinking_delta", "thinking": thinking}
                        )
                    yield _make_cb_stop(i)

                elif b_type == "text":
                    text = b.get("text", "")
                    yield _make_cb_start(i, {"type": "text", "text": ""})
                    if text:
                        yield _make_cb_delta(i, {"type": "text_delta", "text": text})
                    yield _make_cb_stop(i)

                elif b_type == "tool_use":
                    tool_id = b.get("id", f"call_{uuid.uuid4().hex[:8]}")
                    tool_name = b.get("name", "")
                    tool_input = b.get("input", {})
                    yield _make_cb_start(
                        i,
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": tool_name,
                            "input": {},
                        },
                    )
                    yield _make_cb_delta(
                        i,
                        {
                            "type": "input_json_delta",
                            "partial_json": json.dumps(tool_input, ensure_ascii=False),
                        },
                    )
                    yield _make_cb_stop(i)

            yield _make_message_delta(
                anthropic_resp.stop_reason or "end_turn", real_out_tokens
            )
            yield json.dumps({"type": "message_stop"})
            return

        # ────────────────────────────────────────────────────────────────────
        # 分支 B：无工具 → 真实流式推送（支持 thinking + text 双轨）
        # ────────────────────────────────────────────────────────────────────
        yield _make_message_start(input_tokens)

        accumulated_text = ""
        chunk_count = 0
        real_output_tokens: int | None = None

        # 思维过程状态跟踪：管理当前活跃的 content_block 的类型和索引
        block_index = -1  # 当前开放的 block 索引 (-1 = 未开启)
        in_thinking_block = False  # 是否正在流式输出 thinking 块
        in_text_block = False  # 是否正在流式输出 text 块

        try:
            async for chunk in model.async_stream_chat(**kwargs):
                chunk_count += 1

                delta_text = ""
                delta_reasoning = ""

                if hasattr(chunk, "output") and chunk.output:
                    delta = getattr(chunk.output, "delta", None)
                    if delta:
                        if hasattr(delta, "text") and delta.text:
                            delta_text = delta.text
                        if hasattr(delta, "reasoning") and delta.reasoning:
                            delta_reasoning = delta.reasoning

                # 处理 reasoning delta：需要开启 thinking block
                if delta_reasoning:
                    if not in_thinking_block:
                        # 关闭任何当前 open 的 block
                        if block_index >= 0:
                            yield _make_cb_stop(block_index)
                        block_index += 1
                        yield _make_cb_start(
                            block_index, {"type": "thinking", "thinking": ""}
                        )
                        in_thinking_block = True
                        in_text_block = False
                    yield _make_cb_delta(
                        block_index,
                        {"type": "thinking_delta", "thinking": delta_reasoning},
                    )

                # 处理 text delta：如果当前在 thinking block则需要关闭它并开启 text block
                if delta_text:
                    if not in_text_block:
                        if block_index >= 0:
                            yield _make_cb_stop(block_index)
                        block_index += 1
                        yield _make_cb_start(block_index, {"type": "text", "text": ""})
                        in_text_block = True
                        in_thinking_block = False
                    accumulated_text += delta_text
                    yield _make_cb_delta(
                        block_index, {"type": "text_delta", "text": delta_text}
                    )

                if hasattr(chunk, "usage") and chunk.usage:
                    out_val = getattr(chunk.usage, "output_tokens", None)
                    if out_val is not None and out_val > 0:
                        real_output_tokens = out_val

            if chunk_count == 0:
                fallback = "stream response failed"
                accumulated_text = fallback
                if not in_text_block:
                    block_index += 1
                    yield _make_cb_start(block_index, {"type": "text", "text": ""})
                yield _make_cb_delta(
                    block_index, {"type": "text_delta", "text": fallback}
                )

        except Exception as e:
            yield AnthropicStreamResponse(
                type="error",
                error={"type": "api_error", "message": f"流式处理失败: {e}"},
            ).model_dump_json()
            return

        # 关闭最后一个开放的 block
        if block_index >= 0:
            yield _make_cb_stop(block_index)
        # 优先使用 SDK 返回的真实値；若 SDK 不携带 usage 则退化为字符估算（//4）
        out_tokens = (
            real_output_tokens
            if real_output_tokens is not None
            else (len(accumulated_text) // 4)
        )
        yield _make_message_delta(
            "end_turn", out_tokens, cache_tokens=cache_read_input_tokens
        )
        yield json.dumps({"type": "message_stop"})

        debug_log.info(f"[{request_id}] STREAM SUCCESS. Output tokens: {out_tokens}")

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        rid = locals().get("request_id", "unknown")
        debug_log.error(f"[{rid}] STREAM FAILED: {str(e)}\n{error_details}")

        yield AnthropicStreamResponse(
            type="error",
            error={
                "type": "api_error",
                "message": f"LLM 调用失败: {e}\n{traceback.format_exc()}",
            },
        ).model_dump_json()


def list_anthropic_models() -> List[AnthropicModelInfo]:
    """列出 Anthropic 格式的模型信息

    Returns:
        Anthropic 格式的模型信息列表
    """
    try:
        # 直接使用 MengLong SDK 获取模型列表
        model = Model()

        # 尝试从模型管理器获取
        try:
            from models.manager import get_models_manager

            models_manager = get_models_manager()
            managed_models = models_manager.list_all_models(only_enabled=True)

            if managed_models:
                anthropic_models = []
                for m in managed_models:
                    anthropic_models.append(
                        AnthropicModelInfo(
                            id=m.full_id,
                            display_name=m.alias or m.model_name,
                            name=m.model_name,
                            max_tokens=m.max_tokens or 64000,
                            supports=m.supports,
                            price=m.price or {"input": 0.0, "output": 0.0},
                            provider=m.provider,
                        )
                    )
                return anthropic_models
        except ImportError:
            # 如果模型管理器不可用，继续使用其他方法
            pass

        # 尝试从 SDK 获取
        if hasattr(model, "list_models"):
            sdk_models = model.list_models()
            anthropic_models = []
            for sdk_model in sdk_models:
                anthropic_models.append(
                    AnthropicModelInfo(
                        id=getattr(sdk_model, "id", "unknown"),
                        display_name=getattr(sdk_model, "name", "Unknown Model"),
                        name=getattr(sdk_model, "name", "Unknown Model"),
                        max_tokens=getattr(sdk_model, "max_tokens", 4096),
                        supports={
                            "streaming": getattr(sdk_model, "supports_streaming", True),
                            "image": getattr(sdk_model, "supports_image", False),
                            "audio": getattr(sdk_model, "supports_audio", False),
                            "file": getattr(sdk_model, "supports_file", False),
                        },
                        price={"input": 0.0, "output": 0.0},
                    )
                )
            return anthropic_models

    except Exception as e:
        print(f"获取模型列表失败: {e}")
        # 如果获取失败，返回默认模型列表
        return get_default_anthropic_models()

    # 如果上述方法都失败，返回默认列表
    return get_default_anthropic_models()


def get_default_anthropic_models() -> List[AnthropicModelInfo]:
    """获取默认的 Anthropic 模型列表

    当无法从 LLM 提供者获取模型时使用
    """
    from datetime import datetime

    # 默认模型列表
    default_models = [
        AnthropicModelInfo(
            id="deepseek-chat",
            display_name="DeepSeek Chat",
            name="deepseek-chat",
            max_tokens=4096,
            supports={"streaming": True, "image": False, "audio": False, "file": False},
            price={"input": 0.0, "output": 0.0},
        ),
        AnthropicModelInfo(
            id="deepseek-reasoner",
            display_name="DeepSeek Reasoner",
            name="deepseek-reasoner",
            max_tokens=4096,
            supports={"streaming": True, "image": False, "audio": False, "file": False},
            price={"input": 0.0, "output": 0.0},
        ),
        AnthropicModelInfo(
            id="qwen-plus",
            display_name="Qwen Plus",
            name="qwen-plus",
            max_tokens=4096,
            supports={"streaming": True, "image": False, "audio": False, "file": False},
            price={"input": 0.0, "output": 0.0},
        ),
    ]

    return default_models


def get_anthropic_model(model_id: str) -> Optional[AnthropicModelInfo]:
    """获取指定模型的 Anthropic 格式信息

    Args:
        model_id: 模型 ID

    Returns:
        Anthropic 格式的模型信息，如果不存在则返回 None
    """
    # 从模型列表中查找
    models = list_anthropic_models()
    for model in models:
        if model.id == model_id:
            return model
    return None
