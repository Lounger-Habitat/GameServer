"""统计模块数据模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ApiCallLog(BaseModel):
    """API 调用日志记录"""
    id: Optional[int] = None
    timestamp: datetime = Field(..., description="请求时间")
    api_key_name: str = Field(..., description="API Key 名称")
    endpoint: str = Field(..., description="请求端点")
    method: str = Field(..., description="HTTP 方法")
    status_code: Optional[int] = Field(None, description="响应状态码")
    model_name: Optional[str] = Field(None, description="使用的模型名称")
    input_tokens: int = Field(0, description="输入 token 数")
    output_tokens: int = Field(0, description="输出 token 数")
    total_tokens: int = Field(0, description="总 token 数")
    cost: float = Field(0.0, description="费用（元）")
    latency_ms: Optional[int] = Field(None, description="延迟（毫秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    is_stream: bool = Field(False, description="是否为流式请求")


class UsageStatistics(BaseModel):
    """使用统计（总体或按 key）"""
    total_calls: int = Field(0, description="总调用次数")
    successful_calls: int = Field(0, description="成功调用次数")
    failed_calls: int = Field(0, description="失败调用次数")
    total_input_tokens: int = Field(0, description="总输入 token 数")
    total_output_tokens: int = Field(0, description="总输出 token 数")
    total_tokens: int = Field(0, description="总 token 数")
    total_cost: float = Field(0.0, description="总费用（元）")
    stream_calls: int = Field(0, description="流式调用次数")
    non_stream_calls: int = Field(0, description="非流式调用次数")


class KeyStatistics(BaseModel):
    """按 Key 的统计信息"""
    api_key_name: str = Field(..., description="API Key 名称")
    statistics: UsageStatistics = Field(..., description="统计数据")


class StatisticsQuery(BaseModel):
    """统计查询参数"""
    start_date: Optional[datetime] = Field(None, description="开始时间")
    end_date: Optional[datetime] = Field(None, description="结束时间")
    api_key_name: Optional[str] = Field(None, description="API Key 名称")
    model_name: Optional[str] = Field(None, description="模型名称")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(50, ge=1, le=500, description="每页数量")


class LogsResponse(BaseModel):
    """日志查询响应"""
    logs: list[ApiCallLog] = Field([], description="日志列表")
    total: int = Field(0, description="总记录数")
    page: int = Field(1, description="当前页码")
    page_size: int = Field(50, description="每页数量")
    total_pages: int = Field(0, description="总页数")
