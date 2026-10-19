import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base


@pytest.fixture
def db():
    """A fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_user_job_application_relationships(db):
    user = models.User(email="a@example.com", password_hash="x")
    job = models.Job(
        title="Backend Intern", company="Acme", description="Python", user=user
    )
    application = models.Application(user=user, job=job)
    db.add_all([user, job, application])
    db.commit()

    assert application.id is not None
    assert application.status == "saved"  # default status
    assert job.applications[0].id == application.id
    assert user.jobs[0].title == "Backend Intern"


def test_email_must_be_unique(db):
    db.add(models.User(email="dup@example.com", password_hash="x"))
    db.commit()

    db.add(models.User(email="dup@example.com", password_hash="y"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_status_history_is_linked_to_application(db):
    user = models.User(email="b@example.com", password_hash="x")
    job = models.Job(title="Data Intern", company="Globex", description="SQL", user=user)
    application = models.Application(user=user, job=job)
    application.history.append(
        models.StatusHistory(from_status="saved", to_status="applied")
    )
    db.add_all([user, job, application])
    db.commit()

    assert len(application.history) == 1
    assert application.history[0].to_status == "applied"