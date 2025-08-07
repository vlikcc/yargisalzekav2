import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
from app.main import app
from app.security import create_access_token

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Test client for synchronous tests"""
    return TestClient(app)

@pytest.fixture
async def async_client():
    """Async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_token():
    """Create a test JWT token"""
    token_data = {
        "sub": "test@example.com",
        "user_id": "test-user-123",
        "subscription_plan": "premium"
    }
    return create_access_token(data=token_data)

@pytest.fixture
def auth_headers(test_token):
    """Create authorization headers for tests"""
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
def sample_case_text():
    """Sample case text for testing"""
    return """
    Müvekkilim A şirketi ile B şirketi arasında imzalanan satış sözleşmesinde,
    B şirketi teslim tarihini geçirmesi nedeniyle tazminat talep etmekteyiz.
    Sözleşmede belirlenen 30 günlük teslim süresi aşılmış ve bu durum
    müvekkilime maddi zarar vermiştir.
    """