"""Tests for WebSocket endpoints."""

import json
import pytest
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from gameserver.main import app
from gameserver.ws.endpoints.game_events import manager

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_connection_manager():
    """Reset the connection manager before each test."""
    manager.reset()
    yield


def test_websocket_connection():
    """Test basic WebSocket connection."""
    with client.websocket_connect("/ws") as websocket:
        # Test connection is established
        websocket.send_text(json.dumps({"type": "ping", "data": {"message": "hello"}}))        
        data = websocket.receive_text()
        response = json.loads(data)
        assert response["type"] == "echo"
        assert "content" in response


def test_join_game_message():
    """Test joining a game via WebSocket."""
    with client.websocket_connect("/ws") as websocket:
        # Send join game message
        websocket.send_text(json.dumps({
            "type": "join_game",
            "game_id": 1,
            "player_id": 1
        }))
        
        # Should receive a player_joined message
        data = websocket.receive_text()
        response = json.loads(data)
        assert response["type"] == "player_joined"
        assert response["game_id"] == 1
        assert response["player_id"] == 1


def test_game_specific_websocket():
    """Test game-specific WebSocket endpoint."""
    with client.websocket_connect("/ws/1/1") as websocket:
        # Should automatically receive a player_joined message
        data = websocket.receive_text()
        response = json.loads(data)
        assert response["type"] == "player_joined"
        assert response["game_id"] == 1
        assert response["player_id"] == 1
        
        # Send a game message
        websocket.send_text(json.dumps({
            "type": "game_message",
            "content": {"action": "move", "position": {"x": 10, "y": 20}}
        }))
        
        # Should receive the same message back (broadcast to all in game)
        data = websocket.receive_text()
        response = json.loads(data)
        assert response["type"] == "game_message"
        assert response["game_id"] == 1
        assert response["sender"] == 1
        assert response["content"]["action"] == "move"
        assert response["content"]["position"]["x"] == 10
        assert response["content"]["position"]["y"] == 20


def test_invalid_json():
    """Test sending invalid JSON to WebSocket."""
    with client.websocket_connect("/ws") as websocket:
        # Send invalid JSON
        websocket.send_text("not a json")
        
        # Should receive an error message
        data = websocket.receive_text()
        response = json.loads(data)
        assert response["type"] == "error"
        assert "Invalid JSON format" in response["message"]