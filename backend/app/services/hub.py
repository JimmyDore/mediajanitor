"""Client for the Hub (hub.jimmydore.fr).

Every call is fire-and-forget, like the Slack client: a ~10-second timeout, no
retry, any 2xx is success, and every other status or error is logged and never
raised. The next sync sends the full state anyway.
"""

import logging
from collections.abc import Mapping

import httpx

logger = logging.getLogger(__name__)

HUB_TIMEOUT_SECONDS = 10.0


async def _send(method: str, url: str, token: str, payload: Mapping[str, object] | None) -> bool:
    try:
        async with httpx.AsyncClient(timeout=HUB_TIMEOUT_SECONDS) as client:
            response = await client.request(
                method,
                url,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        if 200 <= response.status_code < 300:
            return True
        logger.warning(f"Hub {method} {url} returned status {response.status_code}")
        return False
    except Exception as e:
        logger.warning(f"Hub {method} {url} failed: {e!r}")
        return False


async def send_app_alerts(
    base_url: str, app: str, token: str, snapshot: Mapping[str, object]
) -> bool:
    """Send an app's full App alerts snapshot: PUT /api/app-alerts/{app}.

    Returns True when the Hub accepted it, False otherwise. Never raises.
    """
    url = f"{base_url.rstrip('/')}/api/app-alerts/{app}"
    return await _send("PUT", url, token, snapshot)


async def send_ping(base_url: str, task: str, token: str) -> bool:
    """Ping a Hub Task as succeeded: POST /api/ping/{task}, no body.

    Returns True when the Hub accepted it, False otherwise. Never raises.
    """
    url = f"{base_url.rstrip('/')}/api/ping/{task}"
    return await _send("POST", url, token, None)
