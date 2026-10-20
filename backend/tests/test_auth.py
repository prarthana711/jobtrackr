EMAIL = "student@example.com"
PASSWORD = "supersecret1"


def register(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/auth/login", data={"username": email, "password": password})


def auth_header(client):
    register(client)
    token = login(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_register_success(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == EMAIL
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert register(client, email="STUDENT@example.com").status_code == 409


def test_register_short_password_rejected(client):
    assert register(client, password="short").status_code == 422


def test_register_invalid_email_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_success(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    register(client)
    assert login(client, password="wrongpassword1").status_code == 401


def test_login_unknown_email_gives_same_error(client):
    register(client)
    wrong_password = login(client, password="wrongpassword1")
    unknown_email = login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_valid_token(client):
    response = client.get("/auth/me", headers=auth_header(client))
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


def test_me_with_garbage_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401