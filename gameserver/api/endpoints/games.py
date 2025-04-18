"""Game related API endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from gameserver.models.user import User
from gameserver.utils.auth import get_current_active_user


# Game models
class EnvBase(BaseModel):
    """Base game model."""

    name: str
    description: str
    max_players: int


class Env(EnvBase):
    """Game response model."""

    id: int
    active: bool
    current_players: int = 0

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


# In-memory storage for demo purposes
# In a real application, this would be a database
envs_db = [
    Env(
        id=1,
        name="Adventure Quest",
        description="Fantasy adventure game",
        max_players=10,
        active=True,
        current_players=3,
    ),
    Env(
        id=2,
        name="Space Explorers",
        description="Sci-fi exploration game",
        max_players=5,
        active=True,
        current_players=2,
    ),
]

router = APIRouter()


@router.get("/", response_model=List[Game])
async def get_games():
    """Get all games."""
    return games_db


@router.get("/{game_id}", response_model=Game)
async def get_game(game_id: int):
    """Get a specific game by ID."""
    for game in games_db:
        if game.id == game_id:
            return game
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Game with ID {game_id} not found",
    )


@router.post("/", response_model=Game, status_code=status.HTTP_201_CREATED)
async def create_game(
    game: GameCreate, current_user: User = Depends(get_current_active_user)
):
    """Create a new game."""
    new_game = Game(
        id=len(games_db) + 1, **game.model_dump(), active=True, current_players=0
    )
    games_db.append(new_game)
    return new_game
