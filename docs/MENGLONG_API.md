# MengLong API 接口文档

## 概述

MengLong API 提供了统一的 LLM 对话接口，支持多个模型提供商（OpenAI、Anthropic、Google、DeepSeek 等）。所有接口都需要 API Key 认证。

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

## 支持的模型

当前支持以下模型：

| 模型 ID | 名称 | 提供商 | 最大 Token | 流式支持 |
|---------|------|--------|-----------|---------|
| `deepseek-chat` | DeepSeek Chat | DeepSeek | 4096 | ✅ |
| `gemini-3-pro-preview` | Gemini 3 Pro | Google | 8192 | ✅ |
| `gemini-3-flash-preview` | Gemini 3 Flash | Google | 8192 | ✅ |
| `gpt-5.1` | GPT-5.1 | OpenAI | 128000 | ✅ |
| `claude-sonnet-4-20250514` | Claude 4.5 Sonnet | Infinigence | 200000 | ✅ |
| `global.anthropic.claude-sonnet-4-5-20250929-v1:0` | Claude 4.5 Sonnet | Anthropic | 200000 | ✅ |

---

## 接口列表

### 1. API 根端点

获取 MengLong API 的基本信息。

**端点**: `GET /menglong/`

**权限**: 需要 API Key

**响应示例**:

```json
{
  "message": "MengLong API",
  "version": "1.0",
  "endpoints": [
    "POST /menglong/chat - 对话补全",
    "GET /menglong/models - 列出支持的模型",
    "GET /menglong/models/{model_id} - 获取模型信息"
  ]
}
```

**示例代码**:

```bash
curl -X GET "http://localhost:8000/menglong/" \
  -H "X-API-Key: sk-your-api-key"
```

---

### 2. 列出所有模型

获取所有支持的模型列表及其详细信息。

**端点**: `GET /menglong/models`

**权限**: 需要 API Key

**响应示例**:

```json
[
  {
    "id": "deepseek-chat",
    "name": "DeepSeek Chat",
    "provider": "DeepSeek",
    "description": "DeepSeek 通用对话模型",
    "max_tokens": 4096,
    "supports": {
      "streaming": true,
      "image": false,
      "audio": false,
      "file": false
    },
    "price": {
      "input": 0.0001,
      "cache_input": 0.0001,
      "output": 0.0001
    }
  },
  {
    "id": "gpt-5.1",
    "name": "GPT-5.1",
    "provider": "OpenAI",
    "description": "OpenAI GPT-5.1 多模态模型",
    "max_tokens": 128000,
    "supports": {
      "streaming": true,
      "image": false,
      "audio": false,
      "file": false
    },
    "price": {
      "input": 0.0001,
      "cache_input": 0.0001,
      "output": 0.0001
    }
  }
]
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 模型唯一标识符 |
| name | string | 模型显示名称 |
| provider | string | 模型提供商 |
| description | string | 模型描述 |
| max_tokens | integer | 最大 token 数 |
| supports | object | 支持的功能（streaming、image、audio、file） |
| price | object | 定价信息（input、cache_input、output，单位：元/token） |

**示例代码**:

```javascript
// JavaScript/TypeScript
const response = await fetch('http://localhost:8000/menglong/models', {
  headers: {
    'X-API-Key': 'sk-your-api-key'
  }
});
const models = await response.json();
console.log(models);
```

```python
# Python
import requests

response = requests.get(
    'http://localhost:8000/menglong/models',
    headers={'X-API-Key': 'sk-your-api-key'}
)
models = response.json()
for model in models:
    print(f"{model['name']} ({model['id']})")
