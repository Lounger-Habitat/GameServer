"""Direct message handler."""

import json
import traceback
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler
from ..models import ClientType
from ..utils import ClientNotFoundError, EnvironmentNotFoundError


class MessageHandler(BaseMessageHandler):
    """Handler for direct messages between clients."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle direct messages."""
        try:
            sender = message.get("sender", {})
            recipient = message.get("recipient", {})

            # 详细检查发送者和接收者格式
            if not isinstance(sender, dict):
                raise ValueError(
                    f"Sender must be a dictionary, got {type(sender).__name__}: {sender}"
                )

            if not isinstance(recipient, dict):
                raise ValueError(
                    f"Recipient must be a dictionary, got {type(recipient).__name__}: {recipient}"
                )

            sender_type = sender.get("type")
            sender_id = sender.get("id")
            recipient_type = recipient.get("type")
            recipient_id = recipient.get("id")

            self.logger.info(
                f"Routing direct message from {sender_type}:{sender_id} to {recipient_type}:{recipient_id}"
            )

            # 路由检测：验证接收者类型和ID的有效性
            if not recipient_type:
                raise ValueError("Recipient type is required and cannot be empty")

            # 验证接收者类型是否为有效的 ClientType
            try:
                ClientType(recipient_type)
            except ValueError:
                valid_types = [t.value for t in ClientType]
                raise ValueError(
                    f"Invalid recipient type '{recipient_type}'. Valid types: {valid_types}"
                )

            # 对于非 HUB 类型，验证是否有 ID
            if recipient_type != ClientType.HUB.value and not recipient_id:
                raise ValueError(
                    f"Recipient ID is required for type '{recipient_type}'"
                )

            success = await self.manager.route_message(sender, recipient, message)
            self.logger.info(f"Message routing {'succeeded' if success else 'failed'}")

            if not success:
                await self._send_error(
                    websocket,
                    f"Failed to deliver message to {recipient_type}:{recipient_id}",
                    sender,
                    additional_info="Message routing failed, check if recipient is connected and available",
                )

        except (ClientNotFoundError, EnvironmentNotFoundError) as e:
            self.logger.error(f"Client/Environment not found: {e}")
            await self._send_error(websocket, str(e), sender, traceback.format_exc())
        except ValueError as e:
            self.logger.error(f"Validation error in message handling: {e}")
            await self._send_error(
                websocket,
                f"Message validation error: {str(e)}",
                sender,
                traceback.format_exc(),
            )
        except Exception as e:
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "message_data": message,
            }
            self.logger.error(f"Unexpected error in message handler: {error_details}")
            await self._send_error(
                websocket, f"Server error: {str(e)}", sender, traceback.format_exc()
            )

    async def _send_error(
        self,
        websocket: WebSocket,
        error_message: str,
        target: Dict[str, Any],
        traceback_info: str = None,
        additional_info: str = None,
    ) -> None:
        """Send error response to client."""
        error_payload = {
            "error": error_message,
            "debug_info": (
                traceback_info if traceback_info else "No traceback available"
            ),
        }

        if additional_info:
            error_payload["additional_info"] = additional_info

        error_response = self._build_hub_envelope("error", error_payload, target)
        await websocket.send_text(json.dumps(error_response))
