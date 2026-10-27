import logging
from collections.abc import Callable
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.services.email import build_reminder_email, send_email

logger = logging.getLogger("jobtrackr.reminders")


def utc_now() -> datetime:
    """The current time as a naive UTC datetime, which is how times are stored."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc_naive(value: datetime) -> datetime:
    """Convert a timezone-aware datetime to naive UTC."""
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def process_due_reminders(
    db: Session,
    now: datetime,
    send: Callable[[EmailMessage], None] = send_email,
    max_attempts: int | None = None,
    batch_size: int = 100,
) -> dict:
    """Send every reminder that is due. Returns {"sent": n, "failed": n}.

    `now` and `send` are parameters, not things the function reaches for, so tests can
    give it a fixed time and a fake sender.
    """
    max_attempts = max_attempts or settings.reminder_max_attempts

    due = db.scalars(
        select(models.Reminder)
        .where(
            models.Reminder.sent_at.is_(None),
            models.Reminder.attempts < max_attempts,
            models.Reminder.remind_at <= now,
        )
        .order_by(models.Reminder.remind_at, models.Reminder.id)
        .limit(batch_size)
    ).all()

    sent = failed = 0
    for reminder in due:
        application = reminder.application
        message = build_reminder_email(
            to=application.user.email,
            job_title=application.job.title,
            company=application.job.company,
            status=application.status,
            note=reminder.note,
        )

        reminder.attempts += 1
        try:
            send(message)
        except Exception as exc:  # a mail server can fail in many different ways
            reminder.last_error = str(exc)[:500]
            failed += 1
            logger.warning("Reminder %s failed (attempt %s): %s", reminder.id, reminder.attempts, exc)
        else:
            reminder.sent_at = now
            reminder.last_error = None
            sent += 1

        # Save after EACH reminder, so one crash can't undo the ones already sent
        db.commit()

    return {"sent": sent, "failed": failed}