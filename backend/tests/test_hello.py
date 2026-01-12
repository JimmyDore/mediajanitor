"""Tests for Hello World endpoint - US-0.1."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_hello_endpoint_returns_hello_world():
    """GET /api/hello should return {"message": "Hello World"}."""
    response = client.get("/api/hello")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_hello_endpoint_returns_json():
    """GET /api/hello should return JSON content type."""
    response = client.get("/api/hello")

    assert response.headers["content-type"] == "application/json"
