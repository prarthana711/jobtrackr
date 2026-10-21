import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (registers the tables)
from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture(autouse=True)
def uploads_dir(tmp_path, monkeypatch):
    """Every test saves files into its own temporary folder, never into backend/uploads."""
    folder = tmp_path / "uploads"
    monkeypatch.setattr(settings, "upload_dir", str(folder))
    return folder


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


def build_pdf(lines: list[str], pages: int = 1) -> bytes:
    """Build a minimal but valid text PDF, so tests need no real files."""

    def escape(text: str) -> str:
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = (
        "BT /F1 12 Tf 14 TL 50 750 Td "
        + " T* ".join(f"({escape(line)}) Tj" for line in lines)
        + " ET"
    )
    content_id = pages + 3
    font_id = pages + 4
    kids = " ".join(f"{i} 0 R" for i in range(3, 3 + pages))

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>",
    ]
    for _ in range(pages):
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
        )
    objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode("latin-1")

    xref_start = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    ).encode()
    return out


@pytest.fixture
def make_pdf():
    """Returns the PDF builder: make_pdf(["line one", "line two"])."""
    return build_pdf