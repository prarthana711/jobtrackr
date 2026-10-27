import asyncio
import logging

from app.config import settings
from app.database import SessionLocal
from app.services.reminders import process_due_reminders, utc_now

logger = logging.getLogger("jobtrackr.scheduler")


def run_reminder_check() -> dict:
    """One pass: open a session, send everything that is due, close the session."""
    with SessionLocal() as db:
        return process_due_reminders(db, utc_now())


async def reminder_loop() -> None:
    """Runs forever in the background while the web app is running."""
    logger.info("Reminder checker started (every %s seconds)", settings.reminder_check_seconds)
    while True:
        try:
            # The database and the mail server are blocking, so run them in a worker
            # thread. Otherwise the whole web app would freeze during each check.
            result = await asyncio.to_thread(run_reminder_check)
            if result["sent"] or result["failed"]:
                logger.info("Reminders processed: %s", result)
        except Exception:
            logger.exception("Reminder check crashed; will try again next time")
        await asyncio.sleep(settings.reminder_check_seconds)