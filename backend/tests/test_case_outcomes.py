"""Case outcome lifecycle tests: AI FLAG ≠ FRAUD.

Extends PRD R12 with an explicit human outcome for a risk flag:
    OPEN → UNDER_REVIEW → FIELD_VERIFICATION → RESOLVED | ESCALATED | CLOSED
CLOSED means "the investigation did not substantiate the suspected
irregularity" — never a fraud/innocence verdict, never a statement that the
AI flag was wrong. Covers valid/invalid transitions, the mandatory outcome
+ structured reason on closure, audit-trail creation, detection
preservation, dashboard counting and report content.
"""
from __future__ import annotations

import io

import pytest


def _open_case(client) -> dict:
    """Create a case via the API on a project with no case yet."""
    q = client.get("/api/v1/projects").json()["data"]["items"]
    target = next(i for i in q if i["case_status"] is None)
    officers = client.get("/api/v1/officers").json()["data"]
    case = client.post(
        "/api/v1/cases",
        json={"project_id": target["id"], "assigned_officer_id": officers[0]["id"],
              "note": "Opened for outcome-lifecycle test."},
    ).json()["data"]
    return case


def _advance(client, case_id: str, *statuses: str) -> dict:
    case = {"id": case_id}
    for s in statuses:
        payload: dict = {"status": s}
        if s in ("RESOLVED", "ESCALATED"):
            payload["resolution_type"] = "CONFIRMED_CONCERN"
        if s == "CLOSED":
            payload.update(
                resolution_type="NOT_SUBSTANTIATED",
                resolution_reason="FALSE_DUPLICATE_CANDIDATE",
                resolution_summary="Verified with district office; separate sanctioned works.",
            )
        r = client.patch(f"/api/v1/cases/{case_id}", json=payload)
        assert r.status_code == 200, f"{s}: {r.status_code} {r.text}"
        case = r.json()["data"]
    return case


