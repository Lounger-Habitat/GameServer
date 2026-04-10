"""MengLong 模型配置

定义支持的模型列表和配置
使用模型管理器支持热更新和手动/自动模型融合
"""

from typing import Dict, Any, List
from models.manager import get_models_manager
from .models import MengLongModelInfo

DOLLAR_TO_RMB = 8


def get_model_info(model_id: str) -> MengLongModelInfo | None:
    """获取模型信息"""
    models_manager = get_models_manager()
    info = models_manager.get_model_info(model_id)

    if info:
        return MengLongModelInfo(
            id=info.full_id,
            name=info.alias or info.model_name,
            provider=info.provider,
            max_tokens=info.max_tokens,
            supports=info.supports,
            price=info.price,
            description=info.description,
        )
    return None


def list_all_models() -> List[MengLongModelInfo]:
    """列出所有支持的模型"""
    models_manager = get_models_manager()
    llm_models = models_manager.list_all_models(only_enabled=True)

    menglong_models = []
    for info in llm_models:
        menglong_models.append(
            MengLongModelInfo(
                id=info.full_id,
                name=info.alias or info.model_name,
                provider=info.provider,
                max_tokens=info.max_tokens,
                supports=info.supports,
                price=info.price,
                description=info.description,
            )
        )
    return menglong_models


def is_model_supported(model_id: str) -> bool:
    """检查模型是否支持"""
    models_manager = get_models_manager()
    return models_manager.is_model_supported(model_id, check_enabled=True)


def get_model_provider(model_id: str) -> str | None:
    """获取模型提供者"""
    models_manager = get_models_manager()
    info = models_manager.get_model_info(model_id)
    if info:
        return info.provider
    return "unknown"


def get_model_full_id(model_id: str) -> str | None:
    """获取模型完整 ID (统一化方法)"""
    models_manager = get_models_manager()
    info = models_manager.get_model_info(model_id)
    if info:
        return info.full_id
    return None
