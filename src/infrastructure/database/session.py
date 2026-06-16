from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.database.models import Base

_SessionLocal: sessionmaker | None = None


def init_db(database_url: str) -> None:
    global _SessionLocal
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    Base.metadata.create_all(engine)
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Session:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _SessionLocal()
