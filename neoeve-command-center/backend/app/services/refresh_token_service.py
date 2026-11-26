"""
Refresh token and session management with atomic rotation, concurrency control,
and reuse detection.

Security considerations:
- Tokens are opaque, random, and cryptographically secure (256+ bits)
- Only SHA-256 hashes are stored in the database
- Token comparison uses constant-time operations where applicable
- Rotation is atomic with database-level locking (SELECT FOR UPDATE)
- Reuse detection triggers family revocation
- All operations are transactional
"""

import logging
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from uuid import uuid4

from sqlalchemy import and_, select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.models import RefreshSession, RefreshToken, User, Membership, Tenant

logger = logging.getLogger(__name__)

# Token generation constants
TOKEN_BYTES = 32  # 256 bits of entropy
TOKEN_EXPIRY_DAYS = 7
SESSION_EXPIRY_DAYS = 7


def generate_secure_token() -> str:
    """
    Generate a cryptographically secure random token.

    Returns:
        Opaque random token (base64-like string of 256+ bits)
    """
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for database storage.

    Args:
        token: Original token string

    Returns:
        SHA-256 hex digest of the token
    """
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_session(
    db: Session,
    user_id: str,
    tenant_id: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Create a new refresh session and generate initial token.

    Security checks:
    - User exists and is active
    - User has active Membership in tenant
    - Tenant is active

    Args:
        db: SQLAlchemy session
        user_id: User identifier
        tenant_id: Tenant identifier
        user_agent: Optional HTTP User-Agent header
        ip_address: Optional client IP address

    Returns:
        Tuple of (session_id, refresh_token_original)

    Raises:
        ValueError: If user or membership validation fails
        IntegrityError: If database constraints violated
    """
    logger.info(f"[REFRESH_SESSION] ===== START: user_id={user_id}, tenant_id={tenant_id}")

    # 1. Validate user exists and is active
    logger.info(f"[REFRESH_SESSION] Validating user...")
    user = db.query(User).filter(
        User.user_id == user_id,
        User.deleted_at.is_(None),
        User.is_active.is_(True),
    ).first()

    if not user:
        logger.error(f"[REFRESH_SESSION] User not found or inactive: {user_id}")
        raise ValueError(f"User {user_id} not found or inactive")

    logger.info(f"[REFRESH_SESSION] User validated")

    # 2. Validate tenant exists and is active
    logger.info(f"[REFRESH_SESSION] Validating tenant...")
    tenant = db.query(Tenant).filter(
        Tenant.tenant_id == tenant_id,
        Tenant.deleted_at.is_(None),
        Tenant.is_active.is_(True),
    ).first()

    if not tenant:
        logger.error(f"[REFRESH_SESSION] Tenant not found or inactive: {tenant_id}")
        raise ValueError(f"Tenant {tenant_id} not found or inactive")

    logger.info(f"[REFRESH_SESSION] Tenant validated")

    # 3. Validate user has active Membership in tenant (CRITICAL for multi-tenant)
    logger.info(f"[REFRESH_SESSION] Validating membership...")
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.tenant_id == tenant_id,
        Membership.deleted_at.is_(None),
        Membership.is_active.is_(True),
    ).first()

    if not membership:
        logger.error(f"[REFRESH_SESSION] No membership found: user={user_id}, tenant={tenant_id}")
        raise ValueError(
            f"User {user_id} has no active membership in tenant {tenant_id}"
        )

    logger.info(f"[REFRESH_SESSION] Membership validated")

    # 4. Generate token and session
    logger.info(f"[REFRESH_SESSION] Generating token and session...")
    now = datetime.now(timezone.utc)
    session_id = str(uuid4())
    family_id = str(uuid4())  # All tokens from this session share family_id

    # Create RefreshSession
    logger.info(f"[REFRESH_SESSION] Creating RefreshSession object...")
    refresh_session = RefreshSession(
        session_id=session_id,
        user_id=user_id,
        tenant_id=tenant_id,
        family_id=family_id,
        created_at=now,
        expires_at=now + timedelta(days=SESSION_EXPIRY_DAYS),
        user_agent=user_agent,
        ip_address=ip_address,
    )

    logger.info(f"[REFRESH_SESSION] Adding RefreshSession to db...")
    db.add(refresh_session)

    # 5. Generate and store initial token
    logger.info(f"[REFRESH_SESSION] Generating secure token...")
    token = generate_secure_token()
    token_hash = hash_token(token)

    logger.info(f"[REFRESH_SESSION] Creating RefreshToken object...")
    refresh_token = RefreshToken(
        refresh_token_id=str(uuid4()),
        session_id=session_id,
        token_hash=token_hash,
        created_at=now,
        expires_at=now + timedelta(days=TOKEN_EXPIRY_DAYS),
    )

    logger.info(f"[REFRESH_SESSION] Adding RefreshToken to db...")
    db.add(refresh_token)

    logger.info(f"[REFRESH_SESSION] Committing transaction...")
    db.commit()

    logger.info(
        f"[REFRESH_SESSION] ✅ Refresh session created successfully: "
        f"session_id={session_id} user={user_id} tenant={tenant_id}"
    )

    return session_id, token


