from app.config import settings

RESUME_LINES = [
    "Asha Rao - Information Science Engineering",
    "Skills: Python, SQL, Docker, FastAPI and PostgreSQL",
    "Built a REST API with Node.js and deployed it on AWS",
]
EXPECTED_SKILLS = [
    "aws",
    "docker",
    "fastapi",
    "node.js",
    "postgresql",
    "python",
    "rest api",
    "sql",
]


def upload(client, headers, data, filename="my_cv.pdf", content_type="application/pdf"):
    return client.post(
        "/resumes", files={"file": (filename, data, content_type)}, headers=headers
    )


def upload_ok(client, headers, data, filename="my_cv.pdf"):
    response = upload(client, headers, data, filename)
    assert response.status_code == 201
    return response.json()


def test_resumes_require_authentication(client):
    files = {"file": ("cv.pdf", b"%PDF-1.4", "application/pdf")}
    assert client.get("/resumes").status_code == 401
    assert client.post("/resumes", files=files).status_code == 401
    assert client.get("/resumes/1").status_code == 401
    assert client.get("/resumes/1/file").status_code == 401
    assert client.delete("/resumes/1").status_code == 401


def test_upload_resume_success(client, make_headers, make_pdf, uploads_dir):
    headers = make_headers()
    pdf = make_pdf(RESUME_LINES)

    response = upload(client, headers, pdf)
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "my_cv.pdf"
    assert body["size_bytes"] == len(pdf)
    assert body["parsed_skills"] == EXPECTED_SKILLS
    assert "raw_text" not in body
    assert "stored_filename" not in body
    assert "user_id" not in body

    saved = list(uploads_dir.glob("*.pdf"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == pdf


def test_filename_cannot_escape_upload_folder(
    client, make_headers, make_pdf, tmp_path, uploads_dir
):
    headers = make_headers()
    response = upload(client, headers, make_pdf(RESUME_LINES), filename="../../evil.pdf")

    assert response.status_code == 201
    assert response.json()["original_filename"] == "evil.pdf"

    saved = list(uploads_dir.iterdir())
    assert len(saved) == 1
    assert saved[0].name != "evil.pdf"  # saved under a random name
    assert not (tmp_path / "evil.pdf").exists()
    assert not (tmp_path.parent / "evil.pdf").exists()


def test_rejects_non_pdf_even_if_named_pdf(client, make_headers, uploads_dir):
    headers = make_headers()

    fake = upload(client, headers, b"just some text, not a pdf", filename="cv.pdf")
    assert fake.status_code == 415

    text_file = upload(
        client, headers, b"hello", filename="notes.txt", content_type="text/plain"
    )
    assert text_file.status_code == 415

    assert not uploads_dir.exists() or not any(uploads_dir.iterdir())


def test_rejects_corrupt_pdf(client, make_headers, uploads_dir):
    headers = make_headers()
    response = upload(client, headers, b"%PDF-1.4 this is not really a pdf")

    assert response.status_code == 422
    assert not uploads_dir.exists() or not any(uploads_dir.iterdir())


def test_rejects_pdf_without_text(client, make_headers, make_pdf, uploads_dir):
    headers = make_headers()
    response = upload(client, headers, make_pdf([]))

    assert response.status_code == 422
    assert "text" in response.json()["detail"]
    assert not uploads_dir.exists() or not any(uploads_dir.iterdir())


def test_rejects_oversized_file(client, make_headers, monkeypatch, uploads_dir):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    headers = make_headers()

    too_big = b"%PDF-" + b"0" * (1024 * 1024)
    response = upload(client, headers, too_big)

    assert response.status_code == 413
    assert not uploads_dir.exists() or not any(uploads_dir.iterdir())


def test_resume_limit_per_user(client, make_headers, make_pdf, monkeypatch):
    monkeypatch.setattr(settings, "max_resumes_per_user", 2)
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    pdf = make_pdf(RESUME_LINES)

    upload_ok(client, alice, pdf)
    upload_ok(client, alice, pdf)
    assert upload(client, alice, pdf).status_code == 409
    assert upload(client, bob, pdf).status_code == 201  # the limit is per user


def test_list_returns_only_my_resumes(client, make_headers, make_pdf):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    pdf = make_pdf(RESUME_LINES)
    upload_ok(client, alice, pdf, "first.pdf")
    upload_ok(client, alice, pdf, "second.pdf")
    upload_ok(client, bob, pdf, "bobs.pdf")

    alice_list = client.get("/resumes", headers=alice).json()
    bob_list = client.get("/resumes", headers=bob).json()

    assert [r["original_filename"] for r in alice_list] == ["second.pdf", "first.pdf"]
    assert "raw_text" not in alice_list[0]
    assert [r["original_filename"] for r in bob_list] == ["bobs.pdf"]


def test_get_resume_includes_text(client, make_headers, make_pdf):
    headers = make_headers()
    resume = upload_ok(client, headers, make_pdf(RESUME_LINES))

    response = client.get(f"/resumes/{resume['id']}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "Python" in body["raw_text"]
    assert body["parsed_skills"] == EXPECTED_SKILLS
    assert client.get("/resumes/9999", headers=headers).status_code == 404


def test_download_original_file(client, make_headers, make_pdf):
    headers = make_headers()
    pdf = make_pdf(RESUME_LINES)
    resume = upload_ok(client, headers, pdf)

    response = client.get(f"/resumes/{resume['id']}/file", headers=headers)
    assert response.status_code == 200
    assert response.content == pdf
    assert response.headers["content-type"] == "application/pdf"


def test_cannot_access_other_users_resume(client, make_headers, make_pdf, uploads_dir):
    alice = make_headers("alice@example.com")
    bob = make_headers("bob@example.com")
    resume = upload_ok(client, alice, make_pdf(RESUME_LINES))
    resume_id = resume["id"]

    assert client.get(f"/resumes/{resume_id}", headers=bob).status_code == 404
    assert client.get(f"/resumes/{resume_id}/file", headers=bob).status_code == 404
    assert client.delete(f"/resumes/{resume_id}", headers=bob).status_code == 404

    assert client.get(f"/resumes/{resume_id}", headers=alice).status_code == 200
    assert len(list(uploads_dir.glob("*.pdf"))) == 1


def test_delete_resume_removes_record_and_file(client, make_headers, make_pdf, uploads_dir):
    headers = make_headers()
    resume = upload_ok(client, headers, make_pdf(RESUME_LINES))
    assert len(list(uploads_dir.glob("*.pdf"))) == 1

    assert client.delete(f"/resumes/{resume['id']}", headers=headers).status_code == 204
    assert client.get(f"/resumes/{resume['id']}", headers=headers).status_code == 404
    assert list(uploads_dir.glob("*.pdf")) == []