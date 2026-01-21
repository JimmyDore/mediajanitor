"""Tests for Celery configuration and tasks."""

from unittest.mock import patch


class TestCeleryConfiguration:
    """Tests for Celery app configuration."""

    def test_celery_eager_mode_for_testing(self) -> None:
        """Test that Celery can be configured to run tasks eagerly (synchronously) for testing."""
        from app.celery_app import celery_app
        from app.tasks import test_task

        # Set eager mode (tasks run synchronously without broker)
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        try:
            # Now delay() should work without a broker
            result = test_task.delay("eager_test")
            assert result.get() == {"status": "success", "input": "eager_test"}
        finally:
            # Reset to normal mode
            celery_app.conf.task_always_eager = False
            celery_app.conf.task_eager_propagates = False


class TestCeleryConfigurationBasic:
    """Tests for Celery app configuration."""

    def test_celery_app_exists(self) -> None:
        """Test that Celery app is properly configured."""
        from app.celery_app import celery_app

        assert celery_app is not None
        assert celery_app.main == "plex-dashboard"

    def test_celery_broker_configured(self) -> None:
        """Test that Celery broker is configured to Redis."""
        from app.celery_app import celery_app

        # Broker URL should be Redis
        assert "redis" in celery_app.conf.broker_url

    def test_celery_result_backend_configured(self) -> None:
        """Test that Celery result backend is configured."""
        from app.celery_app import celery_app

        assert celery_app.conf.result_backend is not None


class TestCeleryTasks:
    """Tests for Celery tasks."""

    def test_test_task_exists(self) -> None:
        """Test that test task is registered."""
        from app.tasks import test_task

        assert test_task is not None
        assert hasattr(test_task, "delay")

    def test_test_task_can_be_called_synchronously(self) -> None:
        """Test that test task returns expected result when called directly."""
        from app.tasks import test_task

        result = test_task("test_value")
        assert result == {"status": "success", "input": "test_value"}


class TestCeleryBeatSchedule:
    """Tests for Celery Beat schedule configuration."""

    def test_celery_beat_schedule_exists(self) -> None:
        """Test that Celery Beat schedule is configured."""
        from app.celery_app import celery_app

        assert celery_app.conf.beat_schedule is not None
        assert "sync-all-users-daily" in celery_app.conf.beat_schedule

    def test_sync_all_users_schedule_is_daily_3am_utc(self) -> None:
        """Test that sync-all-users task is scheduled at 3 AM UTC daily."""
        from app.celery_app import celery_app

        schedule = celery_app.conf.beat_schedule["sync-all-users-daily"]
        assert schedule["task"] == "sync_all_users"
        # Check it's a crontab schedule for 3 AM UTC
        assert hasattr(schedule["schedule"], "hour")
        assert schedule["schedule"].hour == {3}

    def test_sync_all_users_task_exists(self) -> None:
        """Test that sync_all_users task is registered."""
        from app.tasks import sync_all_users

        assert sync_all_users is not None
        assert hasattr(sync_all_users, "delay")


class TestSyncAllUsersTask:
    """Tests for the sync_all_users task."""

    def test_sync_all_users_iterates_configured_users(self) -> None:
        """Test that sync_all_users task calls sync for each configured user."""
        from app.celery_app import celery_app
        from app.tasks import sync_all_users, sync_user

        # Set eager mode for testing
        celery_app.conf.task_always_eager = True
        celery_app.conf.task_eager_propagates = True

        try:
            # Mock the database query and sync_user task
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

    def test_sync_user_task_exists(self) -> None:
        """Test that sync_user task is registered."""
        from app.tasks import sync_user

        assert sync_user is not None
        assert hasattr(sync_user, "delay")
