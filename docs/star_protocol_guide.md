# Star Protocol 使用指南

本服务使用 **Star Protocol Python SDK 0.3.0**，业务协议为 **`agent-env-compact/2`**。Hub 直接使用 SDK 的 `MessageRouter`；客户端必须按新版契约发送消息。

## 启动与端点

在 api_server 根目录运行，配置中需启用 `modules.enable_websocket`：

```bash
uv sync
uv run fastapi dev main.py
```

默认端口为 8000：

- API 文档：<http://localhost:8000/docs>
- 系统监控页面：<http://localhost:8000/hub_monitor>
- WebSocket：`ws://localhost:8000/ws/{role}/{client_id}`
- 监控 API：`GET /api/monitor/stats`、`/api/monitor/clients`、`/api/monitor/clients/{client_id}`、`/api/monitor/environments`、`/api/monitor/environments/{env_id}`、`/api/monitor/health`

| role | 用途 |
|---|---|
| `environment` | 连接时建立同名环境，提供实际工具和事件处理器 |
| `agent` / `human` | 加入环境后与同环境主体交互 |
| `monitor` | 订阅特定客户端的业务遥测 |
| `hub_monitor` | 监听 Hub 的系统与业务消息，供网页监控使用 |

SDK 的 `connect()` 接收基础 URL，例如 `ws://localhost:8000`，自动追加 WebSocket 路径。`sender` 必须与连接的 `client_id` 一致；每个客户端同时只能加入一个环境。

## 消息契约

Wire Envelope 的 **六个字段全部必填**，不允许额外字段。Python 本地构造 `Envelope` 可自动生成 `id/timestamp`，接收端不会替裸 JSON 补齐。

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": 1791590400000,
  "type": "message",
  "sender": "agent_01",
  "recipient": "env_main",
  "payload": {
    "type": "discover",
    "content": {"protocols": ["agent-env-compact/2"]}
  }
}
```

| 字段 | 约束 |
|---|---|
| `id` | 合法 UUID，标识一次物理投递 |
| `timestamp` | 非负整数，Unix 毫秒 |
| `type` | `system` / `message` / `broadcast` / `monitor` |
| `sender` / `recipient` | 非空字符串；接收目标为客户端 ID、`hub` 或环境广播目标 `@env` |
| `payload` | 仅含 `type` 和对象 `content`，类型与 Envelope 匹配 |

| Envelope.type | Payload.type |
|---|---|
| `system` | `ctrl` / `notify` / `error` |
| `message` | `discover` / `specification` / `action` / `outcome` / `event` / `stream` |
| `broadcast` | `event` / `stream` |
| `monitor` | `ctrl` / `data` / `notify` |

主要 Content 约定：

- **Action**：恰好包含 `id`、`name`、对象 `params`。无参工具仍传 `{}`。
- **Outcome**：恰好包含自身 `id`、`refs`、`status`、`data`。`refs` 恰好引用一个 Action 的逻辑 ID；状态为 `accepted`、`running`、`completed`、`rejected`、`failed`、`cancelled`；`data` 仅含非空 `text`。旧 `ref_id/success/error` 格式已移除。
- **Event**：包含 `id`、`name`、`data`，可选 `refs` 引用其他 Event。默认 `data` 仅含非空 `text`；额外字段需要接收方声明 `data_schema`，仍需 `text`。`handler="runtime"` 还需安装真实异步处理器。
- **Discover**：`{"protocols": ["agent-env-compact/2"]}`。
- **Specification**：恰好包含 `protocol`、`tools`、`events`，是完整的接收能力快照。Tool 必填 `name/description/parameters`；Event 必填 `name/description/handler`。

Action、Outcome、Event 的 `content.id` 是逻辑 ID，在首次发送前生成并保存。重试保留相同 ID 与 Content；它与 Envelope 的 UUID 用途不同。`text` 最多 32000 字符；消息模型限制规范化后的 Envelope 不超过 512 KiB，并拒绝重复 JSON 键及非有限数值。

## 先协商，再发送业务

1. 两端在连接前注册自身能接收的 Tool/Event 契约和处理器。
2. Environment 先连接。Agent 发 `system.ctrl` 的 `join`，等待 Hub 的 `joined` 通知；`AgentClient.join_with_retry()` 成功后自动发送 discover。
3. Environment 回送 specification，Agent 保存它并回送自身 specification。SDK 随后调用 `on_specification()`；应用等此信号后再发送 Action/Event。
4. Hub 收到双方声明后才允许业务消息，并校验目标工具和参数 Schema。同环境私聊也必须逐对协商；广播使用 `@env`，发送者须与各接收成员完成协商。

重连后需重新协商；更新能力时重新发布完整快照。声明只描述接收能力，工具的执行仍由应用处理器完成。

## Python：Environment 与 Agent

先启动服务，再将下面代码保存为 `echo_environment.py`，运行 `uv run python echo_environment.py`。它持续提供 `echo` 工具及文本 Event 接收入口：

```python
import asyncio
from star_protocol import EnvironmentClient
from star_protocol.models import gen_id


