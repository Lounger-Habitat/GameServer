"""WebSocket endpoints for game events."""

from enum import Enum
import json
from typing import Dict, List, Optional, Callable, Awaitable
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel

from gameserver.utils.log.logger import get_logger
from .component.connection_manager import ConnectionManager


class WSIDInfo(BaseModel):
    """Message user id information."""

    role_type: str
    env_id: Optional[int] = None
    agent_id: Optional[int] = None
    human_id: Optional[int] = None


# Models for WebSocket messages
class WSMessage(BaseModel):
    """Base WebSocket message model."""

    ins: str
    data: str
    msg_from: Optional[WSIDInfo]
    msg_to: Optional[WSIDInfo]
    timestamp: Optional[float]


# Create a connection manager instance
manager = ConnectionManager()

router = APIRouter()
logger = get_logger(__name__)


async def handle_status(websocket: WebSocket, message: dict):
    """Handle status request messages. Just for Server."""
    status_info = manager.check_connections()
    await websocket.send_text(
        json.dumps(
            {
                "ins": "status_response",
                "data": {"status": "ok", "connections": status_info},
                "msg_from": WSIDInfo(role_type="server").model_dump(),
                "msg_to": message.get("msg_from", {}),
                "timestamp": time.time(),
            }
        )
    )


async def handle_ping(
    websocket: WebSocket,
    envelope: dict,
):
    """Handle ping messages. Just for Server, Use for heartbeat."""
    msg_to = envelope.get("msg_to", {})
    # to_type = msg_to.get("role_type", "unknown")
    envelope_timestamp = envelope.get("timestamp", None)
    msg_from = envelope.get("msg_from", {})
    # from_type = msg_from.get("role_type", "unknown")
    # which_env = msg_to.get("env_id") if msg_to else msg_from.get("env_id")
    # which_client = (
    #     msg_to.get("agent_id")
    #     or msg_to.get("human_id")
    #     or msg_from.get("agent_id")
    #     or msg_from.get("human_id")
    # )

    # # Forward ping to the environment if coming from agent or human
    # if to_type in ["agent", "human", "env"]:
    #     logger.info(f"Forwarding ping from {from_type} to env {to_type}")
    #     await manager.send_to_environment(which_env, envelope)

    # Respond with pong
    await websocket.send_text(
        json.dumps(
            {
                "ins": "pong",
                "data": {
                    "original_timestamp": envelope_timestamp,
                    "message": f"Pong from server",
                },
                "msg_from": WSIDInfo(role_type="server").model_dump(),
                "msg_to": msg_from,
                "timestamp": time.time(),
            }
        )
    )


async def handle_notification(websocket: WebSocket, message: dict):
    """Handle environment messages."""
    msg_from = message.get("msg_from", {})
    which_env = msg_from.get("env_id")

    if which_env:
        logger.info(
            f"Broadcasting environment update from env {which_env} to all clients"
        )
        await manager.broadcast_to_env_clients(which_env, message)
    else:
        logger.error("Environment message missing env_id")
        await websocket.send_text(
            json.dumps(
                {
                    "ins": "error",
                    "data": "Environment message must include env_id",
                    "msg_from": WSIDInfo(role_type="server").model_dump(),
                    "msg_to": message.get("msg_from", {}),
                    "timestamp": time.time(),
                }
            )
        )


async def handle_echo(
    websocket: WebSocket,
    message: dict,
):
    """Handle echo messages for testing."""
    msg_from = message.get("msg_from", {})
    msg_to = message.get("msg_to", {})
    to_type = msg_to.get("role_type", "unknown")

    if to_type not in ["agent", "human", "env"]:
        # Echo back the message to the sender
        await websocket.send_text(
            json.dumps(
                {
                    "ins": "response",
                    "data": message.get("data", ""),
                    "msg_from": WSIDInfo(role_type="server").model_dump(),
                    "msg_to": msg_from,
                    "timestamp": time.time(),
                }
            )
        )
        logger.info(f"Echoed message back to {msg_from.get('role_type', 'unknown')}")
    else:
        await manager.send_direct_message(
            to_type,
            msg_to.get("agent_id"),
            msg_to.get("env_id"),
            message,
        )


async def handle_message(
    websocket: WebSocket,
    message: dict,
):
    """Handle direct messages."""
    msg_from = message.get("msg_from", {})
    from_type = msg_from.get("role_type", "unknown")
    msg_to = message.get("msg_to", {})
    target_type = msg_to.get("role_type")
    target_env_id = msg_to.get("env_id")
    target_client_id = msg_to.get("agent_id") or msg_to.get("human_id")

    if not target_type:
        await websocket.send_text(
            json.dumps(
                {
                    "ins": "error",
                    "data": "Direct message must specify target role_type",
                    "msg_from": WSIDInfo(role_type="server").model_dump(),
                    "msg_to": msg_from,
                    "timestamp": time.time(),
                }
            )
        )
        return

    if target_type in ["agent", "human"] and not target_client_id:
        await websocket.send_text(
            json.dumps(
                {
                    "ins": "error",
                    "data": f"Direct message to {target_type} must specify {target_type}_id",
                    "msg_from": WSIDInfo(role_type="server").model_dump(),
                    "msg_to": msg_from,
                    "timestamp": time.time(),
                }
            )
        )
        return

    logger.info(
        f"Sending direct message from {from_type} to {target_type} {target_client_id or target_env_id}"
    )

    success = await manager.send_direct_message(
        target_type, target_client_id, target_env_id, message
    )

    if not success:
        await websocket.send_text(
            json.dumps(
                {
                    "ins": "error",
                    "data": f"Failed to send direct message to {target_type} {target_client_id or target_env_id}",
                    "msg_from": WSIDInfo(role_type="server").model_dump(),
                    "msg_to": msg_from,
                    "timestamp": time.time(),
                }
            )
        )


