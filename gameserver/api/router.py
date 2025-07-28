"""Router configuration for RESTful API endpoints."""

from fastapi import APIRouter

from gameserver.api.endpoints import auth, agent, metaverse  # games, players

api_router = APIRouter(prefix="/api")

# Include specific API endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(metaverse.router, prefix="/rotk", tags=["RoTK"])
