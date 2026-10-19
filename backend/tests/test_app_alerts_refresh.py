"""Media Janitor refreshes its App alerts when the reporting account acts, without a sync.

Each test goes through the HTTP endpoint of an action, with respx mocking the Hub.
"""

import json
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.config import get_settings
from app.database import CachedMediaItem, SyncStatus
from tests.conftest import HUB_ALERTS_URL, HUB_USER_EMAIL, TestingAsyncSessionLocal

PASSWORD = "SecurePassword123!"


def login(client: TestClient, email: str = HUB_USER_EMAIL) -> tuple[dict[str, str], int]:
    client.post("/api/auth/register", json={"email": email, "password": PASSWORD})
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    headers = {"Authorization": f"Bearer {token}"}
    user_id = client.get("/api/auth/me", headers=headers).json()["id"]
    return headers, user_id


async def add_old_movie(user_id: int, jellyfin_id: str = "old-1", tmdb_id: str = "111") -> None:
    """An unwatched 5 GB movie added years ago: Old content, nothing else."""
    async with TestingAsyncSessionLocal() as session:
        session.add(
            CachedMediaItem(
                user_id=user_id,
                jellyfin_id=jellyfin_id,
                name=f"Old Movie {jellyfin_id}",
                media_type="Movie",
                production_year=2015,
                date_created="2020-01-01T00:00:00Z",
                size_bytes=5_000_000_000,
                played=False,
                play_count=0,
                raw_data={"ProviderIds": {"Tmdb": tmdb_id}},
                language_check_result={"has_english": True, "has_french": True},
            )
        )
        await session.commit()


async def set_last_sync(user_id: int, status: str, error: str | None) -> None:
    async with TestingAsyncSessionLocal() as session:
        session.add(SyncStatus(user_id=user_id, last_sync_status=status, last_sync_error=error))
        await session.commit()


def whitelist(client: TestClient, headers: dict[str, str], jellyfin_id: str = "old-1") -> Any:
    return client.post(
        "/api/whitelist/content",
        json={
            "jellyfin_id": jellyfin_id,
            "name": f"Old Movie {jellyfin_id}",
            "media_type": "Movie",
        },
        headers=headers,
    )


def sent(route: respx.Route) -> dict[str, Any]:
    assert route.call_count == 1, f"expected one snapshot, got {route.call_count}"
    body: dict[str, Any] = json.loads(route.calls.last.request.content)
    return body


def keys(snapshot: dict[str, Any]) -> list[str]:
    return [alert["key"] for alert in snapshot["alerts"]]


@pytest.mark.usefixtures("hub_configured")
class TestWhitelistRefreshesAppAlerts:
    @respx.mock
    async def test_whitelisting_the_last_old_item_sends_a_snapshot_without_old(
        self, client: TestClient
    ) -> None:
        headers, user_id = login(client)
        await add_old_movie(user_id)
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        response = client.post(
            "/api/whitelist/content",
            json={"jellyfin_id": "old-1", "name": "Old Movie old-1", "media_type": "Movie"},
            headers=headers,
        )

        assert response.status_code == 201
        snapshot = sent(hub)
        assert snapshot["push"] is False
        assert keys(snapshot) == []


@pytest.mark.usefixtures("hub_configured")
class TestDeletionRefreshesAppAlerts:
    @respx.mock
    @patch("app.routers.settings.validate_radarr_connection", new_callable=AsyncMock)
    @patch("app.routers.content.delete_movie_by_tmdb_id", new_callable=AsyncMock)
    async def test_deleting_a_movie_sends_the_new_count(
        self, delete_movie: AsyncMock, validate_radarr: AsyncMock, client: TestClient
    ) -> None:
        validate_radarr.return_value = True
        delete_movie.return_value = (True, "Movie deleted")
        headers, user_id = login(client)
        client.post(
            "/api/settings/radarr",
            json={"server_url": "https://radarr.example.com", "api_key": "radarr-key"},
            headers=headers,
        )
        await add_old_movie(user_id, "old-1", tmdb_id="111")
        await add_old_movie(user_id, "old-2", tmdb_id="222")
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        response = client.request(
            "DELETE",
            "/api/content/movie/111",
            json={"tmdb_id": 111, "delete_from_arr": True, "delete_from_jellyseerr": False},
            headers=headers,
        )

        assert response.status_code == 200
        snapshot = sent(hub)
        assert snapshot["push"] is False
        assert [a["title"] for a in snapshot["alerts"]] == ["Old content · 1"]


