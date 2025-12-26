"""FastAPI dependencies for authentication."""

from typing import Optional

from fastapi import HTTPException, Request
import jwt

from app.core.config import settings


async def get_current_user(request: Request) -> dict:
    """
    Get current user from JWT token in cookie or Authorization header.

    This dependency extracts and validates the JWT token, returning
    the user payload if valid.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with user info from JWT payload

    Raises:
        HTTPException: If not authenticated or token is invalid
    """
    token = None

    # Try cookie first (set by Flask OAuth flow)
    token = request.cookies.get('auth_token')

    # Fall back to Authorization header
    if not token:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with user info or None if not authenticated
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None
