"""
模型名称规范化器
统一处理不同格式的模型名称，映射到标准化格式
"""

import re
from typing import Optional, Tuple, Dict, List
import yaml
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class ModelNormalizer:
    """模型名称规范化器"""

    def __init__(self, config_file: str = "models/supported_models.yaml"):
        self.config_file = Path(config_file)
        self.model_configs = self._load_model_configs()
        self._build_name_mappings()

    def _load_model_configs(self) -> Dict:
        """加载模型配置"""
        if not self.config_file.exists():
            return {}

        with open(self.config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return data.get("models", {})

    def _build_name_mappings(self):
        """构建名称映射"""
        self.full_id_to_config = {}
        self.alias_to_full_id = {}
        self.short_name_to_full_id = {}
        self.base_name_to_full_ids = defaultdict(list)
        self.provider_to_models = defaultdict(list)

        for full_id, config in self.model_configs.items():
            # 存储完整配置
            self.full_id_to_config[full_id.lower()] = config

            # 构建别名映射
            if "alias" in config and config["alias"]:
                alias = config["alias"]
                self.alias_to_full_id[alias.lower()] = full_id

            # 构建模型名称的各个部分映射
            parts = full_id.split("/")
            if len(parts) == 2:
                provider, model = parts
                self.provider_to_models[provider].append(full_id)

                # 短名称映射（去掉provider）
                self.short_name_to_full_id[model.lower()] = full_id

    def normalize(
        self, model_name: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        规范化模型名称

        Returns:
            (model_full_id, model_provider, model_alias)
        """
        if not model_name:
            return None, None, None

        # 清理模型名称
        clean_name = model_name.strip().lower()

        # 1. 首先尝试直接匹配完整ID (如 infinigence/deepseek-v3.2)
        if clean_name in self.full_id_to_config:
            config = self.full_id_to_config[clean_name]
            return (config["full_id"], config.get("provider"), config.get("alias"))

        # 2. 尝试匹配别名 (alias 字段定义的显示名称)
        if clean_name in self.alias_to_full_id:
            full_id = self.alias_to_full_id[clean_name]
            config = self.full_id_to_config[full_id]
            return (config["full_id"], config.get("provider"), config.get("alias"))

        # 3. 尝试匹配短名称 (不带 provider 的 model_name)
        if clean_name in self.short_name_to_full_id:
            full_id = self.short_name_to_full_id[clean_name]
            config = self.full_id_to_config[full_id]
            return (config["full_id"], config.get("provider"), config.get("alias"))

        # 4. 无法识别，返回原始名称

        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ModelNormalizer.normalize: input={model_name} -> result={(clean_name, None, None)}"
        )
        return model_name, None, None

    def get_model_config(self, model_full_id: str) -> Optional[Dict]:
        """获取模型配置"""
        return self.full_id_to_config.get(model_full_id.lower())

    def get_all_models(self) -> Dict[str, Dict]:
        """获取所有模型配置"""
        return self.full_id_to_config

    def get_models_by_provider(self, provider: str) -> List[str]:
        """按提供商获取模型"""
        return self.provider_to_models.get(provider.lower(), [])


# 单例实例
_model_normalizer: Optional[ModelNormalizer] = None


def get_model_normalizer() -> ModelNormalizer:
    """获取模型规范化器单例"""
    global _model_normalizer
    if _model_normalizer is None:
        _model_normalizer = ModelNormalizer()
    return _model_normalizer


def normalize_model_name(
    model_name: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """规范化模型名称（快捷函数）"""
    normalizer = get_model_normalizer()
    return normalizer.normalize(model_name)
