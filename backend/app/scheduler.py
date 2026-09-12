import asyncio
import logging

from app.database import async_session
from app.escalator import check_escalations, auto_resolve_old_alerts
from app.notifier import process_pending_notifications

logger = logging.getLogger("ajali.scheduler")

# How often each task runs (seconds)
ESCALATION_INTERVAL = 30
NOTIFY_INTERVAL = 10
AUTO_RESOLVE_INTERVAL = 3600  # once per hour


async def run_scheduler():
    """Background loop that runs escalation checks and notification dispatches."""
    logger.info("Scheduler started")
    esc_task = asyncio.create_task(_escalation_loop())
    notify_task = asyncio.create_task(_notify_loop())
    resolve_task = asyncio.create_task(_auto_resolve_loop())
    await asyncio.gather(esc_task, notify_task, resolve_task)


async def _escalation_loop():
    while True:
        try:
            async with async_session() as db:
                count = await check_escalations(db)
                if count:
                    logger.info("Escalated %d alerts", count)
        except Exception as exc:
            logger.error("Escalation loop error: %s", exc)
        await asyncio.sleep(ESCALATION_INTERVAL)


async def _notify_loop():
    while True:
        try:
            async with async_session() as db:
                count = await process_pending_notifications(db)
                if count:
                    logger.info("Sent %d notifications", count)
        except Exception as exc:
            logger.error("Notify loop error: %s", exc)
        await asyncio.sleep(NOTIFY_INTERVAL)


async def _auto_resolve_loop():
    while True:
        try:
            async with async_session() as db:
                count = await auto_resolve_old_alerts(db)
                if count:
                    logger.info("Auto-resolved %d stale alerts", count)
        except Exception as exc:
            logger.error("Auto-resolve loop error: %s", exc)
        await asyncio.sleep(AUTO_RESOLVE_INTERVAL)