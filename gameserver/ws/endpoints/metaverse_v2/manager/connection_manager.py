"""Enhanced connection manager for WebSocket connections."""

from datetime import datetime
from typing import Dict, List, Optional, Set
import json
import time
import traceback
from fastapi import WebSocket

from ..models import ClientInfo, ClientType, ConnectionInfo
from ..utils import (
    ClientNotFoundError,
    EnvironmentNotFoundError,
    DuplicateConnectionError,
)
from gameserver.utils.log import get_logger


class ConnectionManager:
    """Enhanced manager for WebSocket connections with improved error handling and logging."""

    def __init__(self):
        # Core data structures
        self.envs: Dict[str, WebSocket] = {}
        self.agents: Dict[str, Dict[str, WebSocket]] = (
            {}
        )  # agent_id -> {env_id -> websocket}
        self.humans: Dict[str, Dict[str, WebSocket]] = (
            {}
        )  # human_id -> {env_id -> websocket}

        # Environment membership tracking
        self.env_agents: Dict[str, Set[str]] = {}  # env_id -> {agent_id}
        self.env_humans: Dict[str, Set[str]] = {}  # env_id -> {human_id}

        # Connection metadata
        self.connection_times: Dict[str, float] = {}  # connection_key -> timestamp
        self.last_heartbeat_times: Dict[str, float] = {}  # connection_key -> timestamp

        self.logger = get_logger(__name__)

    def reset(self) -> None:
        """Reset all connections - useful for testing."""
        self.envs.clear()
        self.agents.clear()
        self.humans.clear()
        self.env_agents.clear()
        self.env_humans.clear()
        self.connection_times.clear()
        self.last_heartbeat_times.clear()
        self.logger.info("Connection manager reset")

    def _get_connection_key(
        self, client_type: ClientType, client_id: str, env_id: Optional[str] = None
    ) -> str:
        """Generate a unique connection key."""
        if client_type == ClientType.ENV:
            return f"{client_type.value}:{client_id or 'none'}"
        return f"{client_type.value}:{client_id or 'none'}:{env_id or 'none'}"

    async def connect(
        self,
        client_type: str,
        websocket: WebSocket,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        human_id: Optional[int] = None,
    ) -> None:
        """Connect a client based on its type."""

        async def _connect_environment(env_id: int, websocket: WebSocket) -> None:
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
            agent_id: int, env_id: int, websocket: WebSocket
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
            human_id: int, env_id: int, websocket: WebSocket
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

        client_type = ClientType(client_type)
        connection_key = self._get_connection_key(
            client_type, agent_id or human_id, env_id
        )

        # Accept connection first
        await websocket.accept()

        try:
            if client_type == ClientType.ENV:
                await _connect_environment(env_id, websocket)
            elif client_type == ClientType.AGENT:
                await _connect_agent(agent_id, env_id, websocket)
            elif client_type == ClientType.HUMAN:
                await _connect_human(human_id, env_id, websocket)
            else:
                raise ValueError(f"Invalid Client type: {client_type}")

            # Record connection metadata
            self.connection_times[connection_key] = datetime.now()
            self.logger.info(
                f"Connected {client_type.value} (ID: {agent_id or human_id or env_id}, Env: {env_id})"
            )

        except Exception as e:
            self.logger.error(f"Failed to connect {client_type}: {e}")
            await websocket.close(code=1011, reason=str(e))
            raise

    async def disconnect(
        self,
        client_type: str,
        websocket: WebSocket,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        human_id: Optional[int] = None,
    ) -> None:
        """Disconnect a client based on its type."""

        def _disconnect_environment(env_id: int) -> None:
            """Disconnect an environment and clean up all related connections."""
            if env_id not in self.envs:
                self.logger.warning(f"Environment {env_id} not found for disconnect")
                return

            # Remove environment
            del self.envs[env_id]

            # Clean up client tracking
            self.env_agents.pop(env_id, None)
            self.env_humans.pop(env_id, None)

        def _disconnect_agent(agent_id: int, env_id: int) -> None:
            """Disconnect an agent from an environment."""
            if agent_id in self.agents and env_id in self.agents[agent_id]:
                del self.agents[agent_id][env_id]

                # Clean up empty agent dict
                if not self.agents[agent_id]:
                    del self.agents[agent_id]

            # Remove from environment tracking
            if env_id in self.env_agents:
                self.env_agents[env_id].discard(agent_id)

        def _disconnect_human(human_id: int, env_id: int) -> None:
            """Disconnect a human from an environment."""
            if human_id in self.humans and env_id in self.humans[human_id]:
                del self.humans[human_id][env_id]

                # Clean up empty human dict
                if not self.humans[human_id]:
                    del self.humans[human_id]

            # Remove from environment tracking
            if env_id in self.env_humans:
                self.env_humans[env_id].discard(human_id)

        client_type = ClientType(client_type)
        connection_key = self._get_connection_key(
            client_type, agent_id or human_id, env_id
        )

        try:
            if client_type == ClientType.ENV:
                _disconnect_environment(env_id)
            elif client_type == ClientType.AGENT:
                _disconnect_agent(agent_id, env_id)
            elif client_type == ClientType.HUMAN:
                _disconnect_human(human_id, env_id)

            # Clean up metadata
            self.connection_times.pop(connection_key, None)
            self.last_heartbeat_times.pop(connection_key, None)

            self.logger.info(
                f"Disconnected {client_type.value} (ID: {agent_id or human_id or env_id}, Env: {env_id})"
            )

        except Exception as e:
            self.logger.error(f"Error during disconnect: {e}")

    async def route_message(
        self,
        sender: dict,
        recipient: dict,
        message: dict,
    ) -> bool:
        """Route a message to a specific client."""

        try:
            # 详细的路由检测和验证
            self.logger.info(
                f"Starting message routing - Sender: {sender}, Recipient: {recipient}"
            )

            # 验证发送者格式
            if not isinstance(sender, dict):
                raise ValueError(
                    f"Sender must be a dictionary, got {type(sender).__name__}: {sender}"
                )

            # 验证接收者格式
            if not isinstance(recipient, dict):
                raise ValueError(
                    f"Recipient must be a dictionary, got {type(recipient).__name__}: {recipient}"
                )

            # 尝试创建 ClientInfo 对象并捕获具体错误
            try:
                sender_info = ClientInfo(**sender)
                self.logger.info(f"Sender info created: {sender_info}")
            except Exception as e:
                error_msg = f"Invalid sender format: {e}. Sender data: {sender}"
                self.logger.error(f"{error_msg}\nTraceback: {traceback.format_exc()}")
                raise ValueError(error_msg)

            try:
                recipient_info = ClientInfo(**recipient)
                self.logger.info(f"Recipient info created: {recipient_info}")
            except Exception as e:
                error_msg = (
                    f"Invalid recipient format: {e}. Recipient data: {recipient}"
                )
                self.logger.error(f"{error_msg}\nTraceback: {traceback.format_exc()}")
                raise ValueError(error_msg)

            # 路由到环境
            if recipient_info.type == ClientType.ENV:
                return await self._route_to_environment(recipient_info, message)

            # 路由到代理
            elif recipient_info.type == ClientType.AGENT:
                return await self._route_to_agent(sender_info, recipient_info, message)

            # 路由到人类
            elif recipient_info.type == ClientType.HUMAN:
                return await self._route_to_human(sender_info, recipient_info, message)

            else:
                raise ValueError(f"Invalid recipient type: {recipient_info.type}")

        except Exception as e:
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "sender": sender,
                "recipient": recipient,
                "message_type": (
                    message.get("type", "unknown")
                    if isinstance(message, dict)
                    else "invalid"
                ),
            }
            self.logger.error(f"Failed to route message: {error_details}")
            return False

    async def _route_to_environment(
        self, recipient_info: ClientInfo, message: dict
    ) -> bool:
        """Route message to environment."""
        self.logger.info(f"Routing message to environment {recipient_info.id}")

        if recipient_info.id is None:
            raise ValueError("Environment ID required for environment messages")

        if recipient_info.id not in self.envs:
            available_envs = list(self.envs.keys())
            raise ClientNotFoundError(
                f"Environment {recipient_info.id} not found. Available environments: {available_envs}"
            )

        try:
            await self.envs[recipient_info.id].send_text(json.dumps(message))
            self.logger.info(
                f"Message successfully sent to environment {recipient_info.id}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to send message to environment {recipient_info.id}: {e}"
            )
            return False

    async def _route_to_agent(
        self, sender_info: ClientInfo, recipient_info: ClientInfo, message: dict
    ) -> bool:
        """Route message to agent."""
        # 获取接收者的环境ID
        recipient_env_id = self.get_env_id(recipient_info)

        self.logger.info(
            f"Routing message to agent {recipient_info.id} in environment {recipient_env_id}"
        )

        if recipient_info.id is None:
            raise ValueError("Agent ID required for agent messages")

        if recipient_env_id is None:
            available_agents = {
                aid: list(envs.keys()) for aid, envs in self.agents.items()
            }
            raise ClientNotFoundError(
                f"Could not determine environment for agent {recipient_info.id}. Available agents: {available_agents}"
            )

        if recipient_info.id not in self.agents:
            available_agents = list(self.agents.keys())
            raise ClientNotFoundError(
                f"Agent {recipient_info.id} not found. Available agents: {available_agents}"
            )

        if recipient_env_id not in self.agents[recipient_info.id]:
            available_envs = list(self.agents[recipient_info.id].keys())
            raise ClientNotFoundError(
                f"Agent {recipient_info.id} not found in environment {recipient_env_id}. Agent is in environments: {available_envs}"
            )

        try:
            # 发送消息给代理
            await self.agents[recipient_info.id][recipient_env_id].send_text(
                json.dumps(message)
            )
            self.logger.info(
                f"Message successfully sent to agent {recipient_info.id} in env {recipient_env_id}"
            )

            # 如果是代理到代理的消息，抄送给环境
            if sender_info.type == ClientType.AGENT:
                if recipient_env_id in self.envs:
                    await self.envs[recipient_env_id].send_text(json.dumps(message))
                    self.logger.info(
                        f"Message carbon copy sent to environment {recipient_env_id}"
                    )
                else:
                    self.logger.warning(
                        f"Environment {recipient_env_id} not found for carbon copy"
                    )

            return True
        except Exception as e:
            self.logger.error(
                f"Failed to send message to agent {recipient_info.id}: {e}"
            )
            return False

    async def _route_to_human(
        self, sender_info: ClientInfo, recipient_info: ClientInfo, message: dict
    ) -> bool:
        """Route message to human."""
        recipient_env_id = self.get_env_id(recipient_info)

        self.logger.info(
            f"Routing message to human {recipient_info.id} in environment {recipient_env_id}"
        )

        if recipient_info.id is None:
            raise ValueError("Human ID required for human messages")

        if recipient_env_id is None:
            available_humans = {
                hid: list(envs.keys()) for hid, envs in self.humans.items()
            }
            raise ClientNotFoundError(
                f"Could not determine environment for human {recipient_info.id}. Available humans: {available_humans}"
            )

        if recipient_info.id not in self.humans:
            available_humans = list(self.humans.keys())
            raise ClientNotFoundError(
                f"Human {recipient_info.id} not found. Available humans: {available_humans}"
            )

        if recipient_env_id not in self.humans[recipient_info.id]:
            available_envs = list(self.humans[recipient_info.id].keys())
            raise ClientNotFoundError(
                f"Human {recipient_info.id} not found in environment {recipient_env_id}. Human is in environments: {available_envs}"
            )

        try:
            await self.humans[recipient_info.id][recipient_env_id].send_text(
                json.dumps(message)
            )
            self.logger.info(
                f"Message successfully sent to human {recipient_info.id} in env {recipient_env_id}"
            )
            return True
        except Exception as e:
            self.logger.error(
                f"Failed to send message to human {recipient_info.id}: {e}"
            )
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

    def update_heartbeat_time(self, client_info: dict) -> None:
        """Update the last heartbeat time for a client."""
        client_info = ClientInfo(**client_info)
        connection_key = self._get_connection_key(
            client_info.type, client_info.id, self.get_env_id(client_info)
        )
        self.last_heartbeat_times[connection_key] = datetime.now()

    def is_client_connected(self, client_info) -> bool:
        """Check if a client is currently connected."""
        if client_info.type == ClientType.ENV:
            return self.get_env_id(client_info) in self.envs
        elif client_info.type == ClientType.AGENT:
            return (
                client_info.id in self.agents
                and self.get_env_id(client_info) in self.agents[client_info.id]
            )
        elif client_info.type == ClientType.HUMAN:
            return (
                client_info.id in self.humans
                and self.get_env_id(client_info) in self.humans[client_info.id]
            )
        return False

    def get_env_id(self, client_info) -> Optional[str]:
        """Get the environment ID for a specific client."""
        client_type = client_info.type
        client_id = client_info.id

        if client_type == ClientType.ENV:
            return client_id
        elif client_type == ClientType.AGENT:
            if client_id in self.agents:
                return next(iter(self.agents[client_id]), None)
        elif client_type == ClientType.HUMAN:
            if client_id in self.humans:
                return next(iter(self.humans[client_id]), None)
        return None
