"""Database package — engine, session and declarative base.

ARCHITECTURE.md §4 places persistence plumbing under app/db/.
"""
from app.core.database import Base, SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]


def create_all() -> None:
    """Create all tables (development convenience).

    Production deployments should apply Alembic migrations instead;
    main.py gates this helper to non-production environments.
    """
    Base.metadata.create_all(bind=engine)
