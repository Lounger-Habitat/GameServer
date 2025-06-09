"""Direct message handler."""

import json
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
            msg_from = message.get("msg_from", {})
            msg_to = message.get("msg_to", {})

            # Validate message structure
            if not msg_to:
                await self._send_error(
                    websocket, "Direct message must specify target", msg_from
                )
                return

            target_type = msg_to.get("role_type")
            if not target_type:
                await self._send_error(
                    websocket, "Direct message must specify target role_type", msg_from
                )
                return

            # Validate target client information
            target_env_id = msg_to.get("env_id")
            target_client_id = msg_to.get("agent_id") or msg_to.get("human_id")

            if target_type in ["agent", "human"] and not target_client_id:
                await self._send_error(
                    websocket,
                    f"Direct message to {target_type} must specify {target_type}_id",
                    msg_from,
                )
                return

            # Send the message
            from_type = msg_from.get("role_type", "unknown")
            self.logger.info(
                f"Routing direct message from {from_type} to {target_type} {target_client_id or target_env_id}"
            )

            success = await self.manager.send_direct_message(
                target_type, target_client_id, target_env_id, message
            )

            if not success:
                await self._send_error(
                    websocket,
                    f"Failed to deliver message to {target_type} {target_client_id or target_env_id}",
                    msg_from,
                )

        except (ClientNotFoundError, EnvironmentNotFoundError) as e:
            await self._send_error(websocket, str(e), message.get("msg_from", {}))
        except Exception as e:
            self.logger.error(f"Failed to handle direct message: {e}")
            await self._send_error(
                websocket, f"Server error: {str(e)}", message.get("msg_from", {})
            )

    async def _send_error(
        self, websocket: WebSocket, error_message: str, target: Dict[str, Any]
    ) -> None:
        """Send error response to client."""
        error_response = self._create_error_response(error_message, target)
        await websocket.send_text(json.dumps(error_response))
