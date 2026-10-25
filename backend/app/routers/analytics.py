from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.analytics import (
    build_funnel,
    today_utc,
    weak_spots,
    week_start,
    weekly_counts,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/funnel", response_model=schemas.FunnelOut)
def funnel(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # How many applications EVER entered each status? (from the history table)
    reached_rows = db.execute(
        select(
            models.StatusHistory.to_status,
            func.count(models.StatusHistory.application_id.distinct()),
        )
        .select_from(models.StatusHistory)
        .join(
            models.Application,
            models.Application.id == models.StatusHistory.application_id,
        )
        .where(models.Application.user_id == current_user.id)
        .group_by(models.StatusHistory.to_status)
    ).all()

    # What status is each application in RIGHT NOW?
    current_rows = db.execute(
        select(models.Application.status, func.count())
        .where(models.Application.user_id == current_user.id)
        .group_by(models.Application.status)
    ).all()

    reached = {status: count for status, count in reached_rows}
    current = {status: count for status, count in current_rows}
    return build_funnel(reached, current)


@router.get("/weekly", response_model=list[schemas.WeekCount])
def weekly(
    weeks: int = Query(12, ge=1, le=52),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    today = today_utc()
    window_start = week_start(today) - timedelta(weeks=weeks - 1)

    # Only the dates we need. Rows with no applied_on are skipped automatically,
    # because NULL is never >= a date.
    applied_dates = db.scalars(
        select(models.Application.applied_on).where(
            models.Application.user_id == current_user.id,
            models.Application.applied_on >= window_start,
        )
    ).all()
    return weekly_counts(applied_dates, weeks, today)


@router.get("/weak-spots", response_model=schemas.WeakSpotsOut)
def get_weak_spots(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Only the three small columns we need, never the whole match rows
    rows = db.execute(
        select(
            models.MatchResult.job_id,
            models.MatchResult.score,
            models.MatchResult.missing_skills,
        )
        .where(models.MatchResult.user_id == current_user.id)
        .order_by(models.MatchResult.id)
    ).all()
    return weak_spots(rows, limit)