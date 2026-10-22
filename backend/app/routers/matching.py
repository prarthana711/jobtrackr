from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.matcher import match_texts

router = APIRouter(prefix="/match", tags=["match"])


@router.post("", response_model=schemas.MatchOut)
def run_match(
    payload: schemas.MatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # Both the resume and the job must exist AND belong to this user
    resume = db.scalar(
        select(models.Resume).where(
            models.Resume.id == payload.resume_id,
            models.Resume.user_id == current_user.id,
        )
    )
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = db.scalar(
        select(models.Job).where(
            models.Job.id == payload.job_id, models.Job.user_id == current_user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Skills are re-read from the saved text, so skill-list improvements apply
    outcome = match_texts(resume.raw_text, f"{job.title}\n{job.description}")

    # One row per (resume, job) pair: update it if it exists, otherwise create it
    result = db.scalar(
        select(models.MatchResult).where(
            models.MatchResult.resume_id == resume.id,
            models.MatchResult.job_id == job.id,
        )
    )
    if result is None:
        result = models.MatchResult(
            user_id=current_user.id, resume_id=resume.id, job_id=job.id
        )
        db.add(result)

    result.score = outcome.score
    result.skill_score = outcome.skill_score
    result.text_score = outcome.text_score
    result.matched_skills = outcome.matched_skills
    result.missing_skills = outcome.missing_skills
    result.computed_at = func.now()

    try:
        db.commit()
    except IntegrityError:  # two identical requests raced to create the same row
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This match is already being computed, please retry"
        )
    db.refresh(result)
    return result


@router.get("", response_model=list[schemas.MatchOut])
def list_matches(
    job_id: int | None = Query(None),
    resume_id: int | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stmt = select(models.MatchResult).where(
        models.MatchResult.user_id == current_user.id
    )
    if job_id is not None:
        stmt = stmt.where(models.MatchResult.job_id == job_id)
    if resume_id is not None:
        stmt = stmt.where(models.MatchResult.resume_id == resume_id)

    return db.scalars(
        stmt.options(selectinload(models.MatchResult.job))
        .order_by(models.MatchResult.score.desc(), models.MatchResult.id.desc())
        .limit(limit)
    ).all()


@router.get("/{match_id}", response_model=schemas.MatchOut)
def get_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    result = db.scalar(
        select(models.MatchResult).where(
            models.MatchResult.id == match_id,
            models.MatchResult.user_id == current_user.id,
        )
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return result