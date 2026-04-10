"""Anthropic 兼容 API 模块

提供与 Anthropic API 兼容的接口，内部使用 MengLong SDK 调用模型。
"""

from .routes import router

__all__ = ["router"]