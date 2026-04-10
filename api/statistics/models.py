"""
统计系统  数据模型
"""

from datetime import datetime, time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum


class APIMethod(str, Enum):
    """API 方法枚举"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class Currency(str, Enum):
    """货币类型"""

    CNY = "CNY"  # 人民币
    USD = "USD"  # 美元


class TimePriceConfig(BaseModel):
    """分时价格配置"""

    start_time: time
    end_time: time
    input_price_per_million: float = Field(
        ..., gt=0, description="输入价格（元/百万token）"
    )
    output_price_per_million: float = Field(
        ..., gt=0, description="输出价格（元/百万token）"
    )
    cache_input_price_per_million: float = Field(
        default=0.0, description="缓存输入价格（元/百万token）"
    )
    enabled: bool = Field(default=True, description="是否启用")


class ModelPricing(BaseModel):
    """模型定价配置"""

    model_name: str = Field(..., description="模型名称")
    base_input_price_per_million: float = Field(
        ..., gt=0, description="基础输入价格（元/百万token）"
    )
    base_output_price_per_million: float = Field(
        ..., gt=0, description="基础输出价格（元/百万token）"
    )
    base_cache_input_price_per_million: float = Field(
        default=0.0, description="基础缓存输入价格（元/百万token）"
    )
    currency: Currency = Field(default=Currency.CNY, description="货币类型")
    effective_from: datetime = Field(..., description="生效开始时间")
    effective_to: Optional[datetime] = Field(
        default=None, description="生效结束时间（None表示永久有效）"
    )
    enabled: bool = Field(default=True, description="是否启用")
    time_prices: List[TimePriceConfig] = Field(
        default_factory=list, description="分时价格配置"
    )


class ApiCallLog(BaseModel):
    """API 调用日志"""

    timestamp: datetime = Field(default_factory=datetime.now, description="调用时间")
    api_key_name: str = Field(..., description="API Key 名称")
    endpoint: str = Field(..., description="API 端点路径")
    method: APIMethod = Field(..., description="HTTP 方法")

    # 模型信息（统一规范化）
    model_provider: Optional[str] = Field(default=None, description="模型提供商")
    model_full_id: Optional[str] = Field(default=None, description="模型完整ID")
    model_alias: Optional[str] = Field(default=None, description="模型别名")

    # Token 信息
    input_tokens: int = Field(default=0, ge=0, description="输入 token 数量")
    output_tokens: int = Field(default=0, ge=0, description="输出 token 数量")
    cache_input_tokens: int = Field(default=0, ge=0, description="缓存输入 token 数量")
    total_tokens: int = Field(default=0, ge=0, description="总 token 数量")

    # 费用信息
    cost: float = Field(default=0.0, ge=0, description="费用（人民币）")
    input_price_per_million: float = Field(
        default=0.0, ge=0, description="输入价格（元/百万token）"
    )
    output_price_per_million: float = Field(
        default=0.0, ge=0, description="输出价格（元/百万token）"
    )
    cache_input_price_per_million: float = Field(
        default=0.0, ge=0, description="缓存输入价格（元/百万token）"
    )
    currency: Currency = Field(default=Currency.CNY, description="货币类型")

    # 响应信息
    status_code: Optional[int] = Field(default=None, description="HTTP 状态码")
    latency_ms: Optional[int] = Field(default=None, ge=0, description="延迟（毫秒）")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    is_stream: bool = Field(default=False, description="是否为流式响应")
    request_id: Optional[str] = Field(default=None, description="请求ID")

    # 元数据
    client_ip: Optional[str] = Field(default=None, description="客户端IP")
    user_agent: Optional[str] = Field(default=None, description="User Agent")
    tags: Dict[str, Any] = Field(default_factory=dict, description="自定义标签")

    @validator("total_tokens", pre=True, always=True)
    def calculate_total_tokens(cls, v, values):
        """计算总 token 数量"""
        if v == 0:
            input_tokens = values.get("input_tokens", 0)
            output_tokens = values.get("output_tokens", 0)
            cache_input_tokens = values.get("cache_input_tokens", 0)
            return input_tokens + output_tokens + cache_input_tokens
        return v


class UsageStatistics(BaseModel):
    """用量统计"""

    total_calls: int = Field(default=0, description="总调用次数")
    successful_calls: int = Field(default=0, description="成功调用次数")
    failed_calls: int = Field(default=0, description="失败调用次数")

    total_input_tokens: int = Field(default=0, description="总输入 token")
    total_output_tokens: int = Field(default=0, description="总输出 token")
    total_cache_input_tokens: int = Field(default=0, description="总缓存输入 token")
    total_tokens: int = Field(default=0, description="总 token")

    total_cost: float = Field(default=0.0, description="总费用")
    avg_input_tokens: float = Field(default=0.0, description="平均输入 token")
    avg_output_tokens: float = Field(default=0.0, description="平均输出 token")
    avg_cost_per_call: float = Field(default=0.0, description="平均每次调用费用")
    avg_latency_ms: float = Field(default=0.0, description="平均延迟")

    stream_calls: int = Field(default=0, description="流式调用次数")
    non_stream_calls: int = Field(default=0, description="非流式调用次数")


class KeyStatistics(BaseModel):
    """API Key 统计"""

    api_key_name: str = Field(..., description="API Key 名称")
    statistics: UsageStatistics = Field(..., description="用量统计")


class ModelStatistics(BaseModel):
    """模型统计"""

    model_full_id: str = Field(..., description="模型完整ID")
    model_alias: Optional[str] = Field(default=None, description="模型别名")
    model_provider: Optional[str] = Field(default=None, description="模型提供商")
    statistics: UsageStatistics = Field(..., description="用量统计")


class KeyModelStatistics(BaseModel):
    """Key-模型组合统计"""

    api_key_name: str = Field(..., description="API Key 名称")
    model_full_id: str = Field(..., description="模型完整ID")
    statistics: UsageStatistics = Field(..., description="用量统计")


class TimeRangeStatistics(BaseModel):
    """时间范围统计"""

    time_period: str = Field(..., description="时间周期")
    statistics: UsageStatistics = Field(..., description="用量统计")


class StatisticsQuery(BaseModel):
    """统计查询参数"""

    group_by: str = Field(
        default="key", description="分组方式: key, model, key_model, time"
    )
    time_granularity: str = Field(
        default="day", description="时间粒度: year, month, day, hour, minute"
    )
    api_key_name: Optional[str] = Field(default=None, description="API Key 名称")
    model_full_id: Optional[str] = Field(default=None, description="模型完整ID")
    start_date: Optional[datetime] = Field(default=None, description="开始时间")
    end_date: Optional[datetime] = Field(default=None, description="结束时间")


class StatisticsResponse(BaseModel):
    """统计查询响应"""

    results: List[Dict[str, Any]] = Field(default_factory=list, description="查询结果")
    query: StatisticsQuery = Field(..., description="查询参数")


class LogsResponse(BaseModel):
    """日志查询响应"""

    logs: List[ApiCallLog] = Field(default_factory=list, description="日志列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=50, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")


class ModelUsageResponse(BaseModel):
    """模型使用情况响应"""

    model_full_id: str = Field(..., description="模型完整ID")
    model_alias: Optional[str] = Field(default=None, description="模型别名")
    total_calls: int = Field(default=0, description="总调用次数")
    total_input_tokens: int = Field(default=0, description="总输入 token")
    total_output_tokens: int = Field(default=0, description="总输出 token")
    total_cache_input_tokens: int = Field(default=0, description="总缓存输入 token")
    total_tokens: int = Field(default=0, description="总 token")
    total_cost: float = Field(default=0.0, description="总费用")
    avg_input_tokens: float = Field(default=0.0, description="平均输入 token")
    avg_output_tokens: float = Field(default=0.0, description="平均输出 token")
    avg_cost_per_call: float = Field(default=0.0, description="平均每次调用费用")
    unique_api_keys: int = Field(default=0, description="使用该模型的唯一 API Key 数量")


class KeyUsageResponse(BaseModel):
    """API Key 使用情况响应"""

    api_key_name: str = Field(..., description="API Key 名称")
    total_calls: int = Field(default=0, description="总调用次数")
    total_input_tokens: int = Field(default=0, description="总输入 token")
    total_output_tokens: int = Field(default=0, description="总输出 token")
    total_cache_input_tokens: int = Field(default=0, description="总缓存输入 token")
    total_tokens: int = Field(default=0, description="总 token")
    total_cost: float = Field(default=0.0, description="总费用")
    avg_input_tokens: float = Field(default=0.0, description="平均输入 token")
    avg_output_tokens: float = Field(default=0.0, description="平均输出 token")
    avg_cost_per_call: float = Field(default=0.0, description="平均每次调用费用")
    unique_models: int = Field(default=0, description="使用的唯一模型数量")
    models: List[ModelUsageResponse] = Field(
        default_factory=list, description="模型使用详情"
    )
