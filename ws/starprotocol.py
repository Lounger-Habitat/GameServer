"""Star Protocol WebSocket 实现"""

import logging
from fastapi import APIRouter, WebSocket

from .router import MessageRouter


logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 全局消息路由器实例
message_router = MessageRouter(max_connections=1000, heartbeat_interval=30.0)


@router.websocket("/ws/{role}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, role: str, client_id: str):
    """
    Star Protocol WebSocket 端点
    
    Args:
        websocket: WebSocket 连接
        role: 客户端角色 (agent, environment, human, monitor)
        client_id: 客户端唯一标识
    """
    await message_router.handle_connection(websocket, role, client_id)


@router.get("/ws/stats", deprecated=True)
async def get_stats():
    """
    获取 WebSocket 统计信息
    
    **已废弃**: 请使用 /api/monitor/stats
    """
    stats = message_router.connection_manager.get_statistics()
    return {
        "total_clients": stats["total_sessions"],
        "environments": stats["environments"]["details"],
        "uptime": message_router.get_uptime()
    }


@router.get("/ws/environments", deprecated=True)
async def list_environments():
    """
    列出所有环境详情
    
    **已废弃**: 请使用 /api/monitor/environments
    """
    return {
        "environments": message_router.connection_manager.get_environment_details()
    }


@router.get("/ws/clients/{client_id}", deprecated=True)
async def get_client_info(client_id: str):
    """
    获取客户端信息
    
    **已废弃**: 请使用 /api/monitor/clients/{client_id}
    """
    session = message_router.connection_manager.get_session(client_id)
    if not session:
        return {"error": "Client not found"}
    
    return session.to_dict()


@router.get("/ws/clients", deprecated=True)
async def list_all_clients():
    """
    列出所有连接的客户端
    
    **已废弃**: 请使用 /api/monitor/clients
    """
    from ws.connection import ClientRole
    
    all_clients = []
    for role in ClientRole:
        sessions = message_router.connection_manager.get_sessions_by_role(role)
        for session in sessions:
            all_clients.append(session.to_dict())
    
    return {"clients": all_clients}
