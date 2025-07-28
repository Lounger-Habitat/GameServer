"""Router configuration for WebSocket endpoints."""

from fastapi import APIRouter

from gameserver.ws.endpoints import metaverse_v2

ws_router = APIRouter()

# Include WebSocket endpoints
ws_router.include_router(metaverse_v2.router)