@pytest.mark.usefixtures("hub_configured")
class TestThresholdChangeRefreshesAppAlerts:
    @respx.mock
    async def test_lowering_the_large_movie_size_sends_large_content(
        self, client: TestClient
    ) -> None:
        headers, user_id = login(client)
        await add_old_movie(user_id)
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        response = client.post(
            "/api/settings/analysis", json={"large_movie_size_gb": 4}, headers=headers
        )

        assert response.status_code == 200
        snapshot = sent(hub)
        assert snapshot["push"] is False
        assert keys(snapshot) == ["old", "large"]


@pytest.mark.usefixtures("hub_configured")
class TestRefreshKeepsSyncFailed:
    @pytest.mark.parametrize(
        ("status", "error", "context"),
        [
            ("partial", "Jellyseerr sync failed: timed out", "Jellyseerr: timed out"),
            ("failed", "Jellyfin sync failed: 401", "Jellyfin: 401"),
        ],
    )
    @respx.mock
    async def test_a_refresh_after_a_failed_or_partial_sync_keeps_sync_failed(
        self, status: str, error: str, context: str, client: TestClient
    ) -> None:
        headers, user_id = login(client)
        await add_old_movie(user_id)
        await set_last_sync(user_id, status, error)
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        whitelist(client, headers)

        alerts = sent(hub)["alerts"]
        assert [a["key"] for a in alerts] == ["sync-failed"]
        assert alerts[0]["context"] == context

    @respx.mock
    async def test_a_refresh_after_a_successful_sync_has_no_sync_failed(
        self, client: TestClient
    ) -> None:
        headers, user_id = login(client)
        await add_old_movie(user_id)
        await set_last_sync(user_id, "success", None)
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        whitelist(client, headers)

        assert keys(sent(hub)) == []


@pytest.mark.usefixtures("hub_configured")
class TestUnwhitelistRefreshesAppAlerts:
    @respx.mock
    async def test_removing_a_whitelist_entry_brings_the_category_back(
        self, client: TestClient
    ) -> None:
        headers, user_id = login(client)
        await add_old_movie(user_id)
        respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))
        whitelist(client, headers)
        entry_id = client.get("/api/whitelist/content", headers=headers).json()["items"][0]["id"]
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))
        hub.reset()

        response = client.delete(f"/api/whitelist/content/{entry_id}", headers=headers)

        assert response.status_code == 200
        snapshot = sent(hub)
        assert snapshot["push"] is False
        assert keys(snapshot) == ["old"]


@pytest.mark.usefixtures("hub_configured")
class TestRefreshSendsNothing:
    @respx.mock
    async def test_another_users_action_sends_nothing(self, client: TestClient) -> None:
        headers, user_id = login(client, "someone-else@example.com")
        await add_old_movie(user_id)
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        response = whitelist(client, headers)

        assert response.status_code == 201
        assert hub.call_count == 0

    @pytest.mark.parametrize(
        "unset", ["HUB_BASE_URL", "HUB_ALERT_USER_EMAIL", "HUB_APP_ALERT_TOKEN"]
    )
    @respx.mock
    async def test_unset_settings_send_nothing(
        self, unset: str, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(unset, "")
        get_settings.cache_clear()
        headers, user_id = login(client)
        await add_old_movie(user_id)
        hub = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))

        response = whitelist(client, headers)

        assert response.status_code == 201
        assert hub.call_count == 0


@pytest.mark.usefixtures("hub_configured")
class TestHubFailureLeavesTheActionAlone:
    @pytest.mark.parametrize(
        "hub_reply",
        [Response(500), httpx.ConnectTimeout("timed out")],
        ids=["error", "timeout"],
    )
    @respx.mock
    async def test_a_hub_error_or_timeout_does_not_change_the_response(
        self, hub_reply: Any, client: TestClient
    ) -> None:
        headers, user_id = login(client)
        await add_old_movie(user_id)
        hub = respx.put(HUB_ALERTS_URL).mock(side_effect=[hub_reply])

        response = whitelist(client, headers)

        assert response.status_code == 201
        assert response.json()["jellyfin_id"] == "old-1"
        assert hub.call_count == 1
