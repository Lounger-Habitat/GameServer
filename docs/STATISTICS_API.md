# Statistics API 接口文档

## 概述

Statistics API 提供了完整的 API 调用统计、Token 使用统计和费用分析功能。所有接口都需要 API Key 认证。

**Base URL**: `http://localhost:8000`

**认证方式**: 在请求头中添加 API Key

```http
Authorization: Bearer sk-your-api-key
```

或

```http
X-API-Key: sk-your-api-key
```

---

## 权限说明

### 管理员
- API Key 名称包含 `admin`（不区分大小写）
- 可以访问所有端点
- 可以查看所有 Key 的数据

### 普通用户
- 只能访问自己的统计数据
- 部分端点会返回 403 错误

---

## 接口列表

### 1. 获取我的统计

获取当前 API Key 的使用统计。

**端点**: `GET /statistics/my`

**权限**: 所有用户

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string (ISO 8601) | 否 | 开始时间，如 `2024-01-01T00:00:00Z` |
| end_date | string (ISO 8601) | 否 | 结束时间，如 `2024-01-31T23:59:59Z` |

**响应示例**:

```json
{
  "total_calls": 1250,
  "successful_calls": 1200,
  "failed_calls": 50,
  "total_input_tokens": 45000,
  "total_output_tokens": 38000,
  "total_tokens": 83000,
  "total_cost": 0.083,
  "stream_calls": 300,
  "non_stream_calls": 950
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| total_calls | integer | 总调用次数 |
| successful_calls | integer | 成功调用次数（状态码 2xx） |
| failed_calls | integer | 失败调用次数（状态码 4xx/5xx） |
| total_input_tokens | integer | 总输入 Token 数 |
| total_output_tokens | integer | 总输出 Token 数 |
| total_tokens | integer | 总 Token 数 |
| total_cost | float | 总费用（元） |
| stream_calls | integer | 流式调用次数 |
| non_stream_calls | integer | 非流式调用次数 |

**示例代码**:

```javascript
// JavaScript/TypeScript
const response = await fetch('http://localhost:8000/statistics/my?start_date=2024-01-01T00:00:00Z', {
  headers: {
    'X-API-Key': 'sk-your-api-key'
  }
});
const stats = await response.json();
console.log(stats);
```

```python
# Python
import requests

response = requests.get(
    'http://localhost:8000/statistics/my',
    headers={'X-API-Key': 'sk-your-api-key'},
    params={'start_date': '2024-01-01T00:00:00Z'}
)
stats = response.json()
print(stats)
```

```bash
# cURL
curl -X GET "http://localhost:8000/statistics/my?start_date=2024-01-01T00:00:00Z" \
  -H "X-API-Key: sk-your-api-key"
```

---

### 2. 获取总体统计（仅管理员）

获取所有 API Key 的总体统计数据。

**端点**: `GET /statistics/overview`

**权限**: 仅管理员

**请求参数**: 同 `/statistics/my`

**响应格式**: 同 `/statistics/my`

**错误响应**:

```json
{
  "detail": "只有管理员可以查看总体统计"
}
```

状态码: `403 Forbidden`

---

### 3. 获取指定 Key 的统计（仅管理员）

获取指定 API Key 的统计数据。

**端点**: `GET /statistics/by-key/{key_name}`

**权限**: 仅管理员

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key_name | string | 是 | API Key 的名称 |

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string (ISO 8601) | 否 | 开始时间 |
| end_date | string (ISO 8601) | 否 | 结束时间 |

**响应格式**: 同 `/statistics/my`

**示例**:

```javascript
const response = await fetch('http://localhost:8000/statistics/by-key/test-user', {
  headers: {
    'X-API-Key': 'sk-admin-key'
  }
});
const stats = await response.json();
```

---

### 4. 获取所有 Key 的统计列表（仅管理员）

获取所有 API Key 的统计数据列表，按费用降序排列。

**端点**: `GET /statistics/all-keys`

**权限**: 仅管理员

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start_date | string (ISO 8601) | 否 | 开始时间 |
| end_date | string (ISO 8601) | 否 | 结束时间 |

**响应示例**:

```json
[
  {
    "api_key_name": "admin",
    "statistics": {
      "total_calls": 500,
      "successful_calls": 480,
      "failed_calls": 20,
      "total_input_tokens": 20000,
      "total_output_tokens": 18000,
      "total_tokens": 38000,
      "total_cost": 0.038,
      "stream_calls": 100,
      "non_stream_calls": 400
    }
  },
  {
    "api_key_name": "test-user",
    "statistics": {
      "total_calls": 300,
      "successful_calls": 290,
      "failed_calls": 10,
      "total_input_tokens": 12000,
      "total_output_tokens": 10000,
      "total_tokens": 22000,
      "total_cost": 0.022,
      "stream_calls": 50,
      "non_stream_calls": 250
    }
  }
]
```

**示例代码**:

```javascript
const response = await fetch('http://localhost:8000/statistics/all-keys', {
  headers: {
    'X-API-Key': 'sk-admin-key'
  }
});
const allKeysStats = await response.json();

// 渲染排行榜
allKeysStats.forEach(item => {
  console.log(`${item.api_key_name}: ¥${item.statistics.total_cost}`);
});
```

---

### 5. 查询调用日志

查询详细的 API 调用日志，支持分页和筛选。

**端点**: `GET /statistics/logs`

**权限**: 
- 管理员：可查看所有日志
- 普通用户：只能查看自己的日志

**请求参数**:

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| key_name | string | 否 | 筛选指定 API Key（管理员专用） | - |
| model_name | string | 否 | 筛选指定模型 | - |
| start_date | string (ISO 8601) | 否 | 开始时间 | - |
| end_date | string (ISO 8601) | 否 | 结束时间 | - |
| page | integer | 否 | 页码（从 1 开始） | 1 |
| page_size | integer | 否 | 每页数量（1-500） | 50 |

**响应示例**:

```json
{
  "logs": [
    {
      "id": 123,
      "timestamp": "2024-01-15T10:30:45.123456",
      "api_key_name": "test-user",
      "endpoint": "/menglong/chat",
      "method": "POST",
      "status_code": 200,
      "model_name": "deepseek-chat",
      "input_tokens": 150,
      "output_tokens": 200,
      "total_tokens": 350,
      "cost": 0.000035,
      "latency_ms": 1250,
      "error_message": null,
      "is_stream": false
    }
  ],
  "total": 1250,
  "page": 1,
  "page_size": 50,
  "total_pages": 25
}
```

**日志字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | integer | 日志 ID |
| timestamp | string | 请求时间（ISO 8601） |
| api_key_name | string | API Key 名称 |
| endpoint | string | 请求端点 |
| method | string | HTTP 方法 |
| status_code | integer | 响应状态码 |
| model_name | string | 使用的模型名称 |
| input_tokens | integer | 输入 Token 数 |
| output_tokens | integer | 输出 Token 数 |
| total_tokens | integer | 总 Token 数 |
| cost | float | 本次调用费用（元） |
| latency_ms | integer | 延迟（毫秒） |
| error_message | string | 错误信息（如有） |
| is_stream | boolean | 是否为流式请求 |

**示例代码**:

```javascript
// 分页查询
async function fetchLogs(page = 1) {
  const response = await fetch(
    `http://localhost:8000/statistics/logs?page=${page}&page_size=20`,
    {
      headers: {
        'X-API-Key': 'sk-your-api-key'
      }
    }
  );
  return await response.json();
}

// 筛选特定模型
async function fetchModelLogs(modelName) {
  const response = await fetch(
    `http://localhost:8000/statistics/logs?model_name=${modelName}`,
    {
      headers: {
        'X-API-Key': 'sk-your-api-key'
      }
    }
  );
  return await response.json();
}
```

---

### 6. 导出统计数据

导出统计数据为 CSV 或 JSON 格式。

**端点**: `GET /statistics/export`

**权限**: 
- 管理员：可导出所有数据
- 普通用户：只能导出自己的数据

**请求参数**:

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| format | string | 否 | 导出格式：`csv` 或 `json` | csv |
| key_name | string | 否 | 筛选指定 API Key（管理员专用） | - |
| start_date | string (ISO 8601) | 否 | 开始时间 | - |
| end_date | string (ISO 8601) | 否 | 结束时间 | - |

**响应**: 文件下载

**Content-Type**:
- CSV: `text/csv`
- JSON: `application/json`

**示例代码**:

```javascript
// 下载 CSV
async function downloadCSV() {
  const response = await fetch(
    'http://localhost:8000/statistics/export?format=csv',
    {
      headers: {
        'X-API-Key': 'sk-your-api-key'
      }
    }
  );
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'statistics.csv';
  a.click();
}

