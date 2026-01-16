"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Jellyfin Configuration
    jellyfin_api_key: str = ""
    jellyfin_server_url: str = "https://localhost/jellyfin"

    # Jellyseerr Configuration
    jellyseer_api_key: str = ""
    jellyseer_base_url: str = "https://localhost/jellyseerr"

    # Database Configuration
    database_url: str = "sqlite:///./plex_dashboard.db"

    # Celery / Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = ""  # Falls back to redis_url if not set
    celery_result_backend: str = ""  # Falls back to redis_url if not set

    # Authentication
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 15  # Short-lived (15 minutes)
    refresh_token_expire_days: int = 30  # Long-lived (30 days)

    # Content Analysis Settings
    old_content_months_cutoff: int = 4
    min_age_months: int = 3
    large_movie_size_threshold_gb: int = 13
    recent_items_days_back: int = 1500

    # Feature Flags
    filter_future_releases: bool = True
    filter_recent_releases: bool = True
    recent_release_months_cutoff: int = 3

    # Slack Notifications (optional)
    slack_webhook_new_users: str = ""
    slack_webhook_sync_failures: str = ""

    # SMTP Email Configuration (for password reset)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""
    frontend_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
