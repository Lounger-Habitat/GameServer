"""Connection information models."""

from typing import Dict, List, Optional
from pydantic import BaseModel

from .message import ClientType


class ConnectionInfo(BaseModel):
    """Connection information for status reporting."""

    environments: List[int]
    agents: Dict[int, List[int]]  # agent_id -> [env_id]
    humans: Dict[int, List[int]]  # human_id -> [env_id]

    @property
    def env_count(self) -> int:
        """Number of connected environments."""
        return len(self.environments)

    @property
    def agent_count(self) -> int:
        """Total number of connected agents."""
        return sum(len(envs) for envs in self.agents.values())

    @property
    def human_count(self) -> int:
        """Total number of connected humans."""
        return sum(len(envs) for envs in self.humans.values())


class ClientConnectionInfo(BaseModel):
    """Individual client connection information."""

    client_type: ClientType
    client_id: Optional[int] = None
    env_id: Optional[int] = None
    connected_at: float
    last_ping: Optional[float] = None
