"""Tests for game API endpoints."""

import pytest
from fastapi.testclient import TestClient

from gameserver.main import app

client = TestClient(app)


def test_get_games():
    """Test getting all games."""
    response = client.get("/api/games/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # We have at least 2 games in our mock data
    assert data[0]["name"] == "Adventure Quest"


def test_get_game():
    """Test getting a specific game."""
    # Test valid game ID
    response = client.get("/api/games/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["name"] == "Adventure Quest"
    
    # Test invalid game ID
    response = client.get("/api/games/999")
    assert response.status_code == 404


def test_create_game():
    """Test creating a new game."""
    new_game = {
        "name": "Test Game",
        "description": "A test game",
        "max_players": 4
    }
    response = client.post("/api/games/", json=new_game)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Game"
    assert data["description"] == "A test game"
    assert data["max_players"] == 4
    assert data["active"] is True
    assert data["current_players"] == 0
    assert "id" in data


def test_update_game():
    """Test updating an existing game."""
    # First create a game to update
    new_game = {
        "name": "Update Test Game",
        "description": "A game to update",
        "max_players": 5
    }
    create_response = client.post("/api/games/", json=new_game)
    created_game = create_response.json()
    game_id = created_game["id"]
    
    # Now update it
    update_data = {
        "name": "Updated Game",
        "description": "This game has been updated",
        "max_players": 10
    }
    response = client.put(f"/api/games/{game_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == game_id
    assert data["name"] == "Updated Game"
    assert data["description"] == "This game has been updated"
    assert data["max_players"] == 10
    
    # Test updating non-existent game
    response = client.put("/api/games/999", json=update_data)
    assert response.status_code == 404


def test_delete_game():
    """Test deleting a game."""
    # First create a game to delete
    new_game = {
        "name": "Delete Test Game",
        "description": "A game to delete",
        "max_players": 3
    }
    create_response = client.post("/api/games/", json=new_game)
    created_game = create_response.json()
    game_id = created_game["id"]
    
    # Now delete it
    response = client.delete(f"/api/games/{game_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/games/{game_id}")
    assert get_response.status_code == 404
    
    # Test deleting non-existent game
    response = client.delete("/api/games/999")
    assert response.status_code == 404