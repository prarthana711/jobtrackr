import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers the tables)
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def client():
    """A test client wired to a fresh in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keep one shared connection, or the memory DB vanishes
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_headers(client):
    """Returns a function that registers a user, logs in, and gives auth headers."""

    def _make(email="student@example.com", password="supersecret1"):
        client.post("/auth/register", json={"email": email, "password": password})
        response = client.post(
            "/auth/login", data={"username": email, "password": password}
        )
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _make