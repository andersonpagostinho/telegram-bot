"""
Tests for password security (Argon2id hashing and verification).
"""

import pytest
from app.core.security import hash_password, verify_password


class TestPasswordSecurity:
    """Password hashing and verification tests."""

    def test_hash_password_valid(self):
        """Test hashing a valid password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert len(hashed) > 0
        assert password not in hashed  # Original never appears in hash

    def test_hash_password_empty(self):
        """Test that empty password raises ValueError."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            hash_password("")

    def test_hash_password_too_short(self):
        """Test that short password raises ValueError."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            hash_password("short")

    def test_verify_password_valid(self):
        """Test verifying correct password."""
        password = "CorrectPassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_invalid(self):
        """Test verifying incorrect password."""
        password = "CorrectPassword123"
        hashed = hash_password(password)

        assert verify_password("WrongPassword123", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "CorrectPassword123"
        hashed = hash_password(password)

        # Different case should not match
        assert verify_password("correctpassword123", hashed) is False

    def test_hash_unique_salt(self):
        """Test that same password produces different hashes (unique salt)."""
        password = "SamePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to unique salt
        assert hash1 != hash2

        # Both should verify against original password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_verify_password_no_plaintext_exposure(self):
        """Test that password hash is safe to store (not reversible)."""
        password = "SuperSecurePassword123!"
        hashed = hash_password(password)

        # Hash should not be the original password
        assert hashed != password

        # Hash format should be Argon2id
        assert hashed.startswith("$argon2id$")
