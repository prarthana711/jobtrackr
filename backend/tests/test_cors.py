from app.config import settings

ALLOWED = settings.cors_origin_list[0]
UNKNOWN = "http://evil.example.com"


def preflight(client, origin):
    return client.options(
        "/jobs",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )


def test_preflight_from_the_frontend_is_accepted(client):
    response = preflight(client, ALLOWED)
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_preflight_from_an_unknown_origin_is_rejected(client):
    response = preflight(client, UNKNOWN)
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_normal_request_from_the_frontend_gets_cors_headers(client):
    response = client.get("/health", headers={"Origin": ALLOWED})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED


def test_normal_request_from_an_unknown_origin_gets_no_cors_headers(client):
    response = client.get("/health", headers={"Origin": UNKNOWN})
    assert response.status_code == 200  # the server still answers; the browser blocks it
    assert "access-control-allow-origin" not in response.headers