// 下载 JSON
async function downloadJSON() {
  const response = await fetch(
    'http://localhost:8000/statistics/export?format=json',
    {
      headers: {
        'X-API-Key': 'sk-your-api-key'
      }
    }
  );
  
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'statistics.json';
  a.click();
}
```

**CSV 格式示例**:

```csv
ID,时间,API Key,端点,方法,状态码,模型,输入Tokens,输出Tokens,总Tokens,费用(元),延迟(ms),是否流式,错误信息
123,2024-01-15T10:30:45,test-user,/menglong/chat,POST,200,deepseek-chat,150,200,350,0.000035,1250,否,
```

---

### 7. 清理旧记录（仅管理员）

删除指定天数之前的统计记录。

**端点**: `POST /statistics/cleanup`

**权限**: 仅管理员

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | integer | 是 | 保留最近 N 天的记录（≥1） |

**响应示例**:

```json
{
  "message": "已清理 5000 条旧记录",
  "deleted_count": 5000,
  "retention_days": 90
}
```

**示例代码**:

```javascript
// 清理 90 天前的记录
async function cleanupOldRecords() {
  const response = await fetch(
    'http://localhost:8000/statistics/cleanup?days=90',
    {
      method: 'POST',
      headers: {
        'X-API-Key': 'sk-admin-key'
      }
    }
  );
  const result = await response.json();
  console.log(result.message);
}
```

---

### 8. Dashboard 页面

提供可视化统计界面。

**端点**: `GET /statistics/dashboard`

**权限**: 公开访问（页面内需要输入 API Key）

**访问方式**: 直接在浏览器中打开

```
http://localhost:8000/statistics/dashboard
```

---

## 错误处理

### 常见错误码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 400 | 请求参数错误 | 时间格式不正确、分页参数超出范围 |
| 401 | 未认证 | 缺少 API Key 或 Key 无效 |
| 403 | 权限不足 | 普通用户访问管理员端点 |
| 404 | 资源不存在 | 指定的 Key 不存在 |
| 500 | 服务器错误 | 数据库错误、内部异常 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

---

## 数据类型定义

### UsageStatistics

```typescript
interface UsageStatistics {
  total_calls: number;          // 总调用次数
  successful_calls: number;     // 成功调用次数
  failed_calls: number;         // 失败调用次数
  total_input_tokens: number;   // 总输入 Token
  total_output_tokens: number;  // 总输出 Token
  total_tokens: number;         // 总 Token
  total_cost: number;           // 总费用（元）
  stream_calls: number;         // 流式调用次数
  non_stream_calls: number;     // 非流式调用次数
}
```

### KeyStatistics

```typescript
interface KeyStatistics {
  api_key_name: string;         // API Key 名称
  statistics: UsageStatistics;  // 统计数据
}
```

### ApiCallLog

```typescript
interface ApiCallLog {
  id: number;                   // 日志 ID
  timestamp: string;            // 时间戳（ISO 8601）
  api_key_name: string;         // API Key 名称
  endpoint: string;             // 请求端点
  method: string;               // HTTP 方法
  status_code: number | null;   // 状态码
  model_name: string | null;    // 模型名称
  input_tokens: number;         // 输入 Token
  output_tokens: number;        // 输出 Token
  total_tokens: number;         // 总 Token
  cost: number;                 // 费用（元）
  latency_ms: number | null;    // 延迟（毫秒）
  error_message: string | null; // 错误信息
  is_stream: boolean;           // 是否流式
}
```

### LogsResponse

```typescript
interface LogsResponse {
  logs: ApiCallLog[];           // 日志列表
  total: number;                // 总记录数
  page: number;                 // 当前页码
  page_size: number;            // 每页数量
  total_pages: number;          // 总页数
}
```

---

## 最佳实践

### 1. 时间范围查询

```javascript
// 获取最近 7 天的数据
const endDate = new Date();
const startDate = new Date();
startDate.setDate(startDate.getDate() - 7);

