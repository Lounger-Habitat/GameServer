from typing import Dict, List, Optional, Any, Tuple
import json
from fastapi import WebSocket

from gameserver.utils.log.logger import get_logger


class ConnectionManager:
    """Manager for WebSocket connections."""

    def __init__(self):
        # Core data structures
        self.envs: Dict[int, WebSocket] = {}  # env_id -> websocket
        self.agents: Dict[int, Dict[int, WebSocket]] = (
            {}
        )  # agent_id -> {env_id -> websocket}
        self.humans: Dict[int, Dict[int, WebSocket]] = (
            {}
        )  # human_id -> {env_id -> websocket}
        self.env_agents: Dict[int, List[int]] = {}  # env_id -> [agent_id]
        self.env_humans: Dict[int, List[int]] = {}  # env_id -> [human_id]

        self.logger = get_logger(__name__)

    def reset(self):
        """Reset all connections - useful for testing."""
        self.envs.clear()
        self.agents.clear()
        self.humans.clear()
        self.env_agents.clear()
        self.env_humans.clear()

    async def connect(self, ws_type: str, websocket: WebSocket, **kwargs):
        """Connect a client based on its type."""
        env_id = kwargs.get("env_id")

        if ws_type == "env":
            await self._connect_client(
                websocket, self.envs, env_id, None, self._setup_env_collections
            )
        elif ws_type == "agent":
            agent_id = kwargs.get("agent_id")
            await self._connect_client(
                websocket,
                self.agents,
                agent_id,
                env_id,
                lambda: self._register_to_env(self.env_agents, env_id, agent_id),
            )
        elif ws_type == "human":
            human_id = kwargs.get("human_id")
            await self._connect_client(
                websocket,
                self.humans,
                human_id,
                env_id,
                lambda: self._register_to_env(self.env_humans, env_id, human_id),
            )
        else:
            raise ValueError(f"Invalid WebSocket type: {ws_type}")

    async def disconnect(self, ws_type: str, websocket: WebSocket, **kwargs):
        """Disconnect a client based on its type."""
        env_id = kwargs.get("env_id")

        if ws_type == "env":
            self._disconnect_env(env_id, websocket)
        elif ws_type == "agent":
            self._disconnect_client(
                self.agents,
                kwargs.get("agent_id"),
                env_id,
                lambda: self._unregister_from_env(
                    self.env_agents, env_id, kwargs.get("agent_id")
                ),
            )
        elif ws_type == "human":
            self._disconnect_client(
                self.humans,
                kwargs.get("human_id"),
                env_id,
                lambda: self._unregister_from_env(
                    self.env_humans, env_id, kwargs.get("human_id")
                ),
            )
        else:
            raise ValueError(f"Invalid WebSocket type: {ws_type}")

    # Helper methods for connect/disconnect
    async def _connect_client(
        self, websocket, collection, primary_id, secondary_id=None, setup_fn=None
    ):
        """Generic method to connect a client."""
        if primary_id is None:
            raise ValueError(f"Primary ID cannot be None")

        if secondary_id is not None:
            # Handle nested collections (agent/human)
            if primary_id not in collection:
                collection[primary_id] = {}

            if secondary_id in collection[primary_id]:
                self.logger.info(
                    f"Client {primary_id} already connected to {secondary_id}"
                )
                raise ValueError("Client already connected to this environment")

            collection[primary_id][secondary_id] = websocket
        else:
            # Handle direct collections (env)
            if primary_id in collection:
                self.logger.info(f"Replacing existing connection for {primary_id}")
            collection[primary_id] = websocket

        # Accept the connection
        await websocket.accept()

        # Call the setup function if provided
        if setup_fn:
            setup_fn()

        self.logger.info(f"New connection established for ID {primary_id}")

    def _disconnect_env(self, env_id, websocket):
        """Disconnect an environment."""
        if env_id in self.envs:
            del self.envs[env_id]
            if env_id in self.env_agents:
                del self.env_agents[env_id]
            if env_id in self.env_humans:
                del self.env_humans[env_id]
            self.logger.info(f"Disconnected env_id {env_id}")
        else:
            self.logger.warning(f"Environment {env_id} not found")

    def _disconnect_client(self, collection, primary_id, secondary_id, cleanup_fn=None):
        """Generic method to disconnect a client."""
        if primary_id in collection and secondary_id in collection[primary_id]:
            # Remove from collection
            del collection[primary_id][secondary_id]

            # Call cleanup function
            if cleanup_fn:
                cleanup_fn()

            self.logger.info(f"Disconnected client {primary_id} from {secondary_id}")
        else:
            self.logger.warning(f"Client {primary_id} not found in {secondary_id}")

    def _setup_env_collections(self):
        """Initialize collections for a new environment."""
        env_id = list(self.envs.keys())[-1]  # Get the last added env_id
        if env_id not in self.env_agents:
            self.env_agents[env_id] = []
        if env_id not in self.env_humans:
            self.env_humans[env_id] = []

    def _register_to_env(self, collection, env_id, client_id):
        """Register a client to an environment."""
        if env_id not in collection:
            collection[env_id] = []
        collection[env_id].append(client_id)

    def _unregister_from_env(self, collection, env_id, client_id):
        """Unregister a client from an environment."""
        if env_id in collection and client_id in collection[env_id]:
            collection[env_id].remove(client_id)

    async def broadcast_to_env_clients(self, env_id: int, message: dict):
        """Broadcast a message to all clients in an environment."""
        if env_id not in self.env_agents and env_id not in self.env_humans:
            self.logger.warning(f"No clients found for env_id {env_id}")
            return

        # Helper function to send message to clients
        async def send_to_clients(collection, env_clients, env_id):
            for client_id in env_clients.get(env_id, []):
                if client_id in collection and env_id in collection[client_id]:
                    try:
                        await collection[client_id][env_id].send_text(
                            json.dumps(message)
                        )
                        self.logger.debug(
                            f"Message sent to client {client_id} in env {env_id}"
                        )
                    except Exception as e:
                        self.logger.error(
                            f"Error sending to client {client_id}: {str(e)}"
                        )

        # Send to all agents and humans
        await send_to_clients(self.agents, self.env_agents, env_id)
        await send_to_clients(self.humans, self.env_humans, env_id)

    async def send_to_environment(self, env_id: int, message: dict):
        """Send a message to an environment."""
        if env_id not in self.envs:
            self.logger.warning(
                f"Environment {env_id} not found. Available: {list(self.envs.keys())}"
            )
            return False

        try:
            await self.envs[env_id].send_text(json.dumps(message))
            return True
        except Exception as e:
            self.logger.error(f"Error sending to environment {env_id}: {str(e)}")
            return False

    async def send_direct_message(
        self, target_type: str, target_id: int, env_id: int, message: dict
    ):
        """Send a message to a specific client."""
        try:
            if target_type == "env":
                return await self.send_to_environment(env_id, message)

            # Map target types to collections
            collections = {"agent": self.agents, "human": self.humans}

            collection = collections.get(target_type)
            if not collection:
                self.logger.warning(f"Invalid target type: {target_type}")
                return False

            if target_id in collection and env_id in collection[target_id]:
                await collection[target_id][env_id].send_text(json.dumps(message))
                self.logger.debug(f"Direct message sent to {target_type} {target_id}")
                return True
            else:
                self.logger.warning(
                    f"{target_type} {target_id} not found in env {env_id}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Error sending direct message: {str(e)}")
            return False

    def check_connections(self):
        """Check and log the status of all connections."""
        env_count = len(self.envs)
        agent_count = sum(len(agents) for agents in self.agents.values())
        human_count = sum(len(humans) for humans in self.humans.values())

        self.logger.info(
            f"连接状态: {env_count}个 env, {agent_count}个 agents, {human_count}个 humans"
        )

        # Summarize connection information
        connection_info = {
            "environments": list(self.envs.keys()),
            "agents": {
                agent_id: list(envs.keys()) for agent_id, envs in self.agents.items()
            },
            "humans": {
                human_id: list(envs.keys()) for human_id, envs in self.humans.items()
            },
        }

        # Log connection details
        for env_id in self.env_agents:
            self.logger.debug(f"环境 {env_id} 拥有的agent : {self.env_agents[env_id]}")
        for env_id in self.env_humans:
            self.logger.debug(f"环境 {env_id} 拥有的人类 : {self.env_humans[env_id]}")

        return connection_info
