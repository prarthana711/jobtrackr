import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_owned_job(db: Session, job_id: int, user: models.User) -> models.Job:
    """Fetch a job only if it belongs to this user, otherwise raise 404."""
    job = db.scalar(
        select(models.Job).where(
            models.Job.id == job_id, models.Job.user_id == user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def escape_like(value: str) -> str:
    """Treat %, _ and \\ typed by the user as plain characters in a LIKE search."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.post("", response_model=schemas.JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: schemas.JobCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    job = models.Job(**payload.model_dump(), user_id=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=schemas.JobList)
def list_jobs(
    search: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stmt = select(models.Job).where(models.Job.user_id == current_user.id)

    if search and search.strip():
        term = f"%{escape_like(search.strip())}%"
        stmt = stmt.where(
            or_(
                models.Job.title.ilike(term, escape="\\"),
                models.Job.company.ilike(term, escape="\\"),
                models.Job.location.ilike(term, escape="\\"),
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    items = db.scalars(
        stmt.order_by(models.Job.created_at.desc(), models.Job.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return schemas.JobList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_owned_job(db, job_id, current_user)


@router.patch("/{job_id}", response_model=schemas.JobOut)
def update_job(
    job_id: int,
    payload: schemas.JobUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    job = get_owned_job(db, job_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    job = get_owned_job(db, job_id, current_user)
    db.delete(job)
    db.commit()