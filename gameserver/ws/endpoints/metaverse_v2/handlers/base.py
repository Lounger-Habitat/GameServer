"""Base message handler class."""

from abc import ABC, abstractmethod
from datetime import datetime
import time
from typing import Dict, Any
from fastapi import WebSocket

from ..models import Envelope, ClientInfo, ClientType
from ..manager.connection_manager import ConnectionManager
from gameserver.utils.log import get_logger


class BaseMessageHandler(ABC):
    """Base class for message handlers."""

    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    async def handle(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle the message."""
        pass

    def _build_hub_envelope(
        self, msg_type: str, payload: Any, target: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a standardized envelope."""
        return {
            "type": msg_type,
            "payload": payload,
            "sender": ClientInfo(type=ClientType.HUB).model_dump(),
            "msg_to": target,
            "timestamp": datetime.now().timestamp(),
        }
