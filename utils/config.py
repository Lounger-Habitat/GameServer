"""配置管理模块"""
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class ModulesConfig(BaseModel):
    """模块启用配置"""
    enable_openai_api: bool = True
    enable_response_api: bool = True
    enable_menglong_api: bool = True
    enable_agent_api: bool = True
    enable_anthropic_api: bool = True
    enable_websocket: bool = True


class CORSConfig(BaseModel):
    """CORS 配置"""
    enabled: bool = True
    allow_origins: List[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"


class AuthConfig(BaseModel):
    """鉴权配置"""
    enabled: bool = True
    keys_file: str = "api_keys.json"
    allow_no_auth_paths: List[str] = ["/health", "/docs", "/redoc", "/openapi.json", "/auth"]


class StatisticsConfig(BaseModel):
    """统计模块配置"""
    enabled: bool = True
    database_file: str = "statistics.db"
    retention_days: int = 0  # 0 表示永久保留
    async_logging: bool = True


class ProviderConfig(BaseModel):
    """LLM 提供者配置"""
    enabled: bool = True
    priority: int = 1
    config: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[float] = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0


class ModelMapping(BaseModel):
    """模型映射配置"""
    source_model: str
    target_provider: str
    target_model: str
    enabled: bool = True


class LLMConfig(BaseModel):
    """LLM 配置"""
    default_provider: str = "menglong"
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    model_mappings: List[ModelMapping] = Field(default_factory=list)
    cache_enabled: bool = False
    cache_ttl: int = 300
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    enable_health_check: bool = True
    health_check_interval: int = 30


class Settings(BaseSettings):
    """应用配置"""
    server: ServerConfig = ServerConfig()
    modules: ModulesConfig = ModulesConfig()
    cors: CORSConfig = CORSConfig()
    logging: LoggingConfig = LoggingConfig()
    auth: AuthConfig = AuthConfig()
    statistics: StatisticsConfig = StatisticsConfig()
    llm: LLMConfig = LLMConfig()

    @classmethod
    def from_yaml(cls, config_path: str = "config.yaml") -> "Settings":
        """从 YAML 文件加载配置"""
        config_file = Path(config_path)
        if not config_file.exists():
            print(f"⚠️  配置文件 {config_path} 不存在，使用默认配置")
            return cls()
        
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)


# 全局配置实例
settings = Settings.from_yaml()
