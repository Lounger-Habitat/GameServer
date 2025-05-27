"""WebSocket event handling system."""

import json
import asyncio
import time
from typing import Dict, List, Callable, Awaitable, Any, Optional
from datetime import datetime

from fastapi import WebSocket

from gameserver.utils.log.logger import get_logger

logger = get_logger(__name__)

# 类型别名定义
EventHandler = Callable[
    [WebSocket, dict, str, Optional[int], Optional[int], Optional[int]], Awaitable[None]
]


class WebSocketEventHandler:
    """Event-based handler for WebSocket messages."""

    def __init__(
        self,
        websocket: WebSocket,
        ws_type: str,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        human_id: Optional[int] = None,
    ):
        """Initialize the event handler with client details."""
        self.websocket = websocket
        self.ws_type = ws_type
        self.env_id = env_id
        self.agent_id = agent_id
        self.human_id = human_id

        self.handlers: Dict[str, List[EventHandler]] = {}
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 30  # 30秒发送一次心跳
        self.heartbeat_timeout = 90  # 90秒无心跳则认为连接断开
        self.is_connected = True

    def register_handler(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def register_handlers(self, handlers: Dict[str, EventHandler]) -> None:
        """Register multiple handlers at once."""
        for event_type, handler in handlers.items():
            self.register_handler(event_type, handler)

    async def handle_event(self, event_type: str, message: dict) -> bool:
        """Handle an event of the specified type."""
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    await handler(
                        self.websocket,
                        message,
                        self.ws_type,
                        self.env_id,
                        self.agent_id,
                        self.human_id,
                    )
                except Exception as e:
                    logger.error(f"Error in handler for {event_type}: {e}")
            return True
        return False

    async def handle_message(self, data: str) -> None:
        """Process an incoming WebSocket message."""
        try:
            message = json.loads(data)
            msg_type = message.get("type", "")

            # 处理心跳消息
            if msg_type == "heartbeat":
                self.last_heartbeat = time.time()
                await self.websocket.send_text(
                    json.dumps(
                        {
                            "type": "heartbeat_ack",
                            "data": {"server_time": time.time(), "received": True},
                        }
                    )
                )
                return

            # 记录消息接收
            logger.info(f"Received message type: {msg_type} from {self.ws_type}")

            # 尝试分发到特定处理器
            handled = await self.handle_event(msg_type, message)

            # 如果没有特定处理器，尝试使用通用处理器
            if not handled:
                await self.handle_event("*", message)

            # 发送确认
            await self.websocket.send_text(
                json.dumps({"type": "ack", "data": {"received": msg_type}})
            )

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {data}")
            await self.websocket.send_text(
                json.dumps({"type": "error", "data": {"message": "Invalid JSON"}})
            )

    async def start_heartbeat(self) -> None:
        """Start sending heartbeat messages periodically."""
        while self.is_connected:
            try:
                # 检查连接是否超时
                current_time = time.time()
                if current_time - self.last_heartbeat > self.heartbeat_timeout:
                    logger.warning(f"Heartbeat timeout for {self.ws_type} connection")
                    self.is_connected = False
                    break

                # 发送心跳
                await self.websocket.send_text(
                    json.dumps(
                        {
                            "type": "heartbeat",
                            "data": {
                                "timestamp": current_time,
                                "client_info": {
                                    "type": self.ws_type,
                                    "env_id": self.env_id,
                                    "agent_id": self.agent_id,
                                    "human_id": self.human_id,
                                },
                            },
                        }
                    )
                )

                # 等待下一次心跳
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                # 任务被取消，正常退出
                logger.debug("Heartbeat task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in heartbeat: {e}")
                break

    async def start_processing(self) -> None:
        """Start processing incoming messages."""
        # 启动心跳检查任务
        heartbeat_task = asyncio.create_task(self.start_heartbeat())

        try:
            # 主消息处理循环
            while self.is_connected:
                # 接收消息
                data = await self.websocket.receive_text()
                # 处理消息
                await self.handle_message(data)
        except Exception as e:
            logger.error(f"Error processing messages: {e}")
            self.is_connected = False
        finally:
            # 清理心跳任务
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
