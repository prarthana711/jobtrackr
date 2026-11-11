import logging
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models
from app.database import Base
from app.services.email import build_reminder_email, send_email
from app.services.reminders import process_due_reminders, to_utc_naive

NOW = datetime(2040, 1, 15, 9, 0, 0)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class Outbox:
    """A fake mail server. It collects messages, and can be told to fail a few times."""

    def __init__(self, fail_times=0):
        self.messages = []
        self.fail_times = fail_times

    def __call__(self, message):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("SMTP server is down")
        self.messages.append(message)


def make_application(db, email="asha@example.com", title="Backend Intern", company="Acme"):
    user = models.User(email=email, password_hash="x")
    job = models.Job(user=user, title=title, company=company, description="Python")
    application = models.Application(user=user, job=job, status="applied")
    db.add_all([user, job, application])
    db.flush()  # gives everything an id
    return application


def make_reminder(db, application, remind_at, note=None):
    reminder = models.Reminder(
        user_id=application.user_id, application=application, remind_at=remind_at, note=note
    )
    db.add(reminder)
    db.commit()
    return reminder


def test_due_reminder_is_sent_and_marked_as_sent(db):
    reminder = make_reminder(
        db, make_application(db), NOW - timedelta(hours=1), note="Ask about the timeline"
    )
    outbox = Outbox()

    result = process_due_reminders(db, NOW, send=outbox)

    assert result == {"sent": 1, "failed": 0}
    assert len(outbox.messages) == 1
    message = outbox.messages[0]
    assert message["To"] == "asha@example.com"
    assert "Backend Intern" in message["Subject"]
    assert "Ask about the timeline" in message.get_content()
    assert reminder.sent_at == NOW
    assert reminder.attempts == 1


def test_reminder_due_exactly_now_is_sent(db):
    make_reminder(db, make_application(db), NOW)
    assert process_due_reminders(db, NOW, send=Outbox()) == {"sent": 1, "failed": 0}


def test_future_reminder_is_left_alone(db):
    reminder = make_reminder(db, make_application(db), NOW + timedelta(hours=1))
    outbox = Outbox()

    result = process_due_reminders(db, NOW, send=outbox)

    assert result == {"sent": 0, "failed": 0}
    assert outbox.messages == []
    assert reminder.sent_at is None
    assert reminder.attempts == 0


def test_reminder_is_only_sent_once(db):
    make_reminder(db, make_application(db), NOW - timedelta(hours=1))
    outbox = Outbox()

    process_due_reminders(db, NOW, send=outbox)
    second = process_due_reminders(db, NOW + timedelta(hours=1), send=outbox)

    assert second == {"sent": 0, "failed": 0}
    assert len(outbox.messages) == 1


def test_failed_send_is_retried_and_then_given_up(db):
    reminder = make_reminder(db, make_application(db), NOW - timedelta(hours=1))
    outbox = Outbox(fail_times=10)

    results = [process_due_reminders(db, NOW, send=outbox, max_attempts=3) for _ in range(4)]

    assert results == [{"sent": 0, "failed": 1}] * 3 + [{"sent": 0, "failed": 0}]
    assert reminder.attempts == 3
    assert reminder.sent_at is None
    assert "SMTP server is down" in reminder.last_error


def test_reminder_recovers_after_a_failure(db):
    reminder = make_reminder(db, make_application(db), NOW - timedelta(hours=1))
    outbox = Outbox(fail_times=1)

    assert process_due_reminders(db, NOW, send=outbox)["failed"] == 1
    assert process_due_reminders(db, NOW, send=outbox)["sent"] == 1

    assert reminder.attempts == 2
    assert reminder.last_error is None
    assert reminder.sent_at == NOW


def test_one_failure_does_not_block_the_others(db):
    application = make_application(db)
    first = make_reminder(db, application, NOW - timedelta(hours=2))
    second = make_reminder(db, application, NOW - timedelta(hours=1))
    outbox = Outbox(fail_times=1)  # the first send fails, the second works

    result = process_due_reminders(db, NOW, send=outbox)

    assert result == {"sent": 1, "failed": 1}
    assert first.sent_at is None
    assert second.sent_at == NOW


def test_batch_size_limits_one_run(db):
    application = make_application(db)
    for hours in (3, 2, 1):
        make_reminder(db, application, NOW - timedelta(hours=hours))
    outbox = Outbox()

    assert process_due_reminders(db, NOW, send=outbox, batch_size=2)["sent"] == 2
    assert process_due_reminders(db, NOW, send=outbox, batch_size=2)["sent"] == 1
    assert len(outbox.messages) == 3


def test_email_has_the_right_content():
    message = build_reminder_email(
        to="asha@example.com",
        job_title="Backend Intern",
        company="Acme",
        status="online_assessment",
        note="Ask about the timeline",
    )
    assert message["To"] == "asha@example.com"
    assert message["Subject"] == "Follow-up reminder: Backend Intern at Acme"
    body = message.get_content()
    assert "online assessment" in body
    assert "Ask about the timeline" in body


def test_email_without_a_note_has_no_note_line():
    message = build_reminder_email(
        to="asha@example.com", job_title="Backend Intern", company="Acme", status="applied", note=None
    )
    assert "Your note" not in message.get_content()


def test_job_title_cannot_inject_email_headers():
    message = build_reminder_email(
        to="asha@example.com",
        job_title="Intern\nBcc: evil@example.com",
        company="Acme",
        status="applied",
        note=None,
    )
    assert "\n" not in message["Subject"]
    assert message["Bcc"] is None


def test_console_mode_prints_instead_of_sending(caplog):
    caplog.set_level(logging.INFO, logger="jobtrackr.email")
    message = build_reminder_email(
        to="asha@example.com", job_title="Backend Intern", company="Acme", status="applied", note=None
    )

    send_email(message)  # smtp_host is empty during tests, so nothing is sent

    assert "SMTP is not configured" in caplog.text


def test_to_utc_naive_converts_offsets():
    india = timezone(timedelta(hours=5, minutes=30))
    assert to_utc_naive(datetime(2040, 6, 1, 9, 0, tzinfo=india)) == datetime(2040, 6, 1, 3, 30)