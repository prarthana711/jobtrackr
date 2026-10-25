from datetime import timedelta

import pytest

from app.services.analytics import today_utc, week_start

RESUME_LINES = [
    "Asha Rao - Information Science Engineering",
    "Skills: Python, SQL, Docker, FastAPI and PostgreSQL",
    "Built a REST API with Node.js and deployed it on AWS",
]
WEAK_LINES = [
    "Asha Rao - Information Science Engineering",
    "Hobbies: cooking, painting and gardening every weekend",
]
STAGE_ORDER = ["saved", "applied", "online_assessment", "interview", "offer"]


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


def move(client, headers, application_id, *statuses):
    for new_status in statuses:
        response = client.patch(
            f"/applications/{application_id}/status",
            json={"status": new_status},
            headers=headers,
        )
        assert response.status_code == 200


def set_applied_on(client, headers, application_id, day):
    response = client.patch(
        f"/applications/{application_id}",
        json={"applied_on": day.isoformat()},
        headers=headers,
    )
    assert response.status_code == 200


def add_resume(client, headers, make_pdf, lines=RESUME_LINES):
    response = client.post(
        "/resumes",
        files={"file": ("cv.pdf", make_pdf(lines), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def add_job(client, headers, title, description):
    response = client.post(
        "/jobs",
        json={"title": title, "company": "Acme", "description": description},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def run_match(client, headers, resume_id, job_id):
    response = client.post(
        "/match", json={"resume_id": resume_id, "job_id": job_id}, headers=headers
    )
    assert response.status_code == 200
    return response.json()


def match_three_jobs(client, headers, make_pdf):
    """One resume matched against three jobs that all ask for Kubernetes."""
    resume = add_resume(client, headers, make_pdf)
    jobs = [
        ("Backend Engineer", "Python, SQL, Docker, Kubernetes and Redis"),
        ("Cloud Engineer", "Python, Kubernetes and AWS"),
        ("Cache Engineer", "Docker, Redis and Kubernetes"),
    ]
    for title, description in jobs:
        job = add_job(client, headers, title, description)
        run_match(client, headers, resume["id"], job["id"])
    return resume


def test_analytics_require_authentication(client):
    assert client.get("/analytics/funnel").status_code == 401
    assert client.get("/analytics/weekly").status_code == 401
    assert client.get("/analytics/weak-spots").status_code == 401


def test_funnel_for_a_new_user_is_empty(client, make_headers):
    headers = make_headers()
    body = client.get("/analytics/funnel", headers=headers).json()

    assert body["total"] == 0
    assert [s["stage"] for s in body["stages"]] == STAGE_ORDER
    assert [s["count"] for s in body["stages"]] == [0, 0, 0, 0, 0]
    assert body["rejected"] == 0
    assert body["response_rate"] is None
    assert body["current"]["saved"] == 0


def test_funnel_counts_every_stage_an_application_passed_through(client, make_headers):
    headers = make_headers()
    make_application(client, headers, "Job A")  # stays saved
    b = make_application(client, headers, "Job B")
    c = make_application(client, headers, "Job C")
    d = make_application(client, headers, "Job D")
    move(client, headers, b["id"], "applied")
    move(client, headers, c["id"], "applied", "interview", "offer")
    move(client, headers, d["id"], "applied", "online_assessment", "rejected")

    body = client.get("/analytics/funnel", headers=headers).json()
    stages = {s["stage"]: s for s in body["stages"]}

    assert body["total"] == 4
    assert [stages[name]["count"] for name in STAGE_ORDER] == [4, 3, 1, 1, 1]
    assert stages["applied"]["percent_of_total"] == 75.0
    assert stages["offer"]["percent_of_total"] == 25.0
    assert body["rejected"] == 1  # Job D was rejected after the online assessment
    assert body["response_rate"] == pytest.approx(66.7, abs=0.1)  # 2 of 3 sent got a reply
    assert body["current"] == {
        "saved": 1,
        "applied": 1,
        "online_assessment": 0,
        "interview": 0,
        "offer": 1,
        "rejected": 1,
    }


def test_funnel_only_counts_my_applications(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = make_application(client, alice)
    move(client, alice, application["id"], "applied")
    make_application(client, alice, "Second job")

    alice_funnel = client.get("/analytics/funnel", headers=alice).json()
    bob_funnel = client.get("/analytics/funnel", headers=bob).json()

    assert alice_funnel["total"] == 2
    assert alice_funnel["response_rate"] == 0.0
    assert bob_funnel["total"] == 0
    assert bob_funnel["response_rate"] is None


def test_weekly_counts_applications_per_week_with_gaps(client, make_headers):
    headers = make_headers()
    today = today_utc()
    recent = make_application(client, headers, "Recent")
    older = make_application(client, headers, "Older")
    ancient = make_application(client, headers, "Ancient")
    for application in (recent, older, ancient):
        move(client, headers, application["id"], "applied")
    set_applied_on(client, headers, recent["id"], today)
    set_applied_on(client, headers, older["id"], today - timedelta(days=14))
    set_applied_on(client, headers, ancient["id"], today - timedelta(days=400))

    response = client.get("/analytics/weekly", params={"weeks": 4}, headers=headers)
    assert response.status_code == 200
    weeks = response.json()

    assert len(weeks) == 4
    assert weeks[-1]["week_start"] == week_start(today).isoformat()
    # two weeks ago: 1, last week: 0, this week: 1, and the 400-day-old one is outside
    assert [w["applications"] for w in weeks] == [0, 1, 0, 1]


def test_weekly_ignores_applications_that_were_never_sent(client, make_headers):
    headers = make_headers()
    make_application(client, headers)  # still "saved", so applied_on is empty

    weeks = client.get("/analytics/weekly", params={"weeks": 4}, headers=headers).json()
    assert [w["applications"] for w in weeks] == [0, 0, 0, 0]


def test_weekly_only_counts_my_applications(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = make_application(client, alice)
    move(client, alice, application["id"], "applied")

    alice_weeks = client.get("/analytics/weekly", params={"weeks": 4}, headers=alice).json()
    bob_weeks = client.get("/analytics/weekly", params={"weeks": 4}, headers=bob).json()

    assert sum(w["applications"] for w in alice_weeks) == 1
    assert sum(w["applications"] for w in bob_weeks) == 0


def test_weekly_defaults_and_validation(client, make_headers):
    headers = make_headers()
    assert len(client.get("/analytics/weekly", headers=headers).json()) == 12
    zero = client.get("/analytics/weekly", params={"weeks": 0}, headers=headers)
    too_many = client.get("/analytics/weekly", params={"weeks": 53}, headers=headers)
    assert zero.status_code == 422
    assert too_many.status_code == 422


def test_weak_spots_rank_the_most_often_missing_skills(client, make_headers, make_pdf):
    headers = make_headers()
    match_three_jobs(client, headers, make_pdf)

    body = client.get("/analytics/weak-spots", headers=headers).json()
    assert body["jobs_analysed"] == 3
    assert [s["skill"] for s in body["skills"]] == ["kubernetes", "redis"]
    assert [s["missing_in_jobs"] for s in body["skills"]] == [3, 2]
    assert body["skills"][0]["percent_of_jobs"] == 100.0
    assert body["skills"][1]["percent_of_jobs"] == pytest.approx(66.7, abs=0.1)


def test_weak_spots_use_the_best_resume_for_each_job(client, make_headers, make_pdf):
    headers = make_headers()
    strong = add_resume(client, headers, make_pdf, RESUME_LINES)
    weak = add_resume(client, headers, make_pdf, WEAK_LINES)
    job = add_job(
        client, headers, "Backend Engineer", "Python, SQL, Docker, Kubernetes and Redis"
    )
    run_match(client, headers, weak["id"], job["id"])  # the weak resume is matched first
    run_match(client, headers, strong["id"], job["id"])

    body = client.get("/analytics/weak-spots", headers=headers).json()
    assert body["jobs_analysed"] == 1
    # If the weak resume were counted too, python, sql and docker would appear here
    assert [s["skill"] for s in body["skills"]] == ["kubernetes", "redis"]


def test_weak_spots_only_use_my_matches(client, make_headers, make_pdf):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    match_three_jobs(client, alice, make_pdf)

    bob_body = client.get("/analytics/weak-spots", headers=bob).json()
    assert bob_body == {"jobs_analysed": 0, "skills": []}


def test_weak_spots_limit_and_validation(client, make_headers, make_pdf):
    headers = make_headers()
    match_three_jobs(client, headers, make_pdf)

    limited = client.get("/analytics/weak-spots", params={"limit": 1}, headers=headers).json()
    assert [s["skill"] for s in limited["skills"]] == ["kubernetes"]
    assert limited["jobs_analysed"] == 3

    zero = client.get("/analytics/weak-spots", params={"limit": 0}, headers=headers)
    too_many = client.get("/analytics/weak-spots", params={"limit": 51}, headers=headers)
    assert zero.status_code == 422
    assert too_many.status_code == 422