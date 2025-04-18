"""Player related API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from gameserver.models.user import User
from gameserver.utils.auth import get_current_active_user

# Player models
class PlayerBase(BaseModel):
    """Base player model."""
    username: str
    email: str
    display_name: Optional[str] = None

class PlayerCreate(PlayerBase):
    """Player creation model."""
    pass

class Player(PlayerBase):
    """Player response model."""
    id: int
    active: bool = True
    current_game_id: Optional[int] = None

    class Config:
        """Pydantic model configuration."""
        from_attributes = True

# In-memory storage for demo purposes
# In a real application, this would be a database
players_db = [
    Player(id=1, username="player1", email="player1@example.com", display_name="Pro Gamer", active=True),
    Player(id=2, username="player2", email="player2@example.com", active=True, current_game_id=1),
]

router = APIRouter()

@router.get("/", response_model=List[Player])
async def get_players():
    """Get all players."""
    return players_db

@router.get("/{player_id}", response_model=Player)
async def get_player(player_id: int):
    """Get a specific player by ID."""
    for player in players_db:
        if player.id == player_id:
            return player
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Player with ID {player_id} not found"
    )

@router.post("/", response_model=Player, status_code=status.HTTP_201_CREATED)
async def create_player(player: PlayerCreate, current_user: User = Depends(get_current_active_user)):
    """Create a new player."""
    # Check if username already exists
    for existing_player in players_db:
        if existing_player.username == player.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username {player.username} already exists"
            )
    
    new_player = Player(
        id=len(players_db) + 1,
        **player.model_dump(),
        active=True
    )
    players_db.append(new_player)
    return new_player

@router.put("/{player_id}", response_model=Player)
async def update_player(player_id: int, player_update: PlayerBase, current_user: User = Depends(get_current_active_user)):
    """Update an existing player."""
    for i, player in enumerate(players_db):
        if player.id == player_id:
            updated_player = Player(
                id=player_id,
                **player_update.model_dump(),
                active=player.active,
                current_game_id=player.current_game_id
            )
            players_db[i] = updated_player
            return updated_player
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Player with ID {player_id} not found"
    )

@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_player(player_id: int, current_user: User = Depends(get_current_active_user)):
    """Delete a player."""
    for i, player in enumerate(players_db):
        if player.id == player_id:
            players_db.pop(i)
            return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Player with ID {player_id} not found"
    )

@router.post("/{player_id}/join/{game_id}", response_model=Player)
async def join_game(player_id: int, game_id: int, current_user: User = Depends(get_current_active_user)):
    """Join a player to a game."""
    player_found = False
    for i, player in enumerate(players_db):
        if player.id == player_id:
            player_found = True
            # In a real application, we would check if the game exists and has space
            players_db[i].current_game_id = game_id
            return players_db[i]
    
    if not player_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player with ID {player_id} not found"
        )

@router.post("/{player_id}/leave", response_model=Player)
async def leave_game(player_id: int, current_user: User = Depends(get_current_active_user)):
    """Remove a player from their current game."""
    for i, player in enumerate(players_db):
        if player.id == player_id:
            if player.current_game_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Player with ID {player_id} is not in any game"
                )
            players_db[i].current_game_id = None
            return players_db[i]
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Player with ID {player_id} not found"
    )