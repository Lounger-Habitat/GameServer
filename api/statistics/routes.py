"""
统计 API 路由
"""

from datetime import datetime
from typing import Optional
from pathlib import Path
import math

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, FileResponse
import csv
import io
import json

from api.auth.dependencies import verify_api_key
from api.auth.models import ApiKey
from .models import (
    UsageStatistics,
    KeyStatistics,
    ModelStatistics,
    KeyModelStatistics,
    TimeRangeStatistics,
    LogsResponse,
    StatisticsQuery,
    StatisticsResponse,
    ModelUsageResponse,
    KeyUsageResponse,
    ModelPricing,
    TimePriceConfig,
)
from .storage import get_stats_store
from .pricing import get_pricing_manager
from utils.config import settings


router = APIRouter()


@router.get("/dashboard")
async def serve_dashboard():
    """提供 Dashboard HTML 页面"""
    dashboard_path = Path(__file__).parent / "templates" / "dashboard.html"
    return FileResponse(dashboard_path)


def _is_admin_key(api_key: ApiKey) -> bool:
    """检查是否为管理员 Key（名称包含 'admin'）"""
    return "admin" in api_key.name.lower()


@router.get("/")
async def statistics_root():
    """统计 API 根端点"""
    return {
        "message": "Statistics API ",
        "version": "2.0",
        "endpoints": [
            "GET /statistics/overview - 总体统计概览",
            "GET /statistics/my - 我的统计（当前 API Key）",
            "GET /statistics/by-key/{key_name} - 指定 Key 的统计（仅管理员）",
            "GET /statistics/all-keys - 所有 Key 的统计（仅管理员）",
            "GET /statistics/logs - 调用日志查询",
            "GET /statistics/export - 导出统计数据",
            "POST /statistics/cleanup - 清理旧记录（仅管理员）",
            "POST /statistics/query - 高级统计查询（支持多维度分组）",
            "GET /statistics/models - 所有模型的使用统计（仅管理员）",
            "GET /statistics/key-models - 按 Key 和模型的统计（仅管理员）",
            "GET /statistics/time-series - 时间序列统计",
            "GET /statistics/model/{model_full_id}/usage - 模型详细使用情况（仅管理员）",
            "GET /statistics/key/{key_name}/usage - API Key 详细使用情况（仅管理员）",
            "GET /statistics/pricing/{model_full_id} - 模型定价信息（仅管理员）",
            "POST /statistics/pricing - 保存模型定价配置（仅管理员）",
            "GET /statistics/summary - 汇总统计信息（仅管理员）",
            "GET /statistics/system-status - 系统状态信息",
        ],
    }


