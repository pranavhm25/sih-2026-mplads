"""Database package — engine, session and declarative base.

ARCHITECTURE.md §4 places persistence plumbing under app/db/.
"""
import logging
from sqlalchemy import inspect, text

from app.core.database import Base, SessionLocal, engine, get_db
import app.models  # noqa: F401

__all__ = ["Base", "SessionLocal", "engine", "get_db", "create_all"]

logger = logging.getLogger("drishti.db")


def _ensure_columns() -> None:
    """Add any missing columns to existing tables in development environments.

    Base.metadata.create_all() only creates missing tables, leaving pre-existing
    tables untouched when models evolve. This helper inspects each table and
    adds any missing columns with safe defaults.
    """
    try:
        inspector = inspect(engine)
        with engine.begin() as conn:
            for table_name, table in Base.metadata.tables.items():
                if not inspector.has_table(table_name):
                    continue
                existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
                for column in table.columns:
                    if column.name not in existing_cols:
                        col_type = column.type.compile(engine.dialect)
                        default_clause = ""
                        if column.server_default is not None:
                            arg = column.server_default.arg
                            default_clause = f" DEFAULT {arg.text if hasattr(arg, 'text') else arg}"
                        elif not column.nullable:
                            if hasattr(column.default, "arg") and column.default is not None and getattr(column.default, "is_scalar", False):
                                default_clause = f" DEFAULT '{column.default.arg}'"
                            elif "int" in str(col_type).lower():
                                default_clause = " DEFAULT 0"
                            elif "bool" in str(col_type).lower():
                                default_clause = " DEFAULT 0"
                            else:
                                default_clause = " DEFAULT 'WORK_LEVEL'" if column.name == "dataset_type" else " DEFAULT ''"

                        null_clause = " NOT NULL" if (not column.nullable and default_clause) else ""
                        sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{column.name}" {col_type}{default_clause}{null_clause}'
                        logger.info("Migrating schema column: %s", sql)
                        conn.execute(text(sql))
    except Exception as exc:
        logger.warning("Could not auto-migrate missing columns: %s", exc)


def create_all() -> None:
    """Create all tables (development convenience) and ensure columns are up to date.

    Production deployments should apply Alembic migrations instead;
    main.py gates this helper to non-production environments.
    """
    Base.metadata.create_all(bind=engine)
    _ensure_columns()

