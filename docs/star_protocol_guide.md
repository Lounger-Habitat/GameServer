# Star Protocol 使用指南

## 快速开始

### 1. 启动服务器

```bash
# 使用 uv 运行
uv run fastapi dev main.py
```

服务器启动后，访问：
- **API 文档**: http://localhost:8000/docs
- **监控页面**: http://localhost:8000/monitor

### 2. WebSocket 端点

```
ws://localhost:8000/ws/{role}/{client_id}
```

参数：
- `role`: 客户端角色（agent, environment, human, monitor）
- `client_id`: 客户端唯一标识

### 3. HTTP API 端点

- `GET /ws/stats` - 获取统计信息
- `GET /ws/environments` - 获取所有环境详情
- `GET /ws/clients/{client_id}` - 获取客户端信息

---

## 消息格式

所有消息必须符合 **Envelope** 格式：

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1620000000000,
  "type": "system|message|broadcast",
  "sender": "agent_01",
  "recipient": "hub|client_id|@all",
  "payload": {
    "type": "...",
    "content": {}
  }
}
```

### 消息类型

#### 1. System 消息

用于系统控制和通知。

**加入环境**:
```json
{
  "type": "system",
  "sender": "agent_01",
  "recipient": "hub",
  "payload": {
    "type": "ctrl",
    "content": {
      "op": "join",
      "env_id": "env_main"
    }
  }
}
```

**离开环境**:
```json
{
  "type": "system",
  "sender": "agent_01",
  "recipient": "hub",
  "payload": {
    "type": "ctrl",
    "content": {
      "op": "leave"
    }
  }
}
```

#### 2. Message 消息

点对点业务消息。

```json
{
  "type": "message",
  "sender": "agent_01",
  "recipient": "agent_02",
  "payload": {
    "type": "action",
    "content": {
      "name": "move",
      "params": {
        "x": 10,
        "y": 5
      }
    }
  }
}
```

#### 3. Broadcast 消息

广播给同环境的所有成员（需要先加入环境）。

```json
{
  "type": "broadcast",
  "sender": "agent_01",
  "recipient": "@all",
  "payload": {
    "type": "event",
    "content": {
      "name": "game_start",
      "data": {
        "timestamp": 1620000000
      }
    }
  }
}
```

---

## Python 客户端示例

### 基础连接

```python
import asyncio
import websockets
import json
from ws.models import Envelope, SystemPayload, MessagePayload

async def connect_to_hub():
    uri = "ws://localhost:8000/ws/agent/agent_01"
    
    async with websockets.connect(uri) as websocket:
        # 接收欢迎消息
        welcome = await websocket.recv()
        print(f"Welcome: {welcome}")
        
        # 加入环境
        join_envelope = Envelope(
            type="system",
            sender="agent_01",
            recipient="hub",
            payload=SystemPayload(
                type="ctrl",
                content={"op": "join", "env_id": "env_main"}
            )
        )
        await websocket.send(join_envelope.model_dump_json())
        
        # 接收确认
        response = await websocket.recv()
        print(f"Join response: {response}")
        
        # 发送业务消息
        action_envelope = Envelope(
            type="message",
            sender="agent_01",
            recipient="agent_02",
            payload=MessagePayload(
                type="action",
                content={"name": "move", "params": {"x": 10, "y": 5}}
            )
        )
        await websocket.send(action_envelope.model_dump_json())
        
        # 持续接收消息
        while True:
            message = await websocket.recv()
            print(f"Received: {message}")

asyncio.run(connect_to_hub())
```

### 广播消息

```python
async def broadcast_event():
    uri = "ws://localhost:8000/ws/agent/agent_01"
    
    async with websockets.connect(uri) as websocket:
        # 先加入环境
        join_envelope = Envelope(
            type="system",
            sender="agent_01",
            recipient="hub",
            payload=SystemPayload(type="ctrl", content={"op": "join", "env_id": "game_room"})
        )
        await websocket.send(join_envelope.model_dump_json())
        await websocket.recv()  # 等待确认
        
        # 广播事件
        broadcast_envelope = Envelope(
            type="broadcast",
            sender="agent_01",
            recipient="@all",
            payload=BroadcastPayload(
                type="event",
                content={"name": "player_joined", "data": {"player_id": "agent_01"}}
            )
        )
        await websocket.send(broadcast_envelope.model_dump_json())
```

---

## JavaScript 客户端示例

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/agent/agent_01');

ws.onopen = () => {
    console.log('Connected');
    
    // 加入环境
    const joinMsg = {
        type: 'system',
        sender: 'agent_01',
        recipient: 'hub',
        payload: {
            type: 'ctrl',
            content: { op: 'join', env_id: 'env_main' }
        }
    };
    ws.send(JSON.stringify(joinMsg));
};

ws.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    console.log('Received:', envelope);
    
    // 处理不同类型的消息
    if (envelope.type === 'system') {
        console.log('System message:', envelope.payload.content);
    } else if (envelope.type === 'message') {
        console.log('Business message:', envelope.payload.content);
    }
};

// 发送消息
function sendAction(targetId, action) {
    const msg = {
        type: 'message',
        sender: 'agent_01',
        recipient: targetId,
        payload: {
            type: 'action',
            content: action
        }
    };
    ws.send(JSON.stringify(msg));
}
```

---

## 监控页面使用

访问 http://localhost:8000/monitor 查看实时监控：

1. **统计面板**: 显示连接数、环境数、运行时长、消息速率
2. **环境列表**: 显示所有活跃环境及其成员
3. **客户端列表**: 显示所有连接的客户端
4. **消息流向图**: D3.js 可视化节点关系和消息流动
5. **消息日志**: 实时显示所有消息，支持过滤和搜索

### 日志控制

- **搜索**: 按发送者/接收者过滤
- **类型过滤**: 仅显示 system/message/broadcast
- **暂停/继续**: 暂停实时更新
- **清空**: 清除所有日志
- **导出**: 导出为 JSON 文件

---

## 最佳实践

1. **客户端 ID 命名**: 使用有意义的 ID，如 `agent_npc_01`, `env_game_main`
2. **环境管理**: 客户端只能同时在一个环境中
3. **错误处理**: 监听系统错误消息，处理 404（接收者不存在）和 403（未加入环境）
4. **心跳**: 定期发送消息保持连接活跃
5. **监控角色**: 使用 `monitor` 角色连接以避免影响业务逻辑

---

## 故障排查

### 连接失败
- 检查服务器是否启动
- 确认 WebSocket URL 格式正确
- 查看浏览器控制台错误

### 消息未送达
- 确认接收者已连接（查看 `/ws/stats`）
- 检查消息格式是否符合 Envelope 规范
- 广播消息需要先加入环境

### 监控页面空白
- 检查静态文件是否正确部署
- 查看浏览器控制台错误
- 确认 `/static` 路径可访问
