"""Refactored WebSocket endpoints for the star server."""

import json
from typing import Dict, Optional, Callable
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from .models import WSMessage, WSIDInfo, ClientType, MessageType
from .core.connection_manager import ConnectionManager
from .handlers import (
    StatusHandler,
    HeartbeatHandler,
    MessageHandler,
)
from .utils import ValidationError
from gameserver.utils.log import get_logger


class MetaverseWebSocketServer:
    """Enhanced WebSocket server for metaverse communication."""

    def __init__(self):
        self.manager = ConnectionManager()
        self.logger = get_logger(__name__, level="debug")
        self.router = APIRouter()

        # Initialize message handlers
        self.handlers: Dict[str, Callable] = {
            MessageType.STATUS.value: StatusHandler(self.manager).handle,
            MessageType.HEARTBEAT.value: HeartbeatHandler(self.manager).handle,
            MessageType.MESSAGE.value: MessageHandler(self.manager).handle,
        }

        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup WebSocket routes."""

        @self.router.websocket("/ws/metaverse/{ws_type}/{env_id}")
        async def env_websocket(websocket: WebSocket, ws_type: str, env_id: int):
            """WebSocket endpoint for environments."""
            if ws_type != ClientType.ENV.value:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"Invalid WebSocket type: {ws_type}",
                )
                return

            await self._handle_websocket_connection(
                websocket, ws_type=ws_type, env_id=env_id
            )

        @self.router.websocket("/ws/metaverse/{ws_type}/{env_id}/{client_id}")
        async def client_websocket(
            websocket: WebSocket, ws_type: str, env_id: int, client_id: int
        ):
            """WebSocket endpoint for agents and humans."""
            if ws_type == ClientType.AGENT.value:
                await self._handle_websocket_connection(
                    websocket, ws_type=ws_type, env_id=env_id, agent_id=client_id
                )
            elif ws_type == ClientType.HUMAN.value:
                await self._handle_websocket_connection(
                    websocket, ws_type=ws_type, env_id=env_id, human_id=client_id
                )
            else:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"Invalid WebSocket type: {ws_type}",
                )

    async def _handle_websocket_connection(
        self,
        websocket: WebSocket,
        ws_type: str,
        env_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        human_id: Optional[int] = None,
    ) -> None:
        """Handle individual WebSocket connection lifecycle."""

        try:
            # Connect the client
            await self.manager.connect(
                ws_type=ws_type,
                websocket=websocket,
                env_id=env_id,
                agent_id=agent_id,
                human_id=human_id,
            )

            # Send connection confirmation
            await self._send_connection_confirmation(
                websocket, ws_type, env_id, agent_id, human_id
            )

            # Main message processing loop
            await self._message_processing_loop(
                websocket, ws_type, env_id, agent_id, human_id
            )

        except WebSocketDisconnect:
            self.logger.info(
                f"WebSocket disconnected: {ws_type} (env: {env_id}, agent: {agent_id}, human: {human_id})"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in WebSocket handler: {e}")
        finally:
            # Always ensure cleanup
            await self.manager.disconnect(
                ws_type=ws_type,
                websocket=websocket,
                env_id=env_id,
                agent_id=agent_id,
                human_id=human_id,
            )

    async def _send_connection_confirmation(
        self,
        websocket: WebSocket,
        ws_type: str,
        env_id: Optional[int],
        agent_id: Optional[int],
        human_id: Optional[int],
    ) -> None:
        """Send connection confirmation message."""

        confirmation = WSMessage(
            instruction=MessageType.CONNECT,
            data=f"Connected as {ws_type} to environment {env_id}",
            msg_from=WSIDInfo(role_type=ClientType.SERVER),
            msg_to=WSIDInfo(
                role_type=ClientType(ws_type),
                env_id=env_id,
                agent_id=agent_id,
                human_id=human_id,
            ),
        )

        await websocket.send_text(confirmation.model_dump_json())
        self.logger.info(f"Connection confirmed for {ws_type}")

    async def _message_processing_loop(
        self,
        websocket: WebSocket,
        ws_type: str,
        env_id: Optional[int],
        agent_id: Optional[int],
        human_id: Optional[int],
    ) -> None:
        """Main message processing loop."""

        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = await self._parse_and_validate_message(
                    data, ws_type, env_id, agent_id, human_id
                )

                if message:
                    await self._process_message(websocket, message)

            except WebSocketDisconnect:
                # Re-raise to be handled by outer try-catch
                raise
            except ValidationError as e:
                await self._send_validation_error(websocket, str(e))
            except json.JSONDecodeError:
                await self._send_json_error(websocket, data)
            except Exception as e:
                await self._send_processing_error(websocket, str(e))

    async def _parse_and_validate_message(
        self,
        data: str,
        ws_type: str,
        env_id: Optional[int],
        agent_id: Optional[int],
        human_id: Optional[int],
    ) -> Optional[Dict]:
        """Parse and validate incoming message."""

        try:
            message = json.loads(data)
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format")

        # Standardize message format
        self._standardize_message_format(message)

        # Ensure msg_from has correct information
        self._ensure_message_sender_info(message, ws_type, env_id, agent_id, human_id)

        # Validate message instruction
        msg_ins = message.get("instruction", "")
        if not msg_ins:
            raise ValidationError("Message must include 'ins' field")

        self.logger.debug(f"Received {msg_ins} from {ws_type}")
        return message

    def _standardize_message_format(self, message: Dict) -> None:
        """Standardize message format to handle legacy field names."""

        # Handle legacy 'from'/'to' fields
        if "from" in message and "msg_from" not in message:
            message["msg_from"] = message["from"]
        if "to" in message and "msg_to" not in message:
            message["msg_to"] = message["to"]

    def _ensure_message_sender_info(
        self,
        message: Dict,
        ws_type: str,
        env_id: Optional[int],
        agent_id: Optional[int],
        human_id: Optional[int],
    ) -> None:
        """Ensure message has correct sender information."""

        msg_from = message.get("msg_from", {})

        if not msg_from.get("role_type"):
            message["msg_from"] = {
                "role_type": ws_type,
                "env_id": env_id,
                "agent_id": agent_id,
                "human_id": human_id,
            }

    async def _process_message(self, websocket: WebSocket, message: Dict) -> None:
        """Process validated message using appropriate handler."""

        msg_ins = message.get("instruction", "")
        handler = self.handlers.get(msg_ins)

        if handler:
            await handler(websocket, message)
        else:
            await self._send_unknown_message_error(websocket, msg_ins, message)

    async def _send_validation_error(
        self, websocket: WebSocket, error_message: str
    ) -> None:
        """Send validation error response."""

        error_response = {
            "instruction": MessageType.ERROR.value,
            "data": f"Validation error: {error_message}",
            "msg_from": WSIDInfo(role_type=ClientType.SERVER).model_dump(),
            "timestamp": WSMessage(instruction=MessageType.ERROR, data="").timestamp,
        }

        await websocket.send_text(json.dumps(error_response))

    async def _send_json_error(self, websocket: WebSocket, invalid_data: str) -> None:
        """Send JSON parsing error response."""

        self.logger.error(f"Invalid JSON received: {invalid_data[:100]}...")

        error_response = {
            "instruction": MessageType.ERROR.value,
            "data": "Invalid JSON format",
            "msg_from": WSIDInfo(role_type=ClientType.SERVER).model_dump(),
            "timestamp": WSMessage(instruction=MessageType.ERROR, data="").timestamp,
        }

        await websocket.send_text(json.dumps(error_response))

    async def _send_processing_error(
        self, websocket: WebSocket, error_message: str
    ) -> None:
        """Send general processing error response."""

        self.logger.error(f"Error processing message: {error_message}")

        error_response = {
            "instruction": MessageType.ERROR.value,
            "data": f"Server error: {error_message}",
            "msg_from": WSIDInfo(role_type=ClientType.SERVER).model_dump(),
            "timestamp": WSMessage(instruction=MessageType.ERROR, data="").timestamp,
        }

        await websocket.send_text(json.dumps(error_response))

    async def _send_unknown_message_error(
        self, websocket: WebSocket, msg_ins: str, message: Dict
    ) -> None:
        """Send unknown message type error response."""

        self.logger.warning(f"Unknown message type: {msg_ins}")

        error_response = {
            "instruction": MessageType.ERROR.value,
            "data": f"Unknown message type: {msg_ins}",
            "msg_from": WSIDInfo(role_type=ClientType.SERVER).model_dump(),
            "msg_to": message.get("msg_from", {}),
            "timestamp": WSMessage(instruction=MessageType.ERROR, data="").timestamp,
        }

        await websocket.send_text(json.dumps(error_response))


# Create server instance and export router
server = MetaverseWebSocketServer()
router = server.router
