"""
App alerts sent to the Hub at the end of a sync (Hub app-alerts ticket 04).

Drives run_user_sync end to end with respx mocking Jellyfin, Jellyseerr and the Hub,
and checks only what is sent to the Hub.
"""

import asyncio
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

from app.config import get_settings
from app.database import ContentWhitelist, User, UserSettings
from app.services.encryption import encrypt_value
from app.services.sync import run_user_sync
from tests.conftest import TestingAsyncSessionLocal
from tests.test_sync_mocked_integration import mock_library_refresh_endpoints

JELLYFIN = "http://jellyfin.local"
JELLYSEERR = "http://jellyseerr.local"
HUB = "https://hub.example.test"
HUB_ALERTS_URL = f"{HUB}/api/app-alerts/mediajanitor"
FRONTEND = "https://mj.example.test"
ME = "me@example.com"
TOKEN = "mj-test-token"

GIB = 1024 * 1024 * 1024
BOTH_AUDIO = [
    {"Type": "Audio", "Language": "eng"},
    {"Type": "Audio", "Language": "fre"},
]
ENGLISH_ONLY = [{"Type": "Audio", "Language": "eng"}]
FRENCH_ONLY = [{"Type": "Audio", "Language": "fre"}]


def _movie(
    jellyfin_id: str,
    name: str,
    size_bytes: int,
    streams: list[dict[str, str]],
    last_played: str | None = None,
) -> dict[str, Any]:
    user_data: dict[str, Any] = {"Played": False, "PlayCount": 0}
    if last_played:
        user_data = {"Played": True, "PlayCount": 1, "LastPlayedDate": last_played}
    return {
        "Id": jellyfin_id,
        "Name": name,
        "Type": "Movie",
        "ProductionYear": 2000,
        "DateCreated": "2023-01-15T10:00:00Z",
        "Path": f"/media/movies/{name}/movie.mkv",
        "UserData": user_data,
        "MediaSources": [{"Size": size_bytes, "MediaStreams": streams}],
    }


