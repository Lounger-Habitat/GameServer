"""
定价管理器
处理美元到人民币的转换和模型价格管理
"""

import sqlite3
from datetime import datetime, time, timedelta
from typing import Optional, Tuple, Dict, List
from pathlib import Path
import threading

from .models import ModelPricing, TimePriceConfig, Currency
from .model_normalizer import get_model_normalizer


class ModelPricingManager:
    """模型定价管理器"""

    # 汇率：1美元 = 8人民币
    USD_TO_CNY = 8.0

    def __init__(self, db_file: str = "statistics.db"):
        self.db_file = Path(db_file)
        self._local = threading.local()
        self._normalizer = get_model_normalizer()
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

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            # 创建模型定价表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_full_id TEXT NOT NULL,
                    provider TEXT,
                    alias TEXT,
                    base_input_price_usd REAL NOT NULL,
                    base_output_price_usd REAL NOT NULL,
                    base_cache_input_price_usd REAL DEFAULT 0.0,
                    currency TEXT DEFAULT 'USD',
                    effective_from DATETIME NOT NULL,
                    effective_to DATETIME,
                    enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(model_full_id, effective_from)
                )
            """)

            # 创建分时价格表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_full_id TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    input_price_usd REAL NOT NULL,
                    output_price_usd REAL NOT NULL,
                    cache_input_price_usd REAL DEFAULT 0.0,
                    enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (model_full_id) REFERENCES model_pricing(model_full_id) ON DELETE CASCADE
                )
            """)

            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_pricing_full_id
                ON model_pricing(model_full_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_pricing_effective
                ON model_pricing(effective_from, effective_to)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_time_prices_model
                ON time_prices(model_full_id)
            """)

            conn.commit()

        # 初始化默认定价
        self._initialize_default_pricing()

    def _initialize_default_pricing(self):
        """从 supported_models.yaml 初始化默认定价"""
        normalizer = get_model_normalizer()
        all_models = normalizer.get_all_models()

        for model_full_id, config in all_models.items():
            price_info = config.get("price", {})
            if not price_info:
                continue

            # 获取价格（美元/百万token）
            input_price_usd = price_info.get("input", 0.0)
            output_price_usd = price_info.get("output", 0.0)
            cache_input_price_usd = price_info.get("cache_input", 0.0)

            # 检查是否已存在定价
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM model_pricing
                WHERE model_full_id = ? AND enabled = 1
            """,
                (model_full_id,),
            )

            if cursor.fetchone()["count"] == 0:
                # 创建默认定价
                pricing = ModelPricing(
                    model_name=model_full_id,
                    base_input_price_per_million=input_price_usd * self.USD_TO_CNY,
                    base_output_price_per_million=output_price_usd * self.USD_TO_CNY,
                    base_cache_input_price_per_million=cache_input_price_usd
                    * self.USD_TO_CNY,
                    currency=Currency.CNY,
                    effective_from=datetime.now(),
                    enabled=True,
                )
                self.save_model_pricing(pricing)

    def save_model_pricing(self, pricing: ModelPricing) -> int:
        """保存模型定价配置"""
        cursor = self.conn.cursor()

        # 将人民币价格转换为美元存储
        base_input_price_usd = pricing.base_input_price_per_million / self.USD_TO_CNY
        base_output_price_usd = pricing.base_output_price_per_million / self.USD_TO_CNY
        base_cache_input_price_usd = (
            pricing.base_cache_input_price_per_million / self.USD_TO_CNY
        )

        # 规范化模型名称
        model_full_id, provider, alias = self._normalizer.normalize(pricing.model_name)

        cursor.execute(
            """
            INSERT INTO model_pricing (
                model_full_id, provider, alias,
                base_input_price_usd, base_output_price_usd, base_cache_input_price_usd,
                currency, effective_from, effective_to, enabled
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                model_full_id or pricing.model_name,
                provider,
                alias,
                base_input_price_usd,
                base_output_price_usd,
                base_cache_input_price_usd,
                pricing.currency.value,
                pricing.effective_from,
                pricing.effective_to,
                pricing.enabled,
            ),
        )

        pricing_id = cursor.lastrowid

        # 保存分时价格
        for time_price in pricing.time_prices:
            cursor.execute(
                """
                INSERT INTO time_prices (
                    model_full_id, start_time, end_time,
                    input_price_usd, output_price_usd, cache_input_price_usd,
                    enabled
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    model_full_id or pricing.model_name,
                    time_price.start_time.isoformat(),
                    time_price.end_time.isoformat(),
                    time_price.input_price_per_million / self.USD_TO_CNY,
                    time_price.output_price_per_million / self.USD_TO_CNY,
                    time_price.cache_input_price_per_million / self.USD_TO_CNY,
                    time_price.enabled,
                ),
            )

        self.conn.commit()
        return pricing_id

    def get_model_pricing(
        self, model_full_id: str, timestamp: Optional[datetime] = None
    ) -> Optional[ModelPricing]:
        """获取指定时间点的模型定价配置"""
        if timestamp is None:
            timestamp = datetime.now()

        cursor = self.conn.cursor()

        # 规范化模型名称
        normalized_id, provider, alias = self._normalizer.normalize(model_full_id)
        query_id = normalized_id or model_full_id

        # print(f"\n🔍 get_model_pricing 调试:")
        # print(f"  原始模型ID: {model_full_id}")
        # print(f"  规范化后ID: {query_id}")
        # print(f"  查询时间: {timestamp}")

        # 先检查数据库是否有这个模型
        cursor.execute(
            "SELECT COUNT(*) as count FROM model_pricing WHERE model_full_id = ?",
            (query_id,),
        )
        count_row = cursor.fetchone()
        print(f"  数据库中模型数量: {count_row['count']}")

        # 查询模型定价
        cursor.execute(
            """
            SELECT * FROM model_pricing
            WHERE model_full_id = ? AND enabled = 1
            AND effective_from <= ? AND (effective_to IS NULL OR effective_to >= ?)
            ORDER BY effective_from DESC
            LIMIT 1
        """,
            (query_id, timestamp, timestamp),
        )

        row = cursor.fetchone()
        if not row:
            print(f"  ❌ 未找到定价配置")

            # 调试：查看数据库中的所有定价
            cursor.execute(
                "SELECT model_full_id, effective_from, effective_to FROM model_pricing WHERE model_full_id LIKE ?",
                (f"%{query_id.split('/')[-1]}%",),
            )
            all_rows = cursor.fetchall()
            if all_rows:
                print(f"  数据库中的相关记录:")
                for r in all_rows:
                    print(
                        f"    {r['model_full_id']}: {r['effective_from']} 到 {r['effective_to']}"
                    )
            return None

        print(f"  ✅ 找到定价配置: {row['model_full_id']}")
        print(f"    生效时间: {row['effective_from']} 到 {row['effective_to']}")
        print(
            f"    输入价格: ${row['base_input_price_usd']}, 输出价格: ${row['base_output_price_usd']}"
        )

        # 查询分时价格
        cursor.execute(
            """
            SELECT * FROM time_prices
            WHERE model_full_id = ? AND enabled = 1
            ORDER BY start_time
        """,
            (query_id,),
        )

        time_prices = []
        for time_row in cursor.fetchall():
            start_time_str = time_row["start_time"]
            end_time_str = time_row["end_time"]

            # 将字符串转换为 time 对象
            start_time = (
                time.fromisoformat(start_time_str)
                if ":" in start_time_str
                else time.fromisoformat(f"{start_time_str}:00")
            )
            end_time = (
                time.fromisoformat(end_time_str)
                if ":" in end_time_str
                else time.fromisoformat(f"{end_time_str}:00")
            )

            # 将美元价格转换为人民币
            input_price_cny = time_row["input_price_usd"] * self.USD_TO_CNY
            output_price_cny = time_row["output_price_usd"] * self.USD_TO_CNY
            cache_input_price_cny = time_row["cache_input_price_usd"] * self.USD_TO_CNY

            time_prices.append(
                TimePriceConfig(
                    start_time=start_time,
                    end_time=end_time,
                    input_price_per_million=input_price_cny,
                    output_price_per_million=output_price_cny,
                    cache_input_price_per_million=cache_input_price_cny,
                    enabled=bool(time_row["enabled"]),
                )
            )

        # 将美元价格转换为人民币
        base_input_price_cny = row["base_input_price_usd"] * self.USD_TO_CNY
        base_output_price_cny = row["base_output_price_usd"] * self.USD_TO_CNY
        base_cache_input_price_cny = row["base_cache_input_price_usd"] * self.USD_TO_CNY

        return ModelPricing(
            model_name=row["model_full_id"],
            base_input_price_per_million=base_input_price_cny,
            base_output_price_per_million=base_output_price_cny,
            base_cache_input_price_per_million=base_cache_input_price_cny,
            currency=Currency(row["currency"]),
            effective_from=datetime.fromisoformat(row["effective_from"]),
            effective_to=datetime.fromisoformat(row["effective_to"])
            if row["effective_to"]
            else None,
            enabled=bool(row["enabled"]),
            time_prices=time_prices,
        )

    def get_price_at_time(
        self, model_full_id: str, timestamp: Optional[datetime] = None
    ) -> Tuple[float, float, float]:
        """获取指定时间点的价格（人民币/百万token）"""
        if timestamp is None:
            timestamp = datetime.now()

        pricing = self.get_model_pricing(model_full_id, timestamp)
        if not pricing:
            # 默认价格：1元/百万token
            print(
                f"⚠️  定价警告: 未找到模型 {model_full_id} 的定价配置，使用默认价格 1.0"
            )

            # 调试：检查数据库中的定价
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT model_full_id FROM model_pricing WHERE model_full_id LIKE ?",
                (f"%{model_full_id.split('/')[-1]}%",),
            )
            rows = cursor.fetchall()
            if rows:
                print(f"  数据库中类似模型: {[r[0] for r in rows]}")
            else:
                print(f"  数据库中没有类似模型")

            return 1.0, 1.0, 0.0

        # 获取时间部分
        time_of_day = timestamp.time()

        # 查找适用的分时价格
        for time_price in pricing.time_prices:
            if time_price.enabled:
                # 处理跨夜时间
                if time_price.start_time <= time_price.end_time:
                    # 正常时间范围
                    if time_price.start_time <= time_of_day <= time_price.end_time:
                        return (
                            time_price.input_price_per_million,
                            time_price.output_price_per_million,
                            time_price.cache_input_price_per_million,
                        )
                else:
                    # 跨夜时间范围（例如 22:00-06:00）
                    if (
                        time_of_day >= time_price.start_time
                        or time_of_day <= time_price.end_time
                    ):
                        return (
                            time_price.input_price_per_million,
                            time_price.output_price_per_million,
                            time_price.cache_input_price_per_million,
                        )

        # 使用基础价格
        return (
            pricing.base_input_price_per_million,
            pricing.base_output_price_per_million,
            pricing.base_cache_input_price_per_million,
        )

    def get_all_pricing(self) -> List[Dict]:
        """获取所有定价配置"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT mp.*, COUNT(tp.id) as time_price_count
            FROM model_pricing mp
            LEFT JOIN time_prices tp ON mp.model_full_id = tp.model_full_id
            WHERE mp.enabled = 1
            GROUP BY mp.id
            ORDER BY mp.model_full_id, mp.effective_from DESC
        """)

        result = []
        for row in cursor.fetchall():
            # 将美元价格转换为人民币显示
            base_input_price_cny = row["base_input_price_usd"] * self.USD_TO_CNY
            base_output_price_cny = row["base_output_price_usd"] * self.USD_TO_CNY
            base_cache_input_price_cny = (
                row["base_cache_input_price_usd"] * self.USD_TO_CNY
            )

            result.append(
                {
                    "id": row["id"],
                    "model_full_id": row["model_full_id"],
                    "provider": row["provider"],
                    "alias": row["alias"],
                    "base_input_price_cny": base_input_price_cny,
                    "base_output_price_cny": base_output_price_cny,
                    "base_cache_input_price_cny": base_cache_input_price_cny,
                    "currency": row["currency"],
                    "effective_from": row["effective_from"],
                    "effective_to": row["effective_to"],
                    "enabled": bool(row["enabled"]),
                    "time_price_count": row["time_price_count"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
            )

        return result


# 单例实例
_pricing_manager: Optional[ModelPricingManager] = None


def get_pricing_manager(db_file: str = "statistics.db") -> ModelPricingManager:
    """获取定价管理器单例"""
    global _pricing_manager
    if _pricing_manager is None:
        _pricing_manager = ModelPricingManager(db_file)
    return _pricing_manager


def calculate_cost(
    model_full_id: str,
    input_tokens: int,
    output_tokens: int,
    cache_input_tokens: int = 0,
    timestamp: Optional[datetime] = None,
) -> Tuple[float, float, float, float]:
    """计算 API 调用费用（版本）"""
    MILLIONS = 1_000_000

    # 获取价格（人民币/百万token）
    pricing_manager = get_pricing_manager()
    input_price, output_price, cache_input_price = pricing_manager.get_price_at_time(
        model_full_id, timestamp
    )

    # 计算总费用
    cost = (
        (input_tokens / MILLIONS) * input_price
        + (output_tokens / MILLIONS) * output_price
        + (cache_input_tokens / MILLIONS) * cache_input_price
    )

    return round(cost, 6), input_price, output_price, cache_input_price
