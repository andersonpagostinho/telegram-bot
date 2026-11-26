#!/usr/bin/env python3
"""
Administrative password reset tool for NeoEve Command Center.

SECURITY: This tool is for LOCAL ADMIN USE ONLY
- Runs directly on the database server
- Never shares passwords or hashes in logs
- Validates password before persisting
- Invalidates old sessions on success

Usage:
    python scripts/reset_password_admin.py
"""

import os
import sys
import getpass
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password, verify_password, normalize_email
from database.connection import SessionLocal
from database.models import User, RefreshSession


def reset_password_interactive():
    """
    Interactively reset password for a user.

    Prompts for email and new password securely.
    """
    print("\n" + "=" * 60)
    print("NeoEve Command Center - Admin Password Reset")
    print("=" * 60)

    # Get email
    email_input = input("\nEnter user email: ").strip()
    if not email_input:
        print("❌ Email cannot be empty")
        return False

    # Normalize email
    try:
        email = normalize_email(email_input)
    except ValueError as e:
        print(f"❌ Invalid email: {e}")
        return False

    # Get database session
    db = SessionLocal()

    try:
        # Find user
        user = db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None),
        ).first()

        if not user:
            print(f"❌ User not found: {email}")
            return False

        print(f"✓ User found: {user.user_id}")
        print(f"  Active: {user.is_active}")

        # Get new password
        print("\nEnter new password (minimum 8 characters):")
        password = getpass.getpass("New password: ")
        password_confirm = getpass.getpass("Confirm password: ")

        if not password:
            print("❌ Password cannot be empty")
            return False

        if password != password_confirm:
            print("❌ Passwords do not match")
            return False

        # Validate password strength
        if len(password) < 8:
            print("❌ Password must be at least 8 characters")
            return False

        # Hash password
        try:
            new_password_hash = hash_password(password)
        except ValueError as e:
            print(f"❌ Password validation failed: {e}")
            return False

        print("✓ Password hash generated")

        # Update password in database (transaction)
        try:
            user.password_hash = new_password_hash
            user.is_active = True  # Ensure account is active

            db.commit()
            print("✓ Password updated in database")
        except Exception as e:
            db.rollback()
            print(f"❌ Database update failed: {e}")
            return False

        # Invalidate old refresh sessions
        try:
            old_sessions = db.query(RefreshSession).filter(
                RefreshSession.user_id == user.user_id,
                RefreshSession.is_active.is_(True),
            ).all()

            invalidated = 0
            for session in old_sessions:
                session.is_active = False
                invalidated += 1

            if invalidated > 0:
                db.commit()
                print(f"✓ Invalidated {invalidated} old session(s)")
        except Exception as e:
            print(f"⚠ Warning: Could not invalidate sessions: {e}")

        # Verify password
        print("\nVerifying new password...")
        if not verify_password(password, user.password_hash):
            print("❌ Password verification failed")
            return False

        print("✓ Password verified successfully")

        # Success
        print("\n" + "=" * 60)
        print("✅ PASSWORD RESET SUCCESSFUL")
        print("=" * 60)
        print(f"\nUser: {email}")
        print(f"User ID: {user.user_id}")
        print(f"Status: Active")
        print("\nThe user can now log in with the new password.")

        return True

    finally:
        db.close()


def main():
    """Main entry point."""
    try:
        success = reset_password_interactive()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
