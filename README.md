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
- `ws://localhost:8000/ws/{role}/{client_id}` - Star Protocol 客户端连接

## 测试 WebSocket

运行测试脚本：
```bash
uv run python -m tests.test_star_protocol
```

## 统计模块

统计模块自动记录所有 API 调用的详细信息，包括 token 使用、费用计算等。

### 功能特性

- ✅ **自动记录**：通过中间件自动记录每次 API 调用
- ✅ **Token 统计**：精确统计输入/输出 token 数量
- ✅ **费用计算**：根据模型定价自动计算费用
- ✅ **流式支持**：特殊处理流式响应的 token 统计
- ✅ **权限控制**：管理员查看全部，普通用户只看自己
- ✅ **数据导出**：支持 CSV 和 JSON 格式导出
- ✅ **可视化 Dashboard**：图表展示统计数据

### 统计 API 端点

```bash
# 查看我的统计
curl http://localhost:8000/statistics/my \
  -H "X-API-Key: sk-your-key"

# 查看总体统计（仅管理员）
curl http://localhost:8000/statistics/overview \
  -H "X-API-Key: sk-admin-key"

# 查看所有 Key 的统计（仅管理员）
curl http://localhost:8000/statistics/all-keys \
  -H "X-API-Key: sk-admin-key"

# 查询调用日志（分页）
curl http://localhost:8000/statistics/logs?page=1&page_size=20 \
  -H "X-API-Key: sk-your-key"

# 导出数据为 CSV
curl http://localhost:8000/statistics/export?format=csv \
  -H "X-API-Key: sk-your-key" \
  -O

# 清理旧记录（仅管理员）
curl -X POST http://localhost:8000/statistics/cleanup?days=90 \
  -H "X-API-Key: sk-admin-key"
```

### 访问 Dashboard

在浏览器中打开：
```
http://localhost:8000/statistics/dashboard
```

输入您的 API Key 即可查看可视化统计数据。

### 权限说明

- **管理员**：API Key 名称为 `admin`
  - 可以查看所有 Key 的统计
  - 可以查看总体统计
  - 可以清理旧数据
  
- **普通用户**：
  - 只能查看自己的统计
  - 只能导出自己的数据

**创建管理员 Key**：
```bash
uv run utils/api_key.py create admin
```

### 配置说明

在 `config.yaml` 中配置统计模块：

```yaml
statistics:
  enabled: true                  # 是否启用统计
  database_file: "statistics.db" # SQLite 数据库文件
  retention_days: 0              # 数据保留天数（0=永久）
  async_logging: true            # 是否异步记录
```

### 测试统计功能

```bash
# 运行测试脚本
uv run test_statistics.py
```

## 后续开发

- StarProtocol 协议实现：修改 `ws/router.py` 和 `ws/connection.py`
- Response API 实现：修改 `api/response/routes.py`
- 添加新的 API 模块：在 `api/` 下创建新目录