const response = await fetch(
  `http://localhost:8000/statistics/my?start_date=${startDate.toISOString()}&end_date=${endDate.toISOString()}`,
  {
    headers: {
      'X-API-Key': 'sk-your-api-key'
    }
  }
);
```

### 2. 分页处理

```javascript
// 获取所有日志（分页）
async function fetchAllLogs() {
  let allLogs = [];
  let page = 1;
  let hasMore = true;
  
  while (hasMore) {
    const response = await fetch(
      `http://localhost:8000/statistics/logs?page=${page}&page_size=100`,
      {
        headers: {
          'X-API-Key': 'sk-your-api-key'
        }
      }
    );
    
    const data = await response.json();
    allLogs = allLogs.concat(data.logs);
    
    hasMore = page < data.total_pages;
    page++;
  }
  
  return allLogs;
}
```

### 3. 错误处理

```javascript
async function fetchStatsWithErrorHandling() {
  try {
    const response = await fetch('http://localhost:8000/statistics/my', {
      headers: {
        'X-API-Key': 'sk-your-api-key'
      }
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('API Key 无效');
      } else if (response.status === 403) {
        throw new Error('权限不足');
      } else {
        throw new Error(`请求失败: ${response.status}`);
      }
    }
    
    return await response.json();
  } catch (error) {
    console.error('获取统计数据失败:', error);
    throw error;
  }
}
```

### 4. 检查管理员权限

```javascript
async function checkAdminStatus(apiKey) {
  try {
    const response = await fetch('http://localhost:8000/statistics/overview', {
      headers: {
        'X-API-Key': apiKey
      }
    });
    
    return response.ok; // 200 = 管理员，403 = 普通用户
  } catch (error) {
    return false;
  }
}
```

---

## 完整示例：构建统计面板

```javascript
class StatisticsClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = 'http://localhost:8000';
    this.isAdmin = false;
  }
  
  async init() {
    this.isAdmin = await this.checkAdmin();
  }
  
  async checkAdmin() {
    const response = await fetch(`${this.baseUrl}/statistics/overview`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    return response.ok;
  }
  
  async getMyStats(startDate, endDate) {
    const params = new URLSearchParams();
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    
    const response = await fetch(
      `${this.baseUrl}/statistics/my?${params}`,
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    );
    
    if (!response.ok) throw new Error('Failed to fetch stats');
    return await response.json();
  }
  
  async getAllKeysStats() {
    if (!this.isAdmin) {
      throw new Error('Admin access required');
    }
    
    const response = await fetch(`${this.baseUrl}/statistics/all-keys`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    
    if (!response.ok) throw new Error('Failed to fetch all keys stats');
    return await response.json();
  }
  
  async getLogs(options = {}) {
    const params = new URLSearchParams();
    if (options.page) params.append('page', options.page);
    if (options.pageSize) params.append('page_size', options.pageSize);
    if (options.modelName) params.append('model_name', options.modelName);
    
    const response = await fetch(
      `${this.baseUrl}/statistics/logs?${params}`,
      {
        headers: { 'X-API-Key': this.apiKey }
      }
    );
    
    if (!response.ok) throw new Error('Failed to fetch logs');
    return await response.json();
  }
}

// 使用示例
const client = new StatisticsClient('sk-your-api-key');
await client.init();

// 获取统计
const stats = await client.getMyStats();
console.log(`总调用: ${stats.total_calls}`);
console.log(`总费用: ¥${stats.total_cost}`);

// 管理员功能
if (client.isAdmin) {
  const allStats = await client.getAllKeysStats();
  console.log('所有 Keys 统计:', allStats);
}
```

---

## 联系与支持

- **API 文档**: http://localhost:8000/docs
- **Dashboard**: http://localhost:8000/statistics/dashboard
- **健康检查**: http://localhost:8000/health
