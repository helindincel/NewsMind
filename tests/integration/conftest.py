from __future__ import annotations

import os
import pytest

os.environ.setdefault("NEWS_API_KEY", "test-key")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("USE_REDIS", "false")


# ── SQLite in-memory DB for integration tests (no Postgres needed) ────────────

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.database.models import Base
import src.infrastructure.database.session as db_session_module


@pytest.fixture(scope="session", autouse=True)
def sqlite_db():
    """Create a fresh SQLite in-memory database for the test session."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db_session_module._SessionLocal = Session
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables(sqlite_db):
    """Truncate all tables between tests."""
    session = db_session_module.get_session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
