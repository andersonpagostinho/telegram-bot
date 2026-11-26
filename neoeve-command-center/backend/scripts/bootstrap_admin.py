#!/usr/bin/env python3
"""
Bootstrap first administrative account for NeoEve Command Center.

Usage:
    python scripts/bootstrap_admin.py

Inputs (interactive):
    - Email address
    - Password (hidden input via getpass)
    - Password confirmation

Security:
    - Zero credentials in logs
    - Atomic transaction (User + Membership created together)
    - Protection against duplicate creation
    - Uses real hash_password() from app.core.security
"""

import os
import sys
import uuid
import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.security import hash_password
from database.connection import SessionLocal
from database.models import User, Tenant, Membership


def get_admin_credentials():
    """Interactively collect email and password from user."""
    print("\n" + "=" * 60)
    print("NeoEve Command Center — Create First Administrative Account")
    print("=" * 60)

    # Email
    while True:
        email = input("\nEmail address: ").strip().lower()
        if not email or "@" not in email:
            print("❌ Invalid email format. Please try again.")
            continue
        break

    # Password
    while True:
        password = getpass.getpass("Password (hidden): ")
        if not password or len(password) < 8:
            print("❌ Password must be at least 8 characters. Please try again.")
            continue

        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match. Please try again.")
            continue

        break

    return email, password


def create_admin_account(email: str, password: str):
    """Create admin user and membership in atomic transaction."""
    db = SessionLocal()

    try:
        print("\n📝 Creating administrative account...")

        # 1. Check if user already exists
        existing_user = db.query(User).filter(
            User.email == email,
            User.deleted_at.is_(None)
        ).first()

        if existing_user:
            print(f"❌ User already exists: {email}")
            return False

        # 2. Get or create default tenant
        tenant = db.query(Tenant).filter(
            Tenant.is_active == True
        ).first()

        if not tenant:
            print("📦 Creating default tenant...")
            tenant = Tenant(
                tenant_id=str(uuid.uuid4()),
                name="Default",
                is_active=True
            )
            db.add(tenant)
            db.flush()  # Flush to get tenant_id

        # 3. Create user
        user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            password_hash=hash_password(password),
            is_active=True
        )
        db.add(user)
        db.flush()  # Flush to get user_id

        # 4. Create membership with admin role
        membership = Membership(
            membership_id=str(uuid.uuid4()),
            user_id=user.user_id,
            tenant_id=tenant.tenant_id,
            role="admin",
            is_active=True
        )
        db.add(membership)

        # 5. Commit transaction (all or nothing)
        db.commit()

        print(f"✅ Administrative account created successfully!")
        print(f"   Email: {email}")
        print(f"   Role: admin")
        print(f"   Tenant: {tenant.name}")

        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error creating account: {str(e)}")
        return False

    finally:
        db.close()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Create first administrative account for NeoEve Command Center"
    )
    parser.add_argument("--email", help="Administrator email address")
    parser.add_argument("--password", help="Administrator password")
    parser.add_argument("--non-interactive", action="store_true",
                       help="Use command-line arguments instead of prompting")

    args = parser.parse_args()

    try:
        # Determine credentials source
        if args.non_interactive and args.email and args.password:
            email = args.email.strip().lower()
            password = args.password
            print(f"Using provided credentials (email: {email})")
        else:
            # Interactive mode
            email, password = get_admin_credentials()

        success = create_admin_account(email, password)

        if success:
            print("\n" + "=" * 60)
            print("✅ Setup complete! You can now login with:")
            print(f"   Email: {email}")
            print("=" * 60 + "\n")
            sys.exit(0)
        else:
            print("\n❌ Failed to create account.\n")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
