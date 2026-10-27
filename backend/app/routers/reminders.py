from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.routers.applications import get_owned_application
from app.services.reminders import to_utc_naive, utc_now

router = APIRouter(tags=["reminders"])

MAX_DAYS_AHEAD = 365


def pending_conditions():
    """Not sent yet, and still has attempts left."""
    return (
        models.Reminder.sent_at.is_(None),
        models.Reminder.attempts < settings.reminder_max_attempts,
    )


@router.post(
    "/applications/{application_id}/reminders",
    response_model=schemas.ReminderOut,
    status_code=status.HTTP_201_CREATED,
)
def create_reminder(
    application_id: int,
    payload: schemas.ReminderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = get_owned_application(db, application_id, current_user)

    remind_at = to_utc_naive(payload.remind_at)
    now = utc_now()
    if remind_at <= now:
        raise HTTPException(status_code=422, detail="Reminder time must be in the future")
    if remind_at > now + timedelta(days=MAX_DAYS_AHEAD):
        raise HTTPException(
            status_code=422,
            detail=f"Reminder time must be within the next {MAX_DAYS_AHEAD} days",
        )

    pending = db.scalar(
        select(func.count())
        .select_from(models.Reminder)
        .where(models.Reminder.user_id == current_user.id, *pending_conditions())
    )
    if pending >= settings.max_pending_reminders_per_user:
        raise HTTPException(
            status_code=409,
            detail=f"You already have {settings.max_pending_reminders_per_user} pending reminders",
        )

    reminder = models.Reminder(
        user_id=current_user.id,
        application_id=application.id,
        remind_at=remind_at,
        note=payload.note or None,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/reminders", response_model=list[schemas.ReminderOut])
def list_reminders(
    status_filter: Literal["pending", "sent", "failed"] | None = Query(None, alias="status"),
    application_id: int | None = Query(None),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stmt = select(models.Reminder).where(models.Reminder.user_id == current_user.id)
    if application_id is not None:
        stmt = stmt.where(models.Reminder.application_id == application_id)

    if status_filter == "pending":
        stmt = stmt.where(*pending_conditions())
    elif status_filter == "sent":
        stmt = stmt.where(models.Reminder.sent_at.is_not(None))
    elif status_filter == "failed":
        stmt = stmt.where(
            models.Reminder.sent_at.is_(None),
            models.Reminder.attempts >= settings.reminder_max_attempts,
        )

    return db.scalars(
        stmt.order_by(models.Reminder.remind_at, models.Reminder.id).limit(limit)
    ).all()


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    reminder = db.scalar(
        select(models.Reminder).where(
            models.Reminder.id == reminder_id,
            models.Reminder.user_id == current_user.id,
        )
    )
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    db.delete(reminder)
    db.commit()