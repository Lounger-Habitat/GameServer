"""Router configuration for WebSocket endpoints."""

from fastapi import APIRouter

from gameserver.ws.endpoints import metaverse

ws_router = APIRouter()

# Include WebSocket endpoints
ws_router.include_router(metaverse.router)
