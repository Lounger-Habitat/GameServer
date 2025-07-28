"""Connection information models."""

from typing import Dict, List, Optional
from pydantic import BaseModel

from .message import ClientType


class ConnectionInfo(BaseModel):
    """Connection information for status reporting."""

    environments: List[str]
    agents: Dict[str, List[str]]  # agent_id -> [env_id]
    humans: Dict[str, List[str]]  # human_id -> [env_id]

    @property
    def env_info(self) -> dict:
        """Number of connected environments."""
        return {
            env_id: {
                "agents": self.agents.get(env_id, []),
                "agent_count": len(self.agents.get(env_id, [])),
                "humans": self.humans.get(env_id, []),
                "human_count": len(self.humans.get(env_id, [])),
            }
            for env_id in self.environments
        }

    @property
    def agent_info(self) -> dict:
        """Total number of connected agents."""
        return {
            "total": sum(len(envs) for envs in self.agents.values()),
            "details": {
                env_id: {
                    "agents": self.agents.get(env_id, []),
                    "agent_count": len(self.agents.get(env_id, [])),
                }
                for env_id in self.environments
            },
        }

    @property
    def human_info(self) -> dict:
        """Total number of connected humans."""
        return {
            "total": sum(len(envs) for envs in self.humans.values()),
            "details": {
                env_id: {
                    "humans": self.humans.get(env_id, []),
                    "human_count": len(self.humans.get(env_id, [])),
                }
                for env_id in self.environments
            },
        }
