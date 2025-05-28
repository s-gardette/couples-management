"""
Tests for password security utilities.
"""

import pytest
from app.modules.auth.utils.password import (
    validate_password_strength_detailed,
    calculate_password_strength_score,
    get_strength_level,
    generate_secure_password,
    is_password_compromised,
    validate_password_change
)
from app.modules.auth.utils.security import (
    hash_password,
    verify_password_secure,
    generate_verification_token,
    generate_password_reset_token_secure,
    mask_email
)


class TestPasswordStrength:
    """Test password strength validation."""
    
    def test_weak_password(self):
        """Test weak password validation."""
        result = validate_password_strength_detailed("123")
        assert not result["is_valid"]
        assert result["strength_level"] == "very_weak"
        assert len(result["errors"]) > 0
    
    def test_strong_password(self):
        """Test strong password validation."""
        result = validate_password_strength_detailed("MyStr0ng!P@ssw0rd")
        assert result["is_valid"]
        assert result["strength_level"] in ["strong", "very_strong"]
        assert len(result["errors"]) == 0
    
    def test_password_scoring(self):
        """Test password strength scoring."""
        weak_score = calculate_password_strength_score("123")
        strong_score = calculate_password_strength_score("MyStr0ng!P@ssw0rd")
        
        assert weak_score < strong_score
        assert weak_score < 30
        assert strong_score > 70
    
    def test_strength_levels(self):
        """Test strength level categorization."""
        assert get_strength_level(10) == "very_weak"
        assert get_strength_level(30) == "weak"
        assert get_strength_level(50) == "medium"
        assert get_strength_level(70) == "strong"
        assert get_strength_level(90) == "very_strong"


class TestPasswordGeneration:
    """Test secure password generation."""
    
    def test_generate_secure_password(self):
        """Test secure password generation."""
        password = generate_secure_password(12)
        
        assert len(password) == 12
        
        # Test that generated password meets strength requirements
        result = validate_password_strength_detailed(password)
        assert result["is_valid"]
    
    def test_generate_password_with_options(self):
        """Test password generation with specific options."""
        password = generate_secure_password(
            length=16,
            include_uppercase=True,
            include_lowercase=True,
            include_numbers=True,
            include_special=True,
            exclude_ambiguous=True
        )
        
        assert len(password) == 16
        # Should not contain ambiguous characters
        assert '0' not in password
        assert 'O' not in password
        assert 'l' not in password
        assert '1' not in password


class TestPasswordSecurity:
    """Test password hashing and verification."""
    
    def test_password_hashing(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith('$2b$')  # bcrypt format
    
    def test_password_verification(self):
        """Test password verification."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password_secure(password, hashed)
        assert not verify_password_secure("WrongPassword", hashed)
    
    def test_compromised_password_check(self):
        """Test compromised password detection."""
        assert is_password_compromised("password")
        assert is_password_compromised("123456")
        assert not is_password_compromised("MyUniqueP@ssw0rd123!")


class TestSecurityUtilities:
    """Test security utility functions."""
    
    def test_token_generation(self):
        """Test token generation."""
        verification_token = generate_verification_token()
        reset_token = generate_password_reset_token_secure()
        
        assert len(verification_token) > 20
        assert len(reset_token) > 20
        assert verification_token != reset_token
    
    def test_email_masking(self):
        """Test email address masking."""
        assert mask_email("test@example.com") == "t**t@example.com"
        assert mask_email("a@example.com") == "a*@example.com"
        assert mask_email("ab@example.com") == "a*@example.com"
        assert mask_email("john.doe@example.com") == "j******e@example.com"


class TestPasswordChange:
    """Test password change validation."""
    
    def test_password_change_validation(self):
        """Test comprehensive password change validation."""
        current_password = "OldPassword123!"
        current_hash = hash_password(current_password)
        new_password = "NewStr0ng!P@ssw0rd"
        
        result = validate_password_change(
            current_password=current_password,
            new_password=new_password,
            current_password_hash=current_hash
        )
        
        assert result["is_valid"]
        assert len(result["errors"]) == 0
    
    def test_password_change_same_password(self):
        """Test password change with same password."""
        password = "TestPassword123!"
        password_hash = hash_password(password)
        
        result = validate_password_change(
            current_password=password,
            new_password=password,
            current_password_hash=password_hash
        )
        
        assert not result["is_valid"]
        assert "must be different" in str(result["errors"])
    
    def test_password_change_wrong_current(self):
        """Test password change with wrong current password."""
        current_password = "WrongPassword"
        current_hash = hash_password("ActualPassword123!")
        new_password = "NewStr0ng!P@ssw0rd"
        
        result = validate_password_change(
            current_password=current_password,
            new_password=new_password,
            current_password_hash=current_hash
        )
        
        assert not result["is_valid"]
        assert "incorrect" in str(result["errors"]).lower()


if __name__ == "__main__":
    # Run a quick test
    print("Testing password security features...")
    
    # Test password strength
    weak_result = validate_password_strength_detailed("123")
    strong_result = validate_password_strength_detailed("MyStr0ng!P@ssw0rd")
    
    print(f"Weak password result: {weak_result}")
    print(f"Strong password result: {strong_result}")
    
    # Test password generation
    generated_password = generate_secure_password(12)
    print(f"Generated password: {generated_password}")
    
    # Test password hashing
    password = "TestPassword123!"
    hashed = hash_password(password)
    verified = verify_password_secure(password, hashed)
    print(f"Password hashing and verification: {verified}")
    
    print("All basic tests passed!") 