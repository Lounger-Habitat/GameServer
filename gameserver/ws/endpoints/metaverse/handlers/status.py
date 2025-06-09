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
        try:
            connection_info = self.manager.get_connection_info()

            response = self._create_response(
                instruction="status_response",
                data={
                    "status": "ok",
                    "connections": {
                        "environments": connection_info.environments,
                        "agents": connection_info.agents,
                        "humans": connection_info.humans,
                        "total_connections": {
                            "env_count": connection_info.env_count,
                            "agent_count": connection_info.agent_count,
                            "human_count": connection_info.human_count,
                        },
                    },
                },
                target=message.get("msg_from", {}),
            )

            await websocket.send_text(json.dumps(response))
            self.logger.info("Status information sent")

        except Exception as e:
            self.logger.error(f"Failed to handle status request: {e}")
            error_response = self._create_error_response(
                f"Failed to get status: {str(e)}", message.get("msg_from", {})
            )
            await websocket.send_text(json.dumps(error_response))
