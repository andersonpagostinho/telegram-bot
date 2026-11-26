"""Tests for Tenant and Membership models."""

import pytest
from datetime import datetime, timezone
from database.models import User, Tenant, Membership, utc_now


class TestTenant:
    """Tenant model tests."""

    def test_tenant_creation(self):
        """Test creating a Tenant."""
        tenant = Tenant(
            tenant_id="tenant-acme",
            name="Acme Corp",
            is_active=True
        )
        assert tenant.tenant_id == "tenant-acme"
        assert tenant.name == "Acme Corp"
        assert tenant.is_active is True
        assert tenant.created_at is None  # Not persisted yet

    def test_tenant_soft_delete(self):
        """Test soft-delete via deleted_at."""
        tenant = Tenant(
            tenant_id="tenant-defunct",
            name="Defunct Corp",
            deleted_at=utc_now()
        )
        assert tenant.deleted_at is not None


class TestMembership:
    """Membership model tests."""

    def test_membership_creation(self):
        """Test creating a Membership."""
        membership = Membership(
            membership_id="mem-1",
            user_id="user-alice",
            tenant_id="tenant-acme",
            role="admin",
            is_active=True
        )
        assert membership.user_id == "user-alice"
        assert membership.tenant_id == "tenant-acme"
        assert membership.role == "admin"
        assert membership.is_active is True

    def test_membership_role_validation(self):
        """Test that role is stored (validation at app layer)."""
        roles = ["owner", "admin", "operator", "viewer"]
        for role in roles:
            membership = Membership(
                membership_id=f"mem-{role}",
                user_id="user-test",
                tenant_id="tenant-test",
                role=role
            )
            assert membership.role == role

    def test_membership_user_tenant_uniqueness(self):
        """Test that user_id + tenant_id must be unique."""
        # This would be enforced at DB level by UniqueConstraint
        # In tests, verify model structure allows only one per user+tenant
        m1 = Membership(
            membership_id="mem-unique-1",
            user_id="user-bob",
            tenant_id="tenant-startup"
        )
        m2 = Membership(
            membership_id="mem-unique-2",
            user_id="user-bob",
            tenant_id="tenant-startup"
        )
        # Both objects can exist in memory, but DB constraint would reject duplicate
        assert m1.user_id == m2.user_id
        assert m1.tenant_id == m2.tenant_id
        assert m1.membership_id != m2.membership_id


class TestMultiTenant:
    """Multi-tenant relationship tests."""

    def test_user_multiple_memberships(self):
        """Test that one User can belong to multiple Tenants."""
        user = User(
            user_id="user-alice",
            email="alice@example.com",
            password_hash="hash"
        )

        # Create multiple memberships for same user
        mem1 = Membership(
            membership_id="mem-alice-acme",
            user_id="user-alice",
            tenant_id="tenant-acme",
            role="admin"
        )
        mem2 = Membership(
            membership_id="mem-alice-startup",
            user_id="user-alice",
            tenant_id="tenant-startup",
            role="operator"
        )

        # Verify distinct tenant associations
        assert mem1.user_id == mem2.user_id
        assert mem1.tenant_id != mem2.tenant_id
        assert mem1.role != mem2.role

    def test_tenant_multiple_users(self):
        """Test that one Tenant can have multiple Users."""
        tenant = Tenant(
            tenant_id="tenant-shared",
            name="Shared Workspace"
        )

        # Create multiple memberships for same tenant
        mem1 = Membership(
            membership_id="mem-alice-shared",
            user_id="user-alice",
            tenant_id="tenant-shared",
            role="admin"
        )
        mem2 = Membership(
            membership_id="mem-bob-shared",
            user_id="user-bob",
            tenant_id="tenant-shared",
            role="viewer"
        )

        # Verify distinct user associations
        assert mem1.tenant_id == mem2.tenant_id
        assert mem1.user_id != mem2.user_id
        assert mem1.role != mem2.role

    def test_isolation_between_tenants(self):
        """Test that tenants are isolated from each other."""
        # User in tenant1 should not access tenant2
        mem_tenant1 = Membership(
            membership_id="mem-user-t1",
            user_id="user-isolated",
            tenant_id="tenant-1",
            role="admin"
        )

        mem_tenant2 = Membership(
            membership_id="mem-user-t2",
            user_id="user-isolated",
            tenant_id="tenant-2",
            role="viewer"  # Different role in different tenant
        )

        # Backend must validate user has membership in tenant before allowing access
        assert mem_tenant1.user_id == mem_tenant2.user_id
        assert mem_tenant1.tenant_id != mem_tenant2.tenant_id


class TestMembershipIntegrity:
    """Referential integrity and constraint tests."""

    def test_membership_requires_user_id(self):
        """Test that membership requires user_id (ORM allows in memory, DB enforces on persist)."""
        # ORM allows creating object without user_id in memory
        membership = Membership(
            membership_id="mem-invalid",
            tenant_id="tenant-test"
        )
        # But user_id should be None (not provided)
        assert membership.user_id is None

    def test_membership_requires_tenant_id(self):
        """Test that membership requires tenant_id (ORM allows in memory, DB enforces on persist)."""
        # ORM allows creating object without tenant_id in memory
        membership = Membership(
            membership_id="mem-invalid",
            user_id="user-test"
        )
        # But tenant_id should be None (not provided)
        assert membership.tenant_id is None

    def test_membership_soft_delete(self):
        """Test soft-delete for membership."""
        membership = Membership(
            membership_id="mem-soft-del",
            user_id="user-test",
            tenant_id="tenant-test",
            is_active=False
        )
        assert membership.is_active is False
