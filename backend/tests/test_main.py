"""Tests for main FastAPI application."""

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint returns correct message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Plex Dashboard API"
    assert data["status"] == "running"


def test_health_endpoint(client: TestClient) -> None:
    """Test the health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_cors_allows_localhost(client: TestClient) -> None:
    """Test CORS allows localhost origins."""
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_allows_production_domain(client: TestClient) -> None:
    """Test CORS allows production domain https://mediajanitor.com."""
    response = client.get(
        "/health",
        headers={"Origin": "https://mediajanitor.com"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://mediajanitor.com"
