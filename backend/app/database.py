from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(settings.database_url, connect_args=connect_args)

if is_sqlite:
    # SQLite ignores foreign keys unless you turn them on
    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """All models inherit from this."""


def get_db():
    """FastAPI dependency: gives each request its own session, then closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()