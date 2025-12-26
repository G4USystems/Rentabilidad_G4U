"""Authentication utilities for JWT token management."""

from datetime import datetime, timedelta
from typing import Optional

import jwt

from app.core.config import settings


def create_access_token(user_data: dict) -> str:
    """
    Create a JWT access token for authenticated user.

    Args:
        user_data: Dictionary with user info (id, email, name, picture)

    Returns:
        Encoded JWT token string
    """
    expire = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    payload = {
        "sub": user_data["email"],
        "user_id": user_data["id"],
        "name": user_data["name"],
        "picture": user_data.get("picture"),
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict or None if invalid/expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def validate_email_domain(email: str) -> bool:
    """
    Check if email belongs to one of the allowed domains.

    Args:
        email: Email address to validate

    Returns:
        True if email domain matches one of the allowed domains
    """
    if not email:
        return False
    domain = email.split("@")[-1].lower()
    allowed_domains = [d.strip().lower() for d in settings.allowed_email_domains.split(",")]
    return domain in allowed_domains
