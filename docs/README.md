# API 文档

本目录包含 Star Protocol API Server 的完整 API 文档。

## 📚 文档索引

### Monitor API
- **文件**: [monitor.md](./monitor.md)
- **描述**: 监控系统 API，提供实时监控、客户端管理、环境监控和系统统计功能
- **基础路径**: `/api/monitor`
- **版本**: v1.0.0

**主要端点**:
- `GET /api/monitor/stats` - 系统统计信息
- `GET /api/monitor/clients` - 客户端列表（支持过滤）
- `GET /api/monitor/clients/{id}` - 单个客户端信息
- `GET /api/monitor/environments` - 环境列表
- `GET /api/monitor/environments/{id}` - 单个环境信息
- `GET /api/monitor/health` - 系统健康检查

**WebSocket**:
- `ws://{host}/ws/monitor/{monitor_id}` - Monitor 实时连接

---

## 🚀 快速开始

### 1. 启动服务器

```bash
uv run uvicorn core.app:app --reload --port 8000
```

### 2. 访问 API 文档

服务器启动后，可以通过以下方式访问 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Monitor 页面**: http://localhost:8000/monitor

### 3. 测试 API

```bash
# 获取系统统计
curl http://localhost:8000/api/monitor/stats

# 获取客户端列表
curl http://localhost:8000/api/monitor/clients

# 获取健康状态
curl http://localhost:8000/api/monitor/health
```

---

## 📖 API 规范

### 通用规范

#### 基础 URL

```
http://localhost:8000
```

#### 请求头

```http
Content-Type: application/json
Accept: application/json
```

#### 响应格式

所有 API 响应均为 JSON 格式。

**成功响应**:
```json
{
  "data": {...}
}
```

**错误响应**:
```json
{
  "detail": {
    "error": {
      "code": "ERROR_CODE",
      "message": "Error message",
      "details": {...}
    }
  }
}
```

#### HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 429 | 超过速率限制 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 🔐 认证

当前版本的 Monitor API 不需要认证。未来版本可能会添加以下认证方式：

- API Key 认证
- JWT Token 认证
- OAuth 2.0

---

## 📊 数据模型

### 通用类型

#### 时间戳

所有时间戳使用 Unix 时间戳（秒）：

```json
{
  "connected_at": 1770054384.25139,
  "uptime": 120.5
}
```

#### 枚举值

枚举值使用小写字符串：

```json
{
  "role": "agent",
  "state": "connected"
}
```

#### 客户端角色

- `agent` - 代理
- `environment` - 环境
- `human` - 人类
- `monitor` - 监控

#### 客户端状态

- `connected` - 已连接
- `in_env` - 在环境中
- `disconnected` - 已断开

#### 环境状态

- `active` - 活跃
- `closing` - 关闭中

---

## 🛠️ 开发指南

### 添加新的 API 端点

1. 在相应的路由文件中添加端点（如 `ws/.py`）
2. 定义请求/响应模型
3. 实现业务逻辑
4. 添加错误处理
5. 编写文档
6. 添加测试

### 错误处理

使用统一的错误类（定义在 `ws/errors.py`）：

```python
from ws.errors import ClientNotFoundError

@router.get("/api/monitor/clients/{client_id}")
async def get_client_info(client_id: str):
    session = get_session(client_id)
    if not session:
        raise ClientNotFoundError(client_id)
    return session.to_dict()
```

### 文档规范

- 使用 FastAPI 的文档字符串
- 包含请求/响应示例
- 说明所有参数
- 列出可能的错误

---

## 🧪 测试

### 单元测试

```bash
pytest tests/test_monitor_api.py
```

### 集成测试

```bash
pytest tests/integration/test_monitor.py
```

### API 测试

使用 cURL 或 Postman 测试 API 端点。

---

## 📝 版本历史

### v1.0.0 (2026-02-03)

**新增**:
- Monitor API 完整实现
- 6 个 HTTP REST 端点
- WebSocket 实时监控
- 统一错误处理
- 查询过滤功能
- 健康检查端点

**改进**:
- 数据模型增强（message_count, metadata）
- API 路径规范化（/api/monitor/*）
- 响应格式标准化

**废弃**:
- `/ws/stats` → 使用 `/api/monitor/stats`
- `/ws/clients` → 使用 `/api/monitor/clients`
- `/ws/environments` → 使用 `/api/monitor/environments`

---

## 🔗 相关链接

- [项目主页](../../README.md)
- [Star Protocol 文档](../star_protocol.md)
- [部署指南](../deployment.md)
- [贡献指南](../../CONTRIBUTING.md)

---

## 📞 支持与反馈

如有问题或建议，请：

1. 查看 [FAQ](../faq.md)
2. 提交 [Issue](https://github.com/your-repo/issues)
3. 联系开发团队

---

**最后更新**: 2026-02-03  
**维护者**: Star Protocol Team
