"""Refactored WebSocket endpoints for the star server."""

import json
from typing import Dict, Optional, Callable
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from .models import Envelope, ClientInfo, ClientType, MessageType
from .manager.connection_manager import ConnectionManager
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
        self.logger = get_logger(__name__)
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

        @self.router.websocket("/ws/metaverse/env/{env_id}")
        async def env_websocket(websocket: WebSocket, env_id: str):
            """WebSocket endpoint for environments."""

            await self._handle_websocket_connection(
                websocket, client_type="env", env_id=env_id
            )

        @self.router.websocket("/ws/metaverse/env/{env_id}/{client_type}/{client_id}")
        async def client_websocket(
            websocket: WebSocket, client_type: str, env_id: str, client_id: str
        ):
            """WebSocket endpoint for agents and humans."""
            if client_type == ClientType.AGENT.value:
                await self._handle_websocket_connection(
                    websocket,
                    client_type=client_type,
                    env_id=env_id,
                    agent_id=client_id,
                )
            elif client_type == ClientType.HUMAN.value:
                await self._handle_websocket_connection(
                    websocket,
                    client_type=client_type,
                    env_id=env_id,
                    human_id=client_id,
                )
            else:
                await websocket.close(
                    code=status.WS_1008_POLICY_VIOLATION,
                    reason=f"Invalid WebSocket type: {client_type}",
                )

    async def _handle_websocket_connection(
        self,
        websocket: WebSocket,
        client_type: str,
        env_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        human_id: Optional[str] = None,
    ) -> None:
        """Handle individual WebSocket connection lifecycle."""

        try:
            # Connect the client
            await self.manager.connect(
                client_type=client_type,
                websocket=websocket,
                env_id=env_id,
                agent_id=agent_id,
                human_id=human_id,
            )

            current_websocket_client = ClientInfo(
                type=client_type, id=agent_id or human_id or env_id
            )

            # Connection confirmation
            await self.connection_confirmation(
                websocket, client_type, env_id, agent_id, human_id
            )

            # Main message processing loop
            await self._message_processing_loop(websocket, current_websocket_client)

        except WebSocketDisconnect:
            self.logger.info(
                f"WebSocket disconnected: {client_type} (env: {env_id}, agent: {agent_id}, human: {human_id})"
            )
        except Exception as e:
            self.logger.error(f"Unexpected error in WebSocket handler: {e}")
        finally:
            # Always ensure cleanup
            await self.manager.disconnect(
                client_type=client_type,
                websocket=websocket,
                env_id=env_id,
                agent_id=agent_id,
                human_id=human_id,
            )

    async def connection_confirmation(
        self,
        websocket: WebSocket,
        client_type: str,
        env_id: Optional[str],
        agent_id: Optional[str],
        human_id: Optional[str],
    ) -> None:
        """Send connection confirmation message."""

        confirmation = Envelope(
            type=MessageType.CONNECT,
            payload=f"Connected as {client_type} to environment {env_id}",
            sender=ClientInfo(type=ClientType.HUB),
            recipient=ClientInfo(
                type=ClientType(client_type),
                id=agent_id or human_id or env_id,
            ),
        )

        await websocket.send_text(confirmation.model_dump_json())
        self.logger.info(
            f"Connection confirmed for {client_type}, ID: {agent_id or human_id or env_id}"
        )

    async def _message_processing_loop(
        self,
        websocket: WebSocket,
        client_info: ClientInfo,
    ) -> None:
        """Main message processing loop."""

        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message = await self._check_message_format(data)

                if message:
                    await self._process_message(websocket, message)

            except WebSocketDisconnect:
                # Re-raise to be handled by outer try-catch
                raise
            except ValidationError as e:
                await self._validation_error(websocket, client_info, str(e))
            except json.JSONDecodeError:
                await self._json_error(websocket, client_info, data)
            except Exception as e:
                await self._processing_error(websocket, client_info, str(e))

    async def _check_message_format(
        self,
        data: str,
    ) -> Optional[Dict]:
        """Parse and validate incoming message."""

        try:
            message = json.loads(data)
            print(f"message({type(message)}): {message}")
        except json.JSONDecodeError:
            raise ValidationError("Invalid JSON format")

        # Validate required fields
        required_fields = ["type", "payload", "sender", "recipient", "timestamp"]
        for field in required_fields:
            if field not in message:
                raise ValidationError(f"Message must include '{field}' field")
            if field == "sender" or field == "recipient":
                if not message.get(field, {}).get("type"):
                    raise ValidationError(
                        f"Message '{field}' must include 'type' field"
                    )
                # if not message.get(field, {}).get("id"):
                #     raise ValidationError(f"Message '{field}' must include 'id' field")
        return message

    async def _process_message(self, websocket: WebSocket, message: Dict) -> None:
        """Process validated message using appropriate handler."""
        msg_type = message.get("type", "")
        handler = self.handlers.get(msg_type)

        # self.logger.info(f"Processing message of type: {msg_type}, content: {message}")
        if handler:
            await handler(websocket, message)
        else:
            await self._unknown_type_error(websocket, msg_type, message)

    async def _validation_error(
        self, websocket: WebSocket, client_info: ClientInfo, error_message: str
    ) -> None:
        """Send validation error response."""

        error_response = Envelope(
            type=MessageType.ERROR.value,
            payload=f"Validation error: {error_message}",
            sender=ClientInfo(type=ClientType.HUB),
            recipient=client_info,
        )

        await websocket.send_text(error_response.model_dump_json())

    async def _json_error(
        self, websocket: WebSocket, client_info: ClientInfo, invalid_data: str
    ) -> None:
        """Send JSON parsing error response."""

        self.logger.error(f"Invalid JSON received: {invalid_data[:100]}...")

        error_response = Envelope(
            type=MessageType.ERROR.value,
            payload="Invalid JSON format",
            sender=ClientInfo(type=ClientType.HUB),
            recipient=client_info,
        )

        await websocket.send_text(error_response.model_dump_json())

    async def _processing_error(
        self, websocket: WebSocket, client_info: ClientInfo, error_message: str
    ) -> None:
        """Send general processing error response."""

        self.logger.error(f"Error processing message: {error_message}")

        error_response = Envelope(
            type=MessageType.ERROR.value,
            payload=f"Server error: {error_message}",
            sender=ClientInfo(type=ClientType.HUB),
            recipient=client_info,
        )

        await websocket.send_text(error_response.model_dump_json())

    async def _unknown_type_error(
        self, websocket: WebSocket, msg_type: str, message: Dict
    ) -> None:
        """Send unknown message type error response."""

        self.logger.warning(f"Unknown message type: {msg_type}")

        error_response = Envelope(
            type=MessageType.ERROR.value,
            payload=f"Unknown message type: {msg_type}",
            sender=ClientInfo(type=ClientType.HUB),
            recipient=message.get("sender", {}),
        )

        await websocket.send_text(error_response.model_dump_json())


# Create server instance and export router
server = MetaverseWebSocketServer()
router = server.router
