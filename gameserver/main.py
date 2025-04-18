"""Main application module for the GameServer."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gameserver.api.router import api_router
from gameserver.ws.router import ws_router

app = FastAPI(
    title="GameServer",
    description="A game server with RESTful API and WebSocket interfaces",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "GameServer is running"}


def start():
    """Start the application server."""
    uvicorn.run("gameserver.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()