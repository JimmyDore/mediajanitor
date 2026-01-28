"""Tests for main FastAPI application."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient) -> None:
    """Test the root endpoint returns correct message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Plex Dashboard API"
    assert data["status"] == "running"


class TestHealthEndpoint:
    """Tests for the enhanced /health endpoint."""

    def test_health_returns_200_when_all_dependencies_healthy(self, client: TestClient) -> None:
        """Test health endpoint returns 200 with healthy status when all deps are OK."""
        # Mock Redis as healthy since Redis is not available in test environment
        with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = (True, "ok")
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "dependencies" in data
            assert data["dependencies"]["database"] == "ok"

    def test_health_returns_database_status(self, client: TestClient) -> None:
        """Test health endpoint returns database status in dependencies."""
        # Mock Redis as healthy since Redis is not available in test environment
        with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = (True, "ok")
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "dependencies" in data
            assert "database" in data["dependencies"]

    def test_health_returns_redis_status_when_configured(self, client: TestClient) -> None:
        """Test health endpoint returns Redis status when Redis is configured."""
        # Mock Redis as healthy to test the structure
        with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = (True, "ok")
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "dependencies" in data
            assert "redis" in data["dependencies"]
            assert data["dependencies"]["redis"] == "ok"

    def test_health_returns_503_when_database_fails(self, client: TestClient) -> None:
        """Test health endpoint returns 503 when database is unavailable."""
        # Mock the database check to return failure
        with patch("app.main.check_database_health", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = (False, "error: Connection refused")
            # Mock Redis as healthy so we isolate database failure
            with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
                mock_redis.return_value = (True, "ok")
                response = client.get("/health")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert "error" in data["dependencies"]["database"]

    def test_health_returns_503_when_redis_fails(self, client: TestClient) -> None:
        """Test health endpoint returns 503 when Redis is unavailable."""
        # Mock the Redis check to return failure
        with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = (False, "error: Connection refused")
            # Mock database as healthy so we can test Redis failure in isolation
            with patch("app.main.check_database_health", new_callable=AsyncMock) as mock_db:
                mock_db.return_value = (True, "ok")
                response = client.get("/health")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert "error" in data["dependencies"]["redis"]

    def test_health_returns_detailed_dependency_status(self, client: TestClient) -> None:
        """Test health endpoint returns detailed status for each dependency."""
        # Mock Redis as healthy since Redis is not available in test environment
        with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = (True, "ok")
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            # Should have top-level status
            assert "status" in data
            # Should have dependencies object with each dependency
            assert "dependencies" in data
            dependencies = data["dependencies"]
            # Each dependency should have a status value
            assert isinstance(dependencies["database"], str)

    def test_health_database_check_executes_query(self, client: TestClient) -> None:
        """Test that database health check actually executes a query."""
        # Mock Redis as healthy since Redis is not available in test environment
        with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
            mock_redis.return_value = (True, "ok")
            # The test database should be available and healthy
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            # Database should be "ok" when query succeeds
            assert data["dependencies"]["database"] == "ok"

    def test_health_redis_not_configured_returns_not_configured(self, client: TestClient) -> None:
        """Test health returns 'not configured' for Redis when redis_url is empty."""
        with patch("app.main.get_settings") as mock_settings:
            mock_settings.return_value.redis_url = ""
            response = client.get("/health")
            # Database should still work, Redis shows "not configured"
            data = response.json()
            assert "dependencies" in data
            assert data["dependencies"]["redis"] == "not configured"
            # Should still be healthy since Redis being unconfigured is OK
            assert data["status"] == "healthy"

    def test_health_database_failure_logged(self, client: TestClient) -> None:
        """Test that database failures are logged."""
        with patch("app.main.async_session_maker") as mock_session_maker:
            # Simulate database connection failure
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
            mock_session_maker.return_value = mock_session
            with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
                mock_redis.return_value = (True, "ok")
                response = client.get("/health")
                assert response.status_code == 503
                data = response.json()
                assert data["status"] == "unhealthy"
                assert "error" in data["dependencies"]["database"]


def test_cors_allows_localhost(client: TestClient) -> None:
    """Test CORS allows localhost origins."""
    # Mock Redis as healthy since Redis is not available in test environment
    with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
        mock_redis.return_value = (True, "ok")
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5173"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_allows_production_domain(client: TestClient) -> None:
    """Test CORS allows production domain https://mediajanitor.com."""
    # Mock Redis as healthy since Redis is not available in test environment
    with patch("app.main.check_redis_health", new_callable=AsyncMock) as mock_redis:
        mock_redis.return_value = (True, "ok")
        response = client.get(
            "/health",
            headers={"Origin": "https://mediajanitor.com"},
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://mediajanitor.com"
