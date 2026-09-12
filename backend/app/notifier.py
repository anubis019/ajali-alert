import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Notification, NotifyChannelEnum, NotifyStatusEnum

logger = logging.getLogger("ajali.notifier")


async def send_email(recipient: str, subject: str, body: str) -> bool:
    """Send email notification. In production, connect to SMTP.
    For demo, we log the email and mark as sent."""
    logger.info("EMAIL to=%s subject=%s", recipient, subject)
    return True


async def send_sms(recipient: str, message: str) -> bool:
    """Send SMS notification. In production, use Africa's Talking or Twilio.
    For demo, we log the SMS and mark as sent."""
    logger.info("SMS to=%s body=%s", recipient, message[:120])
    # Production integration:
    # if settings.SMS_PROVIDER == "africas_talking":
    #     async with httpx.AsyncClient() as client:
    #         resp = await client.post(
    #             "https://api.africastalking.com/v1/messaging",
    #             headers={"apiKey": settings.AFRICAS_TALKING_API_KEY},
    #             json={
    #                 "username": settings.AFRICAS_TALKING_USERNAME,
    #                 "to": [recipient],
    #                 "message": message,
    #                 "from": settings.AFRICAS_TALKING_SHORTCODE,
    #             },
    #         )
    #         return resp.status_code == 201
    return True  # simulated


async def send_ussd_notification(session_id: str, phone: str, message: str) -> bool:
    """Send a USSD push notification to a feature phone user.
    Typically used for status updates back to the original caller."""
    logger.info("USSD push session=%s phone=%s msg=%s", session_id, phone, message[:80])
    return True  # simulated


async def send_webhook(url: str, payload: dict) -> bool:
    """POST alert payload to an external webhook."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            return resp.status_code in (200, 201, 204)
    except Exception as exc:
        logger.error("Webhook failed: %s", exc)
        return False


async def send_slack(webhook_url: str, message: str) -> bool:
    """Send Slack notification via webhook."""
    payload = {"text": message}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            return resp.status_code in (200, 201, 204)
    except Exception as exc:
        logger.error("Slack webhook failed: %s", exc)
        return False


async def dispatch_notification(notification: Notification, db: AsyncSession) -> None:
    """Attempt to send a single notification and update its status."""
    success = False
    try:
        if notification.channel == NotifyChannelEnum.email:
            success = await send_email(
                notification.recipient,
                subject="[Ajali Alert] Emergency Response Required",
                body=notification.message,
            )
        elif notification.channel == NotifyChannelEnum.sms:
            success = await send_sms(notification.recipient, notification.message)
        elif notification.channel == NotifyChannelEnum.ussd:
            success = await send_ussd_notification(
                session_id="session-override",  # would come from alert metadata
                phone=notification.recipient,
                message=notification.message,
            )
        elif notification.channel == NotifyChannelEnum.webhook:
            url = notification.recipient  # recipient can be a URL for webhooks
            success = await send_webhook(url, {"alert_id": notification.alert_id, "message": notification.message})
        elif notification.channel == NotifyChannelEnum.slack:
            success = await send_slack(notification.recipient, notification.message)
        elif notification.channel == NotifyChannelEnum.pagerduty:
            logger.info("PagerDuty alert for=%s body=%s", notification.recipient, notification.message[:80])
            success = True  # simulated
    except Exception as exc:
        logger.error("Notification dispatch error: %s", exc)
        success = False

    notification.status = NotifyStatusEnum.sent if success else NotifyStatusEnum.failed
    notification.sent_at = datetime.now(timezone.utc)
    if not success:
        notification.error = "Delivery failed"
    db.add(notification)


async def process_pending_notifications(db: AsyncSession) -> int:
    """Background task: send all pending notifications."""
    result = await db.execute(
        select(Notification).where(Notification.status == NotifyStatusEnum.pending).limit(100)
    )
    pending: List[Notification] = result.scalars().all()
    count = 0
    for n in pending:
        await dispatch_notification(n, db)
        count += 1
    if pending:
        await db.commit()
    return count
