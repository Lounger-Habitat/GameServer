"""
统计数据存储 （SQLite）
全新的存储系统，解决脏数据问题
"""

import sqlite3
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import threading
import json

from .models import (
    ApiCallLog,
    UsageStatistics,
    KeyStatistics,
    ModelStatistics,
    KeyModelStatistics,
    TimeRangeStatistics,
    StatisticsQuery,
    ModelPricing,
    TimePriceConfig,
    ModelUsageResponse,
    KeyUsageResponse,
    APIMethod,
    Currency,
)
from .pricing import get_pricing_manager, calculate_cost
from .model_normalizer import get_model_normalizer


class StatisticsStore:
    """统计数据存储类 - 使用 SQLite 数据库"""

    def __init__(self, db_file: str = "statistics.db"):
        self.db_file = Path(db_file)
        self._local = threading.local()  # 线程本地存储
        self._normalizer = get_model_normalizer()
        self._pricing_manager = get_pricing_manager(db_file)
        self._init_db()

    @property
    def conn(self) -> sqlite3.Connection:
        """获取线程本地数据库连接"""
        if not hasattr(self._local, "connection"):
            self._local.connection = sqlite3.connect(
                self.db_file, check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection

    def _init_db(self) -> None:
        """初始化数据库表"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # 创建调用日志表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_call_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    api_key_name TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,

                    -- 模型信息（规范化后）
                    model_full_id TEXT,
                    model_provider TEXT,
                    model_alias TEXT,

                    -- Token 信息
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_input_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,

                    -- 费用信息（人民币）
                    cost REAL DEFAULT 0.0,
                    input_price_per_million REAL DEFAULT 0.0,
                    output_price_per_million REAL DEFAULT 0.0,
                    cache_input_price_per_million REAL DEFAULT 0.0,
                    currency TEXT DEFAULT 'CNY',

                    -- 响应信息
                    status_code INTEGER,
                    latency_ms INTEGER,
                    error_message TEXT,
                    is_stream BOOLEAN DEFAULT 0,
                    request_id TEXT,

                    -- 元数据
                    client_ip TEXT,
                    user_agent TEXT,
                    tags TEXT DEFAULT '{}',

                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_call_logs_api_key
                ON api_call_logs(api_key_name)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_call_logs_timestamp
                ON api_call_logs(timestamp)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_call_logs_model
                ON api_call_logs(model_full_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_call_logs_endpoint
                ON api_call_logs(endpoint)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_call_logs_status
                ON api_call_logs(status_code)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_call_logs_composite
                ON api_call_logs(timestamp, api_key_name, model_full_id)
            """)

            conn.commit()

    def log_api_call(self, log: ApiCallLog) -> int:
        """记录 API 调用"""
        cursor = self.conn.cursor()

        # 规范化模型名称
        model_full_id, model_provider, model_alias = self._normalizer.normalize(
            log.model_full_id or log.model_alias
        )

        # 确保费用已计算
        if log.cost == 0 and (
            log.input_tokens > 0 or log.output_tokens > 0 or log.cache_input_tokens > 0
        ):
            if model_full_id:
                cost, input_price, output_price, cache_input_price = calculate_cost(
                    model_full_id,
                    log.input_tokens,
                    log.output_tokens,
                    log.cache_input_tokens,
                    log.timestamp,
                )
                log.cost = cost
                log.input_price_per_million = input_price
                log.output_price_per_million = output_price
                log.cache_input_price_per_million = cache_input_price

        # 序列化标签
        tags_json = json.dumps(log.tags) if log.tags else "{}"

        cursor.execute(
            """
            INSERT INTO api_call_logs (
                timestamp, api_key_name, endpoint, method,
                model_full_id, model_provider, model_alias,
                input_tokens, output_tokens, cache_input_tokens, total_tokens,
                cost, input_price_per_million, output_price_per_million,
                cache_input_price_per_million, currency,
                status_code, latency_ms, error_message, is_stream, request_id,
                client_ip, user_agent, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                log.timestamp,
                log.api_key_name,
                log.endpoint,
                log.method.value,
                model_full_id,
                model_provider,
                model_alias,
                log.input_tokens,
                log.output_tokens,
                log.cache_input_tokens,
                log.total_tokens,
                log.cost,
                log.input_price_per_million,
                log.output_price_per_million,
                log.cache_input_price_per_million,
                log.currency.value,
                log.status_code,
                log.latency_ms,
                log.error_message,
                log.is_stream,
                log.request_id,
                log.client_ip,
                log.user_agent,
                tags_json,
            ),
        )

        log_id = cursor.lastrowid
        self.conn.commit()
        return log_id

    def get_total_stats(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> UsageStatistics:
        """获取总体统计"""
        cursor = self.conn.cursor()

        # 构建查询条件
        where_clause = []
        params = []

        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""

        # 查询统计数据
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cache_input_tokens) as total_cache_input_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(latency_ms) as total_latency,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
        """,
            params,
        )

        row = cursor.fetchone()

        total_calls = row["total_calls"] or 0
        successful_calls = row["successful_calls"] or 0
        total_input_tokens = row["total_input_tokens"] or 0
        total_output_tokens = row["total_output_tokens"] or 0
        total_cache_input_tokens = row["total_cache_input_tokens"] or 0
        total_tokens = row["total_tokens"] or 0
        total_cost = row["total_cost"] or 0.0
        total_latency = row["total_latency"] or 0

        avg_input_tokens = total_input_tokens / total_calls if total_calls > 0 else 0
        avg_output_tokens = total_output_tokens / total_calls if total_calls > 0 else 0
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
        avg_latency_ms = total_latency / total_calls if total_calls > 0 else 0

        return UsageStatistics(
            total_calls=total_calls,
            successful_calls=successful_calls,
            failed_calls=row["failed_calls"] or 0,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cache_input_tokens=total_cache_input_tokens,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 6),
            stream_calls=row["stream_calls"] or 0,
            non_stream_calls=row["non_stream_calls"] or 0,
            avg_input_tokens=round(avg_input_tokens, 2),
            avg_output_tokens=round(avg_output_tokens, 2),
            avg_cost_per_call=round(avg_cost_per_call, 6),
            avg_latency_ms=round(avg_latency_ms, 2),
        )

    def get_stats_by_key(
        self,
        key_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> UsageStatistics:
        """获取指定 API Key 的统计"""
        cursor = self.conn.cursor()

        # 构建查询条件
        where_clause = ["api_key_name = ?"]
        params = [key_name]

        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clause)

        # 查询统计数据
        cursor.execute(
            f"""
            SELECT
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cache_input_tokens) as total_cache_input_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(latency_ms) as total_latency,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
        """,
            params,
        )

        row = cursor.fetchone()

        if not row or row["total_calls"] is None:
            return UsageStatistics()

        total_calls = row["total_calls"] or 0
        total_input_tokens = row["total_input_tokens"] or 0
        total_output_tokens = row["total_output_tokens"] or 0
        total_cache_input_tokens = row["total_cache_input_tokens"] or 0
        total_cost = row["total_cost"] or 0.0
        total_latency = row["total_latency"] or 0

        avg_input_tokens = total_input_tokens / total_calls if total_calls > 0 else 0
        avg_output_tokens = total_output_tokens / total_calls if total_calls > 0 else 0
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
        avg_latency_ms = total_latency / total_calls if total_calls > 0 else 0

        return UsageStatistics(
            total_calls=total_calls,
            successful_calls=row["successful_calls"] or 0,
            failed_calls=row["failed_calls"] or 0,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_cache_input_tokens=total_cache_input_tokens,
            total_tokens=row["total_tokens"] or 0,
            total_cost=round(total_cost, 6),
            stream_calls=row["stream_calls"] or 0,
            non_stream_calls=row["non_stream_calls"] or 0,
            avg_input_tokens=round(avg_input_tokens, 2),
            avg_output_tokens=round(avg_output_tokens, 2),
            avg_cost_per_call=round(avg_cost_per_call, 6),
            avg_latency_ms=round(avg_latency_ms, 2),
        )

    def get_all_keys_stats(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[KeyStatistics]:
        """获取所有 API Key 的统计列表"""
        cursor = self.conn.cursor()

        # 构建查询条件
        where_clause = []
        params = []

        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""

        # 查询所有 Key 的统计
        cursor.execute(
            f"""
            SELECT
                api_key_name,
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cache_input_tokens) as total_cache_input_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(latency_ms) as total_latency,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
            GROUP BY api_key_name
            ORDER BY total_cost DESC, total_calls DESC
        """,
            params,
        )

        results = []
        for row in cursor.fetchall():
            total_calls = row["total_calls"] or 0
            total_input_tokens = row["total_input_tokens"] or 0
            total_output_tokens = row["total_output_tokens"] or 0
            total_cost = row["total_cost"] or 0.0
            total_latency = row["total_latency"] or 0

            avg_input_tokens = (
                total_input_tokens / total_calls if total_calls > 0 else 0
            )
            avg_output_tokens = (
                total_output_tokens / total_calls if total_calls > 0 else 0
            )
            avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
            avg_latency_ms = total_latency / total_calls if total_calls > 0 else 0

            stats = UsageStatistics(
                total_calls=total_calls,
                successful_calls=row["successful_calls"] or 0,
                failed_calls=row["failed_calls"] or 0,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_cache_input_tokens=row["total_cache_input_tokens"] or 0,
                total_tokens=row["total_tokens"] or 0,
                total_cost=round(total_cost, 6),
                stream_calls=row["stream_calls"] or 0,
                non_stream_calls=row["non_stream_calls"] or 0,
                avg_input_tokens=round(avg_input_tokens, 2),
                avg_output_tokens=round(avg_output_tokens, 2),
                avg_cost_per_call=round(avg_cost_per_call, 6),
                avg_latency_ms=round(avg_latency_ms, 2),
            )

            results.append(
                KeyStatistics(api_key_name=row["api_key_name"], statistics=stats)
            )

        return results

    def get_model_usage_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        api_key_name: Optional[str] = None,
    ) -> List[ModelStatistics]:
        """获取所有模型的统计"""
        cursor = self.conn.cursor()

        # 构建查询条件
        where_clause = []
        params = []

        if api_key_name:
            where_clause.append("api_key_name = ?")
            params.append(api_key_name)

        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""

        # 查询所有模型的统计
        cursor.execute(
            f"""
            SELECT
                model_full_id,
                model_provider,
                model_alias,
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cache_input_tokens) as total_cache_input_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(latency_ms) as total_latency,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
            GROUP BY model_full_id
            HAVING model_full_id IS NOT NULL
            ORDER BY total_cost DESC, total_calls DESC
        """,
            params,
        )

        results = []
        for row in cursor.fetchall():
            total_calls = row["total_calls"] or 0
            total_input_tokens = row["total_input_tokens"] or 0
            total_output_tokens = row["total_output_tokens"] or 0
            total_cost = row["total_cost"] or 0.0
            total_latency = row["total_latency"] or 0

            avg_input_tokens = (
                total_input_tokens / total_calls if total_calls > 0 else 0
            )
            avg_output_tokens = (
                total_output_tokens / total_calls if total_calls > 0 else 0
            )
            avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
            avg_latency_ms = total_latency / total_calls if total_calls > 0 else 0

            stats = UsageStatistics(
                total_calls=total_calls,
                successful_calls=row["successful_calls"] or 0,
                failed_calls=row["failed_calls"] or 0,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_cache_input_tokens=row["total_cache_input_tokens"] or 0,
                total_tokens=row["total_tokens"] or 0,
                total_cost=round(total_cost, 6),
                stream_calls=row["stream_calls"] or 0,
                non_stream_calls=row["non_stream_calls"] or 0,
                avg_input_tokens=round(avg_input_tokens, 2),
                avg_output_tokens=round(avg_output_tokens, 2),
                avg_cost_per_call=round(avg_cost_per_call, 6),
                avg_latency_ms=round(avg_latency_ms, 2),
            )

            results.append(
                ModelStatistics(
                    model_full_id=row["model_full_id"],
                    model_alias=row["model_alias"],
                    model_provider=row["model_provider"],
                    statistics=stats,
                )
            )

        return results

    def get_logs(
        self,
        key_name: Optional[str] = None,
        model_full_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[List[ApiCallLog], int]:
        """查询调用日志（分页）"""
        cursor = self.conn.cursor()

        # 构建查询条件
        where_clause = []
        params = []

        if key_name:
            where_clause.append("api_key_name = ?")
            params.append(key_name)

        if model_full_id:
            where_clause.append("model_full_id = ?")
            params.append(model_full_id)

        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date)

        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date)

        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""

        # 查询总记录数
        cursor.execute(
            f"""
            SELECT COUNT(*) as total
            FROM api_call_logs
            {where_sql}
        """,
            params,
        )
        total = cursor.fetchone()["total"] or 0

        # 查询分页数据
        offset = (page - 1) * page_size
        cursor.execute(
            f"""
            SELECT *
            FROM api_call_logs
            {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """,
            params + [page_size, offset],
        )

        logs = []
        for row in cursor.fetchall():
            # 解析标签
            tags = json.loads(row["tags"]) if row["tags"] else {}

            logs.append(
                ApiCallLog(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    api_key_name=row["api_key_name"],
                    endpoint=row["endpoint"],
                    method=APIMethod(row["method"]),
                    model_full_id=row["model_full_id"],
                    model_provider=row["model_provider"],
                    model_alias=row["model_alias"],
                    input_tokens=row["input_tokens"] or 0,
                    output_tokens=row["output_tokens"] or 0,
                    cache_input_tokens=row["cache_input_tokens"] or 0,
                    total_tokens=row["total_tokens"] or 0,
                    cost=row["cost"] or 0.0,
                    input_price_per_million=row["input_price_per_million"] or 0.0,
                    output_price_per_million=row["output_price_per_million"] or 0.0,
                    cache_input_price_per_million=row["cache_input_price_per_million"]
                    or 0.0,
                    currency=Currency(row["currency"])
                    if row["currency"]
                    else Currency.CNY,
                    status_code=row["status_code"],
                    latency_ms=row["latency_ms"],
                    error_message=row["error_message"],
                    is_stream=bool(row["is_stream"]),
                    request_id=row["request_id"],
                    client_ip=row["client_ip"],
                    user_agent=row["user_agent"],
                    tags=tags,
                )
            )

        return logs, total

    def get_detailed_usage_stats(self, query: StatisticsQuery) -> dict:
        """获取详细使用统计（支持多维度分组）"""
        cursor = self.conn.cursor()

        # 构建查询条件
        where_clause = []
        params = []

        if query.api_key_name:
            where_clause.append("api_key_name = ?")
            params.append(query.api_key_name)

        if query.model_full_id:
            where_clause.append("model_full_id = ?")
            params.append(query.model_full_id)

        if query.start_date:
            where_clause.append("timestamp >= ?")
            params.append(query.start_date)

        if query.end_date:
            where_clause.append("timestamp <= ?")
            params.append(query.end_date)

        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""

        # 构建分组字段
        if query.group_by == "key":
            group_field = "api_key_name"
            select_fields = "api_key_name as group_field"
        elif query.group_by == "model":
            group_field = "model_full_id"
            select_fields = "model_full_id as group_field"
        elif query.group_by == "key_model":
            group_field = "api_key_name, model_full_id"
            select_fields = "api_key_name || '|' || model_full_id as group_field"
        elif query.group_by == "time":
            # 时间分组
            if query.time_granularity == "year":
                date_format = "%Y"
            elif query.time_granularity == "month":
                date_format = "%Y-%m"
            elif query.time_granularity == "day":
                date_format = "%Y-%m-%d"
            elif query.time_granularity == "hour":
                date_format = "%Y-%m-%d %H"
            elif query.time_granularity == "minute":
                date_format = "%Y-%m-%d %H:%M"
            else:
                date_format = "%Y-%m-%d"

            group_field = f"strftime('{date_format}', timestamp)"
            select_fields = f"strftime('{date_format}', timestamp) as group_field"
        else:
            group_field = "api_key_name"
            select_fields = "api_key_name as group_field"

        # 查询统计数据
        cursor.execute(
            f"""
            SELECT
                {select_fields},
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(cache_input_tokens) as total_cache_input_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(latency_ms) as total_latency,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
            GROUP BY {group_field}
            ORDER BY total_cost DESC, total_calls DESC
        """,
            params,
        )

        results = []
        for row in cursor.fetchall():
            total_calls = row["total_calls"] or 0
            total_input_tokens = row["total_input_tokens"] or 0
            total_output_tokens = row["total_output_tokens"] or 0
            total_cost = row["total_cost"] or 0.0
            total_latency = row["total_latency"] or 0

            avg_input_tokens = (
                total_input_tokens / total_calls if total_calls > 0 else 0
            )
            avg_output_tokens = (
                total_output_tokens / total_calls if total_calls > 0 else 0
            )
            avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0
            avg_latency_ms = total_latency / total_calls if total_calls > 0 else 0

            stats = UsageStatistics(
                total_calls=total_calls,
                successful_calls=row["successful_calls"] or 0,
                failed_calls=row["failed_calls"] or 0,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_cache_input_tokens=row["total_cache_input_tokens"] or 0,
                total_tokens=row["total_tokens"] or 0,
                total_cost=round(total_cost, 6),
                stream_calls=row["stream_calls"] or 0,
                non_stream_calls=row["non_stream_calls"] or 0,
                avg_input_tokens=round(avg_input_tokens, 2),
                avg_output_tokens=round(avg_output_tokens, 2),
                avg_cost_per_call=round(avg_cost_per_call, 6),
                avg_latency_ms=round(avg_latency_ms, 2),
            )

            group_field_value = row["group_field"]
            if query.group_by == "key":
                results.append(
                    {"api_key_name": group_field_value, "statistics": stats.dict()}
                )
            elif query.group_by == "model":
                results.append(
                    {"model_full_id": group_field_value, "statistics": stats.dict()}
                )
            elif query.group_by == "key_model":
                key, model = group_field_value.split("|", 1)
                results.append(
                    {
                        "api_key_name": key,
                        "model_full_id": model,
                        "statistics": stats.dict(),
                    }
                )
            elif query.group_by == "time":
                results.append(
                    {"time_period": group_field_value, "statistics": stats.dict()}
                )

        return {"results": results, "query": query.dict()}

    def cleanup_old_records(self, days: int) -> int:
        """清理旧记录"""
        cutoff_date = datetime.now() - timedelta(days=days)

        cursor = self.conn.cursor()
        cursor.execute(
            """
            DELETE FROM api_call_logs
            WHERE timestamp < ?
        """,
            (cutoff_date,),
        )

        deleted_count = cursor.rowcount
        self.conn.commit()
        return deleted_count


# 单例实例
_stats_store: Optional[StatisticsStore] = None


def get_stats_store(db_file: str = "statistics.db") -> StatisticsStore:
    """获取统计存储单例"""
    global _stats_store
    if _stats_store is None:
        _stats_store = StatisticsStore(db_file)
    return _stats_store
