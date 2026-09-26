"""Demo-resilience regression tests beyond the readiness endpoint.

1. signals_for_project_ids must survive >999 project ids (SQLite's
   bind-variable limit) — /dashboard/summary used to 500 with
   `sqlite3.OperationalError: too many SQL variables` on large datasets.
2. The readiness probe stays cheap and never mutates state.
"""
from __future__ import annotations

import pytest


class TestChunkedSignalQuery:
    def test_over_nine_hundred_ids_does_not_crash(self, seeded_db):
        """SQLite rejects >~999 bound variables; the chunked helper must not."""
        from sqlalchemy import text

        from app.models import Project
        from app.services.detection.fusion import signals_for_project_ids

        # Real ids from any projects in the seeded DB, padded to >999 entries.
        base_ids = [pid for (pid,) in seeded_db.query(Project.id).limit(5).all()]
        assert base_ids, "seeded db must contain projects"
        ids = (base_ids * 250)[:1100]  # 1100 ids, duplicates fine for the query
        rows = signals_for_project_ids(seeded_db, ids, text("1 = 1"))
        # Every chunk executed without OperationalError; rows are ProjectSignal.
        assert isinstance(rows, list)

    def test_chunks_return_all_matching_rows(self, seeded_db):
        from app.models import Project, ProjectSignal
        from app.services.detection.fusion import signals_for_project_ids

        ids = [pid for (pid,) in seeded_db.query(Project.id).limit(5).all()]
        expected = (
            seeded_db.query(ProjectSignal)
            .filter(ProjectSignal.project_id.in_(ids))
            .count()
        )
        rows = signals_for_project_ids(seeded_db, ids)
        assert len(rows) == expected


class TestReadinessIsCheap:
    def test_readiness_does_not_create_signals_or_datasets(self, client, seeded_db):
        """The probe is read-only: dataset/signal counts must not change."""
        from app.models import Dataset, ProjectSignal

        before_ds = seeded_db.query(Dataset).count()
        before_sig = seeded_db.query(ProjectSignal).count()
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 200
        assert seeded_db.query(Dataset).count() == before_ds
        assert seeded_db.query(ProjectSignal).count() == before_sig

    def test_readiness_omits_dataset_check_when_autoseed_off(self, client, monkeypatch, seeded_db):
        """Non-autoseed deployments skip the demo-data check entirely."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "demo_autoseed", False)
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 200
        assert "demo_dataset" not in r.json()["checks"]