# Define separate route handlers for each pattern
@router.websocket("/ws/metaverse/{ws_type}/{env_id}")
async def env_websocket(websocket: WebSocket, ws_type: str, env_id: int):
    if ws_type == "env":
        await metaverse_websocket_handler(websocket, ws_type=ws_type, env_id=env_id)
    else:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Invalid WebSocket type: {ws_type}",
        )
        return


@router.websocket("/ws/metaverse/{ws_type}/{env_id}/{play_id}")
async def agent_websocket(
    websocket: WebSocket, ws_type: str, env_id: int, play_id: int
):
    if ws_type == "agent":
        await metaverse_websocket_handler(
            websocket, ws_type=ws_type, env_id=env_id, agent_id=play_id
        )
    elif ws_type == "human":
        await metaverse_websocket_handler(
            websocket, ws_type=ws_type, env_id=env_id, human_id=play_id
        )
    else:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Invalid WebSocket type: {ws_type}",
        )


# Message type to handler mapping
HANDLES = {
    "status": handle_status,  # Server status (to server ,no requirement)
    "heartbeat": handle_ping,  # Server heartbeat (to server ,no requirement)
    "ping": handle_ping,  # Alternative name for heartbeat
    "broadcast": handle_ping,  # Environment broadcast messages (to all clients ,requirement env_id)
    "message": handle_message,  # Direct messages (to specific client ,requirement env_id, agent_id or human_id)
    "response": handle_message,  # Direct messages (to specific client ,requirement env_id, agent_id or human_id)
    "echo": handle_message,  # Echo messages (to specific client for test ,echo self no requirement)
}


# Common handler function
async def metaverse_websocket_handler(
    websocket: WebSocket,
    ws_type: str,
    env_id: Optional[int] = None,
    agent_id: Optional[int] = None,
    human_id: Optional[int] = None,
):
    """WebSocket endpoint for metaverse events."""

    try:
        # Connect the client to the manager
        await manager.connect(
            ws_type=ws_type,
            websocket=websocket,
            env_id=env_id,
            agent_id=agent_id,
            human_id=human_id,
        )

        # Send connection confirmation
        await websocket.send_text(
            WSMessage(
                ins="connected",
                data=f"message: {ws_type} connected, env_id: {env_id}",
                msg_from=WSIDInfo(role_type="server"),
                msg_to=WSIDInfo(
                    role_type=ws_type,
                    env_id=env_id,
                    agent_id=agent_id,
                    human_id=human_id,
                ),
                timestamp=time.time(),
            ).model_dump_json()
        )

        # Main message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_ins = message.get("ins", "")

                # Standardize message format - handle both 'from' and 'msg_from'
                if "from" in message and "msg_from" not in message:
                    message["msg_from"] = message["from"]
                if "to" in message and "msg_to" not in message:
                    message["msg_to"] = message["to"]

                msg_from = message.get("msg_from", {})
                role_type = msg_from.get("role_type", ws_type)

                # Ensure msg_from has correct info if missing
                if not msg_from.get("role_type"):
                    message["msg_from"] = {
                        "role_type": ws_type,
                        "env_id": env_id,
                        "agent_id": agent_id,
                        "human_id": human_id,
                    }

                # Log message receipt
                logger.info(f"Received {msg_ins} message from {role_type}")

                # Find appropriate handler
                handler = HANDLES.get(msg_ins)
                if handler:
                    # Handle message
                    await handler(websocket, message)
                else:
                    logger.warning(f"Unhandled message type: {msg_ins}")
                    await websocket.send_text(
                        json.dumps(
                            {
                                "ins": "error",
                                "data": f"Unknown message type: {msg_ins}",
                                "msg_from": WSIDInfo(role_type="server").model_dump(),
                                "msg_to": message.get("msg_from", {}),
                                "timestamp": time.time(),
                            }
                        )
                    )

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received: {data}")
                await websocket.send_text(
                    json.dumps(
                        {
                            "ins": "error",
                            "data": "Invalid JSON format",
                            "msg_from": WSIDInfo(role_type="server").model_dump(),
                            "timestamp": time.time(),
                        }
                    )
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_text(
                    json.dumps(
                        {
                            "ins": "error",
                            "data": f"Server error: {str(e)}",
                            "msg_from": WSIDInfo(role_type="server").model_dump(),
                            "timestamp": time.time(),
                        }
                    )
                )

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket disconnected for {ws_type} (env: {env_id}, agent: {agent_id}, human: {human_id})"
        )
    except Exception as e:
        logger.error(f"Unexpected error in websocket handler: {e}")
    finally:
        # Always disconnect the client
        await manager.disconnect(
            ws_type=ws_type,
            websocket=websocket,
            env_id=env_id,
            agent_id=agent_id,
            human_id=human_id,
        )
