"""Unit tests for health check endpoint."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client for FastAPI app.
    
    Returns:
        TestClient: FastAPI test client instance.
    """
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    """Test health check endpoint returns correct response.
    
    Args:
        client: FastAPI test client.
    """
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_content_type(client: TestClient) -> None:
    """Test health check endpoint returns correct content type.
    
    Args:
        client: FastAPI test client.
    """
    response = client.get("/api/v1/health")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
