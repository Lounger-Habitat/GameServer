"""统计 API 路由"""
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
    LogsResponse,
    StatisticsQuery
)
from .storage import get_stats_store
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
        "message": "Statistics API",
        "version": "1.0",
        "endpoints": [
            "GET /statistics/overview - 总体统计概览",
            "GET /statistics/my - 我的统计（当前 API Key）",
            "GET /statistics/by-key/{key_name} - 指定 Key 的统计（仅管理员）",
            "GET /statistics/all-keys - 所有 Key 的统计（仅管理员）",
            "GET /statistics/logs - 调用日志查询",
            "GET /statistics/export - 导出统计数据",
            "POST /statistics/cleanup - 清理旧记录（仅管理员）",
        ]
    }


@router.get("/overview", response_model=UsageStatistics)
async def get_overview(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """获取总体统计概览（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以查看总体统计"
        )
    
    stats_store = get_stats_store(settings.statistics.database_file)
    return stats_store.get_total_stats(start_date, end_date)


@router.get("/my", response_model=UsageStatistics)
async def get_my_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """获取当前 API Key 的统计"""
    stats_store = get_stats_store(settings.statistics.database_file)
    return stats_store.get_stats_by_key(api_key.name, start_date, end_date)


@router.get("/by-key/{key_name}", response_model=UsageStatistics)
async def get_statistics_by_key(
    key_name: str,
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """获取指定 API Key 的统计（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以查看其他 Key 的统计"
        )
    
    stats_store = get_stats_store(settings.statistics.database_file)
    return stats_store.get_stats_by_key(key_name, start_date, end_date)


@router.get("/all-keys", response_model=list[KeyStatistics])
async def get_all_keys_statistics(
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """获取所有 API Key 的统计列表（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以查看所有 Key 的统计"
        )
    
    stats_store = get_stats_store(settings.statistics.database_file)
    return stats_store.get_all_keys_stats(start_date, end_date)


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    key_name: Optional[str] = Query(None, description="API Key 名称"),
    model_name: Optional[str] = Query(None, description="模型名称"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=500, description="每页数量"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """查询调用日志（分页）
    
    - 管理员可以查看所有日志
    - 普通用户只能查看自己的日志
    """
    # 如果不是管理员，强制只查询自己的日志
    if not _is_admin_key(api_key):
        key_name = api_key.name
    
    stats_store = get_stats_store(settings.statistics.database_file)
    logs, total = stats_store.get_logs(
        key_name=key_name,
        model_name=model_name,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    
    return LogsResponse(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/export")
async def export_statistics(
    format: str = Query("csv", description="导出格式: csv 或 json"),
    key_name: Optional[str] = Query(None, description="API Key 名称"),
    start_date: Optional[datetime] = Query(None, description="开始时间"),
    end_date: Optional[datetime] = Query(None, description="结束时间"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """导出统计数据
    
    支持 CSV 和 JSON 格式
    """
    # 如果不是管理员，强制只导出自己的数据
    if not _is_admin_key(api_key):
        key_name = api_key.name
    
    stats_store = get_stats_store(settings.statistics.database_file)
    logs, _ = stats_store.get_logs(
        key_name=key_name,
        start_date=start_date,
        end_date=end_date,
        page=1,
        page_size=10000  # 最多导出 10000 条
    )
    
    if format.lower() == "csv":
        # 导出 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow([
            "ID", "时间", "API Key", "端点", "方法", "状态码",
            "模型", "输入Tokens", "输出Tokens", "总Tokens",
            "费用(元)", "延迟(ms)", "是否流式", "错误信息"
        ])
        
        # 写入数据
        for log in logs:
            writer.writerow([
                log.id,
                log.timestamp.isoformat(),
                log.api_key_name,
                log.endpoint,
                log.method,
                log.status_code,
                log.model_name or "",
                log.input_tokens,
                log.output_tokens,
                log.total_tokens,
                log.cost,
                log.latency_ms,
                "是" if log.is_stream else "否",
                log.error_message or ""
            ])
        
        # 返回 CSV 文件
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    
    elif format.lower() == "json":
        # 导出 JSON
        data = [log.model_dump() for log in logs]
        
        return StreamingResponse(
            iter([json.dumps(data, ensure_ascii=False, indent=2, default=str)]),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
    
    else:
        raise HTTPException(
            status_code=400,
            detail="不支持的导出格式，请使用 'csv' 或 'json'"
        )


@router.post("/cleanup")
async def cleanup_old_records(
    days: int = Query(..., ge=1, description="保留最近 N 天的记录"),
    api_key: ApiKey = Depends(verify_api_key)
):
    """清理旧记录（仅管理员）"""
    if not _is_admin_key(api_key):
        raise HTTPException(
            status_code=403,
            detail="只有管理员可以清理记录"
        )
    
    stats_store = get_stats_store(settings.statistics.database_file)
    deleted_count = stats_store.cleanup_old_records(days)
    
    return {
        "message": f"已清理 {deleted_count} 条旧记录",
        "deleted_count": deleted_count,
        "retention_days": days
    }
