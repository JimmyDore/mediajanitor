"""Integration tests targeting real API endpoints.

These tests require Docker containers to be running:
    docker-compose up -d

Run with:
    cd backend && uv run pytest tests/test_integration.py -v -s

Uses credentials from .env.example:
    APP_USER_EMAIL=jimmy291295+2@gmail.com
    APP_USER_PASSWORD=ZSh1YYNsr844!*
"""

import os
import httpx
import pytest

# Base URL for the running Docker instance
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")

# Credentials from .env.example
TEST_EMAIL = "jimmy291295+2@gmail.com"
TEST_PASSWORD = "ZSh1YYNsr844!*"


class TestIntegrationAuth:
    """Integration tests for authentication endpoints."""

    def test_login_returns_token(self):
        """Test POST /api/auth/login returns valid JWT token."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )

            assert response.status_code == 200, f"Login failed: {response.text}"
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert len(data["access_token"]) > 20

    def test_auth_me_returns_user_info(self):
        """Test GET /api/auth/me returns user info with valid token."""
        with httpx.Client(base_url=BASE_URL) as client:
            # Login first
            login_response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = login_response.json()["access_token"]

            # Get user info
            response = client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["email"] == TEST_EMAIL
            assert "id" in data

    def test_auth_me_requires_authentication(self):
        """Test GET /api/auth/me returns 401 without token."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/auth/me")
            assert response.status_code == 401


