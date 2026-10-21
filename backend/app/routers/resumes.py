import uuid
from pathlib import Path, PureWindowsPath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, defer

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.services.resume_parser import ResumeParseError, extract_text_from_pdf
from app.services.skills import extract_skills

router = APIRouter(prefix="/resumes", tags=["resumes"])


def get_owned_resume(db: Session, resume_id: int, user: models.User) -> models.Resume:
    """Fetch a resume only if it belongs to this user, otherwise raise 404."""
    resume = db.scalar(
        select(models.Resume).where(
            models.Resume.id == resume_id, models.Resume.user_id == user.id
        )
    )
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


def clean_filename(raw: str | None) -> str:
    """The client's filename is for DISPLAY only. It is never used as a path."""
    name = PureWindowsPath(raw or "").name  # drops any folders, / or \ style
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return (name or "resume.pdf")[:255]


@router.post("", response_model=schemas.ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    count = db.scalar(
        select(func.count())
        .select_from(models.Resume)
        .where(models.Resume.user_id == current_user.id)
    )
    if count >= settings.max_resumes_per_user:
        raise HTTPException(
            status_code=409,
            detail=f"Resume limit reached ({settings.max_resumes_per_user}). Delete one first.",
        )

    # Read at most limit + 1 bytes, so we never hold a huge file in memory
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=413, detail=f"File too large (max {settings.max_upload_mb} MB)"
        )

    # Check the real content, not the filename or the Content-Type header
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Only PDF files are accepted")

    try:
        text = extract_text_from_pdf(data)
    except ResumeParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    skills = extract_skills(text)

    # Save under a random name. Only now, after every check has passed.
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid.uuid4().hex}.pdf"
    file_path = upload_dir / stored_filename
    file_path.write_bytes(data)

    resume = models.Resume(
        user_id=current_user.id,
        original_filename=clean_filename(file.filename),
        stored_filename=stored_filename,
        size_bytes=len(data),
        raw_text=text,
        parsed_skills=skills,
    )
    db.add(resume)
    try:
        db.commit()
    except Exception:
        db.rollback()
        file_path.unlink(missing_ok=True)  # don't leave an orphan file behind
        raise
    db.refresh(resume)
    return resume


@router.get("", response_model=list[schemas.ResumeOut])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return db.scalars(
        select(models.Resume)
        .where(models.Resume.user_id == current_user.id)
        .options(defer(models.Resume.raw_text))  # don't load the big text column
        .order_by(models.Resume.uploaded_at.desc(), models.Resume.id.desc())
    ).all()


@router.get("/{resume_id}", response_model=schemas.ResumeDetail)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_owned_resume(db, resume_id, current_user)


@router.get("/{resume_id}/file")
def download_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    resume = get_owned_resume(db, resume_id, current_user)
    file_path = Path(settings.upload_dir) / resume.stored_filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="File is missing from storage")
    return FileResponse(
        file_path, media_type="application/pdf", filename=resume.original_filename
    )


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    resume = get_owned_resume(db, resume_id, current_user)
    stored_filename = resume.stored_filename
    db.delete(resume)
    db.commit()
    try:  # the row is already gone, so a file problem must not fail the request
        (Path(settings.upload_dir) / stored_filename).unlink(missing_ok=True)
    except OSError:
        pass