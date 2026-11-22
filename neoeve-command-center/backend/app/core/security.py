"""
Security and authentication for FastAPI Command Center.
JWT-based authentication with multi-tenant validation.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel, ValidationError

from .config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer authentication scheme
security = HTTPBearer(description="Bearer token for authentication")


class TokenPayload(BaseModel):
    """JWT token claims."""
    user_id: str
    tenant_id: str
    actor_id: str
    actor_role: str
    exp: datetime


class Identity(BaseModel):
    """Authenticated user identity."""
    user_id: str
    tenant_id: str
    actor_id: str
    actor_role: str


def create_access_token(
    user_id: str,
    tenant_id: str,
    actor_id: str,
    actor_role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create JWT access token.

    Args:
        user_id: User identifier
        tenant_id: Tenant/Organization identifier (CRITICAL for multi-tenant)
        actor_id: Canonical actor identifier
        actor_role: Actor role (architect, backend, qa, security, etc.)
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token

    Raises:
        ValueError: If SECRET_KEY not configured
    """
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY not configured")

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    logger.info(
        f"Token created for user={user_id} tenant={tenant_id} "
        f"actor_id={actor_id} role={actor_role} exp={expire}"
    )

    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Identity:
    """
    Validate JWT token and extract identity.

    This dependency extracts tenant_id from JWT and validates it.
    Tenant_id is NEVER trusted from request parameters.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Identity with validated tenant_id

    Raises:
        HTTPException: If token invalid, expired, or missing required claims
    """
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Validate required claims
        user_id: str = payload.get("user_id")
        tenant_id: str = payload.get("tenant_id")
        actor_id: str = payload.get("actor_id")
        actor_role: str = payload.get("actor_role")

        if not all([user_id, tenant_id, actor_id, actor_role]):
            logger.warning(f"Token missing required claims. payload={payload}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        identity = Identity(
            user_id=user_id,
            tenant_id=tenant_id,
            actor_id=actor_id,
            actor_role=actor_role,
        )

        logger.debug(f"Token valid for tenant={tenant_id} user={user_id}")
        return identity

    except JWTError as e:
        logger.warning(f"JWT validation failed: {type(e).__name__}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValidationError as e:
        logger.warning(f"Token claims validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed",
        )
