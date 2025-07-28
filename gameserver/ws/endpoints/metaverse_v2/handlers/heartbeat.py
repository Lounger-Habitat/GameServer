"""Ping/Heartbeat message handler."""

import json
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler
from ..models import ClientType


class HeartbeatHandler(BaseMessageHandler):
    """Handler for ping/heartbeat messages."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle ping messages for heartbeat monitoring."""
        try:
            sender = message.get("sender", {})
            envelope_timestamp = message.get("timestamp")

            if sender.get("type") != ClientType.HUB.value:
                self.manager.update_heartbeat_time(sender)

            # self.logger.info(f"Heartbeat received from {sender.get('id')}")
            response = self._build_hub_envelope(
                msg_type="message",
                payload={
                    "message": "ACK",
                },
                target=sender,
            )
            await websocket.send_text(json.dumps(response))

        except Exception as e:
            self.logger.error(f"Failed to handle heartbeat: {e}")
            error_response = self._build_hub_envelope(
                msg_type="error",
                payload={
                    "original_timestamp": envelope_timestamp,
                    "message": f"Failed to process heartbeat: {str(e)}",
                },
                target=sender,
            )
            await websocket.send_text(json.dumps(error_response))
