"""WebSocket StarProtocol 实现"""
from datetime import datetime
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """接受新连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        print(f"🔌 客户端 {client_id} 已连接，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            print(f"🔌 客户端 {client_id} 已断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    
    async def broadcast(self, message: str, exclude: str = None):
        """广播消息"""
        for client_id, connection in self.active_connections.items():
            if client_id != exclude:
                await connection.send_text(message)


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点（基础框架）"""
    # 生成客户端 ID
    client_id = f"client_{datetime.now().timestamp()}"
    
    await manager.connect(websocket, client_id)
    
    # 发送欢迎消息
    await websocket.send_json({
        "type": "connection",
        "status": "connected",
        "client_id": client_id,
        "message": "WebSocket 连接成功",
        "protocol": "StarProtocol (待实现)",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            print(f"📨 收到来自 {client_id} 的消息: {data}")
            
            # 回显消息（示例处理）
            response = {
                "type": "echo",
                "client_id": client_id,
                "received": data,
                "timestamp": datetime.now().isoformat(),
                "note": "这是基础 WebSocket 框架，StarProtocol 协议待实现"
            }
            
            await websocket.send_json(response)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"❌ 客户端 {client_id} 断开连接")


@router.websocket("/ws/{room_id}")
async def websocket_room_endpoint(websocket: WebSocket, room_id: str):
    """WebSocket 房间端点（支持多房间）"""
    client_id = f"client_{room_id}_{datetime.now().timestamp()}"
    
    await manager.connect(websocket, client_id)
    
    await websocket.send_json({
        "type": "connection",
        "status": "connected",
        "client_id": client_id,
        "room_id": room_id,
        "message": f"已加入房间 {room_id}",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # 广播到同一房间的其他客户端
            broadcast_message = {
                "type": "broadcast",
                "room_id": room_id,
                "from": client_id,
                "message": data,
                "timestamp": datetime.now().isoformat()
            }
            
            # 这里简化处理，实际应该按房间分组
            await manager.broadcast(str(broadcast_message), exclude=client_id)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(
            f"客户端 {client_id} 离开了房间 {room_id}",
            exclude=client_id
        )
