import pytest


def job_payload(**overrides):
    payload = {
        "title": "Backend Intern",
        "company": "Acme",
        "location": "Bengaluru",
        "url": "https://acme.com/jobs/1",
        "description": "Python and SQL required",
    }
    payload.update(overrides)
    return payload


def create_job(client, headers, **overrides):
    response = client.post("/jobs", json=job_payload(**overrides), headers=headers)
    assert response.status_code == 201
    return response.json()


def test_jobs_require_authentication(client):
    assert client.get("/jobs").status_code == 401
    assert client.post("/jobs", json=job_payload()).status_code == 401
    assert client.get("/jobs/1").status_code == 401
    assert client.patch("/jobs/1", json={"title": "x"}).status_code == 401
    assert client.delete("/jobs/1").status_code == 401


def test_create_job_success(client, make_headers):
    headers = make_headers()
    response = client.post("/jobs", json=job_payload(), headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["title"] == "Backend Intern"
    assert body["url"] == "https://acme.com/jobs/1"
    assert "user_id" not in body


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": "   "},
        {"url": "javascript:alert(1)"},
        {"description": ""},
    ],
)
def test_create_job_rejects_invalid_input(client, make_headers, overrides):
    headers = make_headers()
    response = client.post("/jobs", json=job_payload(**overrides), headers=headers)
    assert response.status_code == 422


def test_list_returns_only_my_jobs(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    create_job(client, alice, title="Alice Job 1")
    create_job(client, alice, title="Alice Job 2")
    create_job(client, bob, title="Bob Job")

    alice_jobs = client.get("/jobs", headers=alice).json()
    bob_jobs = client.get("/jobs", headers=bob).json()

    assert alice_jobs["total"] == 2
    assert bob_jobs["total"] == 1
    assert bob_jobs["items"][0]["title"] == "Bob Job"


def test_get_job(client, make_headers):
    headers = make_headers()
    job = create_job(client, headers)

    response = client.get(f"/jobs/{job['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Backend Intern"
    assert client.get("/jobs/9999", headers=headers).status_code == 404


def test_cannot_read_other_users_job(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    job = create_job(client, alice)

    assert client.get(f"/jobs/{job['id']}", headers=bob).status_code == 404


def test_cannot_update_other_users_job(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    job = create_job(client, alice)

    response = client.patch(f"/jobs/{job['id']}", json={"title": "Hacked"}, headers=bob)
    assert response.status_code == 404

    unchanged = client.get(f"/jobs/{job['id']}", headers=alice).json()
    assert unchanged["title"] == "Backend Intern"


def test_cannot_delete_other_users_job(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    job = create_job(client, alice)

    assert client.delete(f"/jobs/{job['id']}", headers=bob).status_code == 404
    assert client.get(f"/jobs/{job['id']}", headers=alice).status_code == 200


def test_partial_update(client, make_headers):
    headers = make_headers()
    job = create_job(client, headers)

    response = client.patch(
        f"/jobs/{job['id']}", json={"company": "Globex", "location": None}, headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["company"] == "Globex"
    assert body["location"] is None
    assert body["title"] == "Backend Intern"  # untouched


def test_required_fields_cannot_be_set_to_null(client, make_headers):
    headers = make_headers()
    job = create_job(client, headers)

    response = client.patch(f"/jobs/{job['id']}", json={"title": None}, headers=headers)
    assert response.status_code == 422


def test_delete_job(client, make_headers):
    headers = make_headers()
    job = create_job(client, headers)

    assert client.delete(f"/jobs/{job['id']}", headers=headers).status_code == 204
    assert client.get(f"/jobs/{job['id']}", headers=headers).status_code == 404
    assert client.get("/jobs", headers=headers).json()["total"] == 0


def test_search_filters_jobs(client, make_headers):
    headers = make_headers()
    create_job(client, headers, title="Backend Intern", company="Acme", location="Bengaluru")
    create_job(client, headers, title="Data Analyst", company="Globex", location="Mumbai")
    create_job(client, headers, title="Frontend Developer", company="Acme", location="Remote")
    create_job(client, headers, title="Support Engineer", company="50% Labs", location="Pune")

    def search(term):
        return client.get("/jobs", params={"search": term}, headers=headers).json()

    assert search("intern")["total"] == 1
    assert search("ACME")["total"] == 2
    assert search("mumbai")["total"] == 1
    assert search("%")["total"] == 1  # a literal percent sign, not a wildcard
    assert search("zzz")["total"] == 0
    assert search("")["total"] == 4


def test_pagination(client, make_headers):
    headers = make_headers()
    for i in range(25):
        create_job(client, headers, title=f"Job {i}")

    page1 = client.get("/jobs", headers=headers).json()
    assert len(page1["items"]) == 10
    assert page1["total"] == 25
    assert page1["pages"] == 3
    assert page1["items"][0]["title"] == "Job 24"  # newest first

    page3 = client.get("/jobs", params={"page": 3}, headers=headers).json()
    assert len(page3["items"]) == 5
    assert page3["items"][-1]["title"] == "Job 0"

    page4 = client.get("/jobs", params={"page": 4}, headers=headers).json()
    assert page4["items"] == []


@pytest.mark.parametrize("query", ["page=0", "page_size=0", "page_size=101"])
def test_pagination_rejects_bad_values(client, make_headers, query):
    headers = make_headers()
    assert client.get(f"/jobs?{query}", headers=headers).status_code == 422


def test_newest_jobs_come_first(client, make_headers):
    headers = make_headers()
    create_job(client, headers, title="First")
    create_job(client, headers, title="Second")
    create_job(client, headers, title="Third")

    titles = [job["title"] for job in client.get("/jobs", headers=headers).json()["items"]]
    assert titles == ["Third", "Second", "First"]