def rotate_refresh_token_atomic(
    db: Session, token: str
) -> Tuple[str, Optional[str]]:
    """
    Atomically rotate a refresh token with concurrency protection.

    Flow:
    1. Hash the incoming token
    2. Find RefreshToken by hash and lock for update
    3. Verify token not expired, revoked, or already used
    4. Verify session not revoked or expired
    5. If token was used before (reuse detected): revoke family and return error
    6. Mark token as used
    7. Create new token in same family
    8. Record replaced_by relationship
    9. Commit atomically

    Args:
        db: SQLAlchemy session (must support FOR UPDATE)
        token: Original refresh token string

    Returns:
        Tuple of (new_token_or_none, error_reason_if_failed)
        - If success: (new_token, None)
        - If reuse detected: (None, "token_reused")
        - If token invalid/expired: (None, "token_invalid")

    Raises:
        Exception: On database error (not token-specific)
    """
    token_hash = hash_token(token)
    now = datetime.now(timezone.utc)

    try:
        # 1. Find token with FOR UPDATE lock (pessimistic locking)
        refresh_token = (
            db.query(RefreshToken)
            .with_for_update()  # PostgreSQL: SELECT FOR UPDATE
            .filter(RefreshToken.token_hash == token_hash)
            .first()
        )

        if not refresh_token:
            logger.warning(f"Refresh token not found (hash lookup)")
            return None, "token_invalid"

        # 2. Check token not expired
        if refresh_token.expires_at < now:
            logger.warning(
                f"Refresh token expired: "
                f"token_id={refresh_token.refresh_token_id} "
                f"expired_at={refresh_token.expires_at}"
            )
            return None, "token_expired"

        # 3. Check token not revoked
        if refresh_token.revoked_at is not None:
            logger.warning(
                f"Refresh token revoked: token_id={refresh_token.refresh_token_id}"
            )
            return None, "token_revoked"

        # 4. Lock and fetch session for update
        refresh_session = (
            db.query(RefreshSession)
            .with_for_update()
            .filter(RefreshSession.session_id == refresh_token.session_id)
            .first()
        )

        if not refresh_session:
            logger.error(
                f"Refresh session not found for token "
                f"token_id={refresh_token.refresh_token_id}"
            )
            return None, "session_invalid"

        # 5. Check session not revoked
        if refresh_session.revoked_at is not None:
            logger.warning(
                f"Refresh session revoked: session_id={refresh_session.session_id}"
            )
            return None, "session_revoked"

        # 6. Check session not expired
        if refresh_session.expires_at < now:
            logger.warning(
                f"Refresh session expired: session_id={refresh_session.session_id}"
            )
            return None, "session_expired"

        # 7. CRITICAL: Check for reuse (token was already used)
        if refresh_token.used_at is not None:
            logger.error(
                f"SECURITY: Refresh token reuse detected! "
                f"token_id={refresh_token.refresh_token_id} "
                f"family_id={refresh_session.family_id} "
                f"user={refresh_session.user_id}"
            )

            # Revoke entire family immediately
            _revoke_family(db, refresh_session.family_id, "token_reuse_detected")

            db.commit()
            return None, "token_reused"

        # 8. Mark token as used
        refresh_token.used_at = now

        # 9. Generate new token
        new_token = generate_secure_token()
        new_token_hash = hash_token(new_token)

        new_refresh_token = RefreshToken(
            refresh_token_id=str(uuid4()),
            session_id=refresh_session.session_id,
            token_hash=new_token_hash,
            created_at=now,
            expires_at=now + timedelta(days=TOKEN_EXPIRY_DAYS),
        )

        # 10. Add and flush to ensure new_refresh_token gets ID before referencing
        db.add(new_refresh_token)
        db.flush()

        # 11. Record replacement relationship (after flush ensures ID exists)
        refresh_token.replaced_by_token_id = new_refresh_token.refresh_token_id

        # 12. Update session's last_used_at
        refresh_session.last_used_at = now

        db.commit()

        logger.info(
            f"Refresh token rotated: "
            f"old_token_id={refresh_token.refresh_token_id} "
            f"new_token_id={new_refresh_token.refresh_token_id} "
            f"family_id={refresh_session.family_id}"
        )

        return new_token, None

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error during token rotation: {e}")
        return None, "rotation_failed"
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error during token rotation: {e}")
        raise


