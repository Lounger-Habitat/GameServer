"""Broadcast message handler."""

import json
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler


class BroadcastHandler(BaseMessageHandler):
    """Handler for broadcast messages to all clients in an environment."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle broadcast messages."""
        try:
            msg_from = message.get("msg_from", {})
            env_id = msg_from.get("env_id")

            if not env_id:
                error_response = self._create_error_response(
                    "Broadcast message must include env_id", msg_from
                )
                await websocket.send_text(json.dumps(error_response))
                return

            # Broadcast to all clients in the environment
            success_count = await self.manager.broadcast_to_env_clients(env_id, message)

            self.logger.info(
                f"Broadcast from env {env_id} sent to {success_count} clients"
            )

            # Optionally send confirmation back to sender
            if success_count == 0:
                warning_response = self._create_response(
                    instruction="broadcast_info",
                    data=f"No clients found in environment {env_id}",
                    target=msg_from,
                )
                await websocket.send_text(json.dumps(warning_response))

        except Exception as e:
            self.logger.error(f"Failed to handle broadcast: {e}")
            error_response = self._create_error_response(
                f"Broadcast failed: {str(e)}", message.get("msg_from", {})
            )
            await websocket.send_text(json.dumps(error_response))