```

---

### 3. 获取指定模型信息

获取特定模型的详细信息。

**端点**: `GET /menglong/models/{model_id}`

**权限**: 需要 API Key

**路径参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| model_id | string | 是 | 模型 ID |

**响应格式**: 同 `/menglong/models` 中的单个模型对象

**错误响应**:

```json
{
  "detail": "模型 'invalid-model' 不存在，使用 GET /menglong/models 查看支持的模型"
}
```

状态码: `404 Not Found`

**示例代码**:

```javascript
const response = await fetch('http://localhost:8000/menglong/models/deepseek-chat', {
  headers: {
    'X-API-Key': 'sk-your-api-key'
  }
});
const model = await response.json();
console.log(`${model.name} - Max Tokens: ${model.max_tokens}`);
```

---

### 4. 对话补全（Chat）

向 LLM 发送对话消息并获取回复，支持流式和非流式两种模式。

**端点**: `POST /menglong/chat`

**权限**: 需要 API Key

**请求体**:

```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "system",
      "content": "你是一个有帮助的助手。"
    },
    {
      "role": "user",
      "content": "你好，请介绍一下自己。"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

**请求参数**:

| 参数 | 类型 | 必填 | 说明 | 默认值 |
|------|------|------|------|--------|
| model | string | 是 | 模型 ID | - |
| messages | array | 是 | 对话消息列表 | - |
| temperature | float | 否 | 温度参数（0-2） | 0.7 |
| max_tokens | integer | 否 | 最大生成 token 数 | null |
| stream | boolean | 否 | 是否流式输出 | false |

**Message 对象**:

```typescript
interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}
```

#### 非流式响应

**响应示例**:

```json
{
  "id": "chatcmpl-123456",
  "model": "deepseek-chat",
  "created": 1704441600,
  "output": {
    "role": "assistant",
    "content": "你好！我是一个 AI 助手，基于大语言模型构建。我可以帮助你回答问题、提供建议、进行对话等。有什么我可以帮助你的吗？"
  },
  "usage": {
    "input_tokens": 25,
    "output_tokens": 45,
    "total_tokens": 70
  },
  "finish_reason": "stop"
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 响应 ID |
| model | string | 使用的模型 |
| created | integer | 创建时间戳 |
| output | object | 输出内容 |
| output.role | string | 角色（通常为 "assistant"） |
| output.content | string | 生成的文本内容 |
| usage | object | Token 使用统计 |
| usage.input_tokens | integer | 输入 token 数 |
| usage.output_tokens | integer | 输出 token 数 |
| usage.total_tokens | integer | 总 token 数 |
| finish_reason | string | 结束原因（stop、length、error 等） |

#### 流式响应

当 `stream: true` 时，返回 NDJSON 格式的流式数据。

**Content-Type**: `application/x-ndjson`

**流式响应示例**:

每行一个 JSON 对象：

```json
{"id":"chatcmpl-123","model":"deepseek-chat","created":1704441600,"delta":{"role":"assistant","content":"你"},"finish_reason":null}
{"id":"chatcmpl-123","model":"deepseek-chat","created":1704441600,"delta":{"content":"好"},"finish_reason":null}
{"id":"chatcmpl-123","model":"deepseek-chat","created":1704441600,"delta":{"content":"！"},"finish_reason":null}
{"id":"chatcmpl-123","model":"deepseek-chat","created":1704441600,"delta":{"content":""},"finish_reason":"stop","usage":{"input_tokens":25,"output_tokens":45,"total_tokens":70}}
```

**StreamResponse 字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 响应 ID |
| model | string | 使用的模型 |
| created | integer | 创建时间戳 |
| delta | object | 增量内容 |
| delta.role | string | 角色（仅第一个 chunk） |
| delta.content | string | 增量文本 |
| finish_reason | string | 结束原因（最后一个 chunk） |
| usage | object | Token 使用统计（最后一个 chunk） |

**示例代码**:

```javascript
// 非流式调用
async function chat(messages) {
  const response = await fetch('http://localhost:8000/menglong/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'sk-your-api-key'
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: messages,
      temperature: 0.7,
      stream: false
    })
  });
  
  const data = await response.json();
  return data.output.content;
}

// 使用示例
const reply = await chat([
  { role: 'user', content: '你好' }
]);
console.log(reply);
```

```javascript
// 流式调用
async function streamChat(messages, onChunk) {
  const response = await fetch('http://localhost:8000/menglong/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'sk-your-api-key'
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: messages,
      temperature: 0.7,
      stream: true
    })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n').filter(line => line.trim());
    
    for (const line of lines) {
      try {
        const data = JSON.parse(line);
        if (data.delta?.content) {
          onChunk(data.delta.content);
        }
      } catch (e) {
        console.error('Parse error:', e);
      }
    }
  }
}

