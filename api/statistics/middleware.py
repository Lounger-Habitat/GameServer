"""统计中间件 - 自动记录 API 调用"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from api.auth.storage import get_key_store
from .models import ApiCallLog
from .pricing import calculate_cost
from .storage import get_stats_store
from utils.config import settings


class StatisticsMiddleware(BaseHTTPMiddleware):
    """统计中间件 - 记录每个 API 请求的统计信息"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 跳过不需要统计的路径
        if self._should_skip(request.url.path):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取 API Key 名称
        api_key_name = self._extract_api_key_name(request)
        if not api_key_name:
            api_key_name = "anonymous"  # 未认证请求
        
        # 准备日志对象
        log = ApiCallLog(
            timestamp=datetime.now(timezone.utc),
            api_key_name=api_key_name,
            endpoint=request.url.path,
            method=request.method,
        )
        
        try:
            # 调用下一个中间件/路由
            response = await call_next(request)
            
            # 计算延迟
            latency_ms = int((time.time() - start_time) * 1000)
            log.latency_ms = latency_ms
            log.status_code = response.status_code
            
            # 检查是否为流式响应
            is_stream = isinstance(response, StreamingResponse)
            log.is_stream = is_stream
            
            if is_stream:
                # 流式响应：包装生成器以收集 token 信息
                response = await self._wrap_streaming_response(response, log)
            else:
                # 非流式响应：从响应体中提取 token 信息
                await self._extract_token_info_from_response(response, log)
            
            # 异步记录日志
            if settings.statistics.async_logging:
                asyncio.create_task(self._log_async(log))
            else:
                self._log_sync(log)
            
            return response
            
        except Exception as e:
            # 记录错误
            log.status_code = 500
            log.error_message = str(e)
            log.latency_ms = int((time.time() - start_time) * 1000)
            
            # 异步记录日志
            if settings.statistics.async_logging:
                asyncio.create_task(self._log_async(log))
            else:
                self._log_sync(log)
            
            raise
    
    def _should_skip(self, path: str) -> bool:
        """判断是否跳过统计"""
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/statistics",  # 统计 API 本身不统计
        ]
        return any(path.startswith(p) for p in skip_paths)
    
    def _extract_api_key_name(self, request: Request) -> str | None:
        """从请求中提取 API Key 名称"""
        # 从 Header 中获取 API Key
        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")
        
        key_value = None
        if auth_header.startswith("Bearer "):
            key_value = auth_header[7:]
        elif api_key_header:
            key_value = api_key_header
        
        if not key_value:
            return None
        
        # 通过 Key 值查找 Key 名称
        key_store = get_key_store()
        api_key = key_store.get_key_by_value(key_value)
        
        return api_key.name if api_key else None
    
    async def _extract_token_info_from_response(self, response: Response, log: ApiCallLog):
        """从响应体中提取 token 信息（非流式）"""
        # 只处理成功的 JSON 响应
        if response.status_code != 200:
            return
        
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return
        
        # 读取响应体
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        
        # 恢复响应体（以便可以正常返回给客户端）
        response.body_iterator = self._create_async_iterator([body])
        
        try:
            data = json.loads(body)
            
            # 尝试从 MengLong Response 格式中提取
            if isinstance(data, dict):
                # 提取模型名称
                if "model" in data:
                    log.model_name = data["model"]
                
                # 提取 usage 信息
                usage = data.get("usage", {})
                if usage:
                    log.input_tokens = usage.get("input_tokens", 0)
                    log.output_tokens = usage.get("output_tokens", 0)
                    log.total_tokens = usage.get("total_tokens", 0)
                    
                    # 计算费用
                    if log.model_name:
                        log.cost = calculate_cost(
                            log.model_name,
                            log.input_tokens,
                            log.output_tokens
                        )
        except (json.JSONDecodeError, KeyError):
            pass
    
    async def _wrap_streaming_response(self, response: StreamingResponse, log: ApiCallLog) -> StreamingResponse:
        """包装流式响应以收集 token 信息"""
        original_iterator = response.body_iterator
        
        # 累计的 token 信息
        total_input_tokens = 0
        total_output_tokens = 0
        model_name = None
        
        async def wrapped_generator():
            nonlocal total_input_tokens, total_output_tokens, model_name
            
            async for chunk in original_iterator:
                # 尝试解析 StreamResponse
                try:
                    # 流式响应是 NDJSON 格式（每行一个 JSON）
                    lines = chunk.decode('utf-8').strip().split('\n')
                    for line in lines:
                        if not line:
                            continue
                        
                        data = json.loads(line)
                        
                        # 提取模型名称
                        if "model" in data and not model_name:
                            model_name = data["model"]
                        
                        # 累计 usage 信息
                        usage = data.get("usage", {})
                        if usage:
                            # 对于流式响应，usage 通常在最后一个 chunk
                            total_input_tokens = usage.get("input_tokens", total_input_tokens)
                            total_output_tokens = usage.get("output_tokens", total_output_tokens)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
                
                yield chunk
            
            # 流结束后更新日志
            log.model_name = model_name
            log.input_tokens = total_input_tokens
            log.output_tokens = total_output_tokens
            log.total_tokens = total_input_tokens + total_output_tokens
            
            if model_name:
                log.cost = calculate_cost(
                    model_name,
                    total_input_tokens,
                    total_output_tokens
                )
        
        return StreamingResponse(
            wrapped_generator(),
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
    
    async def _create_async_iterator(self, items):
        """创建异步迭代器"""
        for item in items:
            yield item
    
    async def _log_async(self, log: ApiCallLog):
        """异步记录日志"""
        try:
            stats_store = get_stats_store(settings.statistics.database_file)
            await asyncio.to_thread(stats_store.log_api_call, log)
        except Exception as e:
            print(f"⚠️  记录统计日志失败: {e}")
    
    def _log_sync(self, log: ApiCallLog):
        """同步记录日志"""
        try:
            stats_store = get_stats_store(settings.statistics.database_file)
            stats_store.log_api_call(log)
        except Exception as e:
            print(f"⚠️  记录统计日志失败: {e}")