def _recently() -> str:
    return (datetime.now(UTC) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")


def library() -> list[dict[str, Any]]:
    """A library with 5 old, 1 large, 2 language-issue items and 1 clean one.

    Old (largest first): Dune 20, Heat 4, Alien 3, Arrival 2, Brazil 0.5 GiB = 29.5 GiB
    Large: Dune 20 GiB
    Language: Arrival 2 (EN only), Amelie 1 (FR only) = 3 GiB
    """
    return [
        _movie("dune", "Dune", 20 * GIB, BOTH_AUDIO, last_played="2023-06-15T10:00:00Z"),
        _movie("heat", "Heat", 4 * GIB, BOTH_AUDIO),
        _movie("alien", "Alien", 3 * GIB, BOTH_AUDIO),
        _movie("arrival", "Arrival", 2 * GIB, ENGLISH_ONLY),
        _movie("brazil", "Brazil", GIB // 2, BOTH_AUDIO),
        _movie("amelie", "Amelie", 1 * GIB, FRENCH_ONLY, last_played=_recently()),
        _movie("fresh", "Fresh", 1 * GIB, BOTH_AUDIO, last_played=_recently()),
    ]


CLEAN_LIBRARY = [
    _movie("fresh", "Fresh", 1 * GIB, BOTH_AUDIO, last_played=_recently()),
]


def mock_jellyfin(items: list[dict[str, Any]]) -> None:
    mock_library_refresh_endpoints(jellyfin_base=JELLYFIN)
    respx.get(f"{JELLYFIN}/Users").mock(
        return_value=Response(200, json=[{"Id": "jf-user", "Name": "Admin"}])
    )
    respx.get(f"{JELLYFIN}/Users/jf-user/Items").mock(
        return_value=Response(200, json={"Items": items, "TotalRecordCount": len(items)})
    )
    respx.get(f"{JELLYFIN}/Items").mock(return_value=Response(200, json={"Items": []}))


def _request(request_id: int, tmdb_id: int, media_status: int) -> dict[str, Any]:
    return {
        "id": request_id,
        "status": 2,  # Approved
        "createdAt": f"2024-01-0{request_id}T10:00:00Z",
        "media": {
            "id": request_id,
            "tmdbId": tmdb_id,
            "mediaType": "movie",
            "status": media_status,
        },
        "requestedBy": {"displayName": "Admin"},
    }


# Unavailable: Solaris, Stalker, Ran, Ikiru (newest first). Available: Amadeus.
REQUESTS = [
    (1, 101, "Ikiru", 2),
    (2, 102, "Ran", 2),
    (3, 103, "Stalker", 2),
    (4, 104, "Solaris", 2),
    (5, 105, "Amadeus", 5),
]


def mock_jellyseerr() -> None:
    mock_library_refresh_endpoints(jellyfin_base=JELLYFIN, jellyseerr_base=JELLYSEERR)
    respx.get(f"{JELLYSEERR}/api/v1/user").mock(return_value=Response(200, json={"results": []}))
    respx.get(f"{JELLYSEERR}/api/v1/request").mock(
        return_value=Response(
            200,
            json={
                "pageInfo": {"pages": 1, "results": len(REQUESTS)},
                "results": [_request(rid, tmdb, status) for rid, tmdb, _, status in REQUESTS],
            },
        )
    )
    for _, tmdb_id, title, _ in REQUESTS:
        respx.get(f"{JELLYSEERR}/api/v1/movie/{tmdb_id}").mock(
            return_value=Response(
                200, json={"id": tmdb_id, "title": title, "releaseDate": "2020-01-01"}
            )
        )


def mock_hub(response: Response | None = None) -> respx.Route:
    return respx.put(HUB_ALERTS_URL).mock(return_value=response or Response(200, json={}))


def sent_snapshot(route: respx.Route) -> dict[str, Any]:
    assert route.call_count == 1, f"expected one snapshot, got {route.call_count}"
    request = route.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {TOKEN}"
    body: dict[str, Any] = json.loads(request.content)
    return body


def alerts_by_key(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {alert["key"]: alert for alert in snapshot["alerts"]}


@pytest.fixture
def hub_configured(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("HUB_BASE_URL", HUB)
    monkeypatch.setenv("HUB_APP_ALERT_TOKEN", TOKEN)
    monkeypatch.setenv("HUB_ALERT_USER_EMAIL", ME)
    monkeypatch.setenv("FRONTEND_URL", FRONTEND)
    monkeypatch.setenv("SLACK_WEBHOOK_SYNC_FAILURES", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def create_user(
    email: str = ME,
    with_jellyseerr: bool = False,
) -> int:
    async with TestingAsyncSessionLocal() as session:
        user = User(email=email, hashed_password="fakehash")
        session.add(user)
        await session.flush()
        settings = UserSettings(
            user_id=user.id,
            jellyfin_server_url=JELLYFIN,
            jellyfin_api_key_encrypted=encrypt_value("jellyfin-key"),
        )
        if with_jellyseerr:
            settings.jellyseerr_server_url = JELLYSEERR
            settings.jellyseerr_api_key_encrypted = encrypt_value("jellyseerr-key")
        session.add(settings)
        await session.commit()
        return user.id


async def sync(user_id: int) -> dict[str, Any]:
    async with TestingAsyncSessionLocal() as session:
        return await run_user_sync(session, user_id)


@pytest.mark.usefixtures("hub_configured")
class TestSnapshotAfterSync:
    @respx.mock
    async def test_sends_old_content_alert(self) -> None:
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user()

        result = await sync(user_id)

        assert result["status"] == "success"
        snapshot = sent_snapshot(hub)
        assert snapshot["name"] == "Media Janitor"
        assert snapshot["url"] == f"{FRONTEND}/"
        assert snapshot["push"] is True
        assert alerts_by_key(snapshot)["old"] == {
            "key": "old",
            "title": "Old content · 5",
            "context": "29.5 GB · Dune, Heat, Alien, +2",
            "url": f"{FRONTEND}/issues?filter=old",
        }

    @respx.mock
    async def test_sends_large_and_language_alerts(self) -> None:
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user()

        await sync(user_id)

        alerts = alerts_by_key(sent_snapshot(hub))
        assert set(alerts) == {"old", "large", "language"}
        assert alerts["large"] == {
            "key": "large",
            "title": "Large content · 1",
            "context": "20.0 GB · Dune",
            "url": f"{FRONTEND}/issues?filter=large",
        }
        assert alerts["language"] == {
            "key": "language",
            "title": "Language issues · 2",
            "context": "3.0 GB · Arrival, Amelie",
            "url": f"{FRONTEND}/issues?filter=language",
        }

    @respx.mock
    async def test_whitelisted_media_are_left_out(self) -> None:
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user()
        async with TestingAsyncSessionLocal() as session:
            session.add(
                ContentWhitelist(
                    user_id=user_id, jellyfin_id="heat", name="Heat", media_type="Movie"
                )
            )
            await session.commit()

        await sync(user_id)

        old = alerts_by_key(sent_snapshot(hub))["old"]
        assert old["title"] == "Old content · 4"
        assert old["context"] == "25.5 GB · Dune, Alien, Arrival, +1"

    @respx.mock
    async def test_clean_sync_sends_an_empty_snapshot(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        hub = mock_hub()
        user_id = await create_user()

        await sync(user_id)

        snapshot = sent_snapshot(hub)
        assert snapshot == {
            "name": "Media Janitor",
            "url": f"{FRONTEND}/",
            "push": True,
            "alerts": [],
        }

    @respx.mock
    async def test_sends_unavailable_requests_with_titles_only(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        mock_jellyseerr()
        hub = mock_hub()
        user_id = await create_user(with_jellyseerr=True)

        result = await sync(user_id)

        assert result["status"] == "success"
        assert sent_snapshot(hub)["alerts"] == [
            {
                "key": "requests",
                "title": "Unavailable requests · 4",
                "context": "Solaris, Stalker, Ran, +1",
                "url": f"{FRONTEND}/issues?filter=requests",
            }
        ]


@pytest.mark.usefixtures("hub_configured")
class TestSyncFailedAlert:
    @respx.mock
    async def test_partial_sync_adds_sync_failed(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        mock_library_refresh_endpoints(jellyfin_base=JELLYFIN, jellyseerr_base=JELLYSEERR)
        respx.get(f"{JELLYSEERR}/api/v1/user").mock(
            return_value=Response(200, json={"results": []})
        )
        respx.get(f"{JELLYSEERR}/api/v1/request").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )
        hub = mock_hub()
        user_id = await create_user(with_jellyseerr=True)

        result = await sync(user_id)

        assert result["status"] == "partial"
        alerts = sent_snapshot(hub)["alerts"]
        assert [a["key"] for a in alerts] == ["sync-failed"]
        failed = alerts[0]
        assert failed["title"] == "Media Janitor sync failed"
        assert failed["url"] == f"{FRONTEND}/"
        assert failed["context"].startswith("Jellyseerr: ")
        assert "401" in failed["context"]
        assert len(failed["context"]) <= 300

    @respx.mock
    async def test_failed_sync_still_sends_categories_from_the_cache(self) -> None:
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user()
        await sync(user_id)  # fills the cache
        respx.get(f"{JELLYFIN}/Users").mock(return_value=Response(401, json={"error": "no"}))

        result = await sync(user_id)

        assert result["status"] == "failed"
        assert hub.call_count == 2
        snapshot = json.loads(hub.calls.last.request.content)
        alerts = alerts_by_key(snapshot)
        assert set(alerts) == {"old", "large", "language", "sync-failed"}
        assert alerts["old"]["title"] == "Old content · 5"
        assert alerts["sync-failed"]["context"].startswith("Jellyfin: ")
        assert "401" in alerts["sync-failed"]["context"]


@pytest.mark.usefixtures("hub_configured")
class TestWhoReports:
    @respx.mock
    async def test_another_users_sync_sends_nothing(self) -> None:
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user(email="someone-else@example.com")

        result = await sync(user_id)

        assert result["status"] == "success"
        assert hub.call_count == 0

    @respx.mock
    async def test_email_match_ignores_case(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        hub = mock_hub()
        user_id = await create_user(email="Me@Example.com")

        await sync(user_id)

        assert hub.call_count == 1

    @pytest.mark.parametrize(
        "unset", ["HUB_BASE_URL", "HUB_APP_ALERT_TOKEN", "HUB_ALERT_USER_EMAIL"]
    )
    @respx.mock
    async def test_unset_setting_sends_nothing(
        self, unset: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(unset, "")
        get_settings.cache_clear()
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user()

        result = await sync(user_id)

        assert result["status"] == "success"
        assert hub.call_count == 0

    @respx.mock
    async def test_jellyfin_not_configured_sends_nothing(self) -> None:
        hub = mock_hub()
        async with TestingAsyncSessionLocal() as session:
            user = User(email=ME, hashed_password="fakehash")
            session.add(user)
            await session.commit()
            user_id = user.id

        result = await sync(user_id)

        assert result["error"] == "Jellyfin not configured"
        assert hub.call_count == 0


@pytest.mark.usefixtures("hub_configured")
class TestHubDown:
    @respx.mock
    async def test_hub_500_is_logged_and_sync_ends_normally(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_jellyfin(library())
        hub = mock_hub(Response(500, json={"error": "boom"}))
        user_id = await create_user()

        result = await sync(user_id)

        assert result["status"] == "success"
        assert hub.call_count == 1
        assert any("500" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")

    @respx.mock
    async def test_hub_timeout_is_logged_and_sync_ends_normally(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_jellyfin(library())
        hub = respx.put(HUB_ALERTS_URL).mock(side_effect=httpx.ReadTimeout("too slow"))
        user_id = await create_user()

        result = await sync(user_id)

        assert result["status"] == "success"
        assert hub.call_count == 1
        assert any("Hub" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")


@pytest.mark.usefixtures("hub_configured")
class TestCeleryWrapperUnhandledException:
    @respx.mock
    async def test_unhandled_exception_sends_sync_failed_with_cached_categories(self) -> None:
        mock_jellyfin(library())
        hub = mock_hub()
        user_id = await create_user()
        await sync(user_id)  # fills the cache

        from app.tasks import sync_user

        with (
            patch("app.tasks.async_session_maker", TestingAsyncSessionLocal),
            patch("app.tasks.run_user_sync", side_effect=RuntimeError("worker exploded")),
            patch("app.tasks.send_sync_failure_notification_for_celery"),
        ):
            result = await asyncio.to_thread(sync_user, user_id)

        assert result["status"] == "failed"
        assert hub.call_count == 2
        alerts = alerts_by_key(json.loads(hub.calls.last.request.content))
        assert set(alerts) == {"old", "large", "language", "sync-failed"}
        assert alerts["sync-failed"]["context"] == "Sync: worker exploded"

    @respx.mock
    async def test_unhandled_exception_for_another_user_sends_nothing(self) -> None:
        hub = mock_hub()
        user_id = await create_user(email="someone-else@example.com")

        from app.tasks import sync_user

        with (
            patch("app.tasks.async_session_maker", TestingAsyncSessionLocal),
            patch("app.tasks.run_user_sync", side_effect=RuntimeError("worker exploded")),
            patch("app.tasks.send_sync_failure_notification_for_celery"),
        ):
            result = await asyncio.to_thread(sync_user, user_id)

        assert result["status"] == "failed"
        assert hub.call_count == 0