class TestValidTransitions:
    def test_open_to_under_review(self, client):
        case = _open_case(client)
        r = client.patch(f"/api/v1/cases/{case['id']}", json={"status": "UNDER_REVIEW"})
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "UNDER_REVIEW"

    def test_under_review_to_field_verification(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={"status": "FIELD_VERIFICATION"})
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "FIELD_VERIFICATION"

    def test_field_verification_to_not_substantiated(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED",
            "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_reason": "FALSE_DUPLICATE_CANDIDATE",
            "resolution_summary": "Verified with district office; separate sanctioned works.",
        })
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["status"] == "CLOSED"
        assert body["resolution_type"] == "NOT_SUBSTANTIATED"
        assert body["resolution_reason"] == "FALSE_DUPLICATE_CANDIDATE"
        assert body["closed_at"] is not None

    def test_field_verification_to_substantiated_resolved(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "RESOLVED", "resolution_type": "CONFIRMED_CONCERN",
        })
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "RESOLVED"

    def test_substantiated_then_escalated(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        _advance(client, case["id"], "RESOLVED")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "ESCALATED", "resolution_type": "CONFIRMED_CONCERN",
        })
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "ESCALATED"

    def test_not_substantiated_then_closed_then_reopen(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        _advance(client, case["id"], "CLOSED")
        # Supervisor reopen path: CLOSED → UNDER_REVIEW.
        r = client.patch(f"/api/v1/cases/{case['id']}", json={"status": "UNDER_REVIEW"})
        assert r.status_code == 200
        body = r.json()["data"]
        assert body["status"] == "UNDER_REVIEW"
        assert body["closed_at"] is None
        # Historical outcome stays on the record after reopen.
        assert body["resolution_type"] == "NOT_SUBSTANTIATED"


class TestInvalidTransitions:
    def test_open_cannot_close_directly(self, client):
        case = _open_case(client)
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_reason": "OTHER", "resolution_summary": "x",
        })
        assert r.status_code in (400, 409)

    def test_under_review_cannot_close_directly(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_reason": "OTHER", "resolution_summary": "x",
        })
        assert r.status_code in (400, 409)

    def test_concluded_cases_reject_status_jump(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION", "RESOLVED")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_reason": "OTHER", "resolution_summary": "x",
        })
        assert r.status_code in (400, 409)

    def test_closed_requires_not_substantiated_type(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "CONFIRMED_CONCERN",
            "resolution_reason": "OTHER", "resolution_summary": "x",
        })
        assert r.status_code == 400
        assert "NOT_SUBSTANTIATED" in r.json()["detail"]

    def test_closed_requires_structured_reason(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_summary": "Documents verified on site.",
        })
        assert r.status_code == 400
        assert "reason" in r.json()["detail"].lower()

    def test_closed_requires_free_text_explanation(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_reason": "DOCUMENTATION_PROVIDED",
        })
        assert r.status_code == 400

    def test_unknown_reason_rejected(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        r = client.patch(f"/api/v1/cases/{case['id']}", json={
            "status": "CLOSED", "resolution_type": "NOT_SUBSTANTIATED",
            "resolution_reason": "SOMETHING_MADE_UP", "resolution_summary": "x",
        })
        assert r.status_code == 422  # pydantic enum validation


class TestAuditTrailAndDetectionPreservation:
    def test_closure_records_full_transition(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION")
        _advance(client, case["id"], "CLOSED")
        detail = client.get(f"/api/v1/cases/{case['id']}").json()["data"]
        trans = [e for e in detail["events"] if e["event_type"] == "STATUS_CHANGED"]
        seq = [(e["from_status"], e["to_status"]) for e in trans]
        assert ("OPEN", "UNDER_REVIEW") in seq
        assert ("UNDER_REVIEW", "FIELD_VERIFICATION") in seq
        assert ("FIELD_VERIFICATION", "CLOSED") in seq
        final = trans[-1]
        assert final["metadata_json"]["resolution_type"] == "NOT_SUBSTANTIATED"
        assert final["metadata_json"]["resolution_reason"] == "FALSE_DUPLICATE_CANDIDATE"

    def test_original_signals_untouched_after_closure(self, client):
        """Clearing a flag must never modify the AI-generated evidence."""
        q = client.get("/api/v1/projects").json()["data"]["items"]
        target = next(i for i in q if i["case_status"] is None and i["primary_signals"])
        project_id = target["id"]
        before = client.get(f"/api/v1/projects/{project_id}").json()["data"]
        sig_before = [
            (s["id"], s["signal_type"], s["severity"], s["triggered"], s["explanation"])
            for s in before["signals"]
        ]

        officers = client.get("/api/v1/officers").json()["data"]
        case = client.post(
            "/api/v1/cases",
            json={"project_id": project_id, "assigned_officer_id": officers[0]["id"]},
        ).json()["data"]
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION", "CLOSED")

        after = client.get(f"/api/v1/projects/{project_id}").json()["data"]
        sig_after = [
            (s["id"], s["signal_type"], s["severity"], s["triggered"], s["explanation"])
            for s in after["signals"]
        ]
        assert sig_before == sig_after


class TestDashboardCounts:
    def _open_count(self, client) -> int:
        return client.get("/api/v1/dashboard/summary").json()["data"]["case_open_count"]

    def test_not_substantiated_does_not_count_as_open(self, client):
        q = client.get("/api/v1/projects").json()["data"]["items"]
        target = next(i for i in q if i["case_status"] is None)
        case = client.post("/api/v1/cases", json={"project_id": target["id"]}).json()["data"]
        # An OPEN case adds to the open count...
        assert self._open_count(client) >= 1

        # ...and closing it as NOT_SUBSTANTIATED must bring it back down:
        # a cleared case is concluded work, not unresolved work.
        before = self._open_count(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION", "CLOSED")
        assert self._open_count(client) == before - 1

    def test_open_case_counts_as_open(self, client):
        q = client.get("/api/v1/projects").json()["data"]["items"]
        target = next(i for i in q if i["case_status"] is None)
        before = self._open_count(client)
        client.post("/api/v1/cases", json={"project_id": target["id"]})
        assert self._open_count(client) == before + 1


class TestReportContent:
    def _generate(self, client, case_id: str) -> bytes:
        r = client.post(f"/api/v1/cases/{case_id}/report")
        assert r.status_code == 201
        url = r.json()["data"]["download_url"]
        dl = client.get(url)
        assert dl.status_code == 200
        return dl.content

    def test_cleared_case_report_preserves_flag_and_outcome(self, client):
        case = _open_case(client)
        _advance(client, case["id"], "UNDER_REVIEW", "FIELD_VERIFICATION", "CLOSED")
        pdf = self._generate(client, case["id"])

        from pypdf import PdfReader
        text = " ".join(
            p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages
        )
        assert "NOT SUBSTANTIATED" in text
        assert "False duplicate candidate" in text
        # Original automated evidence remains in the report.
        assert "Detected signals and evidence" in text

    def test_open_case_report_has_no_outcome_section(self, client):
        case = _open_case(client)
        pdf = self._generate(client, case["id"])
        from pypdf import PdfReader
        text = " ".join(
            p.extract_text() or "" for p in PdfReader(io.BytesIO(pdf)).pages
        )
        assert "NOT SUBSTANTIATED" not in text


class TestDemoScenario:
    def test_seed_demo_case_scenario_full_lifecycle(self, seeded_db):
        from sqlalchemy.orm import Session as SASession

        from app.core.database import SessionLocal
        from app.models import InvestigationCase, Project
        from app.services.cases.demo_scenario import (
            seed_demo_case_scenario,
            _DEMO_WORK_ID,
        )

        db = SessionLocal()
        try:
            # Self-contained reset: earlier tests may mutate the seeded
            # scenario case (e.g. test_backlog's precision check), so remove
            # any case on the flagship project and seed fresh.
            project = db.query(Project).filter(Project.work_id == _DEMO_WORK_ID).first()
            if project is not None:
                for c in db.query(InvestigationCase).filter(
                    InvestigationCase.project_id == project.id
                ).all():
                    db.delete(c)
                db.commit()

            assert isinstance(db, SASession)
            case = seed_demo_case_scenario(db)
            assert case is not None
            assert case.status == "CLOSED"
            assert case.resolution_type == "NOT_SUBSTANTIATED"
            assert case.resolution_reason == "FALSE_DUPLICATE_CANDIDATE"
            assert case.resolution_summary
            types = [e.event_type for e in case.events]
            assert "CASE_CREATED" in types
            assert types.count("STATUS_CHANGED") == 3

            # Idempotent: second call returns the same case.
            again = seed_demo_case_scenario(db)
            assert again is not None and again.id == case.id
        finally:
            db.close()
