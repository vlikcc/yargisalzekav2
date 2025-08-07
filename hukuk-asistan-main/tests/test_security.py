import pytest
from fastapi import HTTPException
from app.security import (
    verify_password, get_password_hash, create_access_token, 
    verify_token, validate_input, is_safe_redirect_url
)

class TestSecurity:
    """Security functions tests"""

    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification"""
        token_data = {
            "sub": "test@example.com",
            "user_id": "test-123",
            "subscription_plan": "premium"
        }
        
        token = create_access_token(data=token_data)
        assert token is not None
        
        decoded_data = verify_token(token)
        assert decoded_data is not None
        assert decoded_data.email == token_data["sub"]
        assert decoded_data.user_id == token_data["user_id"]
        assert decoded_data.subscription_plan == token_data["subscription_plan"]

    def test_invalid_jwt_token(self):
        """Test invalid JWT token verification"""
        invalid_token = "invalid.token.here"
        decoded_data = verify_token(invalid_token)
        assert decoded_data is None

    def test_input_validation_success(self):
        """Test successful input validation"""
        valid_text = "Bu geçerli bir hukuki metin örneğidir."
        result = validate_input(valid_text)
        assert result == valid_text.strip()

    def test_input_validation_empty_text(self):
        """Test input validation with empty text"""
        with pytest.raises(HTTPException) as exc_info:
            validate_input("")
        assert exc_info.value.status_code == 400
        assert "boş olamaz" in exc_info.value.detail

    def test_input_validation_too_short(self):
        """Test input validation with too short text"""
        with pytest.raises(HTTPException) as exc_info:
            validate_input("kısa", min_length=10)
        assert exc_info.value.status_code == 400
        assert "en az 10 karakter" in exc_info.value.detail

    def test_input_validation_too_long(self):
        """Test input validation with too long text"""
        long_text = "a" * 10001
        with pytest.raises(HTTPException) as exc_info:
            validate_input(long_text, max_length=10000)
        assert exc_info.value.status_code == 400
        assert "en fazla 10000 karakter" in exc_info.value.detail

    def test_input_validation_xss_protection(self):
        """Test XSS protection in input validation"""
        malicious_text = "Normal metin <script>alert('xss')</script> devamı"
        with pytest.raises(HTTPException) as exc_info:
            validate_input(malicious_text)
        assert exc_info.value.status_code == 400
        assert "güvenlik nedeniyle" in exc_info.value.detail.lower()

    def test_safe_redirect_url_validation(self):
        """Test safe redirect URL validation"""
        # Safe URLs
        assert is_safe_redirect_url("/dashboard") is True
        assert is_safe_redirect_url("http://localhost/page") is True
        assert is_safe_redirect_url("https://yargisalzeka.com/page") is True
        
        # Unsafe URLs
        assert is_safe_redirect_url("//evil.com") is False
        assert is_safe_redirect_url("http://evil.com") is False
        assert is_safe_redirect_url("javascript:alert('xss')") is False
        assert is_safe_redirect_url("") is False