class EchoEnvironment(EnvironmentClient):
    def __init__(self):
        super().__init__("env_main", auto_reconnect=False)
        self.configure_capabilities(
            tools=[{
                "name": "echo",
                "description": "返回调用者提供的文字。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "minLength": 1, "maxLength": 32000}
                    },
                    "required": ["text"],
                    "additionalProperties": False,
                },
            }],
            events=[{
                "name": "speech", "description": "接收文本发言。", "handler": "model"
            }],
        )

    async def on_action(self, sender, content):
        previous = self.action_outcomes(content["id"])
        if previous:
            for original in previous:
                await self.send_outcome(sender, original)
            return
        await self.send_outcome(sender, {
            "id": gen_id("outcome"), "refs": [content["id"]],
            "status": "completed", "data": {"text": content["params"]["text"]},
        })

    async def on_event(self, sender, content):
        print("Event:", sender, content["data"]["text"], flush=True)


async def main():
    async with EchoEnvironment() as env:
        await env.connect("ws://localhost:8000")
        await env.start()
        print("env_main 已连接，等待成员。", flush=True)
        await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
```

另一终端保存下面代码为 `echo_agent.py`，运行 `uv run python echo_agent.py`。它等待 Environment 的声明，发送 Event 并等待 echo 的终态结果：

```python
import asyncio
from star_protocol import AgentClient, COMPACT_PROTOCOL
from star_protocol.models import gen_id


class EchoAgent(AgentClient):
    def __init__(self):
        super().__init__("agent_01", auto_reconnect=False)
        self.ready = asyncio.Event()
        self.configure_capabilities(tools=[], events=[{
            "name": "speech", "description": "接收文本发言。", "handler": "model"
        }])

    async def on_specification(self, sender, content):
        await super().on_specification(sender, content)
        if sender == "env_main":
            self.ready.set()


async def main():
    async with EchoAgent() as agent:
        await agent.connect("ws://localhost:8000")
        await agent.start()
        await agent.join_with_retry("env_main", timeout=5, retry_interval=0.5)
        await asyncio.wait_for(agent.ready.wait(), timeout=5)
        assert agent.protocol_for("env_main") == COMPACT_PROTOCOL
        await agent.send_event(
            "env_main", "speech", {"text": "准备调用 echo。"}, event_id=gen_id("event")
        )
        action_id = gen_id("action")
        result = await agent.request_action(
            "env_main", "echo", {"text": "你好，Star Protocol。"},
            action_id=action_id, timeout=5,
        )
        assert result["refs"] == [action_id]
        print(result["status"], result["data"]["text"])


if __name__ == "__main__":
    asyncio.run(main())
```

`async with` 负责退出时停止客户端；仍需显式 `connect()` 和 `start()`。`start()` 已启动后台接收循环，随后不再调用 `run()`。`request_action()` 只等待终态，超时代表本地尚未确认，不代表远端失败，也不会自动取消或重发。

## JavaScript：完整报文与能力协商

保持上面的 Environment 运行。在本服务页面的浏览器控制台执行以下代码；它先等 join 确认，再等 Env 声明，发送自身声明后才发送业务。所有报文都含六个 Envelope 字段：

```javascript
const clientId = `agent_web_${crypto.randomUUID()}`;
const envId = 'env_main';
const protocol = 'agent-env-compact/2';
const scheme = location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${scheme}//${location.host}/ws/agent/${clientId}`);
let actionId = null;
const ownSpecification = {
    protocol, tools: [],
    events: [{name: 'speech', description: '接收文本发言。', handler: 'model'}]
};

