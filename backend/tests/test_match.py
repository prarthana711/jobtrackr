import pytest

RESUME_LINES = [
    "Asha Rao - Information Science Engineering",
    "Skills: Python, SQL, Docker, FastAPI and PostgreSQL",
    "Built a REST API with Node.js and deployed it on AWS",
]
WEAK_LINES = [
    "Asha Rao - Information Science Engineering",
    "Hobbies: cooking, painting and gardening every weekend",
]
JOB = {
    "title": "Backend Engineer",
    "company": "Acme",
    "description": (
        "Requirements: Python, SQL, Docker, Kubernetes and Redis. "
        "Experience with REST APIs is a plus."
    ),
}


def add_resume(client, headers, make_pdf, lines=RESUME_LINES, filename="cv.pdf"):
    response = client.post(
        "/resumes",
        files={"file": (filename, make_pdf(lines), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def add_job(client, headers, **overrides):
    response = client.post("/jobs", json={**JOB, **overrides}, headers=headers)
    assert response.status_code == 201
    return response.json()


def run_match(client, headers, resume_id, job_id):
    return client.post(
        "/match", json={"resume_id": resume_id, "job_id": job_id}, headers=headers
    )


def test_match_endpoints_require_authentication(client):
    assert client.post("/match", json={"resume_id": 1, "job_id": 1}).status_code == 401
    assert client.get("/match").status_code == 401
    assert client.get("/match/1").status_code == 401


def test_match_success(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)

    response = run_match(client, headers, resume["id"], job["id"])
    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume["id"]
    assert body["job_id"] == job["id"]
    assert body["matched_skills"] == ["docker", "python", "rest api", "sql"]
    assert body["missing_skills"] == ["kubernetes", "redis"]
    assert body["skill_score"] == pytest.approx(66.7, abs=0.1)
    assert 0 < body["text_score"] <= 100
    expected = 0.7 * body["skill_score"] + 0.3 * body["text_score"]
    assert body["score"] == pytest.approx(expected, abs=0.2)
    assert body["job"]["title"] == "Backend Engineer"
    assert "user_id" not in body


def test_match_result_is_saved_and_can_be_read(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)
    result = run_match(client, headers, resume["id"], job["id"]).json()

    listed = client.get("/match", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == result["id"]
    assert listed[0]["job"]["company"] == "Acme"

    single = client.get(f"/match/{result['id']}", headers=headers)
    assert single.status_code == 200
    assert single.json()["missing_skills"] == ["kubernetes", "redis"]
    assert client.get("/match/9999", headers=headers).status_code == 404


def test_matching_again_updates_the_same_result(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)

    first = run_match(client, headers, resume["id"], job["id"]).json()
    second = run_match(client, headers, resume["id"], job["id"]).json()

    assert first["id"] == second["id"]
    assert first["score"] == second["score"]
    assert len(client.get("/match", headers=headers).json()) == 1


def test_rematch_uses_edited_job_text(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)
    first = run_match(client, headers, resume["id"], job["id"]).json()
    assert first["skill_score"] < 100

    edit = client.patch(
        f"/jobs/{job['id']}",
        json={"description": "We need a Python developer"},
        headers=headers,
    )
    assert edit.status_code == 200

    second = run_match(client, headers, resume["id"], job["id"]).json()
    assert second["id"] == first["id"]
    assert second["skill_score"] == 100.0
    assert second["matched_skills"] == ["python"]
    assert second["missing_skills"] == []


def test_job_without_known_skills_uses_text_only(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(
        client,
        headers,
        title="Warehouse Associate",
        description="Lift boxes and load trucks safely every day",
    )

    body = run_match(client, headers, resume["id"], job["id"]).json()
    assert body["skill_score"] is None
    assert body["score"] == body["text_score"]
    assert body["matched_skills"] == []
    assert body["missing_skills"] == []


def test_cannot_match_unknown_resume_or_job(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)

    assert run_match(client, headers, 9999, job["id"]).status_code == 404
    assert run_match(client, headers, resume["id"], 9999).status_code == 404
    assert client.get("/match", headers=headers).json() == []


def test_cannot_match_other_users_resume_or_job(client, make_headers, make_pdf):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    alice_resume = add_resume(client, alice, make_pdf)
    alice_job = add_job(client, alice)
    bob_resume = add_resume(client, bob, make_pdf)
    bob_job = add_job(client, bob)

    assert run_match(client, bob, alice_resume["id"], bob_job["id"]).status_code == 404
    assert run_match(client, bob, bob_resume["id"], alice_job["id"]).status_code == 404
    assert client.get("/match", headers=bob).json() == []


def test_cannot_read_other_users_matches(client, make_headers, make_pdf):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    resume = add_resume(client, alice, make_pdf)
    job = add_job(client, alice)
    result = run_match(client, alice, resume["id"], job["id"]).json()

    assert client.get("/match", headers=bob).json() == []
    assert client.get(f"/match/{result['id']}", headers=bob).status_code == 404
    assert client.get(f"/match/{result['id']}", headers=alice).status_code == 200


def test_list_is_sorted_best_first_and_filterable(client, make_headers, make_pdf):
    headers = make_headers()
    weak_resume = add_resume(client, headers, make_pdf, WEAK_LINES, "weak.pdf")
    strong_resume = add_resume(client, headers, make_pdf, RESUME_LINES, "strong.pdf")
    job = add_job(client, headers)
    other_job = add_job(
        client, headers, title="Another Role", description="Python and Docker wanted"
    )

    run_match(client, headers, weak_resume["id"], job["id"])
    run_match(client, headers, strong_resume["id"], job["id"])
    run_match(client, headers, strong_resume["id"], other_job["id"])

    for_job = client.get("/match", params={"job_id": job["id"]}, headers=headers).json()
    assert [m["resume_id"] for m in for_job] == [strong_resume["id"], weak_resume["id"]]
    assert for_job[0]["score"] > for_job[1]["score"]

    for_resume = client.get(
        "/match", params={"resume_id": strong_resume["id"]}, headers=headers
    ).json()
    assert len(for_resume) == 2

    assert len(client.get("/match", headers=headers).json()) == 3
    assert client.get("/match", params={"job_id": 9999}, headers=headers).json() == []


def test_deleting_a_resume_deletes_its_matches(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)
    run_match(client, headers, resume["id"], job["id"])

    assert client.delete(f"/resumes/{resume['id']}", headers=headers).status_code == 204
    assert client.get("/match", headers=headers).json() == []
    assert client.get(f"/jobs/{job['id']}", headers=headers).status_code == 200


def test_deleting_a_job_deletes_its_matches(client, make_headers, make_pdf):
    headers = make_headers()
    resume = add_resume(client, headers, make_pdf)
    job = add_job(client, headers)
    run_match(client, headers, resume["id"], job["id"])

    assert client.delete(f"/jobs/{job['id']}", headers=headers).status_code == 204
    assert client.get("/match", headers=headers).json() == []
    assert client.get(f"/resumes/{resume['id']}", headers=headers).status_code == 200


def test_match_validation(client, make_headers):
    headers = make_headers()
    assert client.post("/match", json={"resume_id": 1}, headers=headers).status_code == 422
    bad_id = {"resume_id": "abc", "job_id": 1}
    assert client.post("/match", json=bad_id, headers=headers).status_code == 422
    assert client.get("/match", params={"limit": 0}, headers=headers).status_code == 422
    assert client.get("/match", params={"limit": 201}, headers=headers).status_code == 422