class TestIntegrationContentIssues:
    """Integration tests for GET /api/content/issues endpoint (US-D.3)."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            assert response.status_code == 200, f"Login failed: {response.text}"
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_issues_endpoint_requires_auth(self):
        """Test GET /api/content/issues returns 401 without auth."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/content/issues")
            assert response.status_code == 401

    def test_issues_endpoint_returns_valid_response(self, auth_headers):
        """Test GET /api/content/issues returns proper response structure."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/content/issues", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "items" in data
            assert "total_count" in data
            assert "total_size_bytes" in data
            assert "total_size_formatted" in data
            assert isinstance(data["items"], list)
            assert isinstance(data["total_count"], int)
            assert isinstance(data["total_size_bytes"], int)

    def test_issues_endpoint_filter_old(self, auth_headers):
        """Test GET /api/content/issues?filter=old works."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get(
                "/api/content/issues",
                params={"filter": "old"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # All items should have 'old' in their issues list
            for item in data["items"]:
                assert "old" in item["issues"], f"Item {item['name']} missing 'old' issue"

    def test_issues_endpoint_filter_large(self, auth_headers):
        """Test GET /api/content/issues?filter=large works."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get(
                "/api/content/issues",
                params={"filter": "large"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # All items should have 'large' in their issues list
            for item in data["items"]:
                assert "large" in item["issues"], f"Item {item['name']} missing 'large' issue"

    def test_issues_endpoint_filter_language(self, auth_headers):
        """Test GET /api/content/issues?filter=language returns items with language issues."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get(
                "/api/content/issues",
                params={"filter": "language"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # All items should have 'language' in their issues list
            for item in data["items"]:
                assert "language" in item["issues"], f"Item {item['name']} missing 'language' issue"
                # Should have language_issues detail
                assert item.get("language_issues") is not None, f"Item {item['name']} missing language_issues"

    def test_issues_endpoint_filter_requests(self, auth_headers):
        """Test GET /api/content/issues?filter=requests returns unavailable requests.

        Note: Requests are converted to the unified ContentIssueItem format,
        using jellyfin_id='request-{jellyseerr_id}' and name instead of title.
        """
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get(
                "/api/content/issues",
                params={"filter": "requests"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert "items" in data
            assert "total_count" in data
            assert data["total_count"] == len(data["items"])

            # If there are items, verify they have required unified format fields
            if data["items"]:
                item = data["items"][0]
                # Unified format uses jellyfin_id (with request- prefix) and name instead of jellyseerr_id and title
                required_fields = ["jellyfin_id", "name", "media_type", "issues"]
                for field in required_fields:
                    assert field in item, f"Missing required field: {field}"
                assert "request" in item["issues"]
                # Verify jellyfin_id starts with 'request-' for request items
                assert item["jellyfin_id"].startswith("request-"), "Request items should have jellyfin_id starting with 'request-'"

    def test_issues_items_have_required_fields(self, auth_headers):
        """Test that each issue item has all required fields."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/content/issues", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            if data["items"]:
                item = data["items"][0]
                required_fields = [
                    "jellyfin_id",
                    "name",
                    "media_type",
                    "production_year",
                    "size_bytes",
                    "size_formatted",
                    "last_played_date",
                    "path",
                    "issues",
                ]
                for field in required_fields:
                    assert field in item, f"Missing field: {field}"

                # Issues should be a list
                assert isinstance(item["issues"], list)
                assert len(item["issues"]) > 0, "Item should have at least one issue"

    def test_issues_sorted_by_size_descending(self, auth_headers):
        """Test that issues are sorted by size (largest first)."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/content/issues", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            if len(data["items"]) > 1:
                sizes = [item["size_bytes"] or 0 for item in data["items"]]
                # Check descending order
                for i in range(len(sizes) - 1):
                    assert sizes[i] >= sizes[i + 1], "Items should be sorted by size descending"


class TestIntegrationContentSummary:
    """Integration tests for GET /api/content/summary endpoint."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_summary_endpoint_returns_all_categories(self, auth_headers):
        """Test GET /api/content/summary returns all issue categories."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/content/summary", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Verify all categories are present
            assert "old_content" in data
            assert "large_movies" in data
            assert "language_issues" in data
            assert "unavailable_requests" in data
            assert "recently_available" in data

            # Verify structure of issue categories
            for category in ["old_content", "large_movies", "language_issues", "unavailable_requests"]:
                assert "count" in data[category]
                assert "total_size_bytes" in data[category]
                assert "total_size_formatted" in data[category]

            # Verify structure of info categories
            assert "count" in data["recently_available"]


class TestIntegrationSyncStatus:
    """Integration tests for sync-related endpoints."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_sync_status_endpoint(self, auth_headers):
        """Test GET /api/sync/status returns valid structure."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/sync/status", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Should have these fields (can be null if never synced)
            assert "last_synced" in data
            assert "status" in data
            assert "media_items_count" in data
            assert "requests_count" in data


class TestIntegrationWhitelist:
    """Integration tests for whitelist endpoints."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_whitelist_list_endpoint(self, auth_headers):
        """Test GET /api/whitelist/content returns list."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/whitelist/content", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["items"], list)

    def test_french_only_whitelist_endpoint(self, auth_headers):
        """Test GET /api/whitelist/french-only returns list."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/whitelist/french-only", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["items"], list)

    def test_language_exempt_whitelist_endpoint(self, auth_headers):
        """Test GET /api/whitelist/language-exempt returns list."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/whitelist/language-exempt", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["items"], list)

    def test_request_whitelist_endpoint(self, auth_headers):
        """Test GET /api/whitelist/requests returns list."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/whitelist/requests", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["items"], list)


class TestIntegrationDisplaySettings:
    """Integration tests for display settings endpoints (US-31.1)."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_get_display_settings_includes_recently_available_days(self, auth_headers):
        """Test GET /api/settings/display returns recently_available_days."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/settings/display", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Verify recently_available_days is present
            assert "recently_available_days" in data
            assert isinstance(data["recently_available_days"], int)
            assert 1 <= data["recently_available_days"] <= 30

    def test_save_recently_available_days(self, auth_headers):
        """Test POST /api/settings/display saves recently_available_days."""
        with httpx.Client(base_url=BASE_URL) as client:
            # Get current value
            response = client.get("/api/settings/display", headers=auth_headers)
            original_value = response.json()["recently_available_days"]

            # Save new value
            new_value = 14 if original_value != 14 else 21
            response = client.post(
                "/api/settings/display",
                headers=auth_headers,
                json={"recently_available_days": new_value},
            )
            assert response.status_code == 200

            # Verify it was saved
            response = client.get("/api/settings/display", headers=auth_headers)
            assert response.json()["recently_available_days"] == new_value

            # Reset to original value
            client.post(
                "/api/settings/display",
                headers=auth_headers,
                json={"recently_available_days": original_value},
            )


class TestIntegrationNicknames:
    """Integration tests for nickname mapping endpoints (US-31.3)."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_list_nicknames_endpoint(self, auth_headers):
        """Test GET /api/settings/nicknames returns list."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/settings/nicknames", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            assert "items" in data
            assert "total_count" in data
            assert isinstance(data["items"], list)
            assert isinstance(data["total_count"], int)

    def test_nickname_crud_operations(self, auth_headers):
        """Test create, read, update, delete for nicknames."""
        with httpx.Client(base_url=BASE_URL) as client:
            # Create a nickname
            response = client.post(
                "/api/settings/nicknames",
                headers=auth_headers,
                json={
                    "jellyseerr_username": "integration_test_user",
                    "display_name": "Integration Test",
                },
            )
            # 201 = created, 409 = already exists (both are acceptable)
            assert response.status_code in [201, 409]

            if response.status_code == 201:
                nickname_id = response.json()["id"]

                # Verify it appears in list
                response = client.get("/api/settings/nicknames", headers=auth_headers)
                assert response.status_code == 200
                items = response.json()["items"]
                usernames = [item["jellyseerr_username"] for item in items]
                assert "integration_test_user" in usernames

                # Update the nickname
                response = client.put(
                    f"/api/settings/nicknames/{nickname_id}",
                    headers=auth_headers,
                    json={"display_name": "Updated Integration Test"},
                )
                assert response.status_code == 200
                assert response.json()["display_name"] == "Updated Integration Test"

                # Delete the nickname
                response = client.delete(
                    f"/api/settings/nicknames/{nickname_id}",
                    headers=auth_headers,
                )
                assert response.status_code == 200


class TestIntegrationLibrary:
    """Integration tests for library endpoints (US-22.1)."""

    @pytest.fixture
    def auth_headers(self):
        """Get authentication headers by logging in."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.post(
                "/api/auth/login",
                json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            )
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}

    def test_library_endpoint_requires_auth(self):
        """Test GET /api/library returns 401 without token."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/library")
            assert response.status_code == 401

    def test_library_endpoint_returns_valid_response(self, auth_headers):
        """Test GET /api/library returns valid structure."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/library", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "items" in data
            assert "total_count" in data
            assert "total_size_bytes" in data
            assert "total_size_formatted" in data
            assert "service_urls" in data
            assert isinstance(data["items"], list)
            assert isinstance(data["total_count"], int)
            assert isinstance(data["total_size_bytes"], int)

    def test_library_filter_by_type(self, auth_headers):
        """Test GET /api/library with type filter."""
        with httpx.Client(base_url=BASE_URL) as client:
            # Test movie filter
            response = client.get("/api/library?type=movie", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            for item in data["items"]:
                assert item["media_type"] == "Movie"

            # Test series filter
            response = client.get("/api/library?type=series", headers=auth_headers)
            assert response.status_code == 200
            data = response.json()
            for item in data["items"]:
                assert item["media_type"] == "Series"

    def test_library_items_have_required_fields(self, auth_headers):
        """Test that library items have all required fields."""
        with httpx.Client(base_url=BASE_URL) as client:
            response = client.get("/api/library", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            if data["items"]:
                item = data["items"][0]
                required_fields = [
                    "jellyfin_id",
                    "name",
                    "media_type",
                    "production_year",
                    "size_bytes",
                    "size_formatted",
                    "played",
                    "last_played_date",
                    "date_created",
                ]
                for field in required_fields:
                    assert field in item, f"Missing field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
