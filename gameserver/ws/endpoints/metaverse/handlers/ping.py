"""Ping/Heartbeat message handler."""

import json
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler
from ..models import ClientType


class PingHandler(BaseMessageHandler):
    """Handler for ping/heartbeat messages."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle ping messages for heartbeat monitoring."""
        try:
            msg_from = message.get("msg_from", {})
            envelope_timestamp = message.get("timestamp")

            # Update ping time for connection monitoring
            client_type = ClientType(msg_from.get("role_type", "unknown"))
            client_id = msg_from.get("agent_id") or msg_from.get("human_id")
            env_id = msg_from.get("env_id")

            if client_type != ClientType.SERVER:
                self.manager.update_ping_time(client_type, client_id, env_id)

            # Respond with pong
            response = self._create_response(
                instruction="pong",
                data={
                    "original_timestamp": envelope_timestamp,
                    "message": "Pong from server",
                },
                target=msg_from,
            )

            await websocket.send_text(json.dumps(response))
            self.logger.debug(f"Pong sent to {client_type.value}")

        except Exception as e:
            self.logger.error(f"Failed to handle ping: {e}")
            error_response = self._create_error_response(
                f"Failed to process ping: {str(e)}", message.get("msg_from", {})
            )
            await websocket.send_text(json.dumps(error_response))