function send(type, recipient, payloadType, content) {
    ws.send(JSON.stringify({
        id: crypto.randomUUID(), timestamp: Date.now(), type,
        sender: clientId, recipient, payload: {type: payloadType, content}
    }));
}

ws.onopen = () => send('system', 'hub', 'ctrl', {op: 'join', env_id: envId});
ws.onmessage = ({data}) => {
    const envelope = JSON.parse(data);
    const {type, content} = envelope.payload;
    if (envelope.type === 'system') {
        if (envelope.sender === 'hub' && type === 'notify' && content.event === 'joined') {
            send('message', envId, 'discover', {protocols: [protocol]});
        } else if (type === 'error') {
            console.error('Hub error:', content);
        }
        return;
    }
    if (envelope.type !== 'message' || envelope.sender !== envId) return;
    if (type === 'specification' && actionId === null) {
        if (content.protocol !== protocol || !content.tools.some(tool => tool.name === 'echo')) {
            console.error('Env 未提供兼容的 echo 能力。');
            return;
        }
        send('message', envId, 'specification', ownSpecification);
        send('message', envId, 'event', {
            id: `event-${crypto.randomUUID()}`, name: 'speech', data: {text: '准备调用 echo。'}
        });
        actionId = `action-${crypto.randomUUID()}`;
        send('message', envId, 'action', {
            id: actionId, name: 'echo', params: {text: '来自浏览器的问候。'}
        });
    } else if (type === 'outcome' && content.refs[0] === actionId) {
        console.log('Outcome:', content.status, content.data.text);
    }
};
ws.onerror = error => console.error('WebSocket error:', error);
// 演示结束后执行 ws.close()。
```

本例面向上述 echo Schema；通用客户端还应校验收到的声明与数据，并按目标 Schema 构造参数。声明和业务按同一连接的发送顺序到达 Hub，Env 的处理器已在连接前安装。浏览器例子没有自动重连；重连时应重新加入和协商。

## 投递 ACK 与持久化

ACK 使用 **`system.notify`**，`event="ACK"`，`msg` 恰好含 `envelope_id`，指向被确认的原 Envelope UUID。下面的 ACK 假设 Agent 已持久保存 Env 发来的 UUID 为 `550e8400-e29b-41d4-a716-446655440099` 的报文：

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "timestamp": 1791590400100,
  "type": "system",
  "sender": "agent_01",
  "recipient": "env_main",
  "payload": {
    "type": "notify",
    "content": {
      "event": "ACK",
      "msg": {"envelope_id": "550e8400-e29b-41d4-a716-446655440099"}
    }
  }
}
```

应用校验并持久保存完整 Envelope 后，显式调用 `await agent.send_delivery_ack(envelope.sender, envelope.id)`。当前 Hub 支持环境成员向其所属的活动 Environment 发 ACK；Env 在 `on_delivery_ack(sender, envelope_id)` 核对预期接收者并处理 outbox。ACK 确认持久接收，Action 执行结果由 Outcome 表达。

上述最小示例只使用进程内结果缓存，不发送持久 ACK。SDK 不替应用建立持久日志、执行事务或重启恢复；这些能力由应用实现。

## 监控与排查

`/hub_monitor` 页面使用 `hub_monitor` 角色，展示系统、定向业务和广播消息；`monitor` 协议遥测通过订阅客户端接收。网页支持按发送者／接收者搜索、类型过滤、暂停、清空和 JSON 导出。

监控端点的参数和响应见 [Monitor API 文档](MONITOR_API.md)，其他服务文档见 [文档目录](README.md)。

| 现象 | 检查 |
|---|---|
| SDK 导入失败 | 更新后执行 `uv sync`，确保新增依赖已安装 |
| 加入失败 | Environment 是否在线，env_id 是否等于其 client_id |
| Wire／Content 校验失败 | 六个 Envelope 字段、逻辑 ID、Event text 和新版 Outcome 格式 |
| 未协商／未知工具 | 等待 specification；核对双方能力快照及工具参数 Schema |
| 广播拒绝 | 使用 `@env`，确认当前环境及成员间协商 |
| 网页空白 | 检查 `/static`、浏览器控制台与 `/api/monitor/health` |
