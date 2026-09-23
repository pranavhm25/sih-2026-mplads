"""Foundation tests (Prompt-2 scope): health, schema, DB, config hygiene."""
from __future__ import annotations

from app.core.config import settings
from app.models import (
    CaseEvidence,
    CaseEvent,
    CaseNote,
    Dataset,
    DetectionRun,
    InvestigationCase,
    Officer,
    PeerGroup,
    Project,
    ProjectMetrics,
    ProjectPeer,
    ProjectSignal,
    RelatedProject,
    Report,
    RuleDefinition,
    SignalEvidence,
)

EXPECTED_TABLES = {
    "datasets", "projects", "project_metrics", "project_signal",
    "signal_evidence", "peer_group", "project_peer", "related_project",
    "investigation_case", "case_event", "case_note", "case_evidence",
    "officer", "rule_definition", "detection_run", "report",
}


class TestHealthEndpoint:
    def test_health_contract(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok", "service": "drishti-api"}

    def test_root_endpoint(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert data["docs"] == "/docs"

    def test_health_does_not_require_database(self):
        """The health route module must not import DB machinery."""
        import inspect

        from app.api.routes import health
        source = inspect.getsource(health)
        assert "Session" not in source and "engine" not in source


class TestSchema:
    def test_all_sixteen_tables_registered(self):
        from app.db import Base
        assert EXPECTED_TABLES.issubset(set(Base.metadata.tables))

    def test_foreign_keys_defined(self):
        from app.db import Base
        fks = {
            (t, fk.column.table.name)
            for t in Base.metadata.tables
            for fk in Base.metadata.tables[t].foreign_keys
        }
        # Spot-check the layer relationships from BACKEND_SCHEMA.md §2.
        assert ("projects", "datasets") in fks
        assert ("project_metrics", "projects") in fks
        assert ("project_signal", "projects") in fks
        assert ("signal_evidence", "project_signal") in fks
        assert ("investigation_case", "projects") in fks
        assert ("case_event", "investigation_case") in fks
        assert ("report", "investigation_case") in fks

    def test_data_separation_columns(self):
        """Source facts, derived metrics and conclusions live apart."""
        src = {c.name for c in Project.__table__.columns}
        drv = {c.name for c in ProjectMetrics.__table__.columns}
        assert "expenditure" in src            # source fact
        assert "cost_deviation_pct" in drv     # derived metric — never on Project
        assert "cost_deviation_pct" not in src
        assert "resolution_type" in {c.name for c in InvestigationCase.__table__.columns}

    def test_dataset_provenance_fields(self):
        cols = {c.name for c in Dataset.__table__.columns}
        for f in ("source_label", "version", "ingested_at", "row_count",
                  "is_synthetic", "quality_status"):
            assert f in cols


class TestDatabaseConnection:
    def test_connection_roundtrip(self, seeded_db):
        from sqlalchemy import text
        assert seeded_db.execute(text("SELECT 1")).scalar() == 1

    def test_alembic_revision_present(self):
        """The initial migration file exists and is a real revision."""
        import re
        from pathlib import Path
        versions = Path(__file__).parent.parent / "alembic" / "versions"
        files = list(versions.glob("*.py"))
        assert files, "initial Alembic revision missing"
        content = files[0].read_text(encoding="utf-8")
        assert re.search(r"revision(?::\s*str)?\s*=\s*['\"][0-9a-f]+['\"]", content)
        assert "op.create_table" in content


class TestConfigHygiene:
    def test_no_secrets_in_committed_env_example(self):
        from pathlib import Path
        text = (Path(__file__).parent.parent.parent / ".env.example").read_text(encoding="utf-8")
        assert "change-me" in text or "SECRET_KEY=" in text
        assert "sharma@drishti.demo" not in text  # no real-looking credentials

    def test_settings_load_from_env(self):
        assert settings.app_env in ("development", "production", "test")