// 使用示例
await streamChat(
  [{ role: 'user', content: '讲个笑话' }],
  (content) => {
    process.stdout.write(content); // 实时输出
  }
);
```

```python
# Python - 非流式
import requests

def chat(messages, model='deepseek-chat'):
    response = requests.post(
        'http://localhost:8000/menglong/chat',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'sk-your-api-key'
        },
        json={
            'model': model,
            'messages': messages,
            'temperature': 0.7,
            'stream': False
        }
    )
    
    data = response.json()
    return data['output']['content']

# 使用示例
reply = chat([
    {'role': 'user', 'content': '你好'}
])
print(reply)
```

```python
# Python - 流式
import requests
import json

def stream_chat(messages, model='deepseek-chat'):
    response = requests.post(
        'http://localhost:8000/menglong/chat',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'sk-your-api-key'
        },
        json={
            'model': model,
            'messages': messages,
            'temperature': 0.7,
            'stream': True
        },
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            try:
                data = json.loads(line)
                if 'delta' in data and 'content' in data['delta']:
                    print(data['delta']['content'], end='', flush=True)
            except json.JSONDecodeError:
                pass
    print()  # 换行

# 使用示例
stream_chat([
    {'role': 'user', 'content': '讲个笑话'}
])
```

---

## 错误处理

### 常见错误码

| 状态码 | 说明 | 示例 |
|--------|------|------|
| 400 | 请求参数错误 | 模型不存在、消息格式错误、参数超出范围 |
| 401 | 未认证 | 缺少 API Key 或 Key 无效 |
| 404 | 资源不存在 | 指定的模型 ID 不存在 |
| 500 | 服务器错误 | LLM 调用失败、内部异常 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

**示例错误**:

```json
{
  "detail": "模型 'invalid-model' 不存在，使用 GET /menglong/models 查看支持的模型"
}
```

```json
{
  "detail": "LLM 调用失败: Connection timeout"
}
```

---

## 数据类型定义

### TypeScript 类型

```typescript
// 消息类型
interface Message {
  role: "system" | "user" | "assistant";
  content: string;
}

// 聊天请求
interface ChatRequest {
  model: string;
  messages: Message[];
  temperature?: number;  // 0-2，默认 0.7
  max_tokens?: number;
  stream?: boolean;      // 默认 false
}

// 输出内容
interface Output {
  role: string;
  content: string;
}

// Token 使用统计
interface Usage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
}

// 非流式响应
interface Response {
  id: string;
  model: string;
  created: number;
  output: Output;
  usage: Usage;
  finish_reason: string;
}

// 流式增量
interface Delta {
  role?: string;
  content: string;
}

// 流式响应
interface StreamResponse {
  id: string;
  model: string;
  created: number;
  delta: Delta;
  finish_reason: string | null;
  usage?: Usage;
}

// 模型信息
interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  description: string | null;
  max_tokens: number | null;
  supports: {
    streaming: boolean;
    image: boolean;
    audio: boolean;
    file: boolean;
  };
  price: {
    input: number;
    cache_input: number;
    output: number;
  } | null;
}
```

---

## 最佳实践

### 1. 错误处理

```javascript
async function safeChat(messages) {
  try {
    const response = await fetch('http://localhost:8000/menglong/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'sk-your-api-key'
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: messages
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Chat failed:', error);
    throw error;
  }
}
```

### 2. 对话历史管理

```javascript
class ChatSession {
  constructor(apiKey, model = 'deepseek-chat') {
    this.apiKey = apiKey;
    this.model = model;
    this.messages = [];
  }
  
  addSystemMessage(content) {
    this.messages.push({ role: 'system', content });
  }
  
  async sendMessage(content) {
    // 添加用户消息
    this.messages.push({ role: 'user', content });
    
    // 调用 API
    const response = await fetch('http://localhost:8000/menglong/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        model: this.model,
        messages: this.messages
      })
    });
    
    const data = await response.json();
    
    // 添加助手回复到历史
    this.messages.push({
      role: 'assistant',
      content: data.output.content
    });
    
    return data.output.content;
  }
  
  clearHistory() {
    this.messages = [];
  }
}

