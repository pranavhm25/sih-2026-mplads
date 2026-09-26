"""Demo-resilience: /api/v1/health/ready contract.

The readiness probe must (a) answer 200 with ready=true once the demo
dataset is present, (b) answer 503 — not crash — when the storage layer is
unusable, and (c) stay cheap (never run detection). Part of the cold-start
resilience layer; see docs/DEMO_RUNBOOK.md.
"""
from __future__ import annotations

import json

import pytest


class _StubQuery:
    """Chainable query stub: filter(...).count() -> configured value."""

    def __init__(self, count: int) -> None:
        self._count = count

    def filter(self, *_a, **_k):  # noqa: ANN002, ANN003 — stub
        return self

    def count(self) -> int:
        return self._count


class _StubSession:
    """Minimal Session double for the readiness probe."""

    def __init__(self, *, count: int = 1, fail: bool = False) -> None:
        self._count = count
        self._fail = fail
        self.closed = False

    def execute(self, *_a, **_k):
        if self._fail:
            raise RuntimeError("connection refused (simulated outage)")

    def query(self, _model):
        return _StubQuery(self._count)

    def close(self):
        self.closed = True


class TestReadinessEndpoint:
    def test_ready_ok_with_demo_data(self, client):
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["ready"] is True
        assert body["checks"]["database"] == "ok"

    def test_not_ready_when_demo_dataset_missing(self, client, monkeypatch):
        """Autoseed deployments report 503 until the demo dataset exists."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "demo_autoseed", True)
        monkeypatch.setattr(
            "app.core.database.SessionLocal", lambda: _StubSession(count=0)
        )
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "starting"
        assert body["ready"] is False
        assert body["checks"] == {"database": "ok", "demo_dataset": "missing"}

    def test_readiness_survives_database_outage(self, client, monkeypatch):
        """A failing DB connection must degrade to a clean 503, not a 500."""
        monkeypatch.setattr(
            "app.core.database.SessionLocal", lambda: _StubSession(fail=True)
        )
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["ready"] is False
        assert body["checks"] == {"database": "unreachable"}
        # Never leak internals to the demo screen.
        raw = json.dumps(body).lower()
        assert "traceback" not in raw
        assert "runtimeerror" not in raw

    def test_session_is_always_closed(self, client, monkeypatch):
        """The probe must not leak connections when the DB check fails."""
        stub = _StubSession(fail=True)
        monkeypatch.setattr("app.core.database.SessionLocal", lambda: stub)
        client.get("/api/v1/health/ready")
        assert stub.closed
