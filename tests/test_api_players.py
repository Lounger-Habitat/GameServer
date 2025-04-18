"""Tests for player API endpoints."""

import pytest
from fastapi.testclient import TestClient

from gameserver.main import app

client = TestClient(app)


def test_get_players():
    """Test getting all players."""
    response = client.get("/api/players/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # We have at least 2 players in our mock data
    assert data[0]["username"] == "player1"


def test_get_player():
    """Test getting a specific player."""
    # Test valid player ID
    response = client.get("/api/players/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["username"] == "player1"
    
    # Test invalid player ID
    response = client.get("/api/players/999")
    assert response.status_code == 404


def test_create_player():
    """Test creating a new player."""
    new_player = {
        "username": "testplayer",
        "email": "test@example.com",
        "display_name": "Test Player"
    }
    response = client.post("/api/players/", json=new_player)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testplayer"
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test Player"
    assert data["active"] is True
    assert data["current_game_id"] is None
    assert "id" in data


def test_duplicate_username():
    """Test creating a player with a duplicate username."""
    # First create a player
    new_player = {
        "username": "uniqueplayer",
        "email": "unique@example.com",
        "display_name": "Unique Player"
    }
    client.post("/api/players/", json=new_player)
    
    # Try to create another player with the same username
    duplicate_player = {
        "username": "uniqueplayer",
        "email": "another@example.com",
        "display_name": "Another Player"
    }
    response = client.post("/api/players/", json=duplicate_player)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_update_player():
    """Test updating an existing player."""
    # First create a player to update
    new_player = {
        "username": "updateplayer",
        "email": "update@example.com",
        "display_name": "Update Player"
    }
    create_response = client.post("/api/players/", json=new_player)
    created_player = create_response.json()
    player_id = created_player["id"]
    
    # Now update it
    update_data = {
        "username": "updatedplayer",
        "email": "updated@example.com",
        "display_name": "Updated Player"
    }
    response = client.put(f"/api/players/{player_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == player_id
    assert data["username"] == "updatedplayer"
    assert data["email"] == "updated@example.com"
    assert data["display_name"] == "Updated Player"
    
    # Test updating non-existent player
    response = client.put("/api/players/999", json=update_data)
    assert response.status_code == 404


def test_delete_player():
    """Test deleting a player."""
    # First create a player to delete
    new_player = {
        "username": "deleteplayer",
        "email": "delete@example.com",
        "display_name": "Delete Player"
    }
    create_response = client.post("/api/players/", json=new_player)
    created_player = create_response.json()
    player_id = created_player["id"]
    
    # Now delete it
    response = client.delete(f"/api/players/{player_id}")
    assert response.status_code == 204
    
    # Verify it's gone
    get_response = client.get(f"/api/players/{player_id}")
    assert get_response.status_code == 404
    
    # Test deleting non-existent player
    response = client.delete("/api/players/999")
    assert response.status_code == 404


def test_join_leave_game():
    """Test joining and leaving a game."""
    # First create a player
    new_player = {
        "username": "gameplayer",
        "email": "game@example.com",
        "display_name": "Game Player"
    }
    create_response = client.post("/api/players/", json=new_player)
    created_player = create_response.json()
    player_id = created_player["id"]
    
    # Join a game
    response = client.post(f"/api/players/{player_id}/join/1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == player_id
    assert data["current_game_id"] == 1
    
    # Leave the game
    response = client.post(f"/api/players/{player_id}/leave")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == player_id
    assert data["current_game_id"] is None
    
    # Try to leave again (should fail)
    response = client.post(f"/api/players/{player_id}/leave")
    assert response.status_code == 400
    assert "not in any game" in response.json()["detail"]