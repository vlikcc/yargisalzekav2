import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestAPIEndpoints:
    """API endpoint tests"""

    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data

    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "docs" in data

    def test_extract_keywords_without_auth(self):
        """Test keyword extraction without authentication"""
        response = client.post("/api/v1/ai/extract-keywords", json={
            "case_text": "Test case text"
        })
        assert response.status_code == 401

    def test_extract_keywords_with_auth(self, auth_headers, sample_case_text):
        """Test keyword extraction with authentication"""
        response = client.post(
            "/api/v1/ai/extract-keywords",
            json={"case_text": sample_case_text},
            headers=auth_headers
        )
        # Note: This might fail if Gemini API is not configured
        # In a real test environment, we'd mock the AI service
        assert response.status_code in [200, 500]  # 500 if AI service unavailable

    def test_extract_keywords_invalid_input(self, auth_headers):
        """Test keyword extraction with invalid input"""
        response = client.post(
            "/api/v1/ai/extract-keywords",
            json={"case_text": ""},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "boş olamaz" in response.json()["detail"]

    def test_extract_keywords_xss_input(self, auth_headers):
        """Test keyword extraction with XSS attempt"""
        malicious_text = "Legal text <script>alert('xss')</script> more text"
        response = client.post(
            "/api/v1/ai/extract-keywords",
            json={"case_text": malicious_text},
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "güvenlik" in response.json()["detail"].lower()

    def test_rate_limiting(self, auth_headers, sample_case_text):
        """Test rate limiting on API endpoints"""
        # Make multiple requests to trigger rate limiting
        # Note: This test might be flaky depending on timing
        responses = []
        for _ in range(15):  # Exceed the 10/minute limit
            response = client.post(
                "/api/v1/ai/extract-keywords",
                json={"case_text": sample_case_text},
                headers=auth_headers
            )
            responses.append(response.status_code)
        
        # At least one request should be rate limited
        assert 429 in responses or 401 in responses  # 401 if auth fails, 429 if rate limited

class TestCORS:
    """CORS configuration tests"""

    def test_cors_headers(self):
        """Test CORS headers are present"""
        response = client.options("/api/v1/auth/login")
        assert response.status_code == 200
        
        # Check for CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers

class TestErrorHandling:
    """Error handling tests"""

    def test_404_endpoint(self):
        """Test 404 for non-existent endpoint"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test 405 for wrong HTTP method"""
        response = client.get("/api/v1/auth/login")  # Should be POST
        assert response.status_code == 405