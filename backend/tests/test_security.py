"""Tests for security functions."""

import pytest

from app.security import hash_password, verify_password, validate_password_strength


class TestPasswordHashing:
    """Test password hashing and verification."""
    
    def test_hash_password_generates_salt_and_hash(self):
        """Test that hash_password generates both salt and hash."""
        salt, password_hash = hash_password("test_password")
        assert salt is not None
        assert len(salt) > 0
        assert password_hash is not None
        assert len(password_hash) > 0
    
    def test_hash_password_with_custom_salt(self):
        """Test that hash_password works with custom salt."""
        custom_salt = "custom_salt_123"
        salt, password_hash = hash_password("test_password", salt=custom_salt)
        assert salt == custom_salt
    
    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        salt, password_hash = hash_password("test_password")
        assert verify_password("test_password", salt, password_hash) is True
    
    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        salt, password_hash = hash_password("test_password")
        assert verify_password("wrong_password", salt, password_hash) is False
    
    def test_hash_password_deterministic_with_same_salt(self):
        """Test that hashing is deterministic with the same salt."""
        custom_salt = "test_salt"
        _, hash1 = hash_password("password", salt=custom_salt)
        _, hash2 = hash_password("password", salt=custom_salt)
        assert hash1 == hash2


class TestPasswordValidation:
    """Test password strength validation."""
    
    def test_valid_password(self):
        """Test that a strong password passes validation."""
        is_valid, message = validate_password_strength("StrongP@ssw0rd")
        assert is_valid is True
        assert "meets strength requirements" in message
    
    def test_password_too_short(self):
        """Test that short password fails validation."""
        is_valid, message = validate_password_strength("Short1!")
        assert is_valid is False
        assert "at least" in message.lower()
    
    def test_password_missing_uppercase(self):
        """Test that password without uppercase fails."""
        is_valid, message = validate_password_strength("lowercase1!")
        assert is_valid is False
        assert "uppercase" in message.lower()
    
    def test_password_missing_lowercase(self):
        """Test that password without lowercase fails."""
        is_valid, message = validate_password_strength("UPPERCASE1!")
        assert is_valid is False
        assert "lowercase" in message.lower()
    
    def test_password_missing_digit(self):
        """Test that password without digit fails."""
        is_valid, message = validate_password_strength("NoDigits!")
        assert is_valid is False
        assert "digit" in message.lower()
    
    def test_password_missing_special(self):
        """Test that password without special character fails."""
        is_valid, message = validate_password_strength("NoSpecial123")
        assert is_valid is False
        assert "special" in message.lower()
    
    def test_common_password(self):
        """Test that common passwords are rejected."""
        is_valid, message = validate_password_strength("password")
        assert is_valid is False
        assert "too common" in message.lower()
