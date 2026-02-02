# Monitor API 文档

## 📋 概述

Monitor API 提供了对 Star Protocol 系统的实时监控能力，包括客户端管理、环境监控、系统统计和健康检查等功能。

**基础路径**: `/api/monitor`

**版本**: v1.0.0

---

## 🔌 WebSocket 连接

### Monitor 连接端点

```
ws://{host}/ws/monitor/{monitor_id}
```

**描述**: Monitor 客户端通过此端点建立 WebSocket 连接，接收实时消息流。

**路径参数**:
- `monitor_id` (string, required): Monitor 客户端唯一标识符
  - 格式建议: `monitor_{timestamp}`
  - 示例: `monitor_1770054384251`

**连接示例**:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/monitor/monitor_1770054384251');

ws.onopen = () => {
  console.log('Monitor connected');
};

ws.onmessage = (event) => {
  const envelope = JSON.parse(event.data);
  console.log('Received:', envelope);
};
```

**接收消息格式**:

Monitor 接收所有经过系统的消息，格式遵循 Star Protocol Envelope：

```json
{
  "id": "msg_uuid",
  "type": "system|message|broadcast",
  "sender": "client_id",
  "recipient": "client_id|@all|hub",
  "timestamp": "2026-02-03T01:35:05.123456",
  "data": {
    "type": "string",
    "content": {}
  }
}
```

---

## 🌐 HTTP REST API

### 1. 获取系统统计信息

```http
GET /api/monitor/stats
```

**描述**: 获取系统整体统计信息，包括客户端数量、环境数量、运行时间等。

**请求参数**: 无

**响应示例**:

```json
{
  "total_clients": 10,
  "clients_by_role": {
    "agent": 4,
    "environment": 2,
    "human": 3,
    "monitor": 1
  },
  "total_environments": 2,
  "environments": [
    {
      "env_id": "env_game",
      "member_count": 5,
      "members": ["agent_alice", "agent_bob", "human_charlie"]
    }
  ],
  "uptime": 3600.5,
  "message_rate": 0.0
}
```

**响应字段**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `total_clients` | integer | 当前连接的客户端总数 |
| `clients_by_role` | object | 按角色分组的客户端数量 |
| `total_environments` | integer | 当前活跃的环境数量 |
| `environments` | array | 环境详情列表 |
| `uptime` | float | 服务器运行时间（秒） |
| `message_rate` | float | 消息速率（条/秒） |

**状态码**:
- `200 OK`: 成功
- `500 Internal Server Error`: 服务器错误

**cURL 示例**:

```bash
curl http://localhost:8000/api/monitor/stats
```

---

### 2. 获取客户端列表

```http
GET /api/monitor/clients
```

**描述**: 获取所有连接的客户端详细信息，支持按角色、状态、环境过滤。

**查询参数**:

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `role` | string | 否 | 按角色过滤 (`agent`, `environment`, `human`, `monitor`) |
| `state` | string | 否 | 按状态过滤 (`connected`, `in_env`, `disconnected`) |
| `env_id` | string | 否 | 按环境过滤 |

**响应示例**:

```json
{
  "total": 4,
  "clients": [
    {
      "client_id": "agent_alice",
      "role": "agent",
      "state": "in_env",
      "current_env": "env_game",
      "connected_at": 1770054384.25139,
      "uptime": 120.5,
      "last_heartbeat": 1770054500.123,
      "message_count": 45,
      "metadata": {}
    }
  ]
}
```

**响应字段**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `total` | integer | 客户端总数 |
| `clients` | array | 客户端详情列表 |
| `client_id` | string | 客户端唯一标识 |
| `role` | string | 客户端角色 |
| `state` | string | 连接状态 |
| `current_env` | string\|null | 当前所在环境 |
| `connected_at` | float | 连接时间戳 |
| `uptime` | float | 连接持续时间（秒） |
| `last_heartbeat` | float | 最后心跳时间戳 |
| `message_count` | integer | 发送/接收的消息数量 |
| `metadata` | object | 元数据（IP、User-Agent 等） |

**状态码**:
- `200 OK`: 成功
- `400 Bad Request`: 参数错误
- `500 Internal Server Error`: 服务器错误

**cURL 示例**:

```bash
# 获取所有客户端
curl http://localhost:8000/api/monitor/clients

