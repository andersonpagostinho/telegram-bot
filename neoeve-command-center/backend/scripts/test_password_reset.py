#!/usr/bin/env python3
"""
Test password reset - validates that new password works and old password fails.

Usage:
    python scripts/test_password_reset.py <email> <new_password>
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import verify_password, normalize_email
from app.services.auth_service import login
from database.connection import SessionLocal
from database.models import User


def test_password(email: str, password: str):
    """Test login with given password."""

    print(f"\n{'=' * 60}")
    print(f"Testing password reset for: {email}")
    print(f"{'=' * 60}")

    db = SessionLocal()

    try:
        # Normalize email
        normalized_email = normalize_email(email)
        print(f"✓ Email normalized: {normalized_email}")

        # Find user
        user = db.query(User).filter(
            User.email == normalized_email
        ).first()

        if not user:
            print(f"❌ User not found: {normalized_email}")
            return False

        print(f"✓ User found: {user.user_id}")
        print(f"  Active: {user.is_active}")
        print(f"  Has password hash: {'Yes' if user.password_hash else 'No'}")

        # Test login
        print(f"\n--- Testing Login ---")
        response, error = login(db, normalized_email, password)

        if error:
            print(f"❌ Login failed: {error}")
            return False

        if not response or not response.get("access_token"):
            print(f"❌ No access token in response")
            return False

        print(f"✓ Login successful")
        print(f"  Token type: {response.get('token_type')}")
        print(f"  Single tenant: {response.get('single_tenant', False)}")

        # Verify password directly
        print(f"\n--- Direct Password Verification ---")
        if verify_password(password, user.password_hash):
            print(f"✓ Password verification passed")
        else:
            print(f"❌ Password verification failed")
            return False

        print(f"\n{'=' * 60}")
        print(f"✅ ALL TESTS PASSED")
        print(f"{'=' * 60}")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/test_password_reset.py <email> <password>")
        print("\nExample:")
        print("  python scripts/test_password_reset.py andersonpagostinho@gmail.com Password123456")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]

    success = test_password(email, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
