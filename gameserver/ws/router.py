"""Router configuration for WebSocket endpoints."""

from fastapi import APIRouter

from gameserver.ws.endpoints import game_events

ws_router = APIRouter()

# Include WebSocket endpoints
ws_router.include_router(game_events.router)