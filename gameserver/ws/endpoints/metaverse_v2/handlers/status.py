"""Status message handler."""

import json
from typing import Dict, Any
from fastapi import WebSocket

from .base import BaseMessageHandler
from ..models import ClientType


class StatusHandler(BaseMessageHandler):
    """Handler for status request messages."""

    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle status request messages."""
        self.logger.info("Query Hub Status")
        try:
            connection_info = self.manager.get_connection_info()

            response = self._build_hub_envelope(
                msg_type="message",
                payload={
                    "status": "ok",
                    "connections": {
                        "env_info": connection_info.env_info,
                        "agent_info": connection_info.agent_info,
                        "human_info": connection_info.human_info,
                    },
                },
                target=message.get("sender", {}),
            )

            await websocket.send_text(json.dumps(response))
            self.logger.info("Status information Done!")

        except Exception as e:
            self.logger.error(f"Failed to handle status request: {e}")
            error_response = self._build_hub_envelope(
                "error", f"Failed to get status: {str(e)}", message.get("sender", {})
            )
            await websocket.send_text(json.dumps(error_response))
