"""WebSocket authentication utilities."""

from typing import Optional, Tuple

from fastapi import WebSocket, status
from jose import JWTError, jwt

from gameserver.models.user import get_user_by_username
from gameserver.utils.auth import ALGORITHM, SECRET_KEY


async def get_token_from_query(websocket: WebSocket) -> Optional[str]:
    """Extract token from WebSocket query parameters."""
    token = websocket.query_params.get("token")
    print("------", token)
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    return token


async def authenticate_websocket(websocket: WebSocket) -> Tuple[bool, Optional[dict]]:
    """Authenticate a WebSocket connection using JWT token."""
    token = await get_token_from_query(websocket)
    if not token:
        return False, None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return False, None

        user = get_user_by_username(username)
        if user is None:
            return False, None

        return True, {
            "username": user.username,
        }
    except JWTError:
        return False, None