@router.get("/overview", response_model=UsageStatistics)
async def get_overview(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取总体统计概览（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看总体统计")

    stats_store = get_stats_store()
    return stats_store.get_total_stats(start_date, end_date)


@router.get("/my", response_model=UsageStatistics)
async def get_my_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取当前 API Key 的统计"""
    stats_store = get_stats_store()
    return stats_store.get_stats_by_key(api_key.name, start_date, end_date)


@router.get("/by-key/{key_name}", response_model=UsageStatistics)
async def get_statistics_by_key(
    key_name: str,
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取指定 API Key 的统计（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看其他 Key 的统计")

    stats_store = get_stats_store()
    return stats_store.get_stats_by_key(key_name, start_date, end_date)


@router.get("/all-keys", response_model=list[KeyStatistics])
async def get_all_keys_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取所有 API Key 的统计列表（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看所有 Key 的统计")

    stats_store = get_stats_store()
    return stats_store.get_all_keys_stats(start_date, end_date)


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    key_name: Optional[str] = Query(None, description="API Key 名称"),
    model_full_id: Optional[str] = Query(None, description="模型完整ID"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页数量"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """查询调用日志（分页）

    - 管理员可以查看所有日志
    - 普通用户只能查看自己的日志
    """
    # 如果不是管理员，强制只查询自己的日志
    if not _is_admin_key(api_key):
        key_name = api_key.name

    stats_store = get_stats_store()
    logs, total = stats_store.get_logs(
        key_name=key_name,
        model_full_id=model_full_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return LogsResponse(
        logs=logs, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.get("/export")
async def export_statistics(
    format: str = Query("csv", description="导出格式: csv 或 json"),
    key_name: Optional[str] = Query(None, description="API Key 名称"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """导出统计数据

    支持 CSV 和 JSON 格式
    """
    # 如果不是管理员，强制只导出自己的数据
    if not _is_admin_key(api_key):
        key_name = api_key.name

    stats_store = get_stats_store()
    logs, _ = stats_store.get_logs(
        key_name=key_name,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000,  # 最多导出 10000 条
    )

    if format.lower() == "csv":
        # 导出 CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # 写入表头
        writer.writerow(
            [
                "ID",
                "时间",
                "API Key",
                "端点",
                "方法",
                "状态码",
                "模型",
                "提供商",
                "别名",
                "输入Tokens",
                "输出Tokens",
                "缓存Tokens",
                "总Tokens",
                "费用(元)",
                "输入价格/百万",
                "输出价格/百万",
                "缓存价格/百万",
                "延迟(ms)",
                "是否流式",
                "请求ID",
                "客户端IP",
                "User Agent",
            ]
        )

        # 写入数据
        for log in logs:
            writer.writerow(
                [
                    log.id,
                    log.timestamp.isoformat(),
                    log.api_key_name,
                    log.endpoint,
                    log.method.value,
                    log.status_code,
                    log.model_full_id or "",
                    log.model_provider or "",
                    log.model_alias or "",
                    log.input_tokens,
                    log.output_tokens,
                    log.cache_input_tokens,
                    log.total_tokens,
                    f"{log.cost:.6f}",
                    f"{log.input_price_per_million:.6f}",
                    f"{log.output_price_per_million:.6f}",
                    f"{log.cache_input_price_per_million:.6f}",
                    log.latency_ms,
                    "是" if log.is_stream else "否",
                    log.request_id or "",
                    log.client_ip or "",
                    log.user_agent or "",
                ]
            )

        # 返回 CSV 文件
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            },
        )

    elif format.lower() == "json":
        # 导出 JSON
        data = [log.model_dump() for log in logs]

        return StreamingResponse(
            iter([json.dumps(data, ensure_ascii=False, indent=2, default=str)]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            },
        )

    else:
        raise HTTPException(
            status_code=400, detail="不支持的导出格式，请使用 'csv' 或 'json'"
        )


@router.post("/cleanup")
async def cleanup_old_records(
    days: int = Query(..., ge=1, description="保留最近 N 天的记录"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """清理旧记录（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以清理记录")

    stats_store = get_stats_store()
    deleted_count = stats_store.cleanup_old_records(days)

    return {
        "message": f"已清理 {deleted_count} 条旧记录",
        "deleted_count": deleted_count,
        "retention_days": days,
    }


@router.post("/query", response_model=StatisticsResponse)
async def query_statistics(
    query: StatisticsQuery, api_key: ApiKey = Depends(verify_api_key)
):
    """高级统计查询

    支持按多种维度分组查询：
    - group_by: key, model, key_model, time
    - time_granularity: year, month, day, hour, minute (当 group_by=time 时)
    """
    # 权限检查
    if not _is_admin_key(api_key):
        # 普通用户只能查询自己的数据
        if query.api_key_name and query.api_key_name != api_key.name:
            raise HTTPException(status_code=403, detail="只能查询自己的统计信息")
        # 强制设置为自己的 key
        query.api_key_name = api_key.name

    stats_store = get_stats_store()
    return stats_store.get_detailed_usage_stats(query)


@router.get("/models", response_model=list[ModelStatistics])
async def get_models_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取所有模型的使用统计（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看模型统计")

    stats_store = get_stats_store()
    return stats_store.get_model_usage_stats(start_date, end_date)


@router.get("/key-models", response_model=list[KeyModelStatistics])
async def get_key_models_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取按 Key 和模型的统计（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看 Key-模型统计")

    stats_store = get_stats_store()
    return stats_store.get_model_usage_stats(start_date, end_date)


@router.get("/time-series")
async def get_time_series_statistics(
    time_granularity: str = Query(
        "day", description="时间粒度: year, month, day, hour, minute"
    ),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key_name: Optional[str] = Query(None, description="API Key 名称"),
    model_full_id: Optional[str] = Query(None, description="模型完整ID"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取时间序列统计

    - 管理员可以查看所有数据
    - 普通用户只能查看自己的数据
    """
    # 权限检查
    if not _is_admin_key(api_key):
        if api_key_name and api_key_name != api_key.name:
            raise HTTPException(status_code=403, detail="只能查询自己的统计信息")
        # 强制设置为自己的 key
        api_key_name = api_key.name

    stats_store = get_stats_store()

    # 这里需要实现时间序列查询
    # 暂时返回空结果
    return []


@router.get("/model/{model_full_id}/usage", response_model=ModelUsageResponse)
async def get_model_usage(
    model_full_id: str,
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取指定模型的详细使用情况（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(
            status_code=403, detail="只有管理员可以查看模型详细使用情况"
        )

    stats_store = get_stats_store()

    # 获取模型统计
    model_stats = stats_store.get_model_usage_stats(start_date, end_date)
    model_stat = next(
        (ms for ms in model_stats if ms.model_full_id == model_full_id), None
    )

    if not model_stat:
        raise HTTPException(
            status_code=404, detail=f"未找到模型 {model_full_id} 的统计信息"
        )

    # 获取使用该模型的唯一 API Key 数量
    cursor = stats_store.conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(DISTINCT api_key_name) as unique_keys
        FROM api_call_logs
        WHERE model_full_id = ? AND timestamp >= ? AND timestamp <= ?
    """,
        (model_full_id, start_date or datetime.min, end_date or datetime.max),
    )
    unique_keys = cursor.fetchone()["unique_keys"] or 0

    return ModelUsageResponse(
        model_full_id=model_full_id,
        model_alias=model_stat.model_alias,
        total_calls=model_stat.statistics.total_calls,
        total_input_tokens=model_stat.statistics.total_input_tokens,
        total_output_tokens=model_stat.statistics.total_output_tokens,
        total_cache_input_tokens=model_stat.statistics.total_cache_input_tokens,
        total_tokens=model_stat.statistics.total_tokens,
        total_cost=model_stat.statistics.total_cost,
        avg_input_tokens=model_stat.statistics.avg_input_tokens,
        avg_output_tokens=model_stat.statistics.avg_output_tokens,
        avg_cost_per_call=model_stat.statistics.avg_cost_per_call,
        unique_api_keys=unique_keys,
    )


@router.get("/key/{key_name}/usage", response_model=KeyUsageResponse)
async def get_key_usage(
    key_name: str,
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取指定 API Key 的详细使用情况（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(
            status_code=403, detail="只有管理员可以查看其他 Key 的详细使用情况"
        )

    stats_store = get_stats_store()

    # 获取 Key 统计
    key_stat = stats_store.get_stats_by_key(key_name, start_date, end_date)

    # 获取按模型的详细使用情况
    model_stats = stats_store.get_model_usage_stats(start_date, end_date, key_name)

    # 获取使用的唯一模型数量
    cursor = stats_store.conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(DISTINCT model_full_id) as unique_models
        FROM api_call_logs
        WHERE api_key_name = ? AND timestamp >= ? AND timestamp <= ?
    """,
        (key_name, start_date or datetime.min, end_date or datetime.max),
    )
    unique_models = cursor.fetchone()["unique_models"] or 0

    # 转换为 ModelUsageResponse 列表
    model_responses = []
    for ms in model_stats:
        model_responses.append(
            ModelUsageResponse(
                model_full_id=ms.model_full_id,
                model_alias=ms.model_alias,
                total_calls=ms.statistics.total_calls,
                total_input_tokens=ms.statistics.total_input_tokens,
                total_output_tokens=ms.statistics.total_output_tokens,
                total_cache_input_tokens=ms.statistics.total_cache_input_tokens,
                total_tokens=ms.statistics.total_tokens,
                total_cost=ms.statistics.total_cost,
                avg_input_tokens=ms.statistics.avg_input_tokens,
                avg_output_tokens=ms.statistics.avg_output_tokens,
                avg_cost_per_call=ms.statistics.avg_cost_per_call,
                unique_api_keys=1,  # 对于单个 Key 的模型统计，unique_api_keys 总是 1
            )
        )

    return KeyUsageResponse(
        api_key_name=key_name,
        total_calls=key_stat.total_calls,
        total_input_tokens=key_stat.total_input_tokens,
        total_output_tokens=key_stat.total_output_tokens,
        total_cache_input_tokens=key_stat.total_cache_input_tokens,
        total_tokens=key_stat.total_tokens,
        total_cost=key_stat.total_cost,
        avg_input_tokens=key_stat.avg_input_tokens,
        avg_output_tokens=key_stat.avg_output_tokens,
        avg_cost_per_call=key_stat.avg_cost_per_call,
        unique_models=unique_models,
        models=model_responses,
    )


@router.get("/all-pricing")
async def get_all_pricing(api_key: ApiKey = Depends(verify_api_key)):
    """获取所有模型定价配置列表（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看定价信息")
    pricing_manager = get_pricing_manager()
    return pricing_manager.get_all_pricing()


@router.get("/pricing/{model_full_id}")
async def get_model_pricing(
    model_full_id: str,
    timestamp: Optional[datetime] = Query(None, description="查询时间点"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取模型定价信息（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看定价信息")

    pricing_manager = get_pricing_manager()
    pricing = pricing_manager.get_model_pricing(model_full_id, timestamp)

    if not pricing:
        raise HTTPException(
            status_code=404, detail=f"未找到模型 {model_full_id} 的定价信息"
        )

    return {
        "model_full_id": model_full_id,
        "base_input_price_per_million": pricing.base_input_price_per_million,
        "base_output_price_per_million": pricing.base_output_price_per_million,
        "base_cache_input_price_per_million": pricing.base_cache_input_price_per_million,
        "currency": pricing.currency.value,
        "effective_from": pricing.effective_from.isoformat()
        if pricing.effective_from
        else None,
        "effective_to": pricing.effective_to.isoformat()
        if pricing.effective_to
        else None,
        "enabled": pricing.enabled,
        "has_time_pricing": len(pricing.time_prices) > 0,
        "time_prices": [
            {
                "start_time": tp.start_time.isoformat(),
                "end_time": tp.end_time.isoformat(),
                "input_price_per_million": tp.input_price_per_million,
                "output_price_per_million": tp.output_price_per_million,
                "cache_input_price_per_million": tp.cache_input_price_per_million,
                "enabled": tp.enabled,
            }
            for tp in pricing.time_prices
        ],
    }


@router.post("/pricing")
async def save_model_pricing(
    pricing: ModelPricing, api_key: ApiKey = Depends(verify_api_key)
):
    """保存模型定价配置（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以配置定价")

    pricing_manager = get_pricing_manager()
    pricing_id = pricing_manager.save_model_pricing(pricing)

    return {
        "message": "定价配置已保存",
        "pricing_id": pricing_id,
        "model_full_id": pricing.model_name,
    }


@router.get("/summary")
async def get_summary_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key),
):
    """获取汇总统计信息（仅管理员）

    包括：
    - 总体统计
    - Top 10 API Keys（按费用）
    - Top 10 模型（按费用）
    - 时间趋势（按天）
    """
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看汇总统计")

    stats_store = get_stats_store()

    # 总体统计
    overall_stats = stats_store.get_total_stats(start_date, end_date)

    # Top 10 API Keys
    all_keys_stats = stats_store.get_all_keys_stats(start_date, end_date)
    top_keys = all_keys_stats[:10]

    # Top 10 模型
    model_stats = stats_store.get_model_usage_stats(start_date, end_date)
    top_models = model_stats[:10]

    return {
        "overall": overall_stats.dict(),
        "top_keys": [ks.dict() for ks in top_keys],
        "top_models": [ms.dict() for ms in top_models],
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
    }


@router.get("/system-status")
async def get_system_status(api_key: ApiKey = Depends(verify_api_key)):
    """获取系统状态信息（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(status_code=403, detail="只有管理员可以查看系统状态")

    from .model_normalizer import get_model_normalizer
    from .pricing import get_pricing_manager

    normalizer = get_model_normalizer()
    pricing_manager = get_pricing_manager()
    stats_store = get_stats_store()

    # 获取模型配置
    model_configs = normalizer.get_all_models()

    # 获取定价信息
    pricing_info = pricing_manager.get_all_pricing()

    # 获取统计信息
    overall_stats = stats_store.get_total_stats()

    return {
        "system": "Statistics System ",
        "version": "2.0",
        "database": "statistics.db",
        "models": {
            "total_configured": len(model_configs),
            "total_priced": len(pricing_info),
            "sample_models": list(model_configs.keys())[:5],
        },
        "statistics": {
            "total_calls": overall_stats.total_calls,
            "total_tokens": overall_stats.total_tokens,
            "total_cost": overall_stats.total_cost,
            "unique_api_keys": len(stats_store.get_all_keys_stats()),
            "unique_models": len(stats_store.get_model_usage_stats()),
        },
        "features": [
            "模型名称规范化",
            "人民币定价（自动从美元转换）",
            "流式响应Token计数",
            "多维度统计查询",
            "分时价格支持",
        ],
    }
