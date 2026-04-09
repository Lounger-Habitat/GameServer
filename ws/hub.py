import logging
from fastapi import APIRouter, WebSocket
from star_protocol.server import MessageRouter

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 全局消息路由器实例 (使用 SDK 中的版本)
message_router = MessageRouter(max_connections=1000, heartbeat_interval=30.0)


@router.websocket("/ws/{role}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, role: str, client_id: str):
    """
    Star Protocol WebSocket 端点
    
    支持的角色：
    - agent: 代理
    - environment: 环境
    - human: 人类
    - monitor: 业务监控（接收 monitor 协议消息）
    - hub_monitor: 系统监控（监听所有消息）
    
    Args:
        websocket: WebSocket 连接
        role: 客户端角色
        client_id: 客户端唯一标识
    """
    await message_router.handle_connection(websocket, role, client_id)
