"""Database engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = Path(__file__).resolve().parents[1] / "vouchai.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base shared by all ORM models."""


def init_db() -> None:
    """Create tables if they do not exist (no migrations)."""
    from . import models  # noqa: F401  ensure models are registered

    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a session and always close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
