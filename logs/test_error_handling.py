#!/usr/bin/env python3
"""测试改进后的错误处理和路由检测"""

import asyncio
import json
import websockets
from typing import Dict, Any


async def test_invalid_recipient_format():
    """测试无效的接收者格式"""
    uri = "ws://localhost:8000/ws/metaverse/env/test_env/agent/test_agent"

    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            response = await websocket.recv()
            print(f"Connection response: {response}")

            # 测试1: recipient 是字符串而不是字典
            invalid_message_1 = {
                "type": "message",
                "payload": "test message",
                "sender": {"type": "agent", "id": "test_agent"},
                "recipient": "invalid_recipient",  # 这里应该是字典
                "timestamp": "2024-01-01T00:00:00",
            }

            print("\n=== Testing recipient as string ===")
            await websocket.send(json.dumps(invalid_message_1))
            response = await websocket.recv()
            print(f"Error response: {json.loads(response)}")

            # 测试2: recipient 缺少 type 字段
            invalid_message_2 = {
                "type": "message",
                "payload": "test message",
                "sender": {"type": "agent", "id": "test_agent"},
                "recipient": {"id": "test_human"},  # 缺少 type 字段
                "timestamp": "2024-01-01T00:00:00",
            }

            print("\n=== Testing recipient without type ===")
            await websocket.send(json.dumps(invalid_message_2))
            response = await websocket.recv()
            print(f"Error response: {json.loads(response)}")

            # 测试3: recipient 有无效的 type
            invalid_message_3 = {
                "type": "message",
                "payload": "test message",
                "sender": {"type": "agent", "id": "test_agent"},
                "recipient": {"type": "invalid_type", "id": "test_id"},
                "timestamp": "2024-01-01T00:00:00",
            }

            print("\n=== Testing recipient with invalid type ===")
            await websocket.send(json.dumps(invalid_message_3))
            response = await websocket.recv()
            print(f"Error response: {json.loads(response)}")

            # 测试4: recipient 类型为 agent 但缺少 id
            invalid_message_4 = {
                "type": "message",
                "payload": "test message",
                "sender": {"type": "agent", "id": "test_agent"},
                "recipient": {"type": "agent"},  # 缺少 id 字段
                "timestamp": "2024-01-01T00:00:00",
            }

            print("\n=== Testing recipient without required id ===")
            await websocket.send(json.dumps(invalid_message_4))
            response = await websocket.recv()
            print(f"Error response: {json.loads(response)}")

            # 测试5: 尝试路由到不存在的客户端
            invalid_message_5 = {
                "type": "message",
                "payload": "test message",
                "sender": {"type": "agent", "id": "test_agent"},
                "recipient": {"type": "agent", "id": "nonexistent_agent"},
                "timestamp": "2024-01-01T00:00:00",
            }

            print("\n=== Testing routing to nonexistent client ===")
            await websocket.send(json.dumps(invalid_message_5))
            response = await websocket.recv()
            print(f"Error response: {json.loads(response)}")

    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure the server is running on localhost:8000")


async def test_invalid_json():
    """测试无效的JSON格式"""
    uri = "ws://localhost:8000/ws/metaverse/env/test_env/agent/test_agent"

    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            response = await websocket.recv()
            print(f"Connection response: {response}")

            print("\n=== Testing invalid JSON ===")
            # 发送无效的JSON
            await websocket.send("{ invalid json format")
            response = await websocket.recv()
            print(f"Error response: {json.loads(response)}")

    except Exception as e:
        print(f"Connection failed: {e}")


if __name__ == "__main__":
    print("Testing improved error handling and routing detection...")
    print("=" * 60)

    asyncio.run(test_invalid_recipient_format())
    print("\n" + "=" * 60)
    asyncio.run(test_invalid_json())
