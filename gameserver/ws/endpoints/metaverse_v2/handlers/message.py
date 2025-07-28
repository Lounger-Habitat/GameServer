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
            sender = message.get("sender", {})
            recipient = message.get("recipient", {})

            sender_type = sender.get("type")
            sender_id = sender.get("id")
            recipient_type = recipient.get("type")
            recipient_id = recipient.get("id")

            self.logger.info(
                f"Routing direct message from {sender_type}:{sender_id} to {recipient_type}:{recipient_id}"
            )

            success = await self.manager.route_message(sender, recipient, message)
            (f"Message routing {'succeeded' if success else 'failed'}")
            if not success:
                await self._send_error(
                    websocket,
                    f"Failed to deliver message to {recipient_type}:{recipient_id}",
                    sender,
                )

        except (ClientNotFoundError, EnvironmentNotFoundError) as e:
            await self._send_error(websocket, str(e), sender)
        except Exception as e:
            self.logger.error(f"Failed to handle message: {e}")
            await self._send_error(websocket, f"Server error: {str(e)}", sender)

    async def _send_error(
        self, websocket: WebSocket, error_message: str, target: Dict[str, Any]
    ) -> None:
        """Send error response to client."""
        error_response = self._build_hub_envelope("error", error_message, target)
        await websocket.send_text(json.dumps(error_response))
