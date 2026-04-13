"""模型快照管理器

纯粹的极速运行时配置读取器。
服务器启动时调用，**不再负责网络拉取或字典强行覆盖合并**，完全信任之前由 `build_models.py` 编译静态产出的 `supported_models.yaml`。
内部绝对唯一键统一为: provider/model_name
"""

import os
import yaml
import time
import logging
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelInfo(BaseModel):
    """全局详尽模型信息 (完全抛除对废弃 core 层的依赖)"""

    full_id: str = Field(..., description="完整唯一标识 (provider/model)")
    provider: str = Field(..., description="模型提供商")
    model_name: str = Field(..., description="模型简短名称")
    alias: Optional[str] = Field(None, description="前台呈现用的别名")
    max_tokens: Optional[int] = Field(None, description="最大 token 数")
    context_window: Optional[int] = Field(None, description="上下文窗口")
    supports: Dict[str, bool] = Field(
        {
            "streaming": True,
            "image": False,
            "audio": False,
            "file": False,
            "tools": False,
        },
        description="能力支持",
    )
    price: Optional[Dict[str, float]] = Field(
        {"input": 0.0, "cache_input": 0.0, "output": 0.0}, description="模型价格"
    )
    description: Optional[str] = Field(None, description="模型描述")
    verified: bool = Field(False, description="是否官方验证")
    source: Optional[str] = Field(None, description="配置源标记 (sdk, manual 等)")


class ModelsManager:
    """极限读取态模型管理器"""

    def __init__(self, final_config_path: str = None):
        """
        抛弃旧有的读写混合设计，现以大一统快照文件作为绝对输入口。
        """
        if final_config_path is None:
            final_config_path = os.path.join(
                os.path.dirname(__file__), "supported_models.yaml"
            )
        self.final_config_path = final_config_path

        self._supported_models: Dict[str, ModelInfo] = {}
        self._enabled_models: Set[str] = set()

        self._last_mtime: float = 0

        self.load_snapshot()

    def load_snapshot(self) -> bool:
        """极速装载预编译好的字典，没有任何花哨运算，0 网络交互。"""
        try:
            if not os.path.exists(self.final_config_path):
                logger.error(
                    f"❌ 警告：未找到编译快照文件 `{self.final_config_path}`！API Server 极有可能空跑瘫痪。请执行 `python models/build_models.py`。"
                )
                return False

            current_mtime = os.path.getmtime(self.final_config_path)
            if current_mtime == self._last_mtime:
                return True

            with open(self.final_config_path, "r", encoding="utf-8") as f:
                snapshot = yaml.safe_load(f) or {}

            # 清空缓存
            self._supported_models.clear()
            self._enabled_models.clear()

            # 解析大一统的 models 集合
            raw_models = snapshot.get("models", {})
            for f_id, data_block in raw_models.items():
                try:
                    self._supported_models[f_id] = ModelInfo(**data_block)
                except Exception as e:
                    logger.warning(f"跳过格式损坏的静态快照条目 {f_id}: {e}")

            # 解析启用名单
            raw_enabled = snapshot.get("enabled_models", [])
            for m_id in raw_enabled:
                if m_id in self._supported_models:
                    self._enabled_models.add(m_id)
                else:
                    logger.warning(f"启用名单中包含未知模型 ID: {m_id}")

            self._last_mtime = current_mtime
            logger.info(
                f"✨ 快照装载完成！(0运算)，注入了 {len(self._supported_models)} 个模型结构，并启用了 {len(self._enabled_models)} 个模型。"
            )
            return True

        except Exception as e:
            logger.error(f"装载快照灾难性失败: {e}")
            return False

    def is_model_supported(self, model_id: str, check_enabled: bool = True) -> bool:
        """快速布尔定论路由"""
        self.load_snapshot()
        info = self.get_model_info(model_id)
        if not info:
            return False

        if check_enabled:
            return info.full_id in self._enabled_models
        return True

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """双向查找查询口 (提供给 api 端调用的门面)"""
        self.load_snapshot()

        # 1. 完整 ID 匹配 (如 provider/model_name)
        if "/" in model_id:
            return self._supported_models.get(model_id)

        # 2. 短词匹配 (精准匹配 model_name 或 alias)
        # 优先返回已启用的模型
        fallback = None
        for info in self._supported_models.values():
            if info.model_name == model_id or info.alias == model_id:
                if info.full_id in self._enabled_models:
                    return info
                if not fallback:
                    fallback = info
        return fallback

    def list_all_models(self, only_enabled: bool = True) -> List[ModelInfo]:
        """展示路由表内所有实例"""
        self.load_snapshot()
        if only_enabled:
            return [
                info
                for fid, info in self._supported_models.items()
                if fid in self._enabled_models
            ]
        else:
            return list(self._supported_models.values())


# 全局单例管理器
_models_manager: Optional[ModelsManager] = None


def get_models_manager() -> ModelsManager:
    global _models_manager
    if _models_manager is None:
        _models_manager = ModelsManager()
    return _models_manager