# 只获取 agent 角色的客户端
curl "http://localhost:8000/api/monitor/clients?role=agent"

# 获取在环境中的客户端
curl "http://localhost:8000/api/monitor/clients?state=in_env"

# 获取特定环境的客户端
curl "http://localhost:8000/api/monitor/clients?env_id=env_game"
```

---

### 3. 获取单个客户端信息

```http
GET /api/monitor/clients/{client_id}
```

**描述**: 获取指定客户端的详细信息。

**路径参数**:
- `client_id` (string, required): 客户端唯一标识符

**响应示例**:

```json
{
  "client_id": "agent_alice",
  "role": "agent",
  "state": "in_env",
  "current_env": "env_game",
  "connected_at": 1770054384.25139,
  "uptime": 120.5,
  "last_heartbeat": 1770054500.123,
  "message_count": 45,
  "metadata": {}
}
```

**状态码**:
- `200 OK`: 成功
- `404 Not Found`: 客户端不存在
- `500 Internal Server Error`: 服务器错误

**错误响应示例**:

```json
{
  "detail": {
    "error": {
      "code": "CLIENT_NOT_FOUND",
      "message": "Client 'agent_alice' not found",
      "details": {
        "client_id": "agent_alice"
      }
    }
  }
}
```

**cURL 示例**:

```bash
curl http://localhost:8000/api/monitor/clients/agent_alice
```

---

### 4. 获取环境列表

```http
GET /api/monitor/environments
```

**描述**: 获取所有活跃环境的详细信息。

**请求参数**: 无

**响应示例**:

```json
{
  "total": 2,
  "environments": [
    {
      "env_id": "env_game",
      "state": "active",
      "member_count": 5,
      "members": [
        {
          "client_id": "agent_alice",
          "role": "agent",
          "state": "in_env",
          "joined_at": 1770054384.25139,
          "message_count": 45
        }
      ],
      "created_at": 1770054300.0,
      "uptime": 180.5
    }
  ]
}
```

**响应字段**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `total` | integer | 环境总数 |
| `environments` | array | 环境详情列表 |
| `env_id` | string | 环境唯一标识 |
| `state` | string | 环境状态 (`active`, `closing`) |
| `member_count` | integer | 成员数量 |
| `members` | array | 成员详情列表 |
| `created_at` | float | 创建时间戳 |
| `uptime` | float | 运行时间（秒） |

**状态码**:
- `200 OK`: 成功
- `500 Internal Server Error`: 服务器错误

**cURL 示例**:

```bash
curl http://localhost:8000/api/monitor/environments
```

---

### 5. 获取单个环境信息

```http
GET /api/monitor/environments/{env_id}
```

**描述**: 获取指定环境的详细信息。

**路径参数**:
- `env_id` (string, required): 环境唯一标识符

**响应示例**:

```json
{
  "env_id": "env_game",
  "state": "active",
  "member_count": 5,
  "members": [
    {
      "client_id": "agent_alice",
      "role": "agent",
      "state": "in_env",
      "joined_at": 1770054384.25139,
      "message_count": 45
    }
  ],
  "created_at": 1770054300.0,
  "uptime": 180.5
}
```

**状态码**:
- `200 OK`: 成功
- `404 Not Found`: 环境不存在
- `500 Internal Server Error`: 服务器错误

**错误响应示例**:

```json
{
  "detail": {
    "error": {
      "code": "ENVIRONMENT_NOT_FOUND",
      "message": "Environment 'env_game' not found",
      "details": {
        "env_id": "env_game"
      }
    }
  }
}
```

**cURL 示例**:

```bash
curl http://localhost:8000/api/monitor/environments/env_game
```

---

### 6. 获取系统健康状态

```http
GET /api/monitor/health
```

**描述**: 获取系统健康状态和性能指标。

**请求参数**: 无

**响应示例**:

```json
{
  "status": "healthy",
  "uptime": 3600.5,
  "version": "1.0.0",
  "metrics": {
    "cpu_usage": 25.5,
    "memory_usage": 512.3,
    "active_connections": 10,
    "message_rate": 0.0,
    "error_rate": 0.0
  },
  "components": {
    "websocket": "healthy",
    "connection_manager": "healthy"
  }
}
```

**响应字段**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `status` | string | 系统状态 (`healthy`, `unhealthy`) |
| `uptime` | float | 运行时间（秒） |
| `version` | string | API 版本 |
| `metrics` | object | 性能指标 |
| `metrics.cpu_usage` | float | CPU 使用率（%） |
| `metrics.memory_usage` | float | 内存使用量（MB） |
| `metrics.active_connections` | integer | 活跃连接数 |
| `metrics.message_rate` | float | 消息速率（条/秒） |
| `metrics.error_rate` | float | 错误率 |
| `components` | object | 组件状态 |

**状态码**:
- `200 OK`: 系统健康
- `503 Service Unavailable`: 系统不健康

**cURL 示例**:

```bash
curl http://localhost:8000/api/monitor/health
```

---

## 📊 数据模型

### Envelope (消息信封)

```typescript
interface Envelope {
  id: string;              // 消息唯一标识 (UUID)
  type: MessageType;       // 消息类型
  sender: string;          // 发送者 client_id
  recipient: string;       // 接收者 client_id 或 @all
  timestamp: string;       // ISO 8601 时间戳
  data: Payload;           // 消息负载
}

