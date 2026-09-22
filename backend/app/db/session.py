"""Session helpers (compat re-export of core.database).

Kept so imports such as `app.db.session` work as ARCHITECTURE.md implies;
the implementation lives in app/core/database.py.
"""
from app.core.database import Base, SessionLocal, engine, get_db  # noqa: F401
