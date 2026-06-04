"""
统计中间件 - 自动记录 API 调用
改进流式响应的Token计数，按照 Anthropic 官方 SSE 事件规范提取 Usage
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Callable, Dict, Any, Optional
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse, JSONResponse

from api.auth.storage import get_key_store
from .models import ApiCallLog, APIMethod, Currency
from .pricing import calculate_cost
from .model_normalizer import normalize_model_name
from .storage import get_stats_store
from utils.config import settings


class StatisticsMiddleware(BaseHTTPMiddleware):
    """统计中间件 - 记录每个 API 请求的统计信息

    流式响应按照 Anthropic SSE 规范提取 Usage：
    - message_start  → input_tokens（含 cache tokens，TODO）
    - message_delta  → output_tokens（累积最终值）
    非流式 JSON 响应直接从 body 提取 usage 字段。
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # 跳过不需要统计的路径
        if self._should_skip(request.url.path):
            return await call_next(request)

        start_time = time.time()
        api_key_name = self._extract_api_key_name(request) or "anonymous"
        request_id = str(uuid.uuid4())

        log = ApiCallLog(
            timestamp=datetime.now(timezone.utc),
            api_key_name=api_key_name,
            endpoint=request.url.path,
            method=APIMethod(request.method),
            request_id=request_id,
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        try:
            response = await call_next(request)

            latency_ms = int((time.time() - start_time) * 1000)
            log.latency_ms = latency_ms
            log.status_code = response.status_code

            response = await self._wrap_response_for_statistics(response, log)
            return response

        except Exception as e:
            log.status_code = 500
            log.error_message = str(e)
            log.latency_ms = int((time.time() - start_time) * 1000)
            self._log_sync(log)
            raise

    def _should_skip(self, path: str) -> bool:
        """判断是否跳过统计"""
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico",
        ]
        if path.startswith("/statistics/") and not path.startswith(
            "/statistics/dashboard"
        ):
            if path in ["/statistics/", "/statistics"]:
                return True
        return any(path.startswith(p) for p in skip_paths)

    def _extract_api_key_name(self, request: Request) -> str | None:
        """从请求中提取 API Key 名称"""
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")

        key_value = None
        if auth_header.startswith("Bearer "):
            key_value = auth_header[7:]
        elif api_key_header:
            key_value = api_key_header

        if not key_value:
            return None

        key_store = get_key_store()
        api_key = key_store.get_key_by_value(key_value)
        return api_key.name if api_key else None

    async def _wrap_response_for_statistics(
        self, response: Response, log: ApiCallLog
    ) -> Response:
        """包装响应以提取统计信息"""
        content_type = response.headers.get("content-type", "").lower()

        if "text/event-stream" in content_type or isinstance(
            response, StreamingResponse
        ):
            return await self._wrap_streaming_response(response, log)

        # 非流式响应：读取整个 body 后提取统计
        original_body = b""
        async for chunk in response.body_iterator:
            original_body += chunk

        if original_body and response.status_code == 200:
            try:
                if "application/json" in response.headers.get("content-type", ""):
                    data = json.loads(original_body.decode("utf-8"))
                    self._extract_model_and_tokens(data, log)
            except (json.JSONDecodeError, UnicodeDecodeError, Exception):
                pass

        new_response = Response(
            content=original_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
        self._log_sync(log)
        return new_response

    async def _wrap_streaming_response(
        self, response: StreamingResponse, log: ApiCallLog
    ) -> StreamingResponse:
        """包装流式响应以提取统计信息

        按照 Anthropic SSE 规范，Usage 分布于两个事件：
          - message_start.message.usage  → input_tokens（以此为最终输入值）
          - message_delta.usage          → output_tokens（累积值，以此为最终输出值）
        两者均应被记录，message_delta 的字段优先级更高（覆盖 message_start 中的同名字段）。
        """
        original_iterator = response.body_iterator

        model_name: Optional[str] = None

        # 分事件类型跟踪 Usage（按 Anthropic 规范）
        input_tokens: int = 0
        output_tokens: int = 0
        cache_tokens: int = 0

        async def wrapped_generator():
            nonlocal model_name, input_tokens, output_tokens, cache_tokens
            buffer = b""

            async for chunk in original_iterator:
                buffer += chunk

                # 解析 SSE 事件块（以 \n\n 分隔）
                while b"\n\n" in buffer:
                    event_block, buffer = buffer.split(b"\n\n", 1)
                    if not event_block:
                        continue

                    # 解析 SSE 格式：event: <type>\ndata: <json>
                    event_type: Optional[str] = None
                    event_data: Optional[dict] = None

                    for line in event_block.decode("utf-8", errors="replace").split(
                        "\n"
                    ):
                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        elif line.startswith("data: "):
                            try:
                                event_data = json.loads(line[6:])
                            except json.JSONDecodeError:
                                pass

                    if not event_data:
                        continue

                    # ── 提取模型名称 ──────────────────────────────────────────
                    if not model_name:
                        # 直接字段
                        model_name = event_data.get("model")
                        # message_start 包含 message 对象
                        if not model_name and "message" in event_data:
                            model_name = event_data["message"].get("model")

                    # ── 按 Anthropic SSE 规范提取 Usage ──────────────────────
                    #
                    # message_start: message.usage 包含 input_tokens（及初始 output_tokens）
                    # message_delta: usage 包含最终累积的 output_tokens（及可选的 input_tokens）
                    #
                    # 规则：message_delta 的字段优先级更高（是累积最终值），
                    # 若 message_delta 的某字段为 0 或不存在，则保留 message_start 的值。
                    if (
                        event_type == "message_start"
                        or event_data.get("type") == "message_start"
                    ):
                        msg_usage = event_data.get("message", {}).get("usage", {})
                        if msg_usage:
                            # 以 message_start 的值作为初始值
                            input_tokens = msg_usage.get("input_tokens", input_tokens)
                            # message_start 中的 output_tokens 是初始 prefill 数，
                            # 会被 message_delta 的累积值覆盖，暂先记录
                            output_tokens = msg_usage.get(
                                "output_tokens", output_tokens
                            )
                            cache_tokens = msg_usage.get(
                                "cache_input_tokens", cache_tokens
                            )

                    elif (
                        event_type == "message_delta"
                        or event_data.get("type") == "message_delta"
                    ):
                        delta_usage = event_data.get("usage", {})
                        if delta_usage:
                            # output_tokens 是累积最终值，直接覆盖
                            final_out = delta_usage.get("output_tokens", 0)
                            if final_out > 0:
                                output_tokens = final_out
                            # input_tokens 在 message_delta 中是可选的累积值
                            # （web_search 等场景会携带），若存在则以此为准
                            final_in = delta_usage.get("input_tokens", 0)
                            if final_in > 0:
                                input_tokens = final_in
                            final_cache = delta_usage.get("cache_input_tokens", 0)
                            if final_cache > 0:
                                cache_tokens = final_cache

                    # OpenAI 兼容格式兜底（直接包含 usage 字段的响应）
                    elif "usage" in event_data and isinstance(
                        event_data["usage"], dict
                    ):
                        usage = event_data["usage"]
                        in_val = usage.get(
                            "input_tokens", usage.get("prompt_tokens", 0)
                        )
                        out_val = usage.get(
                            "output_tokens", usage.get("completion_tokens", 0)
                        )
                        details_val = usage.get("prompt_tokens_details", {})
                        cache_val = details_val.get("cached_tokens", 0)
                        if in_val > 0:
                            input_tokens = in_val
                        if out_val > 0:
                            output_tokens = out_val
                        if cache_val > 0:
                            cache_tokens = cache_val

                yield chunk

            # ── 流结束后组装统计日志 ──────────────────────────────────────────
            if model_name:
                model_full_id, model_provider, model_alias = normalize_model_name(
                    model_name
                )
                log.model_full_id = model_full_id
                log.model_provider = model_provider
                log.model_alias = model_alias

            log.input_tokens = input_tokens
            log.output_tokens = output_tokens
            log.cache_input_tokens = cache_tokens
            log.total_tokens = input_tokens + output_tokens
            log.is_stream = True

            if log.model_full_id and (
                log.input_tokens > 0
                or log.output_tokens > 0
                or log.cache_input_tokens > 0
            ):
                try:
                    cost, inp_price, out_price, cache_price = calculate_cost(
                        log.model_full_id,
                        log.input_tokens,
                        log.output_tokens,
                        log.cache_input_tokens,
                        log.timestamp,
                    )
                    log.cost = cost
                    log.input_price_per_million = inp_price
                    log.output_price_per_million = out_price
                    log.cache_input_price_per_million = cache_price
                except Exception:
                    pass

            self._log_sync(log)

        return StreamingResponse(
            wrapped_generator(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    def _extract_model_and_tokens(self, data: Dict[str, Any], log: ApiCallLog):
        """从非流式 JSON 响应中提取模型和 Token 信息"""
        if not isinstance(data, dict):
            return

        # 提取模型名称
        model_name = data.get("model")
        if not model_name and data.get("choices"):
            model_name = data["choices"][0].get("model") if data["choices"] else None
        if not model_name and isinstance(data.get("data"), dict):
            model_name = data["data"].get("model")

        if model_name:
            model_full_id, model_provider, model_alias = normalize_model_name(
                model_name
            )
            log.model_full_id = model_full_id
            log.model_provider = model_provider
            log.model_alias = model_alias

        # 提取 Token 信息（兼容 Anthropic / OpenAI / MengLong 格式）
        usage = (
            data.get("usage")
            or (isinstance(data.get("data"), dict) and data["data"].get("usage"))
            or {}
        )
        if isinstance(usage, dict):
            log.input_tokens = usage.get("input_tokens", usage.get("prompt_tokens", 0))
            log.output_tokens = usage.get(
                "output_tokens", usage.get("completion_tokens", 0)
            )
            log.cache_input_tokens = usage.get("cache_input_tokens", 0)
            explicit_total = usage.get("total_tokens")
            if explicit_total is not None and log.cache_input_tokens == 0:
                log.total_tokens = explicit_total
            else:
                log.total_tokens = log.input_tokens + log.output_tokens

        # 计算费用

        # 计算费用
        if log.model_full_id and (
            log.input_tokens > 0 or log.output_tokens > 0 or log.cache_input_tokens > 0
        ):
            try:
                cost, inp_price, out_price, cache_price = calculate_cost(
                    log.model_full_id,
                    log.input_tokens,
                    log.output_tokens,
                    log.cache_input_tokens,
                    log.timestamp,
                )
                log.cost = cost
                log.input_price_per_million = inp_price
                log.output_price_per_million = out_price
                log.cache_input_price_per_million = cache_price
            except Exception:
                pass

    def _log_sync(self, log: ApiCallLog):
        """同步记录日志"""
        try:
            stats_store = get_stats_store()
            stats_store.log_api_call(log)
        except Exception:
            # 记录失败不影响主流程
            pass
        finally:
            self._print_terminal_stats(log)

    def _print_terminal_stats(self, log: ApiCallLog):
        """在终端输出每次生成后的 token 统计信息"""
        if (
            log.input_tokens == 0
            and log.output_tokens == 0
            and log.cache_input_tokens == 0
        ):
            return

        model_desc = log.model_full_id or log.model_alias or "unknown"
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Token Stats: endpoint={log.endpoint} "
            f"model={model_desc} input_tokens={log.input_tokens} "
            f"output_tokens={log.output_tokens} cache_input_tokens={log.cache_input_tokens} "
            f"total_tokens={log.total_tokens} status={log.status_code} latency_ms={log.latency_ms}"
        )
