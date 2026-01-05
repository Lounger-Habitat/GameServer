"""定价配置和费用计算"""
from api.menglong.config import SUPPORTED_MODELS

MILLIONS = 1_000_000

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int, cache_input_tokens: int = 0) -> float:
    """计算 API 调用费用
    
    Args:
        model_name: 模型名称
        input_tokens: 输入 token 数量
        output_tokens: 输出 token 数量
        cache_input_tokens: 缓存输入 token 数量（可选）
    
    Returns:
        费用（元）
    """
    # 从 menglong 配置中获取模型价格
    model_info = SUPPORTED_MODELS.get(model_name)
    
    if not model_info or not model_info.price:
        # 如果模型未找到或没有定价，使用默认价格
        input_price = 0.0001  # 元/token
        output_price = 0.0001
        cache_input_price = 0.0001
    else:
        # 使用模型配置的价格（已经是 元/token 格式）
        input_price = model_info.price.get("input", 0.0001)
        output_price = model_info.price.get("output", 0.0001)
        cache_input_price = model_info.price.get("cache_input", input_price)
    
    # 计算总费用
    cost = (
        (input_tokens/MILLIONS) * input_price +
        (output_tokens/MILLIONS) * output_price +
        (cache_input_tokens/MILLIONS) * cache_input_price
    )
    
    return round(cost, 6)  # 保留 6 位小数


def get_model_pricing(model_name: str) -> dict:
    """获取模型定价信息
    
    Args:
        model_name: 模型名称
    
    Returns:
        定价信息字典
    """
    model_info = SUPPORTED_MODELS.get(model_name)
    
    if not model_info or not model_info.price:
        return {
            "input": 0.0001,
            "output": 0.0001,
            "cache_input": 0.0001,
            "currency": "CNY"
        }
    
    return {
        **model_info.price,
        "currency": "CNY"
    }
