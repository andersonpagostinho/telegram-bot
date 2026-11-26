"""Authentication service: login, tenant selection, token validation."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.core.security import verify_password, create_access_token, normalize_email
from app.core.config import settings
from database.models import User, Tenant, Membership

logger = logging.getLogger(__name__)

SELECTION_TOKEN_EXPIRY_MINUTES = 5  # Temporary selection token


def login(db: Session, email: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    """
    Login user and handle tenant selection.

    Returns:
        Tuple of (response_data, error)
        - response_data: {access_token, tenants} or {access_token, session_id}
        - error: error message if failed
    """
    logger.info(f"[AUTH_LOGIN] ===== START: email={email}")

    # Normalize and validate email
    try:
        normalized_email = normalize_email(email)
        logger.info(f"[AUTH_LOGIN] Email normalized: {normalized_email}")
    except ValueError:
        logger.warning(f"[AUTH_LOGIN] Invalid email format: {email[:10]}...")
        return None, "Invalid credentials"

    # Find user by normalized email
    logger.info(f"[AUTH_LOGIN] Querying user by email...")
    user = db.query(User).filter(
        User.email == normalized_email,
        User.deleted_at.is_(None),
        User.is_active.is_(True),
    ).first()

    if not user:
        logger.warning(f"[AUTH_LOGIN] User not found: {normalized_email}")
        return None, "Invalid credentials"

    logger.info(f"[AUTH_LOGIN] User found: {user.user_id}")

    # Verify password
    logger.info(f"[AUTH_LOGIN] Verifying password...")
    if not verify_password(password, user.password_hash):
        logger.warning(f"[AUTH_LOGIN] Invalid password for user: {user.user_id}")
        return None, "Invalid credentials"

    logger.info(f"[AUTH_LOGIN] Password verified")

    # Find active memberships
    logger.info(f"[AUTH_LOGIN] Querying memberships for user...")
    memberships = db.query(Membership).filter(
        Membership.user_id == user.user_id,
        Membership.deleted_at.is_(None),
        Membership.is_active.is_(True),
    ).all()

    logger.info(f"[AUTH_LOGIN] Found {len(memberships)} memberships")

    if not memberships:
        logger.warning(f"[AUTH_LOGIN] No active memberships for user: {user.user_id}")
        return None, "Invalid credentials"

    # Validate tenants are active
    logger.info(f"[AUTH_LOGIN] Validating tenants...")
    active_memberships = []
    for m in memberships:
        logger.info(f"[AUTH_LOGIN] Checking tenant: {m.tenant_id}")
        tenant = db.query(Tenant).filter(
            Tenant.tenant_id == m.tenant_id,
            Tenant.deleted_at.is_(None),
            Tenant.is_active.is_(True),
        ).first()
        if tenant:
            logger.info(f"[AUTH_LOGIN] Tenant {m.tenant_id} is active")
            active_memberships.append({"membership": m, "tenant": tenant})
        else:
            logger.warning(f"[AUTH_LOGIN] Tenant {m.tenant_id} not found or inactive")

    logger.info(f"[AUTH_LOGIN] Active tenants: {len(active_memberships)}")

    if not active_memberships:
        logger.warning(f"[AUTH_LOGIN] No active tenants for user: {user.user_id}")
        return None, "Invalid credentials"

    # Case 1: Single membership — auto-select tenant
    if len(active_memberships) == 1:
        m = active_memberships[0]["membership"]
        tenant = active_memberships[0]["tenant"]

        logger.info(f"[AUTH_LOGIN] Creating access token...")
        access_token = create_access_token(
            user_id=user.user_id,
            tenant_id=tenant.tenant_id,
            actor_id=user.user_id,  # For now, actor = user
            actor_role=m.role,
        )

        logger.info(f"[AUTH_LOGIN] Access token created successfully")
        logger.info(f"[AUTH_LOGIN] Login successful: user={user.user_id}, tenant={tenant.tenant_id}")

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "single_tenant": True,
            "user_id": user.user_id,
            "tenant_id": tenant.tenant_id,
        }, None

    # Case 2: Multiple memberships — issue selection token
    selection_token = _create_selection_token(user.user_id)

    tenant_list = [
        {
            "tenant_id": am["tenant"].tenant_id,
            "tenant_name": am["tenant"].name,
            "role": am["membership"].role,
        }
        for am in active_memberships
    ]

    logger.info(f"Login pending selection: user={user.user_id}, tenants={len(tenant_list)}")

    return {
        "selection_token": selection_token,
        "tenants": tenant_list,
    }, None


def select_tenant(
    db: Session, user_id: str, tenant_id: str, selection_token: str
) -> Tuple[Optional[dict], Optional[str]]:
    """
    Complete tenant selection and issue access + refresh tokens.

    Revalidates User, Tenant, and Membership in database.
    """
    # Verify selection token
    try:
        payload = jwt.decode(
            selection_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        token_user_id = payload.get("user_id")
        if token_user_id != user_id:
            logger.warning(f"Selection token mismatch: {user_id}")
            return None, "Invalid token"
    except JWTError:
        logger.warning(f"Invalid selection token for user: {user_id}")
        return None, "Invalid token"

    # Revalidate User
    user = db.query(User).filter(
        User.user_id == user_id,
        User.deleted_at.is_(None),
        User.is_active.is_(True),
    ).first()

    if not user:
        logger.warning(f"User not found during selection: {user_id}")
        return None, "Invalid credentials"

    # Revalidate Tenant
    tenant = db.query(Tenant).filter(
        Tenant.tenant_id == tenant_id,
        Tenant.deleted_at.is_(None),
        Tenant.is_active.is_(True),
    ).first()

    if not tenant:
        logger.warning(f"Tenant not found: {tenant_id}")
        return None, "Invalid tenant"

    # Revalidate Membership (CRITICAL: never trust frontend tenant_id)
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.tenant_id == tenant_id,
        Membership.deleted_at.is_(None),
        Membership.is_active.is_(True),
    ).first()

    if not membership:
        logger.warning(f"No membership: user={user_id}, tenant={tenant_id}")
        return None, "Invalid credentials"

    # Create RefreshSession NOW (after tenant confirmed)
    from app.services.refresh_token_service import create_refresh_session

    session_id, refresh_token = create_refresh_session(
        db, user_id, tenant_id, user_agent="", ip_address=""
    )

    # Create access token
    access_token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        actor_id=user_id,
        actor_role=membership.role,
    )

    logger.info(f"Tenant selected: user={user_id}, tenant={tenant_id}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_id": session_id,
        "token_type": "bearer",
    }, None


def _create_selection_token(user_id: str) -> str:
    """Create temporary selection token (signed JWT)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=SELECTION_TOKEN_EXPIRY_MINUTES)

    payload = {
        "user_id": user_id,
        "exp": expire,
        "type": "selection",
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    logger.debug(f"Selection token created for user: {user_id}")
    return token
