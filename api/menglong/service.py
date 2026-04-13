"""MengLong 服务层

直接使用 MengLong SDK 调用 LLM，支持多模态内容（图片、文件、音频、视频）
"""

from typing import AsyncIterator, List, Optional, Any

from menglong import Model
from .config import is_model_supported, get_model_full_id
from datetime import datetime


class MengLongService:
    """MengLong LLM 服务"""

    def __init__(self):
        """初始化服务，直接使用 MengLong SDK"""
        self.model_client = Model()

    async def chat(
        self,
        model: str,
        messages: List[Any],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None,
        tool_choice: Optional[str] = "auto",
    ) -> Any:
        """对话补全

        Args:
            model: 模型名称
            messages: 消息列表（支持字典或 SDK Message 类型）
            temperature: 温度参数
            max_tokens: 最大 token 数
            tools: 工具列表
            tool_choice: 工具选择模式

        Returns:
            MengLong SDK 的 Response 对象
        """
        # 验证并获取完整模型 ID
        if not is_model_supported(model):
            raise ValueError(f"不支持的模型: {model}")

        full_model_id = get_model_full_id(model)
        from datetime import datetime

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] MengLongService.chat: input={model} -> resolved={full_model_id}"
        )

        try:
            # 直接透传给 SDK，SDK 会自动处理消息归一化（包括多模态支持）
            response = await self.model_client.async_chat(
                model=full_model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
            )

            # 防御性检查：确保 response 不为 None 且 output 存在
            if response is None:
                raise ValueError("SDK 返回了空响应 (None)")

            return response

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            raise ValueError(f"MengLong SDK 调用失败: {str(e)}\n{error_details}")

    async def stream_chat(
        self,
        model: str,
        messages: List[Any],
        temperature: Optional[float] = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list] = None,
        tool_choice: Optional[str] = "auto",
    ) -> AsyncIterator[Any]:
        """流式对话补全

        Args:
            model: 模型名称
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            tools: 工具列表
            tool_choice: 工具选择模式

        Yields:
            MengLong SDK 的 StreamResponse 对象
        """
        # 验证并获取完整模型 ID
        if not is_model_supported(model):
            raise ValueError(f"不支持的模型: {model}")

        full_model_id = get_model_full_id(model)

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] MengLongService.stream_chat: input={model} -> resolved={full_model_id}"
        )

        try:
            # async_stream_chat 返回的是 async_generator，必须用 async for
            sdk_gen = self.model_client.async_stream_chat(
                model=full_model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice=tool_choice,
            )
            async for chunk in sdk_gen:
                yield chunk

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            raise ValueError(f"MengLong SDK 流式调用失败: {str(e)}\n{error_details}")


# 全局服务实例
_service: MengLongService | None = None


def get_service() -> MengLongService:
    """获取全局服务实例"""
    global _service
    if _service is None:
        _service = MengLongService()
    return _service