enum MessageType {
  SYSTEM = "system",
  MESSAGE = "message",
  BROADCAST = "broadcast"
}
```

### Client (客户端)

```typescript
interface Client {
  client_id: string;       // 客户端唯一标识
  role: ClientRole;        // 客户端角色
  state: ClientState;      // 连接状态
  current_env: string | null;  // 当前环境
  connected_at: number;    // 连接时间戳
  uptime: number;          // 连接持续时间（秒）
  last_heartbeat: number;  // 最后心跳时间戳
  message_count: number;   // 消息计数
  metadata: object;        // 元数据
}

enum ClientRole {
  AGENT = "agent",
  ENVIRONMENT = "environment",
  HUMAN = "human",
  MONITOR = "monitor"
}

enum ClientState {
  CONNECTED = "connected",
  IN_ENV = "in_env",
  DISCONNECTED = "disconnected"
}
```

### Environment (环境)

```typescript
interface Environment {
  env_id: string;          // 环境唯一标识
  state: EnvironmentState; // 环境状态
  member_count: number;    // 成员数量
  members: Member[];       // 成员列表
  created_at: number;      // 创建时间戳
  uptime: number;          // 运行时间（秒）
}

enum EnvironmentState {
  ACTIVE = "active",
  CLOSING = "closing"
}

interface Member {
  client_id: string;
  role: ClientRole;
  state: ClientState;
  joined_at: number;
  message_count: number;
}
```

---

## ⚠️ 错误处理

### 错误响应格式

所有错误响应遵循统一格式：

```json
{
  "detail": {
    "error": {
      "code": "ERROR_CODE",
      "message": "Human readable error message",
      "details": {
        "additional": "context"
      }
    }
  }
}
```

### 错误码列表

| 错误码 | HTTP 状态码 | 描述 |
|--------|-------------|------|
| `CLIENT_NOT_FOUND` | 404 | 客户端不存在 |
| `ENVIRONMENT_NOT_FOUND` | 404 | 环境不存在 |
| `INVALID_PARAMETER` | 400 | 参数错误 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超过速率限制 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |

### 错误示例

**客户端不存在**:
```json
{
  "detail": {
    "error": {
      "code": "CLIENT_NOT_FOUND",
      "message": "Client 'agent_alice' not found",
      "details": {
        "client_id": "agent_alice"
      }
    }
  }
}
```

**参数错误**:
```json
{
  "detail": {
    "error": {
      "code": "INVALID_PARAMETER",
      "message": "Invalid role: invalid_role",
      "details": {
        "parameter": "role"
      }
    }
  }
}
```

---

## 📝 命名规范

### API 端点命名

- 使用 RESTful 风格
- 资源使用复数形式: `/clients`, `/environments`
- 使用小写字母和连字符
- 统一前缀: `/api/monitor/`

### 字段命名

- 使用 `snake_case`: `client_id`, `message_count`
- 时间戳字段后缀: `_at` (`created_at`, `connected_at`)
- 持续时间字段: `uptime` (秒)
- 计数字段后缀: `_count` (`message_count`, `member_count`)

### 枚举值

- 使用小写字母: `"agent"`, `"connected"`
- 多词使用下划线: `"in_env"`

---

## 🚀 使用示例

### Python 客户端

```python
import requests
import websockets
import asyncio
import json

