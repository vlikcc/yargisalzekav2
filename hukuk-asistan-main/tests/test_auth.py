import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAuthentication:
    """Authentication endpoint tests"""

    def test_register_user_success(self):
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "password": "strongpassword123",
            "full_name": "New User"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["email"] == user_data["email"]

    def test_register_user_weak_password(self):
        """Test registration with weak password"""
        user_data = {
            "email": "test@example.com",
            "password": "123",
            "full_name": "Test User"
        }
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "en az 8 karakter" in response.json()["detail"]

    def test_login_success(self):
        """Test successful login with demo credentials"""
        login_data = {
            "email": "demo@yargisalzeka.com",
            "password": "demo123"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        login_data = {
            "email": "wrong@example.com",
            "password": "wrongpassword"
        }
        response = client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "Email veya şifre hatalı" in response.json()["detail"]

    def test_get_current_user_without_token(self):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_current_user_with_valid_token(self, auth_headers):
        """Test accessing protected endpoint with valid token"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "subscription_plan" in data

    def test_logout_success(self, auth_headers):
        """Test successful logout"""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "çıkış yapıldı" in response.json()["message"]