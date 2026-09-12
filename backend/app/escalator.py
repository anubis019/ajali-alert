import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    Alert, AlertEvent, EscalationPolicy, Notification,
    EmergencyCategoryEnum, ResponderTypeEnum,
    SeverityEnum, StatusEnum, EventKindEnum,
    NotifyChannelEnum, NotifyStatusEnum,
)

logger = logging.getLogger("ajali.escalator")

# Map categories to escalation responder types
CATEGORY_RESPONDER_MAP = {
    EmergencyCategoryEnum.accident: ResponderTypeEnum.ambulance,
    EmergencyCategoryEnum.fire: ResponderTypeEnum.fire_brigade,
    EmergencyCategoryEnum.medical: ResponderTypeEnum.ambulance,
    EmergencyCategoryEnum.security: ResponderTypeEnum.police,
}


async def check_escalations(db: AsyncSession) -> int:
    """Find active alerts that have exceeded their escalation delay
    and auto-escalate them. Prioritizes by emergency type for
    Golden Hour compliance."""

    # Load active escalation policies
    result = await db.execute(
        select(EscalationPolicy).where(
            EscalationPolicy.is_active == True,
            EscalationPolicy.auto_escalate == True,
        )
    )
    policies: List[EscalationPolicy] = result.scalars().all()

    escalated = 0
    now = datetime.now(timezone.utc)

    for policy in policies:
        threshold = now - timedelta(minutes=policy.delay_minutes)

        # Build query — filter by severity, and optionally by category
        conditions = [
            Alert.severity == policy.severity,
            Alert.status.in_([StatusEnum.active, StatusEnum.acknowledged, StatusEnum.dispatching]),
            Alert.created_at < threshold,
        ]

        # If policy specifies a category, only escalate that emergency type
        if policy.category:
            conditions.append(Alert.category == policy.category)

        result = await db.execute(
            select(Alert).where(and_(*conditions))
        )
        stale_alerts: List[Alert] = result.scalars().all()

        for alert in stale_alerts:
            alert.status = StatusEnum.escalated
            alert.updated_at = now
            db.add(alert)

            # Determine escalation target
            responder = policy.responder_type or CATEGORY_RESPONDER_MAP.get(alert.category, ResponderTypeEnum.all)

            # Create audit event
            event = AlertEvent(
                alert_id=alert.id,
                kind=EventKindEnum.escalated,
                message=(
                    f"🚨 ESCALATED: {alert.category.value.upper()} emergency — "
                    f"no response after {policy.delay_minutes} min. "
                    f"Escalating to {responder.value} / county backup."
                ),
            )
            db.add(event)

            # Create escalation notification (SMS is primary for Kenya)
            channel = policy.notify_channel
            recipient = policy.notify_recipient or alert.team or "county-backup"
            notification = Notification(
                alert_id=alert.id,
                channel=channel,
                recipient=recipient,
                message=(
                    f"🚨 ESCALATION ALERT\n"
                    f"Type: {alert.category.value.upper()} | Severity: {alert.severity.value.upper()}\n"
                    f"Location: {alert.location or 'GPS coordinates available'}\n"
                    f"Casualties: {alert.casualty_count}\n"
                    f"No response after {policy.delay_minutes} min\n"
                    f"Action: {responder.value} dispatch required NOW\n"
                    f"Title: {alert.title}"
                ),
                status=NotifyStatusEnum.pending,
            )
            db.add(notification)

            escalated += 1
            logger.info(
                "Escalated alert id=%d category=%s severity=%s — no response after %d min",
                alert.id, alert.category.value, alert.severity.value, policy.delay_minutes,
            )

    if escalated:
        await db.commit()
    return escalated


async def auto_resolve_old_alerts(db: AsyncSession, max_age_hours: int = 72) -> int:
    """Auto-resolve low-severity alerts older than max_age_hours.
    This reduces noise — but critical/high alerts are NEVER auto-resolved
    (they must be explicitly resolved by a human)."""
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(hours=max_age_hours)

    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.severity == SeverityEnum.low,
                Alert.status == StatusEnum.active,
                Alert.created_at < threshold,
            )
        )
    )
    old_alerts: List[Alert] = result.scalars().all()
    count = 0
    for alert in old_alerts:
        alert.status = StatusEnum.resolved
        alert.resolved_at = now
        alert.updated_at = now
        alert.resolution_time_seconds = (now - alert.created_at).total_seconds()
        db.add(alert)

        event = AlertEvent(
            alert_id=alert.id,
            kind=EventKindEnum.resolved,
            message=f"Auto-resolved after {max_age_hours}h (low severity — no further action needed)",
        )
        db.add(event)
        count += 1

    if count:
        await db.commit()
    logger.info("Auto-resolved %d low-severity alerts", count)
    return count