# HTTP API
def get_stats():
    response = requests.get('http://localhost:8000/api/monitor/stats')
    stats = response.json()
    print(f"Total clients: {stats['total_clients']}")
    return stats

def get_agents():
    response = requests.get(
        'http://localhost:8000/api/monitor/clients',
        params={'role': 'agent'}
    )
    data = response.json()
    print(f"Agents: {data['total']}")
    return data['clients']

def get_client(client_id):
    try:
        response = requests.get(
            f'http://localhost:8000/api/monitor/clients/{client_id}'
        )
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        error = e.response.json()
        print(f"Error: {error['detail']['error']['code']}")
        return None

# WebSocket
async def monitor_messages():
    uri = "ws://localhost:8000/ws/monitor/monitor_python"
    async with websockets.connect(uri) as websocket:
        print("Monitor connected")
        while True:
            message = await websocket.recv()
            envelope = json.loads(message)
            print(f"{envelope['sender']} → {envelope['recipient']}: {envelope['type']}")

# 运行
if __name__ == "__main__":
    # HTTP 示例
    stats = get_stats()
    agents = get_agents()
    client = get_client('agent_alice')
    
    # WebSocket 示例
    asyncio.run(monitor_messages())
```

### JavaScript 客户端

```javascript
// HTTP API
async function getStats() {
  const response = await fetch('/api/monitor/stats');
  const stats = await response.json();
  console.log(`Total clients: ${stats.total_clients}`);
  return stats;
}

async function getAgents() {
  const response = await fetch('/api/monitor/clients?role=agent');
  const data = await response.json();
  console.log(`Agents: ${data.total}`);
  return data.clients;
}

async function getClient(clientId) {
  try {
    const response = await fetch(`/api/monitor/clients/${clientId}`);
    if (!response.ok) {
      const error = await response.json();
      console.error(`Error: ${error.detail.error.code}`);
      return null;
    }
    return await response.json();
  } catch (error) {
    console.error('Request failed:', error);
    return null;
  }
}

// WebSocket
function connectMonitor() {
  const ws = new WebSocket('ws://localhost:8000/ws/monitor/monitor_js');
  
  ws.onopen = () => {
    console.log('Monitor connected');
  };
  
  ws.onmessage = (event) => {
    const envelope = JSON.parse(event.data);
    console.log(`${envelope.sender} → ${envelope.recipient}: ${envelope.type}`);
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };
  
  ws.onclose = () => {
    console.log('Monitor disconnected');
    // 3秒后重连
    setTimeout(connectMonitor, 3000);
  };
  
  return ws;
}

// 使用示例
(async () => {
  // HTTP 示例
  const stats = await getStats();
  const agents = await getAgents();
  const client = await getClient('agent_alice');
  
  // WebSocket 示例
  const ws = connectMonitor();
})();
```

---

## 🔄 迁移指南

### 从旧 API 迁移

旧的 API 端点已标记为 deprecated，建议尽快迁移到新端点：

| 旧端点 | 新端点 | 变更 |
|--------|--------|------|
| `GET /ws/stats` | `GET /api/monitor/stats` | 响应格式增强 |
| `GET /ws/clients` | `GET /api/monitor/clients` | 添加过滤参数 |
| `GET /ws/clients/{id}` | `GET /api/monitor/clients/{id}` | 错误处理规范化 |
| `GET /ws/environments` | `GET /api/monitor/environments` | 响应格式增强 |

### 响应格式变更

**旧格式**:
```json
{
  "total_clients": 10,
  "environments": [...]
}
```

**新格式**:
```json
{
  "total_clients": 10,
  "clients_by_role": {...},
  "total_environments": 2,
  "environments": [...],
  "uptime": 3600.5,
  "message_rate": 0.0
}
```

---

## 📚 相关资源

- [Star Protocol 文档](../star_protocol.md)
- [WebSocket 连接指南](../websocket.md)
- [错误处理最佳实践](../error_handling.md)
- [API 认证](../authentication.md)

---

## 📞 支持

如有问题或建议，请联系开发团队或提交 Issue。

**版本**: 1.0.0  
**最后更新**: 2026-02-03
