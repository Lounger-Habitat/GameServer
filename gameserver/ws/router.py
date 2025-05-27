"""Router configuration for WebSocket endpoints."""

from fastapi import APIRouter

from gameserver.ws.endpoints import game_events, metaverse

ws_router = APIRouter()

# Include WebSocket endpoints
# ws_router.include_router(game_events.router)
ws_router.include_router(metaverse.router)
