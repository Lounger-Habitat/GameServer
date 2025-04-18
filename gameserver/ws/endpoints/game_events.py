"""WebSocket endpoints for game events."""

import json
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel


# Models for WebSocket messages
class WSMessage(BaseModel):
    """Base WebSocket message model."""

    type: str
    data: dict


class GameEvent(BaseModel):
    """Game event model for WebSocket communication."""

    event_type: str
    env_id: Optional[int] = None
    agent_id: Optional[int] = None
    content: dict = {}


# Connection manager for WebSocket clients
class ConnectionManager:
    """Manager for WebSocket connections."""

    def __init__(self):
        # All active connections
        self.active_connections: List[WebSocket] = []
        # Connections by env ID
        self.env_connections: Dict[int, List[WebSocket]] = {}
        # Agent ID to connection mapping
        self.agent_connections: Dict[int, WebSocket] = {}

    def reset(self):
        """Reset all connections - useful for testing."""
        self.active_connections = []
        self.env_connections = {}
        self.agent_connections = {}

    async def connect(
        self,
        websocket: WebSocket,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
    ):
        """Connect a client to the WebSocket server."""
        # Only accept the connection if it's not already in active_connections
        if websocket not in self.active_connections:
            await websocket.accept()
            self.active_connections.append(websocket)

        # Add to env if specified
        if env_id is not None:
            if env_id not in self.env_connections:
                self.env_connections[env_id] = []
            self.env_connections[env_id].append(websocket)

        # Map agent ID to connection if specified
        if agent_id is not None:
            self.agent_connections[agent_id] = websocket

    def disconnect(
        self,
        websocket: WebSocket,
        agent_id: Optional[int] = None,
        env_id: Optional[int] = None,
    ):
        """Disconnect a client from the WebSocket server."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from game room if specified
        if env_id is not None and env_id in self.env_connections:
            if websocket in self.env_connections[env_id]:
                self.env_connections[env_id].remove(websocket)
            # Clean up empty game rooms
            if not self.env_connections[env_id]:
                del self.env_connections[env_id]

        # Remove player mapping if specified
        if agent_id is not None and agent_id in self.agent_connections:
            del self.agent_connections[agent_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific client."""
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

    async def broadcast_to_env(self, env_id: int, message: dict):
        """Broadcast a message to all clients in a specific environment."""
        if env_id in self.env_connections:
            for connection in self.env_connections[env_id]:
                await connection.send_text(json.dumps(message))

    async def send_to_agent(self, agent_id: int, message: dict):
        """Send a message to a specific agent."""
        if agent_id in self.agent_connections:
            await self.agent_connections[agent_id].send_text(json.dumps(message))


# Create a connection manager instance
manager = ConnectionManager()

router = APIRouter()


@router.websocket("/ws")
async def websocket_test_endpoint(websocket: WebSocket):
    """General WebSocket endpoint for all connections."""
    # Authenticate the WebSocket connection
    from gameserver.utils.ws_auth import authenticate_websocket

    authenticated, user_data = await authenticate_websocket(websocket)

    if not authenticated:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="认证失败")
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                # Process the message based on its type
                if "type" in message_data:
                    if message_data["type"] == "test" and "env_id" in message_data:
                        env_id = int(message_data["env_id"])
                        agent_id = int(message_data.get("agent_id", 0))
                        # Re-register the connection with game and player info
                        await manager.connect(websocket, env_id, agent_id)
                        # Notify the game room about the new player
                        await manager.broadcast_to_game(
                            env_id,
                            {
                                "type": "player_joined",
                                "game_id": env_id,
                                "player_id": agent_id,
                                "message": f"Player {agent_id} joined the game",
                            },
                        )
                    elif (
                        message_data["type"] == "game_message"
                        and "game_id" in message_data
                    ):
                        # Forward the message to all players in the game
                        game_id = int(message_data["game_id"])
                        await manager.broadcast_to_game(
                            game_id,
                            {
                                "type": "game_message",
                                "game_id": game_id,
                                "sender": message_data.get("player_id", "unknown"),
                                "content": message_data.get("content", {}),
                            },
                        )
                    else:
                        # Echo the message back to the sender
                        await manager.send_personal_message(
                            {"type": "echo", "content": message_data}, websocket
                        )
                else:
                    # Echo the message back to the sender
                    await manager.send_personal_message(
                        {"type": "echo", "content": message_data}, websocket
                    )
            except json.JSONDecodeError:
                # Send an error message for invalid JSON
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        # Handle disconnection
        manager.disconnect(websocket)


@router.websocket("/ws/{env_id}/{agent_id}")
async def game_websocket_endpoint(websocket: WebSocket, env_id: int, agent_id: int):
    """Game-specific WebSocket endpoint with env and agent identification."""
    # Authenticate the WebSocket connection
    from gameserver.utils.ws_auth import authenticate_websocket

    authenticated, user_data = await authenticate_websocket(websocket)

    if not authenticated:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="认证失败")
        return

    # Connect the websocket with game and player info
    await manager.connect(websocket, env_id, agent_id)
    try:
        # Notify the game room about the new player
        await manager.broadcast_to_game(
            env_id,
            {
                "type": "player_joined",
                "game_id": env_id,
                "player_id": agent_id,
                "message": f"Player {agent_id} joined the game",
            },
        )

        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                # Add game and player context to the message
                message_data["game_id"] = env_id
                message_data["player_id"] = agent_id

                # Process the message based on its type
                if "type" in message_data:
                    if message_data["type"] == "game_message":
                        # Forward the message to all players in the game
                        await manager.broadcast_to_game(
                            env_id,
                            {
                                "type": "game_message",
                                "game_id": env_id,
                                "sender": agent_id,
                                "content": message_data.get("content", {}),
                            },
                        )
                    elif (
                        message_data["type"] == "direct_message"
                        and "to_player_id" in message_data
                    ):
                        # Send a direct message to a specific player
                        to_player_id = int(message_data["to_player_id"])
                        await manager.send_to_player(
                            to_player_id,
                            {
                                "type": "direct_message",
                                "from_player_id": agent_id,
                                "content": message_data.get("content", {}),
                            },
                        )
                    else:
                        # Echo the message back to the sender
                        await manager.send_personal_message(
                            {"type": "echo", "content": message_data}, websocket
                        )
                else:
                    # Echo the message back to the sender
                    await manager.send_personal_message(
                        {"type": "echo", "content": message_data}, websocket
                    )
            except json.JSONDecodeError:
                # Send an error message for invalid JSON
                await manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        # Handle disconnection
        manager.disconnect(websocket, env_id, agent_id)
        # Notify the game room about the player leaving
        await manager.broadcast_to_game(
            env_id,
            {
                "type": "player_left",
                "game_id": env_id,
                "player_id": agent_id,
                "message": f"Player {agent_id} left the game",
            },
        )
