"""WebSocket 测试脚本"""
import asyncio
import json
from websockets import connect


async def test_websocket():
    """测试 WebSocket 连接"""
    uri = "ws://localhost:8000/ws"
    
    print(f"🔌 连接到 WebSocket: {uri}")
    
    try:
        async with connect(uri) as websocket:
            # 接收欢迎消息
            welcome = await websocket.recv()
            print(f"\n✅ 收到欢迎消息:")
            print(json.dumps(json.loads(welcome), indent=2, ensure_ascii=False))
            
            # 发送测试消息
            test_message = "Hello from WebSocket client!"
            print(f"\n📤 发送消息: {test_message}")
            await websocket.send(test_message)
            
            # 接收响应
            response = await websocket.recv()
            print(f"\n📥 收到响应:")
            print(json.dumps(json.loads(response), indent=2, ensure_ascii=False))
            
            print("\n✅ WebSocket 测试成功！")
            
    except Exception as e:
        print(f"\n❌ WebSocket 测试失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
