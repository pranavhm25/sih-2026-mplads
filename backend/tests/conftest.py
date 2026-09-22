"""Shared pytest fixtures: isolated database + demo ingestion per session."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Make `app` importable when running pytest from backend/ or repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Fresh file DB per test session (set BEFORE app modules are imported).
_tmpdir = tempfile.mkdtemp(prefix="drishti-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["DEMO_AUTOSEED"] = "false"
os.environ["REPORT_STORAGE_PATH"] = str(Path(_tmpdir) / "reports")


@pytest.fixture(scope="session")
def seeded_db():
    """A database seeded once with the demo dataset + full detection run."""
    from app.core.database import Base, SessionLocal, engine
    from app.data.demo_data import REFERENCE_DATE
    from app.services.bootstrap import seed_demo_if_empty

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.core.config import settings
        settings.demo_autoseed = True  # seed explicitly in tests
        dataset = seed_demo_if_empty(db)
        assert dataset is not None, "demo seed failed"
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(seeded_db):
    """TestClient bound to the seeded database (lifespan disabled)."""
    from fastapi.testclient import TestClient

    from app.main import app

    # Autoseed is env-controlled and already seeded; lifespan bootstrap is a no-op.
    with TestClient(app) as c:
        yield c
