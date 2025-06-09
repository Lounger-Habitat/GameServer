"""Enhanced connection manager for WebSocket connections."""

from typing import Dict, List, Optional, Set
import json
import time
from fastapi import WebSocket

from ..models import WSIDInfo, ClientType, ConnectionInfo
from ..utils import (
    ClientNotFoundError,
    EnvironmentNotFoundError,
    DuplicateConnectionError,
)
from gameserver.utils.log.logger import get_logger


class ConnectionManager:
    """Enhanced manager for WebSocket connections with improved error handling and logging."""

    def __init__(self):
        # Core data structures
        self.envs: Dict[int, WebSocket] = {}
        self.agents: Dict[int, Dict[int, WebSocket]] = (
            {}
        )  # agent_id -> {env_id -> websocket}
        self.humans: Dict[int, Dict[int, WebSocket]] = (
            {}
        )  # human_id -> {env_id -> websocket}

        # Environment membership tracking
        self.env_agents: Dict[int, Set[int]] = {}  # env_id -> {agent_id}
        self.env_humans: Dict[int, Set[int]] = {}  # env_id -> {human_id}

        # Connection metadata
        self.connection_times: Dict[str, float] = {}  # connection_key -> timestamp
        self.last_ping_times: Dict[str, float] = {}  # connection_key -> timestamp

        self.logger = get_logger(__name__)

    def reset(self) -> None:
        """Reset all connections - useful for testing."""
        self.envs.clear()
        self.agents.clear()
        self.humans.clear()
        self.env_agents.clear()
        self.env_humans.clear()
        self.connection_times.clear()
        self.last_ping_times.clear()
        self.logger.info("Connection manager reset")

    def _get_connection_key(
        self, client_type: ClientType, client_id: Optional[int], env_id: Optional[int]
    ) -> str:
        """Generate a unique connection key."""
        return f"{client_type.value}:{client_id or 'none'}:{env_id or 'none'}"

    async def connect(
        self,
        ws_type: str,
        websocket: WebSocket,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        human_id: Optional[int] = None,
    ) -> None:
        """Connect a client based on its type."""
        client_type = ClientType(ws_type)
        connection_key = self._get_connection_key(
            client_type, agent_id or human_id, env_id
        )

        # Accept connection first
        await websocket.accept()

        try:
            if client_type == ClientType.ENV:
                await self._connect_environment(env_id, websocket)
            elif client_type == ClientType.AGENT:
                await self._connect_agent(agent_id, env_id, websocket)
            elif client_type == ClientType.HUMAN:
                await self._connect_human(human_id, env_id, websocket)
            else:
                raise ValueError(f"Invalid WebSocket type: {ws_type}")

            # Record connection metadata
            self.connection_times[connection_key] = time.time()
            self.logger.info(
                f"Connected {client_type.value} (ID: {agent_id or human_id or env_id}, Env: {env_id})"
            )

        except Exception as e:
            self.logger.error(f"Failed to connect {ws_type}: {e}")
            await websocket.close(code=1011, reason=str(e))
            raise

    async def disconnect(
        self,
        ws_type: str,
        websocket: WebSocket,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        human_id: Optional[int] = None,
    ) -> None:
        """Disconnect a client based on its type."""
        client_type = ClientType(ws_type)
        connection_key = self._get_connection_key(
            client_type, agent_id or human_id, env_id
        )

        try:
            if client_type == ClientType.ENV:
                self._disconnect_environment(env_id)
            elif client_type == ClientType.AGENT:
                self._disconnect_agent(agent_id, env_id)
            elif client_type == ClientType.HUMAN:
                self._disconnect_human(human_id, env_id)

            # Clean up metadata
            self.connection_times.pop(connection_key, None)
            self.last_ping_times.pop(connection_key, None)

            self.logger.info(
                f"Disconnected {client_type.value} (ID: {agent_id or human_id or env_id}, Env: {env_id})"
            )

        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")

    async def _connect_environment(self, env_id: int, websocket: WebSocket) -> None:
        """Connect an environment."""
        if env_id is None:
            raise ValueError("Environment ID cannot be None")

        if env_id in self.envs:
            self.logger.warning(
                f"Replacing existing environment connection for env_id {env_id}"
            )

        self.envs[env_id] = websocket

        # Initialize client tracking for this environment
        if env_id not in self.env_agents:
            self.env_agents[env_id] = set()
        if env_id not in self.env_humans:
            self.env_humans[env_id] = set()

    async def _connect_agent(
        self, agent_id: int, env_id: int, websocket: WebSocket
    ) -> None:
        """Connect an agent to an environment."""
        if agent_id is None or env_id is None:
            raise ValueError("Agent ID and Environment ID cannot be None")

        # Initialize agent's environment dict if needed
        if agent_id not in self.agents:
            self.agents[agent_id] = {}

        # Check for duplicate connection
        if env_id in self.agents[agent_id]:
            raise DuplicateConnectionError(
                f"Agent {agent_id} already connected to environment {env_id}"
            )

        # Store connection
        self.agents[agent_id][env_id] = websocket

        # Add to environment tracking
        if env_id not in self.env_agents:
            self.env_agents[env_id] = set()
        self.env_agents[env_id].add(agent_id)

    async def _connect_human(
        self, human_id: int, env_id: int, websocket: WebSocket
    ) -> None:
        """Connect a human to an environment."""
        if human_id is None or env_id is None:
            raise ValueError("Human ID and Environment ID cannot be None")

        # Initialize human's environment dict if needed
        if human_id not in self.humans:
            self.humans[human_id] = {}

        # Check for duplicate connection
        if env_id in self.humans[human_id]:
            raise DuplicateConnectionError(
                f"Human {human_id} already connected to environment {env_id}"
            )

        # Store connection
        self.humans[human_id][env_id] = websocket

        # Add to environment tracking
        if env_id not in self.env_humans:
            self.env_humans[env_id] = set()
        self.env_humans[env_id].add(human_id)

    def _disconnect_environment(self, env_id: int) -> None:
        """Disconnect an environment and clean up all related connections."""
        if env_id not in self.envs:
            self.logger.warning(f"Environment {env_id} not found for disconnect")
            return

        # Remove environment
        del self.envs[env_id]

        # Clean up client tracking
        self.env_agents.pop(env_id, None)
        self.env_humans.pop(env_id, None)

    def _disconnect_agent(self, agent_id: int, env_id: int) -> None:
        """Disconnect an agent from an environment."""
        if agent_id in self.agents and env_id in self.agents[agent_id]:
            del self.agents[agent_id][env_id]

            # Clean up empty agent dict
            if not self.agents[agent_id]:
                del self.agents[agent_id]

        # Remove from environment tracking
        if env_id in self.env_agents:
            self.env_agents[env_id].discard(agent_id)

    def _disconnect_human(self, human_id: int, env_id: int) -> None:
        """Disconnect a human from an environment."""
        if human_id in self.humans and env_id in self.humans[human_id]:
            del self.humans[human_id][env_id]

            # Clean up empty human dict
            if not self.humans[human_id]:
                del self.humans[human_id]

        # Remove from environment tracking
        if env_id in self.env_humans:
            self.env_humans[env_id].discard(human_id)

    async def broadcast_to_env_clients(self, env_id: int, message: dict) -> int:
        """
        Broadcast a message to all clients in an environment.

        Returns:
            Number of successful broadcasts
        """
        if env_id not in self.env_agents and env_id not in self.env_humans:
            self.logger.warning(f"No clients found for env_id {env_id}")
            return 0

        success_count = 0
        message_json = json.dumps(message)

        # Send to agents
        for agent_id in self.env_agents.get(env_id, set()):
            if agent_id in self.agents and env_id in self.agents[agent_id]:
                try:
                    await self.agents[agent_id][env_id].send_text(message_json)
                    success_count += 1
                    self.logger.debug(
                        f"Broadcast sent to agent {agent_id} in env {env_id}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to send broadcast to agent {agent_id}: {e}"
                    )

        # Send to humans
        for human_id in self.env_humans.get(env_id, set()):
            if human_id in self.humans and env_id in self.humans[human_id]:
                try:
                    await self.humans[human_id][env_id].send_text(message_json)
                    success_count += 1
                    self.logger.debug(
                        f"Broadcast sent to human {human_id} in env {env_id}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Failed to send broadcast to human {human_id}: {e}"
                    )

        self.logger.info(f"Broadcast to env {env_id}: {success_count} successful sends")
        return success_count

    async def send_to_environment(self, env_id: int, message: dict) -> bool:
        """Send a message to an environment."""
        if env_id not in self.envs:
            raise EnvironmentNotFoundError(f"Environment {env_id} not found")

        try:
            await self.envs[env_id].send_text(json.dumps(message))
            self.logger.debug(f"Message sent to environment {env_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send to environment {env_id}: {e}")
            return False

    async def send_direct_message(
        self,
        target_type: str,
        target_id: Optional[int],
        env_id: Optional[int],
        message: dict,
    ) -> bool:
        """Send a message to a specific client."""
        try:
            client_type = ClientType(target_type)

            if client_type == ClientType.ENV:
                if env_id is None:
                    raise ValueError("Environment ID required for environment messages")
                return await self.send_to_environment(env_id, message)

            elif client_type == ClientType.AGENT:
                if target_id is None or env_id is None:
                    raise ValueError(
                        "Agent ID and Environment ID required for agent messages"
                    )

                if target_id not in self.agents or env_id not in self.agents[target_id]:
                    raise ClientNotFoundError(
                        f"Agent {target_id} not found in environment {env_id}"
                    )

                await self.agents[target_id][env_id].send_text(json.dumps(message))
                self.logger.debug(
                    f"Direct message sent to agent {target_id} in env {env_id}"
                )
                return True

            elif client_type == ClientType.HUMAN:
                if target_id is None or env_id is None:
                    raise ValueError(
                        "Human ID and Environment ID required for human messages"
                    )

                if target_id not in self.humans or env_id not in self.humans[target_id]:
                    raise ClientNotFoundError(
                        f"Human {target_id} not found in environment {env_id}"
                    )

                await self.humans[target_id][env_id].send_text(json.dumps(message))
                self.logger.debug(
                    f"Direct message sent to human {target_id} in env {env_id}"
                )
                return True

            else:
                raise ValueError(f"Invalid target type: {target_type}")

        except Exception as e:
            self.logger.error(f"Failed to send direct message: {e}")
            return False

    def get_connection_info(self) -> ConnectionInfo:
        """Get comprehensive connection information."""
        return ConnectionInfo(
            environments=list(self.envs.keys()),
            agents={
                agent_id: list(envs.keys()) for agent_id, envs in self.agents.items()
            },
            humans={
                human_id: list(envs.keys()) for human_id, envs in self.humans.items()
            },
        )

    def update_ping_time(
        self, client_type: ClientType, client_id: Optional[int], env_id: Optional[int]
    ) -> None:
        """Update the last ping time for a client."""
        connection_key = self._get_connection_key(client_type, client_id, env_id)
        self.last_ping_times[connection_key] = time.time()

    def is_client_connected(
        self, client_type: ClientType, client_id: Optional[int], env_id: Optional[int]
    ) -> bool:
        """Check if a client is currently connected."""
        if client_type == ClientType.ENV:
            return env_id in self.envs
        elif client_type == ClientType.AGENT:
            return client_id in self.agents and env_id in self.agents[client_id]
        elif client_type == ClientType.HUMAN:
            return client_id in self.humans and env_id in self.humans[client_id]
        return False
