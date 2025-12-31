"""MengLong 模型配置

定义支持的模型列表和配置
"""
from fastapi._compat.model_field import ModelField
from .models import ModelInfo


# 支持的模型配置
SUPPORTED_MODELS = {
    "deepseek-chat": ModelInfo(
        id="deepseek-chat",
        name="DeepSeek Chat",
        provider="DeepSeek",
        description="DeepSeek 通用对话模型",
        max_tokens=4096,
        supports={"streaming": True,"image": False,"audio": False,"file": False},
        price={"input": 0.0001,"cache_input":0.0001,"output": 0.0001}
    ),
    "gemini-3-pro-preview": ModelInfo(
        id="gemini-3-pro-preview",
        name="Gemini 3 Pro",
        provider="Google",
        description="Google Gemini 3 Pro Preview",
        max_tokens=8192,
        supports={"streaming": True,"image": False,"audio": False,"file": False},
        price={"input": 0.0001,"cache_input":0.0001,"output": 0.0001}
    ),
    "gemini-3-flash-preview": ModelInfo(
        id="gemini-3-flash-preview",
        name="Gemini 3 Flash",
        provider="Google",
        description="Google Gemini 3 Flash Preview",
        max_tokens=8192,
        supports={"streaming": True,"image": False,"audio": False,"file": False},
        price={"input": 0.0001,"cache_input":0.0001,"output": 0.0001}
    ),
    "gpt-5.1": ModelInfo(
        id="gpt-5.1",
        name="GPT-5.1",
        provider="OpenAI",
        description="OpenAI GPT-5.1 多模态模型",
        max_tokens=128000,
        supports={"streaming": True,"image": False,"audio": False,"file": False},
        price={"input": 0.0001,"cache_input":0.0001,"output": 0.0001}
    ),
    "claude-sonnet-4-20250514": ModelInfo(
        id="claude-sonnet-4-20250514",
        name="Claude 4.5 Sonnet",
        provider="Infinigence",
        description="Anthropic Claude 4.5 Sonnet",
        max_tokens=200000,
        supports={"streaming": True,"image": False,"audio": False,"file": False},
        price={"input": 0.0001,"cache_input":0.0001,"output": 0.0001}
    ),
    "global.anthropic.claude-sonnet-4-5-20250929-v1:0": ModelInfo(
        id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        name="Claude 4.5 Sonnet",
        provider="Anthropic",
        description="Anthropic Claude 4.5 Sonnet",
        max_tokens=200000,
        supports={"streaming": True,"image": False,"audio": False,"file": False},
        price={"input": 0.0001,"cache_input":0.0001,"output": 0.0001}
    ),
}


def get_model_info(model_id: str) -> ModelInfo | None:
    """获取模型信息"""
    return SUPPORTED_MODELS.get(model_id)


def list_all_models() -> list[ModelInfo]:
    """列出所有支持的模型"""
    # return [info.id for info in SUPPORTED_MODELS.values()]
    return list(SUPPORTED_MODELS.values())


def is_model_supported(model_id: str) -> bool:
    """检查模型是否支持"""
    return model_id in SUPPORTED_MODELS

def get_model_provider(model_id: str) -> str | None:
    """获取模型提供者"""
    model_info = get_model_info(model_id)
    return model_info.provider if model_info else None

def get_model_full_id(model_id: str) -> str | None:
    """获取模型完整 ID"""
    model_provider = get_model_provider(model_id)
    return model_provider.lower() + "/" + model_id if model_provider else None