// 使用示例
const session = new ChatSession('sk-your-api-key');
session.addSystemMessage('你是一个友好的助手。');

const reply1 = await session.sendMessage('你好');
console.log(reply1);

const reply2 = await session.sendMessage('我刚才说了什么？');
console.log(reply2); // 会记住之前的对话
```

### 3. 模型选择

```javascript
// 根据任务选择合适的模型
async function selectModel(task) {
  const response = await fetch('http://localhost:8000/menglong/models', {
    headers: { 'X-API-Key': 'sk-your-api-key' }
  });
  const models = await response.json();
  
  if (task === 'long-context') {
    // 选择支持长上下文的模型
    return models.find(m => m.max_tokens >= 100000)?.id || 'claude-sonnet-4-20250514';
  } else if (task === 'fast') {
    // 选择快速模型
    return 'gemini-3-flash-preview';
  } else {
    // 默认模型
    return 'deepseek-chat';
  }
}
```

### 4. 流式输出优化

```javascript
// React 组件示例
function ChatComponent() {
  const [content, setContent] = useState('');
  
  async function handleStream() {
    setContent('');
    
    const response = await fetch('http://localhost:8000/menglong/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'sk-your-api-key'
      },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: [{ role: 'user', content: '讲个故事' }],
        stream: true
      })
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const data = JSON.parse(line);
          if (data.delta?.content) {
            setContent(prev => prev + data.delta.content);
          }
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
  }
  
  return (
    <div>
      <button onClick={handleStream}>开始生成</button>
      <div>{content}</div>
    </div>
  );
}
```

---

## 完整示例：构建聊天客户端

```javascript
class MengLongClient {
  constructor(apiKey, baseUrl = 'http://localhost:8000') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }
  
  async listModels() {
    const response = await fetch(`${this.baseUrl}/menglong/models`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    
    if (!response.ok) throw new Error('Failed to list models');
    return await response.json();
  }
  
  async getModel(modelId) {
    const response = await fetch(`${this.baseUrl}/menglong/models/${modelId}`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    
    if (!response.ok) throw new Error(`Model ${modelId} not found`);
    return await response.json();
  }
  
  async chat(options) {
    const {
      model = 'deepseek-chat',
      messages,
      temperature = 0.7,
      maxTokens,
      stream = false,
      onChunk
    } = options;
    
    const response = await fetch(`${this.baseUrl}/menglong/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        model,
        messages,
        temperature,
        max_tokens: maxTokens,
        stream
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Chat failed');
    }
    
    if (stream) {
      return this._handleStream(response, onChunk);
    } else {
      return await response.json();
    }
  }
  
  async _handleStream(response, onChunk) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullContent = '';
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const data = JSON.parse(line);
          if (data.delta?.content) {
            fullContent += data.delta.content;
            if (onChunk) onChunk(data.delta.content);
          }
        } catch (e) {
          // 忽略解析错误
        }
      }
    }
    
    return { content: fullContent };
  }
}

// 使用示例
const client = new MengLongClient('sk-your-api-key');

// 列出模型
const models = await client.listModels();
console.log('Available models:', models.map(m => m.name));

// 非流式对话
const response = await client.chat({
  model: 'deepseek-chat',
  messages: [
    { role: 'system', content: '你是一个有帮助的助手。' },
    { role: 'user', content: '你好' }
  ]
});
console.log(response.output.content);

// 流式对话
await client.chat({
  model: 'deepseek-chat',
  messages: [{ role: 'user', content: '讲个笑话' }],
  stream: true,
  onChunk: (content) => {
    process.stdout.write(content);
  }
});
```

---

## 联系与支持

- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **统计 Dashboard**: http://localhost:8000/statistics/dashboard
