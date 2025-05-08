"""Router configuration for RESTful API endpoints."""

from fastapi import APIRouter

from gameserver.api.endpoints import auth, agent, rotk  # games, players

api_router = APIRouter(prefix="/api")

# Include specific API endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent"])
api_router.include_router(rotk.router, prefix="/rotk", tags=["RoTK"])
# api_router.include_router(games.router, prefix="/games", tags=["Games"])
# api_router.include_router(players.router, prefix="/players", tags=["Players"])
