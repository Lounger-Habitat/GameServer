"""Base message handler class."""

from abc import ABC, abstractmethod
from typing import Dict, Any
from fastapi import WebSocket

from ..models import WSMessage, WSIDInfo, ClientType
from ..core.connection_manager import ConnectionManager
from gameserver.utils.log.logger import get_logger


class BaseMessageHandler(ABC):
    """Base class for message handlers."""

    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle the message."""
        pass

    def _create_error_response(
        self, error_message: str, target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "instruction": "error",
            "data": error_message,
            "msg_from": WSIDInfo(role_type=ClientType.SERVER).model_dump(),
            "msg_to": target,
            "timestamp": WSMessage(instruction="error", data="").timestamp,
        }

    def _create_response(
        self, instruction: str, data: Any, target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a standardized response."""
        return {
            "instruction": instruction,
            "data": data,
            "msg_from": WSIDInfo(role_type=ClientType.SERVER).model_dump(),
            "msg_to": target,
            "timestamp": WSMessage(instruction=instruction, data="").timestamp,
        }
