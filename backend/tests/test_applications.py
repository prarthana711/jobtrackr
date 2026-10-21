def make_job(client, headers, title="Backend Intern"):
    response = client.post(
        "/jobs",
        json={"title": title, "company": "Acme", "description": "Python and SQL required"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()


def make_application(client, headers, job_id, **extra):
    response = client.post(
        "/applications", json={"job_id": job_id, **extra}, headers=headers
    )
    assert response.status_code == 201
    return response.json()


def new_application(client, headers, title="Backend Intern"):
    """Shortcut: create a job, then an application for it."""
    job = make_job(client, headers, title)
    return make_application(client, headers, job["id"])


def move(client, headers, application_id, new_status):
    return client.patch(
        f"/applications/{application_id}/status",
        json={"status": new_status},
        headers=headers,
    )


def test_applications_require_authentication(client):
    assert client.get("/applications").status_code == 401
    assert client.post("/applications", json={"job_id": 1}).status_code == 401
    assert client.get("/applications/1").status_code == 401
    assert client.patch("/applications/1", json={"notes": "x"}).status_code == 401
    assert client.patch("/applications/1/status", json={"status": "applied"}).status_code == 401
    assert client.get("/applications/1/history").status_code == 401
    assert client.delete("/applications/1").status_code == 401


def test_create_application(client, make_headers):
    headers = make_headers()
    job = make_job(client, headers)

    response = client.post(
        "/applications",
        json={"job_id": job["id"], "notes": "Referred by a friend"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "saved"
    assert body["applied_on"] is None
    assert body["notes"] == "Referred by a friend"
    assert body["job"]["title"] == "Backend Intern"
    assert body["allowed_next"] == ["applied"]
    assert "user_id" not in body

    history = client.get(f"/applications/{body['id']}/history", headers=headers).json()
    assert len(history) == 1
    assert history[0]["from_status"] is None
    assert history[0]["to_status"] == "saved"


def test_cannot_apply_to_unknown_job(client, make_headers):
    headers = make_headers()
    response = client.post("/applications", json={"job_id": 9999}, headers=headers)
    assert response.status_code == 404


def test_cannot_apply_to_other_users_job(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    job = make_job(client, alice)

    response = client.post("/applications", json={"job_id": job["id"]}, headers=bob)
    assert response.status_code == 404


def test_duplicate_application_rejected(client, make_headers):
    headers = make_headers()
    job = make_job(client, headers)
    make_application(client, headers, job["id"])

    response = client.post("/applications", json={"job_id": job["id"]}, headers=headers)
    assert response.status_code == 409


def test_list_returns_only_my_applications(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    new_application(client, alice, "Alice Job")
    new_application(client, bob, "Bob Job")

    alice_list = client.get("/applications", headers=alice).json()
    bob_list = client.get("/applications", headers=bob).json()

    assert alice_list["total"] == 1
    assert alice_list["items"][0]["job"]["title"] == "Alice Job"
    assert bob_list["total"] == 1
    assert bob_list["items"][0]["job"]["title"] == "Bob Job"


def test_list_filter_by_status(client, make_headers):
    headers = make_headers()
    applications = [new_application(client, headers, f"Job {i}") for i in range(3)]
    move(client, headers, applications[0]["id"], "applied")

    def total(params):
        return client.get("/applications", params=params, headers=headers).json()["total"]

    assert total({}) == 3
    assert total({"status": "applied"}) == 1
    assert total({"status": "saved"}) == 2
    assert total({"status": "offer"}) == 0

    bad = client.get("/applications", params={"status": "banana"}, headers=headers)
    assert bad.status_code == 422


def test_list_pagination(client, make_headers):
    headers = make_headers()
    for i in range(12):
        new_application(client, headers, f"Job {i}")

    page1 = client.get("/applications", headers=headers).json()
    assert page1["total"] == 12
    assert page1["pages"] == 2
    assert len(page1["items"]) == 10
    assert page1["items"][0]["job"]["title"] == "Job 11"  # newest first

    page2 = client.get("/applications", params={"page": 2}, headers=headers).json()
    assert len(page2["items"]) == 2
    assert page2["items"][-1]["job"]["title"] == "Job 0"


def test_get_application(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)

    response = client.get(f"/applications/{application['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["job"]["company"] == "Acme"
    assert client.get("/applications/9999", headers=headers).status_code == 404


def test_cannot_read_other_users_application(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = new_application(client, alice)

    assert client.get(f"/applications/{application['id']}", headers=bob).status_code == 404
    assert client.get(f"/applications/{application['id']}/history", headers=bob).status_code == 404


def test_update_notes_and_applied_on(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)

    response = client.patch(
        f"/applications/{application['id']}",
        json={"notes": "Called HR", "applied_on": "2025-01-15", "status": "offer"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["notes"] == "Called HR"
    assert body["applied_on"] == "2025-01-15"
    assert body["status"] == "saved"  # the general PATCH cannot change status

    cleared = client.patch(
        f"/applications/{application['id']}", json={"notes": None}, headers=headers
    )
    assert cleared.json()["notes"] is None


def test_cannot_update_other_users_application(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = new_application(client, alice)

    response = client.patch(
        f"/applications/{application['id']}", json={"notes": "Hacked"}, headers=bob
    )
    assert response.status_code == 404

    unchanged = client.get(f"/applications/{application['id']}", headers=alice).json()
    assert unchanged["notes"] is None


def test_full_path_records_history(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)

    for new_status in ["applied", "online_assessment", "interview", "offer"]:
        response = move(client, headers, application["id"], new_status)
        assert response.status_code == 200
        assert response.json()["status"] == new_status

    body = response.json()
    assert body["applied_on"] is not None
    assert body["allowed_next"] == []

    history = client.get(f"/applications/{application['id']}/history", headers=headers).json()
    assert [h["from_status"] for h in history] == [
        None, "saved", "applied", "online_assessment", "interview",
    ]
    assert [h["to_status"] for h in history] == [
        "saved", "applied", "online_assessment", "interview", "offer",
    ]


def test_cannot_skip_stages(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)

    assert move(client, headers, application["id"], "offer").status_code == 409

    current = client.get(f"/applications/{application['id']}", headers=headers).json()
    assert current["status"] == "saved"
    history = client.get(f"/applications/{application['id']}/history", headers=headers).json()
    assert len(history) == 1  # the blocked move left no trace


def test_cannot_leave_final_state(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)
    move(client, headers, application["id"], "applied")
    move(client, headers, application["id"], "rejected")

    for blocked in ["applied", "interview", "offer"]:
        assert move(client, headers, application["id"], blocked).status_code == 409

    current = client.get(f"/applications/{application['id']}", headers=headers).json()
    assert current["status"] == "rejected"


def test_cannot_move_to_same_status(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)
    assert move(client, headers, application["id"], "saved").status_code == 409


def test_invalid_status_value_rejected(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)
    assert move(client, headers, application["id"], "banana").status_code == 422


def test_existing_applied_on_is_kept(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)
    client.patch(
        f"/applications/{application['id']}",
        json={"applied_on": "2025-01-15"},
        headers=headers,
    )

    body = move(client, headers, application["id"], "applied").json()
    assert body["applied_on"] == "2025-01-15"


def test_cannot_change_status_of_other_users_application(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = new_application(client, alice)

    assert move(client, bob, application["id"], "applied").status_code == 404

    current = client.get(f"/applications/{application['id']}", headers=alice).json()
    assert current["status"] == "saved"


def test_delete_application(client, make_headers):
    headers = make_headers()
    job = make_job(client, headers)
    application = make_application(client, headers, job["id"])

    assert client.delete(f"/applications/{application['id']}", headers=headers).status_code == 204
    assert client.get(f"/applications/{application['id']}", headers=headers).status_code == 404
    assert client.get(f"/jobs/{job['id']}", headers=headers).status_code == 200  # job survives


def test_cannot_delete_other_users_application(client, make_headers):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    application = new_application(client, alice)

    assert client.delete(f"/applications/{application['id']}", headers=bob).status_code == 404
    assert client.get(f"/applications/{application['id']}", headers=alice).status_code == 200


def test_deleting_a_job_deletes_its_applications(client, make_headers):
    headers = make_headers()
    application = new_application(client, headers)

    assert client.delete(f"/jobs/{application['job_id']}", headers=headers).status_code == 204
    assert client.get(f"/applications/{application['id']}", headers=headers).status_code == 404