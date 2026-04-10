#!/usr/bin/env python3
"""离线模型编译脚手架
负责将手工配置 (models_config.yaml) 与孟鸟 SDK 同步的环境模型进行全量编译合并。
彻底输出纯净、完整的字典落盘至 supported_models.yaml。
"""

import os
import yaml
import logging
from datetime import datetime

# 设置基础路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANUAL_CONFIG_PATH = os.path.join(BASE_DIR, "models_config.yaml")
FINAL_CONFIG_PATH = os.path.join(BASE_DIR, "supported_models.yaml")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("build_models")


def build_supported_models():
    logger.info("============== 开始编译模型配置 ==============")

    # 1. 加载手工模型池
    manual_data = {}
    enabled_models_list = []
    if os.path.exists(MANUAL_CONFIG_PATH):
        try:
            with open(MANUAL_CONFIG_PATH, "r", encoding="utf-8") as f:
                raw_manual = yaml.safe_load(f) or {}
                # 由于这是遗留文件，里面可能混合了老的 auto_models 节点，我们只取 manual 和 enabled
                manual_data = raw_manual.get("manual_models", {})
                enabled_models_list = raw_manual.get("enabled_models", [])
                logger.info(
                    f"读取手工配置：共 {len(manual_data)} 个手动覆写节点，要求启用 {len(enabled_models_list)} 个模型。"
                )
        except Exception as e:
            logger.error(f"严重错误：手工配置文件读取断裂: {e}")
            return
    else:
        logger.warning(
            f"手工配置文件未找到: {MANUAL_CONFIG_PATH}，将全量依靠远端 SDK。"
        )

    # 结果池
    final_models = {}

    # 2. 从 SDK 拉取远端节点
    try:
        from menglong import Model

        model = Model()
        if hasattr(model, "list_all_models"):
            logger.info("正在唤醒 MengLong SDK 进行接口侦听 (list_all_models)...")
            all_sdk_models = (
                model.list_all_models()
            )  # 返回 {"provider": [ModelInfo, ...]}
            print("================================================")
            print(all_sdk_models)
            print("================================================")
            for provider_name, sdk_models in all_sdk_models.items():
                for sm in sdk_models:
                    m_id = getattr(sm, "id", None)
                    m_provider = getattr(sm, "provider", provider_name)
                    if not m_id:
                        continue

                    # 纠正或抽取 provider
                    if "/" not in m_id:
                        full_id = f"{m_provider}/{m_id}"
                        model_name = m_id
                    else:
                        full_id = m_id
                        m_provider, model_name = m_id.split("/", 1)

                    final_models[full_id] = {
                        "full_id": full_id,
                        "provider": m_provider,
                        "model_name": model_name,
                        "alias": getattr(sm, "name", model_name),
                        "max_tokens": getattr(sm, "max_tokens", 4096),
                        "context_window": getattr(sm, "context_window", None),
                        "supports": {
                            "streaming": getattr(sm, "supports_streaming", True),
                            "image": getattr(sm, "supports_image", False),
                            "audio": getattr(sm, "supports_audio", False),
                            "file": getattr(sm, "supports_file", False),
                            "tools": getattr(sm, "supports_tools", False),
                        },
                        "price": getattr(sm, "price", {"input": 0.0, "output": 0.0}),
                        "verified": True,
                        "description": getattr(sm, "description", None),
                        "source": "sdk_auto",
                    }
            logger.info(
                f"SDK 拉取完成！从所有 Provider 中抓取到底层 {len(final_models)} 个存活基建。"
            )
        else:
            logger.warning("SDK 当前不支持 list_all_models 方法！")
    except ImportError:
        logger.warning("当前环境未挂载猛鸟 SDK (MengLong)，跳过网络抓取！")
    except Exception as e:
        import traceback
        logger.warning(f"抓取异常: {e}\n{traceback.format_exc()}")

    # 3. 压入高优手工覆盖节点
    logger.info("进行手工高优依赖注入覆写...")
    override_count = 0
    new_addition_count = 0

    for key, mdata in manual_data.items():
        if "/" in key:
            provider, model_name = key.split("/", 1)
        else:
            provider = mdata.get("provider")
            if not provider or str(provider).strip().lower() == "unknown":
                logger.warning(f"手工拦截：提供商不能够为 unknown 抛弃模型 {key}")
                continue
            model_name = key

        full_id = f"{provider}/{model_name}"

        # 覆写原节点或创建一个全新的隔离节点
        if full_id in final_models:
            override_count += 1
            # 增量覆写核心字段
            base_node = final_models[full_id]
            base_node["alias"] = mdata.get("alias") or mdata.get(
                "name", base_node["alias"]
            )  # 兼容旧名
            if "max_tokens" in mdata:
                base_node["max_tokens"] = mdata["max_tokens"]
            if "context_window" in mdata:
                base_node["context_window"] = mdata["context_window"]
            if "supports" in mdata:
                base_node["supports"].update(mdata["supports"])
            if "price" in mdata:
                base_node["price"].update(mdata["price"])
            base_node["source"] = "manual_override"
        else:
            new_addition_count += 1
            final_models[full_id] = {
                "full_id": full_id,
                "provider": provider,
                "model_name": model_name,
                "alias": mdata.get("alias") or mdata.get("name", model_name),
                "max_tokens": mdata.get("max_tokens", 4096),
                "context_window": mdata.get("context_window"),
                "supports": mdata.get(
                    "supports",
                    {
                        "streaming": True,
                        "image": False,
                        "audio": False,
                        "file": False,
                        "tools": False,
                    },
                ),
                "price": mdata.get("price", {"input": 0.0, "output": 0.0}),
                "verified": mdata.get("verified", False),
                "description": mdata.get("description"),
                "source": "manual_addition",
            }

    logger.info(
        f"覆写操作完毕：修改底座 {override_count} 处，完全新生 {new_addition_count} 处。"
    )

    # 5. 生成最终物理快照 (支持池 + 激活名单集成在同一份最终文件中)
    snapshot = {"last_compiled": datetime.now().isoformat(), "models": final_models}

    try:
        with open(FINAL_CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(
                snapshot,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )
        logger.info(f"✅ 生成成功！全静态编译池落盘于 ==> {FINAL_CONFIG_PATH}")
    except Exception as e:
        logger.error(f"❌ 快照落地严重错误: {e}")


if __name__ == "__main__":
    build_supported_models()
