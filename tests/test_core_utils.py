"""
Tests for core utility functions.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, mock_open

from app.core.utils.helpers import (
    slugify, format_currency, split_amount_equally, 
    utc_now, parse_name, truncate_text,
    generate_uuid, mask_email, calculate_percentage
)
from app.core.utils.validators import (
    validate_email_address, validate_password_strength, validate_username,
    validate_currency_amount, validate_file_extension,
    validate_phone_number, sanitize_filename
)


class TestHelpers:
    """Test cases for helper functions."""
    
    def test_slugify(self):
        """Test slug generation."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test & Special Characters!") == "test-special-characters"
        assert slugify("Multiple   Spaces") == "multiple-spaces"
        assert slugify("") == ""
        assert slugify("123 Numbers") == "123-numbers"
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(Decimal("123.45"), "USD") == "$123.45"
        assert format_currency(Decimal("1000.00"), "USD") == "$1,000.00"
        assert format_currency(Decimal("0.99"), "USD") == "$0.99"
        assert format_currency(Decimal("123.45"), "EUR") == "€123.45"
    
    def test_split_amount_equally(self):
        """Test amount splitting."""
        # Equal split
        result = split_amount_equally(Decimal("100.00"), 3)
        assert len(result) == 3
        assert sum(result) == Decimal("100.00")
        assert all(isinstance(x, Decimal) for x in result)
        
        # Uneven split
        result = split_amount_equally(Decimal("10.00"), 3)
        assert len(result) == 3
        assert sum(result) == Decimal("10.00")
    
    def test_utc_now(self):
        """Test UTC datetime generation."""
        dt = utc_now()
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None
    
    def test_parse_name(self):
        """Test name parsing."""
        result = parse_name("John Doe")
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        
        result = parse_name("John")
        assert result["first_name"] == "John"
        assert result["last_name"] == ""
        
        result = parse_name("John Middle Doe")
        assert result["first_name"] == "John"
        assert result["last_name"] == "Middle Doe"
    
    def test_truncate_text(self):
        """Test text truncation."""
        text = "This is a long text that needs to be truncated"
        assert truncate_text(text, 10) == "This is..."
        assert truncate_text(text, 50) == text  # No truncation needed
        assert truncate_text("", 10) == ""
        assert truncate_text(text, 10, suffix="...") == "This is..."
    
    def test_generate_uuid(self):
        """Test UUID generation."""
        result = generate_uuid()
        assert isinstance(result, str)
        assert len(result) == 36  # Standard UUID length
        
        # Test uniqueness
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()
        assert uuid1 != uuid2
    
    def test_mask_email(self):
        """Test email masking."""
        assert mask_email("test@example.com") == "t**t@example.com"
        assert mask_email("a@b.com") == "a*@b.com"
        assert mask_email("longname@domain.org") == "l******e@domain.org"
        assert mask_email("invalid-email") == "invalid-email"
    
    def test_calculate_percentage(self):
        """Test percentage calculation."""
        assert calculate_percentage(25, 100) == 25.0
        assert calculate_percentage(1, 3) == pytest.approx(33.33, rel=1e-2)
        assert calculate_percentage(0, 100) == 0.0
        
        # Division by zero
        assert calculate_percentage(25, 0) == 0.0


class TestValidators:
    """Test cases for validator functions."""
    
    def test_validate_email(self):
        """Test email validation."""
        # Note: email-validator may require DNS resolution for some domains
        # Testing with a simple validation approach
        from unittest.mock import patch
        
        with patch('app.core.utils.validators.validate_email') as mock_validate:
            # Test successful validation
            mock_validate.return_value = True
            assert validate_email_address("test@example.com") is True
            
            # Test failed validation
            from email_validator import EmailNotValidError
            mock_validate.side_effect = EmailNotValidError("Invalid email")
            assert validate_email_address("invalid-email") is False
    
    def test_validate_password(self):
        """Test password validation."""
        # Valid passwords
        is_valid, errors = validate_password_strength("StrongPass123!")
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid passwords - too short
        is_valid, errors = validate_password_strength("weak")
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_username(self):
        """Test username validation."""
        # Valid usernames
        is_valid, error = validate_username("user123")
        assert is_valid is True
        assert error is None
        
        is_valid, error = validate_username("test_user")
        assert is_valid is True
        assert error is None
        
        # Invalid usernames
        is_valid, error = validate_username("ab")  # Too short
        assert is_valid is False
        assert error is not None
        
        is_valid, error = validate_username("")  # Empty
        assert is_valid is False
        assert error is not None
    
    def test_validate_currency_amount(self):
        """Test currency amount validation."""
        # Valid amounts
        is_valid, error = validate_currency_amount(10.50)
        assert is_valid is True
        assert error is None
        
        is_valid, error = validate_currency_amount("25.99")
        assert is_valid is True
        assert error is None
        
        # Invalid amounts
        is_valid, error = validate_currency_amount(-10.50)
        assert is_valid is False
        assert error is not None
        
        is_valid, error = validate_currency_amount("invalid")
        assert is_valid is False
        assert error is not None
    
    def test_validate_file_extension(self):
        """Test file extension validation."""
        # Valid extensions
        assert validate_file_extension("document.pdf", ["pdf", "jpg"]) is True
        assert validate_file_extension("image.jpg", ["pdf", "jpg"]) is True
        
        # Invalid extension
        assert validate_file_extension("document.txt", ["pdf", "jpg"]) is False
        assert validate_file_extension("", ["pdf"]) is False
    
    def test_validate_phone_number(self):
        """Test phone number validation."""
        # Valid phone numbers
        assert validate_phone_number("(123) 456-7890") is True
        assert validate_phone_number("123-456-7890") is True
        assert validate_phone_number("1234567890") is True
        assert validate_phone_number("+1 123 456 7890") is True
        
        # Invalid phone numbers
        assert validate_phone_number("123") is False  # Too short
        assert validate_phone_number("abc-def-ghij") is False  # Letters
        assert validate_phone_number("") is False  # Empty
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        assert sanitize_filename("normal_file.txt") == "normal_file.txt"
        assert sanitize_filename("file with spaces.pdf") == "file_with_spaces.pdf"
        assert sanitize_filename("file@#$%^&*().txt") == "file_.txt"
        assert sanitize_filename("") == "unnamed_file" 