"""Tests for app.services.hub: the Hub client never raises and says whether the Hub
accepted the call."""

import json

import httpx
import pytest
import respx
from httpx import Response

from app.services.hub import send_app_alerts, send_ping

HUB = "https://hub.example.test/"
SNAPSHOT = {"name": "Media Janitor", "url": "https://mj.example.test/", "push": True, "alerts": []}


class TestSendAppAlerts:
    @respx.mock
    async def test_puts_the_snapshot_with_the_apps_token(self) -> None:
        route = respx.put("https://hub.example.test/api/app-alerts/mediajanitor").mock(
            return_value=Response(200, text="OK")
        )

        accepted = await send_app_alerts(HUB, "mediajanitor", "app-token", SNAPSHOT)

        assert accepted is True
        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer app-token"
        assert json.loads(request.content) == SNAPSHOT

    @respx.mock
    async def test_an_error_status_is_logged_and_returns_false(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        respx.put("https://hub.example.test/api/app-alerts/mediajanitor").mock(
            return_value=Response(422)
        )

        accepted = await send_app_alerts(HUB, "mediajanitor", "app-token", SNAPSHOT)

        assert accepted is False
        assert any("422" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")

    @respx.mock
    async def test_a_timeout_is_logged_and_returns_false(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        respx.put("https://hub.example.test/api/app-alerts/mediajanitor").mock(
            side_effect=httpx.ReadTimeout("too slow")
        )

        accepted = await send_app_alerts(HUB, "mediajanitor", "app-token", SNAPSHOT)

        assert accepted is False
        assert any("Hub" in r.getMessage() for r in caplog.records if r.levelname == "WARNING")


class TestSendPing:
    @respx.mock
    async def test_posts_the_task_ping_without_a_body(self) -> None:
        route = respx.post("https://hub.example.test/api/ping/mediajanitor-sync").mock(
            return_value=Response(200, text="OK")
        )

        accepted = await send_ping(HUB, "mediajanitor-sync", "ping-token")

        assert accepted is True
        request = route.calls.last.request
        assert request.headers["Authorization"] == "Bearer ping-token"
        assert request.content == b""

    @respx.mock
    async def test_an_error_status_returns_false(self) -> None:
        respx.post("https://hub.example.test/api/ping/mediajanitor-sync").mock(
            return_value=Response(401)
        )

        assert await send_ping(HUB, "mediajanitor-sync", "ping-token") is False
