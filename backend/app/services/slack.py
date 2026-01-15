"""Slack notification service for sending messages to Slack channels."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


async def send_slack_message(webhook_url: str, message: dict[str, Any]) -> bool:
    """
    Send a message to a Slack channel via webhook.

    Args:
        webhook_url: The Slack webhook URL to send the message to.
        message: The message payload in Slack Block Kit or simple text format.
                 Example: {"text": "Hello!"} or {"blocks": [...]}

    Returns:
        True if the message was sent successfully, False otherwise.

    Note:
        This function handles errors gracefully - it logs warnings but never
        raises exceptions. This makes it safe to use in fire-and-forget scenarios.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=message)

            if response.status_code == 200:
                return True
            else:
                logger.warning(
                    f"Slack webhook returned status {response.status_code}: {response.text}"
                )
                return False

    except httpx.RequestError as e:
        logger.warning(f"Failed to send Slack message: {e}")
        return False
    except httpx.TimeoutException as e:
        logger.warning(f"Slack webhook request timed out: {e}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error sending Slack message: {e}")
        return False
