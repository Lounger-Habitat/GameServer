"""Monitor API 端点 - 符合 API 规范"""
import logging
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import time

from .hub import message_router
from .connection import ClientRole, SessionState
from .errors import (
    ClientNotFoundError,
    EnvironmentNotFoundError,
    InvalidParameterError
)


logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/monitor", tags=["monitor"])


@router.get("/stats")
async def get_system_stats():
    """
    获取系统统计信息
    
    Returns:
        系统整体统计，包括客户端数量、环境数量、运行时间等
    """
    try:
        stats = message_router.connection_manager.get_statistics()
        
        return {
            "total_clients": stats["total_sessions"],
            "clients_by_role": {
                "agent": stats["by_role"]["agents"],
                "environment": stats["by_role"]["environments"],
                "human": stats["by_role"]["humans"],
                "monitor": stats["by_role"]["monitors"],
                "hub_monitor": stats["by_role"]["hub_monitors"],
            },
            "total_environments": len(stats["environments"]["details"]),
            "environments": stats["environments"]["details"],
            "uptime": message_router.get_uptime(),
            "message_rate": 0.0  # TODO: 实现消息速率统计
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients")
async def list_clients(
    role: Optional[str] = Query(None, description="按角色过滤 (agent/environment/human/monitor/hub_monitor)"),
    state: Optional[str] = Query(None, description="按状态过滤 (connected/in_env/disconnected)"),
    env_id: Optional[str] = Query(None, description="按环境过滤")
):
    """
    获取客户端列表（支持过滤）
    
    Args:
        role: 按角色过滤
        state: 按状态过滤
        env_id: 按环境过滤
    
    Returns:
        客户端列表及总数
    """
    try:
        # 验证参数
        if role and role not in ["agent", "environment", "human", "monitor", "hub_monitor"]:
            raise InvalidParameterError("role", f"Invalid role: {role}")
        
        if state and state not in ["connected", "in_env", "disconnected"]:
            raise InvalidParameterError("state", f"Invalid state: {state}")
        
        # 获取所有客户端
        all_clients = []
        for r in ClientRole:
            sessions = message_router.connection_manager.get_sessions_by_role(r)
            for session in sessions:
                all_clients.append(session.to_dict())
        
        # 应用过滤
        filtered_clients = all_clients
        
        if role:
            filtered_clients = [c for c in filtered_clients if c['role'] == role]
        
        if state:
            filtered_clients = [c for c in filtered_clients if c['state'] == state]
        
        if env_id:
            filtered_clients = [c for c in filtered_clients if c['current_env'] == env_id]
        
        return {
            "total": len(filtered_clients),
            "clients": filtered_clients
        }
    except (InvalidParameterError, ClientNotFoundError, EnvironmentNotFoundError):
        raise
    except Exception as e:
        logger.error(f"Failed to list clients: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clients/{client_id}")
async def get_client_info(client_id: str):
    """
    获取单个客户端信息
    
    Args:
        client_id: 客户端唯一标识符
    
    Returns:
        客户端详细信息
    
    Raises:
        ClientNotFoundError: 客户端不存在
    """
    try:
        session = message_router.connection_manager.get_session(client_id)
        
        if not session:
            raise ClientNotFoundError(client_id)
        
        return session.to_dict()
    except ClientNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get client info for {client_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/environments")
async def list_environments():
    """
    获取环境列表
    
    Returns:
        所有活跃环境的详细信息
    """
    try:
        envs = message_router.connection_manager.get_environments_info()
        
        # 增强环境信息
        enhanced_envs = []
        for env in envs:
            env_info = message_router.connection_manager.get_environment_info(env["env_id"])
            if env_info:
                enhanced_envs.append(env_info)
        
        return {
            "total": len(enhanced_envs),
            "environments": enhanced_envs
        }
    except Exception as e:
        logger.error(f"Failed to list environments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/environments/{env_id}")
async def get_environment_info(env_id: str):
    """
    获取单个环境信息
    
    Args:
        env_id: 环境唯一标识符
    
    Returns:
        环境详细信息
    
    Raises:
        EnvironmentNotFoundError: 环境不存在
    """
    try:
        env_info = message_router.connection_manager.get_environment_info(env_id)
        
        if not env_info:
            raise EnvironmentNotFoundError(env_id)
        
        return env_info
    except EnvironmentNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get environment info for {env_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_health():
    """
    获取系统健康状态
    
    Returns:
        系统健康状态和性能指标
    """
    try:
        stats = message_router.connection_manager.get_statistics()
        
        # 尝试获取系统资源信息
        cpu_usage = 0.0
        memory_usage = 0.0
        
        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory_usage = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            logger.warning("psutil not installed, system metrics unavailable")
        
        return {
            "status": "healthy",
            "uptime": message_router.get_uptime(),
            "version": "1.0.0",
            "metrics": {
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "active_connections": stats["total_sessions"],
                "message_rate": 0.0,  # TODO: 实现消息速率统计
                "error_rate": 0.0  # TODO: 实现错误率统计
            },
            "components": {
                "websocket": "healthy",
                "connection_manager": "healthy"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
