"""
The nightly sync pings the Hub's `mediajanitor-sync` Task (Hub app-alerts ticket 05).

Drives run_user_sync and the Celery task wrappers with respx mocking Jellyfin and
the Hub, and checks only the ping sent to the Hub.
"""

import asyncio
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

import httpx
import pytest
import respx
from httpx import Response

from app.config import get_settings
from app.services.sync import run_user_sync
from tests.conftest import TestingAsyncSessionLocal
from tests.test_hub_app_alerts import (
    CLEAN_LIBRARY,
    FRONTEND,
    HUB,
    HUB_ALERTS_URL,
    JELLYFIN,
    JELLYSEERR,
    ME,
    TOKEN,
    create_user,
    mock_jellyfin,
)
from tests.test_sync_mocked_integration import mock_library_refresh_endpoints

PING_URL = f"{HUB}/api/ping/mediajanitor-sync"
PING_TOKEN = "hub-ping-test-token"


@pytest.fixture
def hub_configured(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("HUB_BASE_URL", HUB)
    monkeypatch.setenv("HUB_APP_ALERT_TOKEN", TOKEN)
    monkeypatch.setenv("HUB_PING_TOKEN", PING_TOKEN)
    monkeypatch.setenv("HUB_ALERT_USER_EMAIL", ME)
    monkeypatch.setenv("FRONTEND_URL", FRONTEND)
    monkeypatch.setenv("SLACK_WEBHOOK_SYNC_FAILURES", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def mock_hub(ping_response: Response | None = None) -> respx.Route:
    respx.put(HUB_ALERTS_URL).mock(return_value=Response(200, json={}))
    return respx.post(PING_URL).mock(return_value=ping_response or Response(200, text="OK"))


def assert_pinged_once(ping: respx.Route) -> None:
    assert ping.call_count == 1, f"expected one ping, got {ping.call_count}"
    request = ping.calls.last.request
    assert request.headers["Authorization"] == f"Bearer {PING_TOKEN}"


async def sync(user_id: int, scheduled: bool) -> dict[str, Any]:
    async with TestingAsyncSessionLocal() as session:
        return await run_user_sync(session, user_id, scheduled=scheduled)


@pytest.mark.usefixtures("hub_configured")
class TestScheduledSyncPings:
    @respx.mock
    async def test_successful_scheduled_sync_pings_once(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub()
        user_id = await create_user()

        result = await sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert_pinged_once(ping)

    @respx.mock
    async def test_partial_scheduled_sync_pings_once(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        mock_library_refresh_endpoints(jellyfin_base=JELLYFIN, jellyseerr_base=JELLYSEERR)
        respx.get(f"{JELLYSEERR}/api/v1/user").mock(
            return_value=Response(200, json={"results": []})
        )
        respx.get(f"{JELLYSEERR}/api/v1/request").mock(
            return_value=Response(401, json={"error": "Unauthorized"})
        )
        ping = mock_hub()
        user_id = await create_user(with_jellyseerr=True)

        result = await sync(user_id, scheduled=True)

        assert result["status"] == "partial"
        assert_pinged_once(ping)

    @respx.mock
    async def test_failed_scheduled_sync_pings_once(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        respx.get(f"{JELLYFIN}/Users").mock(return_value=Response(401, json={"error": "no"}))
        ping = mock_hub()
        user_id = await create_user()

        result = await sync(user_id, scheduled=True)

        assert result["status"] == "failed"
        assert_pinged_once(ping)


@pytest.mark.usefixtures("hub_configured")
class TestNoPing:
    @respx.mock
    async def test_manual_sync_sends_no_ping(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub()
        user_id = await create_user()

        result = await sync(user_id, scheduled=False)

        assert result["status"] == "success"
        assert ping.call_count == 0

    @respx.mock
    async def test_another_users_scheduled_sync_sends_no_ping(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub()
        user_id = await create_user(email="someone-else@example.com")

        await sync(user_id, scheduled=True)

        assert ping.call_count == 0

    @pytest.mark.parametrize("unset", ["HUB_BASE_URL", "HUB_PING_TOKEN", "HUB_ALERT_USER_EMAIL"])
    @respx.mock
    async def test_unset_setting_sends_no_ping(
        self, unset: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(unset, "")
        get_settings.cache_clear()
        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub()
        user_id = await create_user()

        result = await sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert ping.call_count == 0


@pytest.mark.usefixtures("hub_configured")
class TestHubDown:
    @respx.mock
    async def test_ping_error_does_not_change_the_outcome(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub(Response(500, text="boom"))
        user_id = await create_user()

        result = await sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert ping.call_count == 1
        assert any("500" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")

    @respx.mock
    async def test_ping_timeout_does_not_change_the_outcome(self) -> None:
        mock_jellyfin(CLEAN_LIBRARY)
        respx.put(HUB_ALERTS_URL).mock(return_value=Response(200, json={}))
        ping = respx.post(PING_URL).mock(side_effect=httpx.ReadTimeout("too slow"))
        user_id = await create_user()

        result = await sync(user_id, scheduled=True)

        assert result["status"] == "success"
        assert ping.call_count == 1


@pytest.fixture
def celery_eager() -> Generator[None, None, None]:
    from app.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    yield
    celery_app.conf.task_always_eager = False
    celery_app.conf.task_eager_propagates = False


@pytest.mark.usefixtures("hub_configured", "celery_eager")
class TestCeleryWrappers:
    @respx.mock
    async def test_nightly_fan_out_pings_once(self) -> None:
        from app.tasks import sync_all_users

        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub()
        user_id = await create_user()

        with (
            patch("app.tasks.async_session_maker", TestingAsyncSessionLocal),
            patch("app.tasks.get_configured_user_ids", return_value=[user_id]),
        ):
            await asyncio.to_thread(sync_all_users)

        assert_pinged_once(ping)

    @respx.mock
    async def test_manual_sync_task_sends_no_ping(self) -> None:
        from app.tasks import sync_user

        mock_jellyfin(CLEAN_LIBRARY)
        ping = mock_hub()
        user_id = await create_user()

        with patch("app.tasks.async_session_maker", TestingAsyncSessionLocal):
            result = await asyncio.to_thread(sync_user.delay, user_id)

        assert result.get()["status"] == "success"
        assert ping.call_count == 0

    @respx.mock
    async def test_unhandled_exception_in_scheduled_sync_pings_once(self) -> None:
        from app.tasks import sync_user

        ping = mock_hub()
        user_id = await create_user()

        with (
            patch("app.tasks.async_session_maker", TestingAsyncSessionLocal),
            patch("app.tasks.run_user_sync", side_effect=RuntimeError("worker exploded")),
            patch("app.tasks.send_sync_failure_notification_for_celery"),
        ):
            result = await asyncio.to_thread(sync_user, user_id, scheduled=True)

        assert result["status"] == "failed"
        assert_pinged_once(ping)

    @respx.mock
    async def test_unhandled_exception_in_manual_sync_sends_no_ping(self) -> None:
        from app.tasks import sync_user

        ping = mock_hub()
        user_id = await create_user()

        with (
            patch("app.tasks.async_session_maker", TestingAsyncSessionLocal),
            patch("app.tasks.run_user_sync", side_effect=RuntimeError("worker exploded")),
            patch("app.tasks.send_sync_failure_notification_for_celery"),
        ):
            result = await asyncio.to_thread(sync_user, user_id)

        assert result["status"] == "failed"
        assert ping.call_count == 0
