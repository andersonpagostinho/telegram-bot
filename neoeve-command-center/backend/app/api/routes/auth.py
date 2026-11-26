"""Authentication endpoints: login and tenant selection."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.security import create_access_token
from app.services.auth_service import login, select_tenant
from app.services.refresh_token_service import (
    create_refresh_session,
    rotate_refresh_token_atomic,
    hash_token,
)
from database.models import RefreshToken, RefreshSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response models
class LoginRequest(BaseModel):
    email: str
    password: str


class SelectTenantRequest(BaseModel):
    selection_token: str
    tenant_id: str


class TenantOption(BaseModel):
    tenant_id: str
    tenant_name: str
    role: str


class LoginResponse(BaseModel):
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    selection_token: Optional[str] = None
    tenants: Optional[list[TenantOption]] = None
    single_tenant: Optional[bool] = None


@router.post("/login")
def api_login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Login endpoint (temporary: without Set-Cookie due to Uvicorn incompatibility).

    Returns:
    - Single tenant: access_token only (refresh_token temporarily unavailable)
    - Multiple tenants: selection_token + tenant list
    - Invalid credentials: Generic error (401)

    NOTE: Refresh token functionality is currently unavailable.
    Access token valid for 15 minutes. User may need to login again after expiration.
    """
    logger.info(f"[LOGIN] Start: email={request.email}")

    try:
        result, error = login(db, request.email, request.password)
        if error:
            logger.warning(f"[LOGIN] Auth failed: {error}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LOGIN] Exception: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login service failed",
        )

    # Case 1: Single tenant — return access token
    if result.get("single_tenant"):
        logger.info(f"[LOGIN] ✅ Single tenant login success")
        return LoginResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
        )

    # Case 2: Multiple tenants — return selection token + options
    logger.info(f"[LOGIN] ✅ Multiple tenants: returning selection token")
    tenants = [TenantOption(**t) for t in result["tenants"]]
    return LoginResponse(
        selection_token=result["selection_token"],
        tenants=tenants,
    )


@router.post("/select-tenant", response_model=LoginResponse)
def api_select_tenant(
    request: SelectTenantRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Complete tenant selection and issue tokens.

    Revalidates User, Tenant, and Membership in database.
    Refresh token set in HttpOnly cookie.
    """
    # Extract user_id from token (would be from JWT in real scenario)
    # For now, we'll pass it from request (in production, extract from selection_token JWT)

    result, error = select_tenant(
        db,
        user_id="<extracted-from-selection-token>",  # TODO: Extract from JWT
        tenant_id=request.tenant_id,
        selection_token=request.selection_token,
    )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Set refresh token in HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=result["refresh_token"],
        httponly=True,
        secure=False,  # Allow HTTP in development
        samesite="Lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )

    return LoginResponse(
        access_token=result["access_token"],
        token_type=result["token_type"],
    )


@router.post("/refresh", response_model=LoginResponse)
def api_refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Refresh access token using refresh token from cookie.

    Security:
    - Refresh token read from HttpOnly cookie
    - Token rotation: old token marked used, new token issued
    - Reuse detection: entire family revoked if old token reused
    - Access token returned in body (new token valid for 15 min)
    - New refresh token returned in cookie (valid for 7 days)

    Returns:
    - access_token: New JWT (15 min expiry)
    - Refresh token in HttpOnly cookie (7 day expiry)
    """
    from app.services.refresh_token_service import rotate_refresh_token_atomic
    from app.core.security import create_access_token

    # 1. Extract refresh token from cookie
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    # 2. Rotate token (atomic operation with reuse detection)
    new_refresh_token, error = rotate_refresh_token_atomic(db, refresh_token)

    if error:
        logger.warning(f"Refresh token rotation failed: {error}")
        # Clear the invalid refresh token cookie
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=False,
            samesite="Lax",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token refresh failed: {error}",
        )

    # 3. Get session details from the original token's session
    old_token_hash = hash_token(refresh_token)
    old_token_record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == old_token_hash
    ).first()

    if not old_token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found",
        )

    session = db.query(RefreshSession).filter(
        RefreshSession.session_id == old_token_record.session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found",
        )

    # 4. Create new access token
    try:
        access_token = create_access_token(
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            actor_id=session.user_id,  # Using user_id as actor for now
            actor_role="admin",  # TODO: Get from Membership
        )
    except Exception as e:
        logger.error(f"Failed to create access token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate access token",
        )

    # 5. Set new refresh token in cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,  # Allow HTTP in development
        samesite="Lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )

    logger.info(
        f"Token refreshed: user={session.user_id} tenant={session.tenant_id}"
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
    )


@router.post("/logout")
def api_logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Logout endpoint: revoke session and all refresh tokens.

    Extracts user_id from access token (via JWT decode).
    Revokes RefreshSession and all tokens in family.
    Clears refresh_token cookie.
    Idempotent: safe to call multiple times.
    """
    from app.core.config import settings
    from app.core.security import create_access_token
    from jose import jwt as jose_jwt, JWTError
    from database.models import RefreshSession
    from app.services.refresh_token_service import revoke_family

    # Extract access token from Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token",
        )

    access_token = auth_header.split(" ")[1]

    # Decode JWT
    try:
        payload = jose_jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id = payload.get("user_id")
        tenant_id = payload.get("tenant_id")
        session_id = payload.get("session_id")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    # Find RefreshSession
    session = db.query(RefreshSession).filter(
        RefreshSession.session_id == session_id,
        RefreshSession.user_id == user_id,
        RefreshSession.tenant_id == tenant_id,
    ).first()

    if session:
        # Revoke family (atomic)
        revoke_family(db, session.family_id)
        logger.info(f"Logout: user={user_id}, tenant={tenant_id}, session={session_id}")

    # Clear refresh_token cookie (idempotent)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=True,
        samesite="Lax",
    )

    return {"message": "Logged out successfully"}
