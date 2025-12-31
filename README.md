# 模块化 FastAPI 服务器 - 使用说明

## 快速开始

### 启动服务器

```bash
# 开发模式（自动重载）
uv run fastapi dev main.py

# 生产模式
uv run fastapi run main.py
```

### 访问 API 文档

服务器启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 配置说明

编辑 `config.yaml` 文件来配置服务器：

```yaml
# 服务器配置
server:
  host: "0.0.0.0"
  port: 8000
  reload: true

# 模块启用开关（设置为 false 可禁用模块）
modules:
  enable_openai_api: true      # OpenAI 兼容 API
  enable_response_api: true    # Response API
  enable_custom_api: true      # 自定义 API
  enable_websocket: true       # WebSocket

# 鉴权配置
auth:
  enabled: true                # 启用 API Key 鉴权
  keys_file: "api_keys.json"   # Key 存储文件
```

## API Key 鉴权

启用鉴权后，访问受保护的 API 需要提供 API Key。

### 管理 API Keys（命令行）

```bash
# 创建 Key（永久有效）
uv run api_key.py create my-app

# 创建 Key（30天有效）
uv run api_key.py create my-app --days 30

# 列出所有 Keys
uv run api_key.py list

# 删除 Key
uv run api_key.py delete my-app
```

### 使用 API Key

请求时添加 Header（二选一）：

```bash
# 方式一：Authorization Header
curl http://localhost:8000/custom/hello \
  -H "Authorization: Bearer sk-your-api-key"

# 方式二：X-API-Key Header
curl http://localhost:8000/custom/hello \
  -H "X-API-Key: sk-your-api-key"
```

## API 端点

### 系统端点
- `GET /health` - 健康检查

### OpenAI 兼容 API
- `GET /v1/models` - 列出模型
- `POST /v1/chat` - 聊天

### Response API（预留）
- `GET /response/status` - 获取状态

### MengLong API
- `GET /menglong/models` - 列出模型
- `GET /menglong/models/{model_id}` - 查看模型信息
- `POST /menglong/chat` - 聊天

### WebSocket
- `ws://localhost:8000/ws` - 基础连接
- `ws://localhost:8000/ws/{room_id}` - 房间连接

## 测试 WebSocket

运行测试脚本：
```bash
uv run test_websocket.py
```

## 后续开发

- StarProtocol 协议实现：修改 `ws/starprotocol.py`
- Response API 实现：修改 `api/response/routes.py`
- 添加新的 API 模块：在 `api/` 下创建新目录
