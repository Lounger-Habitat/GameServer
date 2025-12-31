"""MengLong 服务层

使用 MengLong SDK 调用 LLM
"""
from typing import AsyncIterator, List, Optional

from menglong import Model
from menglong.schemas.chat import Message, Response, StreamResponse

from .config import is_model_supported,get_model_full_id


class MengLongService:
    """MengLong LLM 服务"""
    
    def __init__(self):
        """初始化服务"""
        # MengLong SDK 会自动从配置文件加载
        self.model = Model()
    
    async def chat(
        self,
        model: str,
        messages: List[Message],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Response:
        """对话补全
        
        Args:
            model: 模型名称
            messages: 消息列表（MengLong SDK 的 Message 类型）
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            Response: MengLong SDK 的 Response 对象
            
        Raises:
            ValueError: 模型不支持
        """
        # 验证模型
        if not is_model_supported(model):
            raise ValueError(f"不支持的模型: {model}")
        else:
            model = get_model_full_id(model)
        
        # 调用 MengLong SDK，直接返回 Response
        return self.model.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    async def stream_chat(
    # def stream_chat(
        self,
        model: str,
        messages: List[Message],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[StreamResponse]:
    # ):
        """流式对话补全
        
        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Yields:
            StreamResponse: MengLong SDK 的 StreamResponse 对象
        """
        # 验证模型
        if not is_model_supported(model):
            raise ValueError(f"不支持的模型: {model}")
        else:
            model = get_model_full_id(model)
        
        # 调用 MengLong SDK 流式接口，直接 yield StreamResponse
        async for chunk in self.model.async_stream_chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk


# 全局服务实例
_service: MengLongService | None = None


def get_service() -> MengLongService:
    """获取全局服务实例"""
    global _service
    if _service is None:
        _service = MengLongService()
    return _service

