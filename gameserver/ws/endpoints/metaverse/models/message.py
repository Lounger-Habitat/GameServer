"""Message models for WebSocket communication."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import time


class ClientType(str, Enum):
    """Client type enumeration."""

    ENV = "env"
    AGENT = "agent"
    HUMAN = "human"
    SERVER = "server"


class MessageType(str, Enum):
    """Message type enumeration."""

    # Server messages
    STATUS = "status"
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    ERROR = "error"

    # Communication messages
    PING = "ping"
    PONG = "pong"
    HEARTBEAT = "heartbeat"

    # Data messages
    MESSAGE = "message"
    RESPONSE = "response"
    ECHO = "echo"
    BROADCAST = "broadcast"
    NOTIFICATION = "notification"


class WSIDInfo(BaseModel):
    """WebSocket client identification information."""

    role_type: ClientType
    env_id: Optional[int] = None
    agent_id: Optional[int] = None
    human_id: Optional[int] = None

    def __hash__(self) -> int:
        """Make WSIDInfo hashable for use in dictionaries."""
        return hash((self.role_type, self.env_id, self.agent_id, self.human_id))


class WSMessage(BaseModel):
    """WebSocket message model."""

    instruction: MessageType = Field(..., description="Message instruction/type")
    data: str = Field(..., description="Message data payload")
    msg_from: Optional[WSIDInfo] = Field(None, description="Message sender")
    msg_to: Optional[WSIDInfo] = Field(None, description="Message recipient")
    timestamp: float = Field(default_factory=time.time, description="Message timestamp")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            MessageType: lambda v: v.value,
            ClientType: lambda v: v.value,
        }
