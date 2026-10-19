"""App alerts: what Media Janitor reports to the Hub at the end of a sync.

One App alert per non-empty issue category (old, large, language, requests),
plus `sync-failed` when the sync failed or was partial. The categories come
from the same per-user computation as the dashboard summary and issue lists.
"""

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.services.content_queries import (
    get_content_issues,
    get_content_summary,
    get_unavailable_requests,
)
from app.services.hub import send_app_alerts

logger = logging.getLogger(__name__)

APP_SLUG = "mediajanitor"
APP_NAME = "Media Janitor"
TITLES_SHOWN = 3
CONTEXT_MAX = 300
ERROR_MAX = 200


@dataclass(frozen=True)
class SyncFailure:
    """The service that made a sync fail or end partial, and its error."""

    service: str
    error: str


def hub_reporting_enabled() -> bool:
    """True when the Hub URL, App alert token and reporting email are all set."""
    settings = get_settings()
    return bool(
        settings.hub_base_url and settings.hub_app_alert_token and settings.hub_alert_user_email
    )


def _hub_settings_for(user_email: str) -> Settings | None:
    if not hub_reporting_enabled():
        return None
    settings = get_settings()
    if user_email.strip().lower() != settings.hub_alert_user_email.strip().lower():
        return None
    return settings


def _titles_context(titles: list[str], total: int, size: str | None = None) -> str:
    shown = titles[:TITLES_SHOWN]
    parts = list(shown)
    if total > len(shown):
        parts.append(f"+{total - len(shown)}")
    text = ", ".join(parts)
    if size:
        text = f"{size} · {text}" if text else size
    return text[:CONTEXT_MAX]


async def build_snapshot(
    db: AsyncSession,
    user_id: int,
    frontend_url: str,
    failure: SyncFailure | None = None,
) -> dict[str, Any]:
    """Build the App alerts snapshot for a user from the cached data."""
    home = f"{frontend_url.rstrip('/')}/"
    summary = await get_content_summary(db, user_id)
    issues = await get_content_issues(db, user_id)

    alerts: list[dict[str, Any]] = []

    for key, label, category in (
        ("old", "Old content", summary.old_content),
        ("large", "Large content", summary.large_movies),
        ("language", "Language issues", summary.language_issues),
    ):
        if category.count == 0:
            continue
        titles = [item.name for item in issues.items if key in item.issues]
        alerts.append(
            {
                "key": key,
                "title": f"{label} · {category.count}",
                "context": _titles_context(
                    titles, category.count, size=category.total_size_formatted
                ),
                "url": f"{home}issues?filter={key}",
            }
        )

    if summary.unavailable_requests.count:
        requests = await get_unavailable_requests(db, user_id)
        count = summary.unavailable_requests.count
        alerts.append(
            {
                "key": "requests",
                "title": f"Unavailable requests · {count}",
                "context": _titles_context([r.title for r in requests], count),
                "url": f"{home}issues?filter=requests",
            }
        )

    if failure:
        alerts.append(
            {
                "key": "sync-failed",
                "title": "Media Janitor sync failed",
                "context": f"{failure.service}: {failure.error[:ERROR_MAX]}"[:CONTEXT_MAX],
                "url": home,
            }
        )

    return {"name": APP_NAME, "url": home, "push": True, "alerts": alerts}


async def report_sync_to_hub(
    db: AsyncSession,
    user_id: int,
    user_email: str,
    failure: SyncFailure | None = None,
) -> None:
    """Send the user's App alerts snapshot to the Hub at the end of a sync.

    Only for the account matching HUB_ALERT_USER_EMAIL, and only when the Hub
    settings are set. Never raises: the sync must not depend on the Hub.
    """
    try:
        settings = _hub_settings_for(user_email)
        if settings is None:
            return
        snapshot = await build_snapshot(db, user_id, settings.frontend_url, failure)
        await send_app_alerts(
            settings.hub_base_url, APP_SLUG, settings.hub_app_alert_token, snapshot
        )
    except Exception as e:
        logger.warning(f"Failed to report sync of user {user_id} to the Hub: {e!r}")
