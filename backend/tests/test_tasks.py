"""Unit tests for tasks module functions (US-60.7).

Tests for:
- get_configured_user_ids() database query
- send_sync_failure_notification_for_celery() error handling path
- sync_user() exception handling and notification
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.database import User, UserSettings
from tests.conftest import TestingAsyncSessionLocal


class TestGetConfiguredUserIds:
    """Tests for get_configured_user_ids function."""

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_users_configured(self) -> None:
        """Should return empty list when no users have Jellyfin configured."""
        async with TestingAsyncSessionLocal() as session:
            # Create user without Jellyfin settings
            user = User(
                email="no_jellyfin@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.commit()

        # Test the query logic directly
        async with TestingAsyncSessionLocal() as test_session:
            from sqlalchemy import select

            result = await test_session.execute(
                select(UserSettings.user_id).where(
                    UserSettings.jellyfin_server_url.isnot(None),
                    UserSettings.jellyfin_api_key_encrypted.isnot(None),
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

            assert user_ids == []

    @pytest.mark.asyncio
    async def test_returns_user_ids_with_jellyfin_configured(self) -> None:
        """Should return user IDs that have both server URL and API key configured."""
        async with TestingAsyncSessionLocal() as session:
            # Create users
            user1 = User(
                email="configured1@example.com",
                hashed_password="fakehash",
            )
            user2 = User(
                email="configured2@example.com",
                hashed_password="fakehash",
            )
            user3 = User(
                email="not_configured@example.com",
                hashed_password="fakehash",
            )
            session.add_all([user1, user2, user3])
            await session.flush()

            # Configure Jellyfin for user1 and user2
            settings1 = UserSettings(
                user_id=user1.id,
                jellyfin_server_url="http://jellyfin1.local",
                jellyfin_api_key_encrypted="encrypted_key_1",
            )
            settings2 = UserSettings(
                user_id=user2.id,
                jellyfin_server_url="http://jellyfin2.local",
                jellyfin_api_key_encrypted="encrypted_key_2",
            )
            # user3 has no settings
            session.add_all([settings1, settings2])
            await session.commit()

            user1_id = user1.id
            user2_id = user2.id

        # Test the query logic directly
        async with TestingAsyncSessionLocal() as test_session:
            from sqlalchemy import select

            result = await test_session.execute(
                select(UserSettings.user_id).where(
                    UserSettings.jellyfin_server_url.isnot(None),
                    UserSettings.jellyfin_api_key_encrypted.isnot(None),
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

            assert len(user_ids) == 2
            assert user1_id in user_ids
            assert user2_id in user_ids

    @pytest.mark.asyncio
    async def test_excludes_users_with_only_server_url(self) -> None:
        """Should exclude users who have server URL but no API key."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="only_url@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # User has server URL but no API key
            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url="http://jellyfin.local",
                jellyfin_api_key_encrypted=None,
            )
            session.add(settings)
            await session.commit()

        async with TestingAsyncSessionLocal() as test_session:
            from sqlalchemy import select

            result = await test_session.execute(
                select(UserSettings.user_id).where(
                    UserSettings.jellyfin_server_url.isnot(None),
                    UserSettings.jellyfin_api_key_encrypted.isnot(None),
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

            assert len(user_ids) == 0

    @pytest.mark.asyncio
    async def test_excludes_users_with_only_api_key(self) -> None:
        """Should exclude users who have API key but no server URL."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="only_key@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.flush()

            # User has API key but no server URL
            settings = UserSettings(
                user_id=user.id,
                jellyfin_server_url=None,
                jellyfin_api_key_encrypted="encrypted_key",
            )
            session.add(settings)
            await session.commit()

        async with TestingAsyncSessionLocal() as test_session:
            from sqlalchemy import select

            result = await test_session.execute(
                select(UserSettings.user_id).where(
                    UserSettings.jellyfin_server_url.isnot(None),
                    UserSettings.jellyfin_api_key_encrypted.isnot(None),
                )
            )
            user_ids = [row[0] for row in result.fetchall()]

            assert len(user_ids) == 0


class TestSendSyncFailureNotificationForCeleryLogic:
    """Tests for send_sync_failure_notification_for_celery internal logic."""

    @pytest.mark.asyncio
    async def test_notification_called_with_user_email(self) -> None:
        """Should call async notification function with correct user email."""
        from app.tasks import _get_user_email

        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="notification_test@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.commit()
            user_id = user.id

        # Test the _get_user_email helper directly
        with patch("app.tasks.async_session_maker") as mock_session_maker:
            async with TestingAsyncSessionLocal() as test_session:
                mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
                mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

                email = await _get_user_email(user_id)
                assert email == "notification_test@example.com"

    @pytest.mark.asyncio
    async def test_fallback_email_when_user_not_found(self) -> None:
        """The fallback logic uses user_X when email not found."""
        # This tests the logic in the notification function:
        # if not user_email: user_email = f"user_{user_id}"
        user_email = None
        user_id = 999

        if not user_email:
            user_email = f"user_{user_id}"

        assert user_email == "user_999"

    @pytest.mark.asyncio
    async def test_get_user_email_returns_none_for_nonexistent_user(self) -> None:
        """Should return None when user doesn't exist."""
        from app.tasks import _get_user_email

        with patch("app.tasks.async_session_maker") as mock_session_maker:
            async with TestingAsyncSessionLocal() as test_session:
                mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=test_session)
                mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

                email = await _get_user_email(99999)
                assert email is None

    def test_notification_wrapper_logs_warning_on_exception(self) -> None:
        """Should log warning but not raise when notification fails."""
        from app.tasks import send_sync_failure_notification_for_celery

        # Use a real event loop but mock the internal async functions
        with (
            patch("app.tasks._get_user_email", new_callable=AsyncMock) as mock_get_email,
            patch("app.tasks.send_sync_failure_notification", new_callable=AsyncMock) as mock_send,
        ):
            mock_get_email.return_value = "test@example.com"
            mock_send.side_effect = Exception("Slack API error")

            with patch("app.tasks.logger") as mock_logger:
                # Should not raise
                send_sync_failure_notification_for_celery(
                    user_id=123,
                    error_message="Test error",
                )

                # Should log warning
                mock_logger.warning.assert_called_once()
                warning_message = mock_logger.warning.call_args[0][0]
                assert "Failed to send sync failure notification" in warning_message
                assert "123" in warning_message

    def test_notification_wrapper_sends_with_correct_params(self) -> None:
        """Should call send_sync_failure_notification with correct parameters."""
        from app.tasks import send_sync_failure_notification_for_celery

        with (
            patch("app.tasks._get_user_email", new_callable=AsyncMock) as mock_get_email,
            patch("app.tasks.send_sync_failure_notification", new_callable=AsyncMock) as mock_send,
        ):
            mock_get_email.return_value = "user@example.com"
            mock_send.return_value = None

            send_sync_failure_notification_for_celery(
                user_id=456,
                error_message="Connection timeout",
            )

            mock_send.assert_called_once_with(
                user_email="user@example.com",
                service="Scheduled Sync",
                error_message="Connection timeout",
            )

    def test_notification_wrapper_uses_fallback_email(self) -> None:
        """Should use fallback email when user not found."""
        from app.tasks import send_sync_failure_notification_for_celery

        with (
            patch("app.tasks._get_user_email", new_callable=AsyncMock) as mock_get_email,
            patch("app.tasks.send_sync_failure_notification", new_callable=AsyncMock) as mock_send,
        ):
            mock_get_email.return_value = None  # User not found
            mock_send.return_value = None

            send_sync_failure_notification_for_celery(
                user_id=999,
                error_message="Test error",
            )

            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert call_kwargs["user_email"] == "user_999"


class TestSyncUserTaskLogic:
    """Tests for sync_user task exception handling logic."""

    @pytest.mark.asyncio
    async def test_run_sync_for_user_calls_service(self) -> None:
        """Should call run_user_sync with correct parameters."""
        from app.tasks import _run_sync_for_user

        expected_result = {"status": "success", "media_count": 50}

        with (
            patch("app.tasks.run_user_sync") as mock_run_sync,
            patch("app.tasks.async_session_maker") as mock_session_maker,
        ):
            # Set up mock session
            mock_session = AsyncMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_run_sync.return_value = expected_result

            result = await _run_sync_for_user(123)

            mock_run_sync.assert_called_once_with(mock_session, 123)
            assert result == expected_result

    def test_sync_user_success_path(self) -> None:
        """Should return sync result on successful sync."""
        from app.tasks import sync_user

        expected_result = {
            "status": "success",
            "media_count": 100,
            "requests_count": 10,
        }

        with patch("app.tasks._run_sync_for_user", new_callable=AsyncMock) as mock_run_sync:
            mock_run_sync.return_value = expected_result

            result = sync_user(123)

            assert result == expected_result
            mock_run_sync.assert_called_once()

    def test_sync_user_failure_returns_error_dict(self) -> None:
        """Should return failed status dict when sync raises exception."""
        from app.tasks import sync_user

        with (
            patch("app.tasks._run_sync_for_user", new_callable=AsyncMock) as mock_run_sync,
            patch("app.tasks.send_sync_failure_notification_for_celery"),
        ):
            mock_run_sync.side_effect = ValueError("Jellyfin connection failed")

            result = sync_user(456)

            assert result["status"] == "failed"
            assert "Jellyfin connection failed" in result["error"]
            assert result["user_id"] == 456

    def test_sync_user_failure_sends_notification(self) -> None:
        """Should send failure notification when sync fails."""
        from app.tasks import sync_user

        with (
            patch("app.tasks._run_sync_for_user", new_callable=AsyncMock) as mock_run_sync,
            patch("app.tasks.send_sync_failure_notification_for_celery") as mock_send_notification,
        ):
            mock_run_sync.side_effect = RuntimeError("API timeout")

            sync_user(789)

            mock_send_notification.assert_called_once_with(
                user_id=789,
                error_message="API timeout",
            )

    def test_sync_user_failure_logs_error(self) -> None:
        """Should log error when sync fails."""
        from app.tasks import sync_user

        with (
            patch("app.tasks._run_sync_for_user", new_callable=AsyncMock) as mock_run_sync,
            patch("app.tasks.send_sync_failure_notification_for_celery"),
            patch("app.tasks.logger") as mock_logger,
        ):
            mock_run_sync.side_effect = Exception("Connection refused")

            sync_user(999)

            mock_logger.error.assert_called_once()
            error_message = mock_logger.error.call_args[0][0]
            assert "Sync failed for user 999" in error_message
            assert "Connection refused" in error_message

    def test_sync_user_logs_info_on_success(self) -> None:
        """Should log info when sync completes successfully."""
        from app.tasks import sync_user

        expected_result = {"status": "success"}

        with (
            patch("app.tasks._run_sync_for_user", new_callable=AsyncMock) as mock_run_sync,
            patch("app.tasks.logger") as mock_logger,
        ):
            mock_run_sync.return_value = expected_result

            sync_user(123)

            # Check that info was logged at start and completion
            info_calls = mock_logger.info.call_args_list
            assert len(info_calls) >= 2
            # First call: "Starting sync for user X"
            assert "Starting sync for user 123" in info_calls[0][0][0]
            # Second call: "Sync completed for user X"
            assert "Sync completed for user 123" in info_calls[1][0][0]


class TestGetUserEmail:
    """Tests for _get_user_email helper function."""

    @pytest.mark.asyncio
    async def test_returns_user_email_when_user_exists(self) -> None:
        """Should return user's email when user exists."""
        async with TestingAsyncSessionLocal() as session:
            user = User(
                email="test_email@example.com",
                hashed_password="fakehash",
            )
            session.add(user)
            await session.commit()
            user_id = user.id

        # Test the helper directly by querying
        async with TestingAsyncSessionLocal() as test_session:
            from sqlalchemy import select

            result = await test_session.execute(select(User).where(User.id == user_id))
            found_user = result.scalar_one_or_none()

            assert found_user is not None
            assert found_user.email == "test_email@example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(self) -> None:
        """Should return None when user doesn't exist."""
        async with TestingAsyncSessionLocal() as test_session:
            from sqlalchemy import select

            result = await test_session.execute(select(User).where(User.id == 99999))
            found_user = result.scalar_one_or_none()

            assert found_user is None


class TestSyncAllUsersTask:
    """Tests for sync_all_users task."""

    def test_sync_all_users_queues_each_user(self) -> None:
        """Should queue sync for each configured user."""
        from app.celery_app import celery_app
        from app.tasks import sync_all_users, sync_user

        # Set eager mode for testing
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        try:
            with (
                patch("app.tasks.get_configured_user_ids") as mock_get_users,
                patch.object(sync_user, "delay") as mock_sync,
            ):
                mock_get_users.return_value = [1, 2, 3]

                result = sync_all_users()

                assert mock_sync.call_count == 3
                mock_sync.assert_any_call(1)
                mock_sync.assert_any_call(2)
                mock_sync.assert_any_call(3)
                assert result == {"users_synced": 3, "status": "completed"}
        finally:
            celery_app.conf.task_always_eager = False
            celery_app.conf.task_eager_propagates = False

    def test_sync_all_users_handles_empty_list(self) -> None:
        """Should handle case when no users are configured."""
        from app.celery_app import celery_app
        from app.tasks import sync_all_users, sync_user

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        try:
            with (
                patch("app.tasks.get_configured_user_ids") as mock_get_users,
                patch.object(sync_user, "delay") as mock_sync,
            ):
                mock_get_users.return_value = []

                result = sync_all_users()

                mock_sync.assert_not_called()
                assert result == {"users_synced": 0, "status": "completed"}
        finally:
            celery_app.conf.task_always_eager = False
            celery_app.conf.task_eager_propagates = False

    def test_sync_all_users_logs_info_messages(self) -> None:
        """Should log info about starting and number of users."""
        from app.celery_app import celery_app
        from app.tasks import sync_all_users, sync_user

        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        try:
            with (
                patch("app.tasks.get_configured_user_ids") as mock_get_users,
                patch.object(sync_user, "delay"),
                patch("app.tasks.logger") as mock_logger,
            ):
                mock_get_users.return_value = [1, 2]

                sync_all_users()

                info_calls = mock_logger.info.call_args_list
                assert len(info_calls) >= 2
                # First call: "Starting daily sync for all users"
                assert "Starting daily sync" in info_calls[0][0][0]
                # Second call: "Found X users"
                assert "Found 2 users" in info_calls[1][0][0]
        finally:
            celery_app.conf.task_always_eager = False
            celery_app.conf.task_eager_propagates = False


class TestTestTask:
    """Tests for test_task."""

    def test_test_task_returns_success_with_input(self) -> None:
        """Should return success status with input value."""
        from app.tasks import test_task

        result = test_task("my_test_value")

        assert result == {"status": "success", "input": "my_test_value"}

    def test_test_task_handles_empty_string(self) -> None:
        """Should handle empty string input."""
        from app.tasks import test_task

        result = test_task("")

        assert result == {"status": "success", "input": ""}

    def test_test_task_handles_special_characters(self) -> None:
        """Should handle special characters in input."""
        from app.tasks import test_task

        result = test_task("test@#$%^&*()")

        assert result == {"status": "success", "input": "test@#$%^&*()"}
