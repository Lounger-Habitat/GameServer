"""统计数据存储（SQLite）"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import threading

from .models import ApiCallLog, UsageStatistics, KeyStatistics


class StatisticsStore:
    """统计数据存储类 - 使用 SQLite 数据库"""
    
    def __init__(self, db_file: str = "statistics.db"):
        self.db_file = Path(db_file)
        self._local = threading.local()  # 线程本地存储
        self._init_db()
    
    @property
    def conn(self) -> sqlite3.Connection:
        """获取线程本地数据库连接"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_file,
                check_same_thread=False
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
                    status_code INTEGER,
                    model_name TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    latency_ms INTEGER,
                    error_message TEXT,
                    is_stream BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引以提升查询性能
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_key_name 
                ON api_call_logs(api_key_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON api_call_logs(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_name 
                ON api_call_logs(model_name)
            """)
            
            conn.commit()
    
    def log_api_call(self, log: ApiCallLog) -> int:
        """记录 API 调用
        
        Args:
            log: API 调用日志
            
        Returns:
            插入记录的 ID
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO api_call_logs (
                timestamp, api_key_name, endpoint, method, status_code,
                model_name, input_tokens, output_tokens, total_tokens,
                cost, latency_ms, error_message, is_stream
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            log.timestamp,
            log.api_key_name,
            log.endpoint,
            log.method,
            log.status_code,
            log.model_name,
            log.input_tokens,
            log.output_tokens,
            log.total_tokens,
            log.cost,
            log.latency_ms,
            log.error_message,
            log.is_stream
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_total_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageStatistics:
        """获取总体统计
        
        Args:
            start_date: 开始时间
            end_date: 结束时间
            
        Returns:
            总体统计数据
        """
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
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
        """, params)
        
        row = cursor.fetchone()
        
        return UsageStatistics(
            total_calls=row["total_calls"] or 0,
            successful_calls=row["successful_calls"] or 0,
            failed_calls=row["failed_calls"] or 0,
            total_input_tokens=row["total_input_tokens"] or 0,
            total_output_tokens=row["total_output_tokens"] or 0,
            total_tokens=row["total_tokens"] or 0,
            total_cost=round(row["total_cost"] or 0.0, 6),
            stream_calls=row["stream_calls"] or 0,
            non_stream_calls=row["non_stream_calls"] or 0
        )
    
    def get_stats_by_key(
        self,
        key_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> UsageStatistics:
        """获取指定 API Key 的统计
        
        Args:
            key_name: API Key 名称
            start_date: 开始时间
            end_date: 结束时间
            
        Returns:
            该 Key 的统计数据
        """
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
        cursor.execute(f"""
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
        """, params)
        
        row = cursor.fetchone()
        
        return UsageStatistics(
            total_calls=row["total_calls"] or 0,
            successful_calls=row["successful_calls"] or 0,
            failed_calls=row["failed_calls"] or 0,
            total_input_tokens=row["total_input_tokens"] or 0,
            total_output_tokens=row["total_output_tokens"] or 0,
            total_tokens=row["total_tokens"] or 0,
            total_cost=round(row["total_cost"] or 0.0, 6),
            stream_calls=row["stream_calls"] or 0,
            non_stream_calls=row["non_stream_calls"] or 0
        )
    
    def get_all_keys_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[KeyStatistics]:
        """获取所有 API Key 的统计列表
        
        Args:
            start_date: 开始时间
            end_date: 结束时间
            
        Returns:
            所有 Key 的统计列表
        """
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
        
        # 查询每个 Key 的统计
        cursor.execute(f"""
            SELECT 
                api_key_name,
                COUNT(*) as total_calls,
                SUM(CASE WHEN status_code >= 200 AND status_code < 300 THEN 1 ELSE 0 END) as successful_calls,
                SUM(CASE WHEN status_code IS NULL OR status_code >= 400 THEN 1 ELSE 0 END) as failed_calls,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                SUM(CASE WHEN is_stream = 1 THEN 1 ELSE 0 END) as stream_calls,
                SUM(CASE WHEN is_stream = 0 THEN 1 ELSE 0 END) as non_stream_calls
            FROM api_call_logs
            {where_sql}
            GROUP BY api_key_name
            ORDER BY total_cost DESC
        """, params)
        
        results = []
        for row in cursor.fetchall():
            results.append(KeyStatistics(
                api_key_name=row["api_key_name"],
                statistics=UsageStatistics(
                    total_calls=row["total_calls"] or 0,
                    successful_calls=row["successful_calls"] or 0,
                    failed_calls=row["failed_calls"] or 0,
                    total_input_tokens=row["total_input_tokens"] or 0,
                    total_output_tokens=row["total_output_tokens"] or 0,
                    total_tokens=row["total_tokens"] or 0,
                    total_cost=round(row["total_cost"] or 0.0, 6),
                    stream_calls=row["stream_calls"] or 0,
                    non_stream_calls=row["non_stream_calls"] or 0
                )
            ))
        
        return results
    
    def get_logs(
        self,
        key_name: Optional[str] = None,
        model_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> tuple[list[ApiCallLog], int]:
        """查询调用日志（分页）
        
        Args:
            key_name: API Key 名称
            model_name: 模型名称
            start_date: 开始时间
            end_date: 结束时间
            page: 页码
            page_size: 每页数量
            
        Returns:
            (日志列表, 总记录数)
        """
        cursor = self.conn.cursor()
        
        # 构建查询条件
        where_clause = []
        params = []
        
        if key_name:
            where_clause.append("api_key_name = ?")
            params.append(key_name)
        if model_name:
            where_clause.append("model_name = ?")
            params.append(model_name)
        if start_date:
            where_clause.append("timestamp >= ?")
            params.append(start_date)
        if end_date:
            where_clause.append("timestamp <= ?")
            params.append(end_date)
        
        where_sql = " WHERE " + " AND ".join(where_clause) if where_clause else ""
        
        # 查询总数
        cursor.execute(f"SELECT COUNT(*) as total FROM api_call_logs{where_sql}", params)
        total = cursor.fetchone()["total"]
        
        # 查询日志（分页）
        offset = (page - 1) * page_size
        cursor.execute(f"""
            SELECT * FROM api_call_logs
            {where_sql}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
        """, params + [page_size, offset])
        
        logs = []
        for row in cursor.fetchall():
            logs.append(ApiCallLog(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                api_key_name=row["api_key_name"],
                endpoint=row["endpoint"],
                method=row["method"],
                status_code=row["status_code"],
                model_name=row["model_name"],
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                total_tokens=row["total_tokens"],
                cost=row["cost"],
                latency_ms=row["latency_ms"],
                error_message=row["error_message"],
                is_stream=bool(row["is_stream"])
            ))
        
        return logs, total
    
    def cleanup_old_records(self, days: int) -> int:
        """清理旧记录
        
        Args:
            days: 保留最近 N 天的记录
            
        Returns:
            删除的记录数
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM api_call_logs
            WHERE timestamp < datetime('now', '-' || ? || ' days')
        """, (days,))
        self.conn.commit()
        return cursor.rowcount


# 全局存储实例
_stats_store: Optional[StatisticsStore] = None


def get_stats_store(db_file: str = "statistics.db") -> StatisticsStore:
    """获取全局统计存储实例"""
    global _stats_store
    if _stats_store is None:
        _stats_store = StatisticsStore(db_file)
    return _stats_store
