"""FastAPI dependency injection providers."""

from typing import Generator

from sqlalchemy.orm import Session

from backend.config import SessionLocal, get_settings, Settings


def get_db() -> Generator[Session, None, None]:
    """Yield a database session, closing it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_settings_dep() -> Settings:
    """Return cached application settings."""
    return get_settings()
