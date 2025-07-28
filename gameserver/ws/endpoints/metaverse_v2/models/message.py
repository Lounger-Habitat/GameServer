"""Message models for WebSocket communication."""

from datetime import datetime
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field
import time


class ClientType(str, Enum):
    """Client type enumeration."""

    ENV = "env"
    AGENT = "agent"
    HUMAN = "human"
    HUB = "hub"


class MessageType(str, Enum):
    """Message type enumeration."""

    # Server messages
    STATUS = "status"

    # Connection messages
    CONNECT = "connect"
    DISCONNECT = "disconnect"

    # Error messages
    ERROR = "error"

    # Communication messages
    HEARTBEAT = "heartbeat"

    # Data messages
    MESSAGE = "message"


class ClientInfo(BaseModel):
    """WebSocket client identification information."""

    type: ClientType
    id: Optional[str] = None


class Envelope(BaseModel):
    """Envelope model"""

    type: MessageType = Field(..., description="Message type")
    sender: Optional[ClientInfo] = Field(None, description="Message sender")
    recipient: Optional[ClientInfo] = Field(None, description="Message recipient")
    payload: Union[str, dict, None] = Field(..., description="Message data payload")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="Message timestamp"
    )


if __name__ == "__main__":
    # Example usage
    message = Envelope(
        type=MessageType.MESSAGE,
        sender=ClientInfo(type=ClientType.AGENT, id="agent123"),
        recipient=ClientInfo(type=ClientType.HUMAN, id="human456"),
        payload="Hello, World!",
    )
    print(type(message.model_dump_json()))
    print(message.model_dump_json())
    print(type(datetime.now()))
    print(datetime.now())
