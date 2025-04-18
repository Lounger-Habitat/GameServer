"""Tests for authentication API endpoints."""

import pytest
from fastapi.testclient import TestClient

from gameserver.main import app

client = TestClient(app)


def test_register_user():
    """Test registering a new user."""
    new_user = {
        "username": "testuser",
        "email": "test@example.com",
        "display_name": "Test User",
        "password": "password123"
    }
    response = client.post("/api/auth/register", json=new_user)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test User"
    assert "password" not in data


def test_login():
    """Test user login and token generation."""
    # First register a user
    new_user = {
        "username": "loginuser",
        "email": "login@example.com",
        "display_name": "Login User",
        "password": "password123"
    }
    client.post("/api/auth/register", json=new_user)
    
    # Then try to login
    login_data = {
        "username": "loginuser",
        "password": "password123"
    }
    response = client.post("/api/auth/token", data=login_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_me_endpoint():
    """Test the /me endpoint with authentication."""
    # First register a user
    new_user = {
        "username": "meuser",
        "email": "me@example.com",
        "display_name": "Me User",
        "password": "password123"
    }
    client.post("/api/auth/register", json=new_user)
    
    # Then login to get a token
    login_data = {
        "username": "meuser",
        "password": "password123"
    }
    login_response = client.post("/api/auth/token", data=login_data)
    token = login_response.json()["access_token"]
    
    # Use the token to access the /me endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"
    assert data["email"] == "me@example.com"


def test_unauthorized_access():
    """Test that endpoints requiring authentication reject unauthorized requests."""
    # Try to create a game without authentication
    new_game = {
        "name": "Test Game",
        "description": "A test game",
        "max_players": 4
    }
    response = client.post("/api/games/", json=new_game)
    assert response.status_code == 401
    
    # Try to update a player without authentication
    player_update = {
        "username": "updatedplayer",
        "email": "updated@example.com",
        "display_name": "Updated Player"
    }
    response = client.put("/api/players/1", json=player_update)
    assert response.status_code == 401


def test_authorized_access():
    """Test that endpoints requiring authentication accept authorized requests."""
    # First register a user
    new_user = {
        "username": "authuser",
        "email": "auth@example.com",
        "display_name": "Auth User",
        "password": "password123"
    }
    client.post("/api/auth/register", json=new_user)
    
    # Then login to get a token
    login_data = {
        "username": "authuser",
        "password": "password123"
    }
    login_response = client.post("/api/auth/token", data=login_data)
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to create a game with authentication
    new_game = {
        "name": "Auth Game",
        "description": "An authenticated game",
        "max_players": 4
    }
    response = client.post("/api/games/", json=new_game, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Auth Game"