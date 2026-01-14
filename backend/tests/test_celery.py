"""Tests for Celery configuration and tasks."""

import pytest


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
