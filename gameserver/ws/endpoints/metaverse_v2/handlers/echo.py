"""Echo message handler for testing."""

import json
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler


class EchoHandler(BaseMessageHandler):
    """Handler for echo messages - useful for testing."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle echo messages."""
        try:
            msg_from = message.get("msg_from", {})
            msg_to = message.get("msg_to", {})
            to_type = msg_to.get("role_type") if msg_to else None

            if to_type and to_type in ["agent", "human", "env"]:
                # Forward to the specified target
                target_client_id = msg_to.get("agent_id") or msg_to.get("human_id")
                target_env_id = msg_to.get("env_id")

                success = await self.manager.send_direct_message(
                    to_type, target_client_id, target_env_id, message
                )

                if not success:
                    error_response = self._create_error_response(
                        f"Failed to forward echo to {to_type}", msg_from
                    )
                    await websocket.send_text(json.dumps(error_response))
            else:
                # Echo back to sender
                response = self._create_response(
                    instruction="response",
                    data=message.get("data", ""),
                    target=msg_from,
                )

                await websocket.send_text(json.dumps(response))
                self.logger.info(
                    f"Echoed message back to {msg_from.get('role_type', 'unknown')}"
                )

        except Exception as e:
            self.logger.error(f"Failed to handle echo: {e}")
            error_response = self._create_error_response(
                f"Echo failed: {str(e)}", message.get("msg_from", {})
            )
            await websocket.send_text(json.dumps(error_response))
