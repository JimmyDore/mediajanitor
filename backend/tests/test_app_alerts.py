"""Tests for app.services.app_alerts: who and when report_sync_end reports to the Hub.

What a sync's snapshot holds is tested end to end through run_user_sync in
test_sync_mocked_integration.py; the Celery wrapper's cases are in test_tasks.py.
"""

import pytest
import respx
from httpx import Response

from app.config import get_settings
from app.database import User
from app.services.app_alerts import SyncFailure, report_sync_end
from tests.conftest import (
    HUB_ALERTS_URL,
    HUB_PING_URL,
    HUB_USER_EMAIL,
    TestingAsyncSessionLocal,
)


def mock_hub() -> tuple[respx.Route, respx.Route]:
    alerts = respx.put(HUB_ALERTS_URL).mock(return_value=Response(200))
    ping = respx.post(HUB_PING_URL).mock(return_value=Response(200, text="OK"))
    return alerts, ping


async def report(email: str, scheduled: bool = True, failure: SyncFailure | None = None) -> None:
    async with TestingAsyncSessionLocal() as session:
        user = User(email=email, hashed_password="fakehash")
        session.add(user)
        await session.commit()
        await report_sync_end(session, user.id, email, failure, scheduled)


@pytest.mark.usefixtures("hub_configured")
class TestReportSyncEnd:
    @respx.mock
    async def test_my_scheduled_sync_sends_the_snapshot_and_pings(self) -> None:
        alerts, ping = mock_hub()

        await report(HUB_USER_EMAIL, scheduled=True)

        assert alerts.call_count == 1
        assert ping.call_count == 1

    @respx.mock
    async def test_my_manual_sync_sends_the_snapshot_without_a_ping(self) -> None:
        alerts, ping = mock_hub()

        await report(HUB_USER_EMAIL, scheduled=False)

        assert alerts.call_count == 1
        assert ping.call_count == 0

    @respx.mock
    async def test_email_match_ignores_case(self) -> None:
        alerts, ping = mock_hub()

        await report("Me@Example.com")

        assert alerts.call_count == 1
        assert ping.call_count == 1

    @respx.mock
    async def test_another_account_sends_nothing(self) -> None:
        alerts, ping = mock_hub()

        await report("someone-else@example.com", failure=SyncFailure("Jellyfin", "down"))

        assert alerts.call_count == 0
        assert ping.call_count == 0

    @pytest.mark.parametrize("unset", ["HUB_BASE_URL", "HUB_ALERT_USER_EMAIL"])
    @respx.mock
    async def test_unset_hub_or_account_sends_nothing(
        self, unset: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(unset, "")
        get_settings.cache_clear()
        alerts, ping = mock_hub()

        await report(HUB_USER_EMAIL)

        assert alerts.call_count == 0
        assert ping.call_count == 0

    @respx.mock
    async def test_unset_app_alert_token_still_pings(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HUB_APP_ALERT_TOKEN", "")
        get_settings.cache_clear()
        alerts, ping = mock_hub()

        await report(HUB_USER_EMAIL)

        assert alerts.call_count == 0
        assert ping.call_count == 1

    @respx.mock
    async def test_unset_ping_token_still_sends_the_snapshot(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HUB_PING_TOKEN", "")
        get_settings.cache_clear()
        alerts, ping = mock_hub()

        await report(HUB_USER_EMAIL)

        assert alerts.call_count == 1
        assert ping.call_count == 0