def revoke_session(
    db: Session, session_id: str, reason: str = "user_logout"
) -> bool:
    """
    Revoke a refresh session and all associated tokens.

    Args:
        db: SQLAlchemy session
        session_id: Session identifier to revoke
        reason: Revocation reason (logout, security_incident, etc.)

    Returns:
        True if revoked, False if not found
    """
    refresh_session = db.query(RefreshSession).filter(
        RefreshSession.session_id == session_id
    ).first()

    if not refresh_session:
        return False

    now = datetime.now(timezone.utc)
    refresh_session.revoked_at = now
    refresh_session.revoke_reason = reason

    # Revoke all tokens in this session
    db.query(RefreshToken).filter(
        RefreshToken.session_id == session_id,
        RefreshToken.revoked_at.is_(None),
    ).update({"revoked_at": now})

    db.commit()

    logger.info(
        f"Refresh session revoked: session_id={session_id} reason={reason}"
    )

    return True


def _revoke_family(
    db: Session, family_id: str, reason: str = "family_revocation"
) -> None:
    """
    Internal function to revoke an entire family of tokens.

    Args:
        db: SQLAlchemy session
        family_id: Family identifier
        reason: Revocation reason
    """
    now = datetime.now(timezone.utc)

    # Find all sessions with this family_id
    sessions = db.query(RefreshSession).filter(
        RefreshSession.family_id == family_id
    ).all()

    for session in sessions:
        session.revoked_at = now
        session.revoke_reason = reason

        # Revoke all tokens in this session
        db.query(RefreshToken).filter(
            RefreshToken.session_id == session.session_id,
            RefreshToken.revoked_at.is_(None),
        ).update({"revoked_at": now})

    db.commit()

    logger.info(f"Token family revoked: family_id={family_id} reason={reason}")


def revoke_family(db: Session, family_id: str, reason: str = "logout") -> None:
    """
    Revoke an entire family of refresh tokens (all rotations from a login).

    Args:
        db: SQLAlchemy session
        family_id: Family identifier
        reason: Revocation reason
    """
    _revoke_family(db, family_id, reason)


def get_active_sessions(
    db: Session, user_id: str, tenant_id: Optional[str] = None
) -> list:
    """
    Get all active refresh sessions for a user.

    Args:
        db: SQLAlchemy session
        user_id: User identifier
        tenant_id: Optional tenant filter

    Returns:
        List of active RefreshSession objects
    """
    query = db.query(RefreshSession).filter(
        RefreshSession.user_id == user_id,
        RefreshSession.revoked_at.is_(None),
        RefreshSession.expires_at > datetime.now(timezone.utc),
    )

    if tenant_id:
        query = query.filter(RefreshSession.tenant_id == tenant_id)

    return query.all()


def cleanup_expired_tokens(db: Session) -> int:
    """
    Clean up expired and revoked tokens (optional for storage management).

    This is a maintenance operation and can be called periodically.

    Args:
        db: SQLAlchemy session

    Returns:
        Number of tokens deleted
    """
    # Note: Soft-delete pattern could be used here if needed
    # For now, we keep all tokens for audit purposes
    logger.info("Token cleanup not implemented (audit trail preserved)")
    return 0
