import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.services.workflow import can_transition

router = APIRouter(prefix="/applications", tags=["applications"])


def get_owned_application(
    db: Session, application_id: int, user: models.User
) -> models.Application:
    """Fetch an application only if it belongs to this user, otherwise raise 404."""
    application = db.scalar(
        select(models.Application).where(
            models.Application.id == application_id,
            models.Application.user_id == user.id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def today_utc():
    return datetime.now(timezone.utc).date()


@router.post(
    "", response_model=schemas.ApplicationOut, status_code=status.HTTP_201_CREATED
)
def create_application(
    payload: schemas.ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    # The job must exist AND belong to this user
    job = db.scalar(
        select(models.Job).where(
            models.Job.id == payload.job_id, models.Job.user_id == current_user.id
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    already_exists = db.scalar(
        select(models.Application.id).where(
            models.Application.user_id == current_user.id,
            models.Application.job_id == job.id,
        )
    )
    if already_exists is not None:
        raise HTTPException(
            status_code=409, detail="You already have an application for this job"
        )

    application = models.Application(
        user_id=current_user.id,
        job_id=job.id,
        status=models.ApplicationStatus.SAVED.value,
        notes=payload.notes,
    )
    # The first history row: it had no previous status
    application.history.append(
        models.StatusHistory(
            from_status=None, to_status=models.ApplicationStatus.SAVED.value
        )
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError:  # the database constraint caught a simultaneous duplicate
        db.rollback()
        raise HTTPException(
            status_code=409, detail="You already have an application for this job"
        )
    db.refresh(application)
    return application


@router.get("", response_model=schemas.ApplicationList)
def list_applications(
    status_filter: models.ApplicationStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stmt = select(models.Application).where(
        models.Application.user_id == current_user.id
    )
    if status_filter is not None:
        stmt = stmt.where(models.Application.status == status_filter.value)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))

    items = db.scalars(
        stmt.options(selectinload(models.Application.job))
        .order_by(models.Application.created_at.desc(), models.Application.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return schemas.ApplicationList(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/{application_id}", response_model=schemas.ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_owned_application(db, application_id, current_user)


@router.patch("/{application_id}", response_model=schemas.ApplicationOut)
def update_application(
    application_id: int,
    payload: schemas.ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = get_owned_application(db, application_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}/status", response_model=schemas.ApplicationOut)
def change_status(
    application_id: int,
    payload: schemas.StatusChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = get_owned_application(db, application_id, current_user)
    new_status = payload.status

    if not can_transition(application.status, new_status):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot move from '{application.status}' to '{new_status.value}'",
        )

    old_status = application.status
    application.status = new_status.value
    if (
        new_status == models.ApplicationStatus.APPLIED
        and application.applied_on is None
    ):
        application.applied_on = today_utc()

    db.add(
        models.StatusHistory(
            application_id=application.id,
            from_status=old_status,
            to_status=new_status.value,
        )
    )
    db.commit()  # the status change and its history row are saved together
    db.refresh(application)
    return application


@router.get(
    "/{application_id}/history", response_model=list[schemas.StatusHistoryOut]
)
def get_history(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = get_owned_application(db, application_id, current_user)
    return db.scalars(
        select(models.StatusHistory)
        .where(models.StatusHistory.application_id == application.id)
        .order_by(models.StatusHistory.id)
    ).all()


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    application = get_owned_application(db, application_id, current_user)
    db.delete(application)
    db.commit()