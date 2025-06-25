import json
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler


class ConnectHandler(BaseMessageHandler):
    """Handler for connect messages - useful for verifying connections."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle connect messages."""
        try:
            msg_from = message.get("msg_from", {})
            msg_to = message.get("msg_to", {})
            to_type = msg_to.get("role_type") if msg_to else None

            if to_type and to_type is "server":
                # Handle server connection
                response = self._create_response(
                    instruction="connect",
                    data="Server connected successfully",
                    target=msg_from,
                )
                await websocket.send_text(json.dumps(response))
                self.logger.info(
                    f"Server connected: {msg_from.get('role_type', 'unknown')}"
                )

        except Exception as e:
            self.logger.error(f"Failed to handle connect: {e}")
            error_response = self._create_error_response(
                f"Connect failed: {str(e)}", message.get("msg_from", {})
            )
            await websocket.send_text(json.dumps(error_response))
