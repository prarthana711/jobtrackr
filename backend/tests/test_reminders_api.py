from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import get_db
from app.main import app
from app.services.reminders import process_due_reminders, utc_now


class Outbox:
    """A fake mail server. It collects messages, and can be told to fail."""

    def __init__(self, fail_times=0):
        self.messages = []
        self.fail_times = fail_times

    def __call__(self, message):
        if self.fail_times > 0:
            self.fail_times -= 1
            raise RuntimeError("SMTP server is down")
        self.messages.append(message)


def iso_from_now(**delta):
    return (datetime.now(timezone.utc) + timedelta(**delta)).isoformat()


def make_application(client, headers, title="Backend Intern"):
    job = client.post(
        "/jobs",
        json={"title": title, "company": "Acme", "description": "Python and SQL required"},
        headers=headers,
    )
    assert job.status_code == 201
    application = client.post(
        "/applications", json={"job_id": job.json()["id"]}, headers=headers
    )
    assert application.status_code == 201
    return application.json()


def add_reminder(client, headers, application_id, remind_at=None, note=None):
    return client.post(
        f"/applications/{application_id}/reminders",
        json={"remind_at": remind_at or iso_from_now(days=3), "note": note},
        headers=headers,
    )


def run_reminder_job(now, send):
    """Run the reminder sender against the same test database the API is using."""
    generator = app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        return process_due_reminders(db, now, send=send)
    finally:
        generator.close()


def test_reminder_endpoints_require_authentication(client):
    body = {"remind_at": iso_from_now(days=1)}
    assert client.post("/applications/1/reminders", json=body).status_code == 401
    assert client.get("/reminders").status_code == 401
    assert client.delete("/reminders/1").status_code == 401


def test_create_reminder(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)

    response = add_reminder(client, headers, application["id"], note="Ask about the timeline")

    assert response.status_code == 201
    body = response.json()
    assert body["application_id"] == application["id"]
    assert body["note"] == "Ask about the timeline"
    assert body["status"] == "pending"
    assert body["attempts"] == 0
    assert body["sent_at"] is None
    assert "user_id" not in body
    assert "last_error" not in body


def test_timezone_offsets_are_converted_to_utc(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)
    india = timezone(timedelta(hours=5, minutes=30))
    # 30 days from now, written as an Indian local time such as 2026-12-11T14:30:00+05:30
    local_time = (
        (datetime.now(timezone.utc) + timedelta(days=30)).astimezone(india).replace(microsecond=0)
    )

    response = add_reminder(client, headers, application["id"], remind_at=local_time.isoformat())

    assert response.status_code == 201, response.json()
    expected_utc = local_time.astimezone(timezone.utc).replace(tzinfo=None)
    assert response.json()["remind_at"] == expected_utc.isoformat()


def test_reminder_time_needs_a_timezone(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)
    # A perfectly valid future time, except that it has no timezone
    naive_time = (datetime.now(timezone.utc) + timedelta(days=30)).replace(tzinfo=None)

    response = add_reminder(client, headers, application["id"], remind_at=naive_time.isoformat())

    assert response.status_code == 422
    assert "timezone" in str(response.json()["detail"])


def test_reminder_must_be_in_the_future(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)

    response = add_reminder(client, headers, application["id"], remind_at=iso_from_now(hours=-1))
    assert response.status_code == 422
    assert "future" in response.json()["detail"]


def test_reminder_cannot_be_more_than_a_year_away(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)

    response = add_reminder(client, headers, application["id"], remind_at=iso_from_now(days=400))
    assert response.status_code == 422


def test_cannot_add_reminder_to_unknown_or_other_users_application(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = make_application(client, alice)

    assert add_reminder(client, alice, 9999).status_code == 404
    assert add_reminder(client, bob, application["id"]).status_code == 404


def test_pending_reminder_limit_per_user(client, make_headers, monkeypatch):
    monkeypatch.setattr(settings, "max_pending_reminders_per_user", 2)
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    alice_application = make_application(client, alice)
    bob_application = make_application(client, bob)

    assert add_reminder(client, alice, alice_application["id"]).status_code == 201
    assert add_reminder(client, alice, alice_application["id"]).status_code == 201
    assert add_reminder(client, alice, alice_application["id"]).status_code == 409
    assert add_reminder(client, bob, bob_application["id"]).status_code == 201  # per user


def test_list_reminders_with_filters(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    first = make_application(client, alice, "Job A")
    second = make_application(client, alice, "Job B")
    later = add_reminder(client, alice, first["id"], remind_at=iso_from_now(days=5)).json()
    sooner = add_reminder(client, alice, second["id"], remind_at=iso_from_now(days=2)).json()

    everything = client.get("/reminders", headers=alice).json()
    assert [r["id"] for r in everything] == [sooner["id"], later["id"]]  # soonest first

    only_first = client.get("/reminders", params={"application_id": first["id"]}, headers=alice)
    assert [r["id"] for r in only_first.json()] == [later["id"]]

    pending = client.get("/reminders", params={"status": "pending"}, headers=alice).json()
    assert len(pending) == 2
    assert client.get("/reminders", params={"status": "sent"}, headers=alice).json() == []
    assert client.get("/reminders", params={"status": "banana"}, headers=alice).status_code == 422
    assert client.get("/reminders", headers=bob).json() == []


def test_sent_reminders_are_reported_as_sent(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)
    add_reminder(client, headers, application["id"], remind_at=iso_from_now(hours=1))
    outbox = Outbox()

    result = run_reminder_job(utc_now() + timedelta(hours=2), outbox)

    assert result == {"sent": 1, "failed": 0}
    assert len(outbox.messages) == 1
    sent = client.get("/reminders", params={"status": "sent"}, headers=headers).json()
    assert len(sent) == 1
    assert sent[0]["status"] == "sent"
    assert sent[0]["sent_at"] is not None
    assert client.get("/reminders", params={"status": "pending"}, headers=headers).json() == []


def test_reminders_that_keep_failing_are_reported_as_failed(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)
    add_reminder(client, headers, application["id"], remind_at=iso_from_now(hours=1))
    outbox = Outbox(fail_times=99)

    for _ in range(settings.reminder_max_attempts):
        run_reminder_job(utc_now() + timedelta(hours=2), outbox)

    failed = client.get("/reminders", params={"status": "failed"}, headers=headers).json()
    assert len(failed) == 1
    assert failed[0]["status"] == "failed"
    assert failed[0]["attempts"] == settings.reminder_max_attempts
    assert "last_error" not in failed[0]
    assert client.get("/reminders", params={"status": "pending"}, headers=headers).json() == []


def test_cancel_reminder(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)
    created = add_reminder(client, headers, application["id"]).json()

    assert client.delete(f"/reminders/{created['id']}", headers=headers).status_code == 204
    assert client.get("/reminders", headers=headers).json() == []
    assert client.delete(f"/reminders/{created['id']}", headers=headers).status_code == 404


def test_cannot_cancel_other_users_reminder(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = make_application(client, alice)
    created = add_reminder(client, alice, application["id"]).json()

    assert client.delete(f"/reminders/{created['id']}", headers=bob).status_code == 404
    assert len(client.get("/reminders", headers=alice).json()) == 1


def test_deleting_an_application_deletes_its_reminders(client, make_headers):
    headers = make_headers()
    application = make_application(client, headers)
    add_reminder(client, headers, application["id"])

    assert client.delete(f"/applications/{application['id']}", headers=headers).status_code == 204
    assert client.get("/reminders", headers=headers).json() == []