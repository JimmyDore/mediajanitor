"""Tests for library refresh integration in run_user_sync (US-64.5)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.database import User, UserSettings
from tests.conftest import TestingAsyncSessionLocal


class TestLibraryRefreshIntegration:
    """Test that library refresh is called at the START of sync."""

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    @patch("app.services.sync.trigger_jellyfin_library_refresh")
    @patch("app.services.sync.wait_for_jellyfin_scan_completion")
    async def test_jellyfin_refresh_called_before_fetch(
        self,
        mock_wait_jellyfin: AsyncMock,
        mock_trigger_jellyfin: AsyncMock,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_fetch_jellyfin: AsyncMock,
    ) -> None:
        """Should trigger Jellyfin library refresh BEFORE fetching media data."""
        from app.services.sync import run_user_sync

        # Track call order
        call_order: list[str] = []

        async def track_trigger_jellyfin(*args, **kwargs):
            call_order.append("trigger_jellyfin_refresh")
            return True

        async def track_wait_jellyfin(*args, **kwargs):
            call_order.append("wait_jellyfin_refresh")
            return True

        async def track_fetch_jellyfin(*args, **kwargs):
            call_order.append("fetch_jellyfin_media")
            return []

        mock_trigger_jellyfin.side_effect = track_trigger_jellyfin
        mock_wait_jellyfin.side_effect = track_wait_jellyfin
        mock_fetch_jellyfin.side_effect = track_fetch_jellyfin
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                await run_user_sync(session, user.id)

            # Verify call order: refresh BEFORE fetch
            assert "trigger_jellyfin_refresh" in call_order
            assert "fetch_jellyfin_media" in call_order
            trigger_idx = call_order.index("trigger_jellyfin_refresh")
            fetch_idx = call_order.index("fetch_jellyfin_media")
            assert trigger_idx < fetch_idx, "Jellyfin refresh must happen before fetch"

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyseerr_requests")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    @patch("app.services.sync.trigger_jellyfin_library_refresh")
    @patch("app.services.sync.wait_for_jellyfin_scan_completion")
    @patch("app.services.sync.trigger_jellyseerr_library_sync")
    @patch("app.services.sync.wait_for_jellyseerr_sync_completion")
    async def test_jellyseerr_sync_called_before_requests_fetch(
        self,
        mock_wait_jellyseerr: AsyncMock,
        mock_trigger_jellyseerr: AsyncMock,
        mock_wait_jellyfin: AsyncMock,
        mock_trigger_jellyfin: AsyncMock,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_fetch_requests: AsyncMock,
        mock_fetch_jellyfin: AsyncMock,
    ) -> None:
        """Should trigger Jellyseerr library sync BEFORE fetching requests."""
        from app.services.sync import run_user_sync

        # Track call order
        call_order: list[str] = []

        async def track_trigger_jellyseerr(*args, **kwargs):
            call_order.append("trigger_jellyseerr_sync")
            return True

        async def track_wait_jellyseerr(*args, **kwargs):
            call_order.append("wait_jellyseerr_sync")
            return True

        async def track_fetch_requests(*args, **kwargs):
            call_order.append("fetch_jellyseerr_requests")
            return []

        mock_trigger_jellyfin.return_value = True
        mock_wait_jellyfin.return_value = True
        mock_trigger_jellyseerr.side_effect = track_trigger_jellyseerr
        mock_wait_jellyseerr.side_effect = track_wait_jellyseerr
        mock_fetch_jellyfin.return_value = []
        mock_fetch_requests.side_effect = track_fetch_requests
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted="encrypted-jellyseerr-key",
            )
            session.add(settings)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                await run_user_sync(session, user.id)

            # Verify Jellyseerr sync happens before fetching requests
            assert "trigger_jellyseerr_sync" in call_order
            assert "fetch_jellyseerr_requests" in call_order
            trigger_idx = call_order.index("trigger_jellyseerr_sync")
            fetch_idx = call_order.index("fetch_jellyseerr_requests")
            assert trigger_idx < fetch_idx, "Jellyseerr sync must happen before request fetch"

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    @patch("app.services.sync.trigger_jellyfin_library_refresh")
    @patch("app.services.sync.wait_for_jellyfin_scan_completion")
    async def test_sync_continues_if_jellyfin_refresh_fails(
        self,
        mock_wait_jellyfin: AsyncMock,
        mock_trigger_jellyfin: AsyncMock,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_fetch_jellyfin: AsyncMock,
    ) -> None:
        """Should continue sync if Jellyfin library refresh fails (non-blocking)."""
        from app.services.sync import run_user_sync

        # Refresh fails, but sync should continue
        mock_trigger_jellyfin.return_value = False
        mock_wait_jellyfin.return_value = False
        mock_fetch_jellyfin.return_value = [
            {"Id": "test-1", "Name": "Test Movie", "Type": "Movie", "UserData": {}}
        ]
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                result = await run_user_sync(session, user.id)

            # Sync should succeed even if refresh failed
            assert result["status"] == "success"
            assert result["media_items_synced"] == 1

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyseerr_requests")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    @patch("app.services.sync.trigger_jellyfin_library_refresh")
    @patch("app.services.sync.wait_for_jellyfin_scan_completion")
    @patch("app.services.sync.trigger_jellyseerr_library_sync")
    @patch("app.services.sync.wait_for_jellyseerr_sync_completion")
    async def test_sync_continues_if_jellyseerr_sync_fails(
        self,
        mock_wait_jellyseerr: AsyncMock,
        mock_trigger_jellyseerr: AsyncMock,
        mock_wait_jellyfin: AsyncMock,
        mock_trigger_jellyfin: AsyncMock,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_fetch_requests: AsyncMock,
        mock_fetch_jellyfin: AsyncMock,
    ) -> None:
        """Should continue sync if Jellyseerr library sync fails (non-blocking)."""
        from app.services.sync import run_user_sync

        # Jellyfin refresh succeeds, Jellyseerr sync fails
        mock_trigger_jellyfin.return_value = True
        mock_wait_jellyfin.return_value = True
        mock_trigger_jellyseerr.return_value = False
        mock_wait_jellyseerr.return_value = False
        mock_fetch_jellyfin.return_value = [
            {"Id": "test-1", "Name": "Test Movie", "Type": "Movie", "UserData": {}}
        ]
        mock_fetch_requests.return_value = [
            {"id": 1, "media": {"tmdbId": 123, "mediaType": "movie"}, "status": 2}
        ]
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted="encrypted-jellyseerr-key",
            )
            session.add(settings)
            await session.commit()

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                result = await run_user_sync(session, user.id)

            # Sync should succeed even if Jellyseerr sync failed
            assert result["status"] == "success"
            assert result["media_items_synced"] == 1
            assert result["requests_synced"] == 1


class TestSyncProgressRefreshingLibraries:
    """Test that sync progress shows 'refreshing_libraries' step."""

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    @patch("app.services.sync.trigger_jellyfin_library_refresh")
    @patch("app.services.sync.wait_for_jellyfin_scan_completion")
    async def test_updates_progress_to_refreshing_libraries_step(
        self,
        mock_wait_jellyfin: AsyncMock,
        mock_trigger_jellyfin: AsyncMock,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_fetch_jellyfin: AsyncMock,
    ) -> None:
        """Should update sync progress to 'refreshing_libraries' step during refresh."""
        from app.services.sync import run_user_sync

        # Track what steps are set
        captured_steps: list[str | None] = []

        mock_trigger_jellyfin.return_value = True
        mock_wait_jellyfin.return_value = True
        mock_fetch_jellyfin.return_value = []
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
            )
            session.add(settings)
            await session.commit()

            # Patch update_sync_progress to track what steps are set (without recursion)
            async def track_progress(db, user_id, current_step=None, **kwargs):
                if current_step:
                    captured_steps.append(current_step)

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                with patch(
                    "app.services.sync.update_sync_progress",
                    side_effect=track_progress,
                ):
                    await run_user_sync(session, user.id)

            # Verify "refreshing_libraries" step was set
            assert (
                "refreshing_libraries" in captured_steps
            ), f"Expected 'refreshing_libraries' step, got: {captured_steps}"

    @pytest.mark.asyncio
    @patch("app.services.sync.fetch_jellyfin_media_with_progress")
    @patch("app.services.sync.fetch_jellyseerr_requests")
    @patch("app.services.sync.fetch_jellyfin_users")
    @patch("app.services.sync.fetch_jellyseerr_users")
    @patch("app.services.sync.trigger_jellyfin_library_refresh")
    @patch("app.services.sync.wait_for_jellyfin_scan_completion")
    @patch("app.services.sync.trigger_jellyseerr_library_sync")
    @patch("app.services.sync.wait_for_jellyseerr_sync_completion")
    async def test_total_steps_increased_for_refresh_step(
        self,
        mock_wait_jellyseerr: AsyncMock,
        mock_trigger_jellyseerr: AsyncMock,
        mock_wait_jellyfin: AsyncMock,
        mock_trigger_jellyfin: AsyncMock,
        mock_jellyseerr_users: AsyncMock,
        mock_jellyfin_users: AsyncMock,
        mock_fetch_requests: AsyncMock,
        mock_fetch_jellyfin: AsyncMock,
    ) -> None:
        """Should include refreshing_libraries in total_steps count."""

        from app.services.sync import run_user_sync

        mock_trigger_jellyfin.return_value = True
        mock_wait_jellyfin.return_value = True
        mock_trigger_jellyseerr.return_value = True
        mock_wait_jellyseerr.return_value = True
        mock_fetch_jellyfin.return_value = []
        mock_fetch_requests.return_value = []
        mock_jellyfin_users.return_value = []
        mock_jellyseerr_users.return_value = []

        async with TestingAsyncSessionLocal() as session:
            user = User(email="test@example.com", hashed_password="fakehash")
            session.add(user)
            await session.flush()

            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted="encrypted-key",
                jellyseerr_server_url="http://jellyseerr.local",
                jellyseerr_api_key_encrypted="encrypted-jellyseerr-key",
            )
            session.add(settings)
            await session.commit()

            # Track total_steps passed to update_sync_status
            captured_total_steps = None

            async def capture_total_steps(db, user_id, status, total_steps=None, **kwargs):
                nonlocal captured_total_steps
                if total_steps is not None:
                    captured_total_steps = total_steps

            with patch("app.services.sync.decrypt_value", return_value="decrypted-key"):
                with patch(
                    "app.services.sync.update_sync_status",
                    side_effect=capture_total_steps,
                ):
                    await run_user_sync(session, user.id)

            # With Jellyseerr configured, total steps should be 3:
            # 1. refreshing_libraries
            # 2. syncing_media
            # 3. syncing_requests
            assert (
                captured_total_steps == 3
            ), f"Expected 3 total steps (refresh, media, requests), got {captured_total_steps}"
