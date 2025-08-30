# WebSocket 错误处理和路由检测改进

## 问题描述
原系统在处理错误的 WebSocket 消息时，只返回了模糊的错误信息如 `{'error': "str object has no attribute get"}`，无法帮助开发者定位具体的错误原因。缺乏详细的调试信息。

## 解决方案

### 1. 增强消息格式验证 (`mataverse.py`)

#### 改进前：
```python
if field == "sender" or field == "recipient":
    if not message.get(field, {}).get("type"):
        raise ValidationError(f"Message '{field}' must include 'type' field")
```

#### 改进后：
```python
if field == "sender" or field == "recipient":
    field_value = message.get(field)
    
    # 检查是否为字典类型
    if not isinstance(field_value, dict):
        raise ValidationError(
            f"Message '{field}' must be a dictionary object, got {type(field_value).__name__}: {field_value}"
        )
    
    # 检查必需的子字段
    if not field_value.get("type"):
        raise ValidationError(f"Message '{field}' must include 'type' field")
    
    # 验证 type 是否为有效的 ClientType
    try:
        client_type = field_value.get("type")
        ClientType(client_type)  # 验证是否为有效的 ClientType
    except ValueError:
        raise ValidationError(
            f"Message '{field}' has invalid type '{client_type}'. Valid types: {[t.value for t in ClientType]}"
        )
    
    # 对于非 HUB 类型，检查是否有 id 字段
    if field_value.get("type") != ClientType.HUB.value and not field_value.get("id"):
        raise ValidationError(
            f"Message '{field}' with type '{field_value.get('type')}' must include 'id' field"
        )
```

**改进点：**
- 详细检查数据类型，明确指出期望的格式
- 验证 ClientType 的有效性，提供有效类型列表
- 检查必需字段，避免后续处理时出现属性错误

### 2. 添加 Traceback 支持

#### 在多个错误处理函数中添加了 traceback 信息：

```python
import traceback

# 错误处理示例
except Exception as e:
    error_details = {
        "error": str(e),
        "traceback": traceback.format_exc(),
        "message_type": msg_type,
        "message_data": message
    }
    self.logger.error(f"Error in message handler: {error_details}")
    
    # 向客户端发送详细错误信息
    await self._handler_error(websocket, message, str(e), traceback.format_exc())
```

### 3. 增强路由检测 (`connection_manager.py`)

#### 改进前：
```python
async def route_message(self, sender: dict, recipient: dict, message: dict) -> bool:
    try:
        sender = ClientInfo(**sender)
        recipient = ClientInfo(**recipient)
        # ... 简单的路由逻辑
    except Exception as e:
        self.logger.error(f"Failed to send direct message: {e}")
        return False
```

#### 改进后：
```python
async def route_message(self, sender: dict, recipient: dict, message: dict) -> bool:
    try:
        # 详细的路由检测和验证
        self.logger.info(f"Starting message routing - Sender: {sender}, Recipient: {recipient}")
        
        # 验证发送者格式
        if not isinstance(sender, dict):
            raise ValueError(f"Sender must be a dictionary, got {type(sender).__name__}: {sender}")
        
        # 验证接收者格式  
        if not isinstance(recipient, dict):
            raise ValueError(f"Recipient must be a dictionary, got {type(recipient).__name__}: {recipient}")
        
        # 尝试创建 ClientInfo 对象并捕获具体错误
        try:
            sender_info = ClientInfo(**sender)
        except Exception as e:
            error_msg = f"Invalid sender format: {e}. Sender data: {sender}"
            self.logger.error(f"{error_msg}\nTraceback: {traceback.format_exc()}")
            raise ValueError(error_msg)
        
        # ... 详细的路由逻辑
```

**改进点：**
- 分步骤验证数据格式，在每一步都提供详细的错误信息
- 显示可用的客户端/环境列表，帮助调试
- 分离不同类型的路由逻辑到独立方法，便于维护

### 4. 分离路由方法

将路由逻辑分解为专门的方法：
- `_route_to_environment()` - 路由到环境
- `_route_to_agent()` - 路由到代理
- `_route_to_human()` - 路由到人类

每个方法都包含详细的错误检查和可用性检测。

### 5. 改进错误响应格式

#### 改进前：
```python
error_response = Envelope(
    type=MessageType.ERROR.value,
    payload=f"Server error: {error_message}",
    sender=ClientInfo(type=ClientType.HUB),
    recipient=client_info,
)
```

#### 改进后：
```python
error_payload = {
    "error": f"Server error: {error_message}",
    "debug_info": traceback_info if traceback_info else "No traceback available"
}

error_response = Envelope(
    type=MessageType.ERROR.value,
    payload=error_payload,
    sender=ClientInfo(type=ClientType.HUB),
    recipient=client_info,
)
```

## 测试

创建了 `test_error_handling.py` 脚本来测试各种错误情况：

1. **接收者格式错误** - 字符串而非字典
2. **缺少必需字段** - 无 type 或 id 字段
3. **无效的客户端类型** - 不在 ClientType 枚举中
4. **路由到不存在的客户端**
5. **无效的 JSON 格式**

## 效果

### 改进前的错误信息：
```json
{"error": "str object has no attribute get"}
```

### 改进后的错误信息：
```json
{
  "type": "error",
  "payload": {
    "error": "Message validation error: Message 'recipient' must be a dictionary object, got str: invalid_recipient",
    "debug_info": "Traceback (most recent call last):\n  File \"...\", line ..., in handle\n    ...\nValueError: Message 'recipient' must be a dictionary object, got str: invalid_recipient"
  },
  "sender": {"type": "hub"},
  "recipient": {"type": "agent", "id": "test_agent"},
  "timestamp": "2024-01-01T00:00:00"
}
```

## 使用方法

1. 启动服务器
2. 运行测试脚本：
   ```bash
   python test_error_handling.py
   ```
3. 查看详细的错误信息和调试信息

## 总结

通过这些改进，HUB 现在能够：

1. **精确识别错误类型** - 明确指出数据格式问题
2. **提供详细的错误信息** - 包括期望格式、实际收到的数据
3. **显示可用的替代选项** - 如可用的客户端列表、有效的类型值
4. **包含完整的 traceback** - 便于开发者调试
5. **分类错误处理** - 不同类型的错误有不同的处理逻辑

这样就能彻底解决之前只返回模糊错误信息的问题，大大提高了调试效率。