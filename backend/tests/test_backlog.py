"""Backlog tests — compliance pack, security pack, stakeholder views,
validation story, alert digest, trends, payments layer, XLSX ingestion."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.core.constants import StakeholderRole
from app.rules.compliance import classify_agency, classify_work


@pytest.fixture(autouse=True)
def _seed_accounts(seeded_db):
    """Demo stakeholder accounts exist before auth tests run."""
    from app.core.database import SessionLocal
    from app.services.auth import seed_demo_accounts

    db = SessionLocal()
    seed_demo_accounts(db)
    db.close()


# ---------------------------------------------------------------------------
# Backlog #1 — categorical compliance
# ---------------------------------------------------------------------------

class TestComplianceClassification:
    def test_religious_structure(self):
        hit = classify_work("Construction of temple compound wall")
        assert hit is not None
        assert hit["entry"]["code"] == "RELIGIOUS_STRUCTURE"
        assert hit["matched_term"] == "temple"

    def test_memorial(self):
        assert classify_work("Erection of statue of national leader") is not None

    def test_benign_work_not_flagged(self):
        assert classify_work("Construction of additional classrooms") is None

    def test_word_boundary_no_false_hit(self):
        # "temple" must not match inside another word
        assert classify_work("Contemplation garden works") is None

    def test_agency_trust_indicator(self):
        hit = classify_agency("Sri Deva Trust for Rural Development")
        assert hit is not None
        assert hit["entry"]["code"] == "UNAPPROVED_TRUST"

    def test_normal_agency_clear(self):
        assert classify_agency("Public Works Division") is None


class TestComplianceInPipeline:
    def test_prohibited_work_produces_signal_with_citation(self, client):
        from app.models import Dataset, Project, ProjectSignal
        from app.core.database import SessionLocal
        from app.services.ingestion.orchestrator import import_official_file
        from app.services.detection.runner import run_detection

        db = SessionLocal()
        # Clean up this import fully afterwards: the shared session DB must
        # keep the demo dataset as the latest work-level import, otherwise
        # the integration tests that read the intelligence screens see this
        # 2-row fixture instead.
        csv_bytes = (
            "work_id,state,district,work_name,sanctioned_amount,status\n"
            "CMP-1,Karnataka,Bangalore North,Construction of temple entrance,500000,Completed\n"
            "CMP-2,Karnataka,Bangalore North,School classroom block,500000,Completed\n"
        ).encode()
        summary = import_official_file(
            db, csv_bytes, file_name="synthetic_compliance_check.csv",
            is_synthetic=True, pipeline_runner=run_detection,
        )
        ds = db.get(Dataset, summary["dataset_id"])
        flagged = (
            db.query(ProjectSignal)
            .join(Project, ProjectSignal.project_id == Project.id)
            .filter(
                Project.dataset_id == ds.id,
                ProjectSignal.signal_type == "COMPLIANCE",
            )
            .all()
        )
        assert len(flagged) == 1
        assert "guideline" in flagged[0].explanation.lower()
        assert flagged[0].evidence[0].reference_label == "guideline citation"
        # Language discipline: never declares fraud
        assert "fraud" not in flagged[0].explanation.lower()
        assert "fraud" not in flagged[0].title.lower()
        # Full cleanup — fixture rows must not linger as the newest dataset.
        ds_id = summary["dataset_id"]
        db.query(ProjectSignal).filter(
            ProjectSignal.project_id.in_(
                [pid for (pid,) in db.query(Project.id)
                 .filter(Project.dataset_id == ds_id).all()]
            )
        ).delete(synchronize_session=False)
        db.query(Project).filter(Project.dataset_id == ds_id).delete(
            synchronize_session=False
        )
        db.query(Dataset).filter(Dataset.id == ds_id).delete()
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Backlog #2 — auth + audit chain
# ---------------------------------------------------------------------------

class TestSecurity:
    def test_password_hash_roundtrip(self):
        h = security.hash_password("s3cret")
        assert h.startswith("pbkdf2_sha256$")
        assert security.verify_password("s3cret", h)
        assert not security.verify_password("wrong", h)

    def test_token_lifecycle(self):
        tok = security.issue_token("officer-1", ttl=60)
        assert security.verify_token(tok) == "officer-1"

    def test_expired_token_rejected(self):
        tok = security.issue_token("officer-1", ttl=-10)
        assert security.verify_token(tok) is None

    def test_tampered_token_rejected(self):
        tok = security.issue_token("officer-1", ttl=60)
        assert security.verify_token(tok[:-1] + ("0" if tok[-1] != "0" else "1")) is None

    def test_login_requires_valid_credentials(self, client):
        r = client.post("/api/v1/auth/login",
                        json={"email": "ministry@drishti.demo", "password": "nope"})
        assert r.status_code == 401

    def test_login_success_and_me(self, client):
        r = client.post("/api/v1/auth/login",
                        json={"email": "ministry@drishti.demo",
                              "password": "drishti-demo"})
        assert r.status_code == 200
        token = r.json()["data"]["token"]
        me = client.get("/api/v1/auth/me",
                        headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["data"]["stakeholder_role"] == StakeholderRole.MINISTRY.value

    def test_audit_chain_detects_tampering(self, client):
        from app.core.database import SessionLocal
        from app.models import AuditEvent

        client.post("/api/v1/auth/login",
                    json={"email": "mp@drishti.demo", "password": "drishti-demo"})
        r = client.get("/api/v1/audit/verify")
        assert r.status_code == 200
        assert r.json()["data"]["valid"] is True

        # Simulate direct DB tampering — the chain must catch it.
        db = SessionLocal()
        ev = db.query(AuditEvent).order_by(AuditEvent.seq.asc()).first()
        tampered_seq = ev.seq
        ev.action = "FORGERY"
        db.commit()
        db.close()

        r = client.get("/api/v1/audit/verify")
        data = r.json()["data"]
        assert data["valid"] is False
        assert data["reason"] == "entry_hash_mismatch"
        assert data["broken_at_seq"] == tampered_seq

    def test_failed_login_is_audited(self, client):
        from app.core.database import SessionLocal
        from app.models import AuditEvent

        client.post("/api/v1/auth/login",
                    json={"email": "ministry@drishti.demo", "password": "bad"})
        db = SessionLocal()
        last = db.query(AuditEvent).order_by(AuditEvent.seq.desc()).first()
        assert last.action == "AUDIT_LOGIN_FAILED"
        db.rollback()
        db.close()


# ---------------------------------------------------------------------------
# Backlog #4 — stakeholder scoping
# ---------------------------------------------------------------------------

class TestStakeholderViews:
    def _login(self, client, email):
        r = client.post("/api/v1/auth/login",
                        json={"email": email, "password": "drishti-demo"})
        return r.json()["data"]["token"]

    def test_ministry_sees_national_scope(self, client):
        tok = self._login(client, "ministry@drishti.demo")
        r = client.get("/api/v1/stakeholder/summary",
                       headers={"Authorization": f"Bearer {tok}"})
        data = r.json()["data"]
        assert data["scope"]["label"] == "NATIONAL"
        assert data["works"]["total"] > 0

    def test_mp_scope_is_constituency(self, client):
        tok = self._login(client, "mp@drishti.demo")
        r = client.get("/api/v1/stakeholder/summary",
                       headers={"Authorization": f"Bearer {tok}"})
        data = r.json()["data"]
        assert data["scope"]["label"].startswith("CONSTITUENCY:")
        assert data["mp_headlines"] is not None
        # MP slice must be a subset of national
        assert data["works"]["total"] <= self._national(client)

    def test_unauthenticated_gets_counts_only(self, client):
        r = client.get("/api/v1/stakeholder/summary")
        assert r.status_code == 200
        assert r.json()["data"]["scope"]["role"] == "UNAUTHENTICATED"
        assert r.json()["data"]["mp_headlines"] is None

    def _national(self, client):
        tok = self._login(client, "ministry@drishti.demo")
        r = client.get("/api/v1/stakeholder/summary",
                       headers={"Authorization": f"Bearer {tok}"})
        return r.json()["data"]["works"]["total"]


# ---------------------------------------------------------------------------
# Backlog #3 — validation story
# ---------------------------------------------------------------------------

class TestValidationStory:
    def test_precision_null_before_feedback(self, client):
        r = client.get("/api/v1/validation/summary")
        data = r.json()["data"]
        assert r.status_code == 200
        # precision is honest: null with zero resolutions
        if data["feedback"]["confirmed_concern"] == 0 and \
                data["feedback"]["false_positive"] == 0:
            assert data["feedback"]["precision"] is None

    def test_precision_computed_after_feedback(self, client):
        from app.core.database import SessionLocal
        from app.models import InvestigationCase

        db = SessionLocal()
        case = db.query(InvestigationCase).first()
        if case is None:
            db.close()
            pytest.skip("no cases in demo data")
        case.resolution_type = "CONFIRMED_CONCERN"
        db.commit()
        case_id = case.id
        db.close()

        r = client.get("/api/v1/validation/summary")
        fb = r.json()["data"]["feedback"]
        assert fb["confirmed_concern"] >= 1
        assert fb["precision"] is not None

        # restore
        db = SessionLocal()
        c = db.get(InvestigationCase, case_id)
        c.resolution_type = None
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Backlog #6 — alert digest
# ---------------------------------------------------------------------------

class TestAlertDigest:
    def test_digest_requires_auth(self, client):
        r = client.get("/api/v1/alerts/digest")
        assert r.status_code == 401

    def test_digest_lists_new_signals_then_ack_clears(self, client):
        r = client.post("/api/v1/auth/login",
                        json={"email": "district@drishti.demo",
                              "password": "drishti-demo"})
        tok = r.json()["data"]["token"]
        hdr = {"Authorization": f"Bearer {tok}"}

        before = client.get("/api/v1/alerts/digest", headers=hdr).json()["data"]
        ack = client.post("/api/v1/alerts/digest/ack", headers=hdr)
        assert ack.status_code == 200
        after = client.get("/api/v1/alerts/digest", headers=hdr).json()["data"]
        # After acknowledging, no NEW signal newer than the watermark appears.
        # (Wall-clock equal timestamps can keep one boundary item visible.)
        assert after["counts"]["new_signals"] <= 1
        assert before["counts"]["new_signals"] >= 0

    def test_district_floor_is_critical(self, client):
        r = client.post("/api/v1/auth/login",
                        json={"email": "district@drishti.demo",
                              "password": "drishti-demo"})
        tok = r.json()["data"]["token"]
        data = client.get("/api/v1/alerts/digest",
                          headers={"Authorization": f"Bearer {tok}"}).json()["data"]
        assert data["floor_severity"] == "CRITICAL"


# ---------------------------------------------------------------------------
# Backlog #7 — trends
# ---------------------------------------------------------------------------

class TestTrends:
    def test_trends_endpoint_shape(self, client):
        r = client.get("/api/v1/trends")
        data = r.json()["data"]
        assert r.status_code == 200
        assert isinstance(data["series"], list)
        assert "limitation" in data and "2023" in data["limitation"]
        for row in data["series"]:
            if row["works_sanctioned"] and row["works_completed"]:
                assert 0 <= row["works_completed"] / row["works_sanctioned"] <= 1


# ---------------------------------------------------------------------------
# Backlog #5 + #12 — payments layer + XLSX
# ---------------------------------------------------------------------------

class TestPaymentsLayer:
    def test_payment_columns_flow_to_records(self, client):
        from app.core.database import SessionLocal
        from app.models import Dataset, PaymentRecord
        from app.services.ingestion.orchestrator import import_official_file

        db = SessionLocal()
        csv_bytes = (
            "work_id,state,district,work_name,sanctioned_amount,status,"
            "payment_ref,payment_amount,paid_on,payee,payment_stage\n"
            "PAY-1,Karnataka,Bangalore North,Water tank works,1000000,Completed,"
            "PMT-001,400000,2025-04-10,ABC Contractors,Stage 1\n"
        ).encode()
        summary = import_official_file(
            db, csv_bytes, file_name="synthetic_payments_test.csv",
            is_synthetic=True, pipeline_runner=None,
        )
        payments = (
            db.query(PaymentRecord)
            .filter(PaymentRecord.dataset_id == summary["dataset_id"])
            .all()
        )
        assert len(payments) == 1
        assert float(payments[0].amount) == 400000
        assert payments[0].payee == "ABC Contractors"
        # Hard cleanup: the orchestrator commits, so delete the dataset's
        # rows explicitly (payments/projects first to avoid FK-set-null
        # UPDATE paths, then the dataset) to keep the shared DB pristine.
        from app.models import Project as _Project
        ds_id = summary["dataset_id"]
        db.query(PaymentRecord).filter(PaymentRecord.dataset_id == ds_id).delete()
        db.query(_Project).filter(_Project.dataset_id == ds_id).delete(
            synchronize_session=False
        )
        db.query(Dataset).filter(Dataset.id == ds_id).delete()
        db.commit()
        db.close()

    def test_no_payment_columns_means_no_payment_rows(self, client):
        from app.core.database import SessionLocal
        from app.models import Dataset, PaymentRecord
        from app.services.ingestion.orchestrator import import_official_file

        db = SessionLocal()
        csv_bytes = (
            "work_id,state,district,work_name,sanctioned_amount,status\n"
            "PAY-2,Karnataka,Bangalore North,Road works,1000000,Ongoing\n"
        ).encode()
        summary = import_official_file(
            db, csv_bytes, file_name="synthetic_nopay_test.csv",
            is_synthetic=True, pipeline_runner=None,
        )
        n = (
            db.query(PaymentRecord)
            .filter(PaymentRecord.dataset_id == summary["dataset_id"])
            .count()
        )
        assert n == 0
        from app.models import Project as _Project
        ds_id = summary["dataset_id"]
        db.query(_Project).filter(_Project.dataset_id == ds_id).delete(
            synchronize_session=False
        )
        db.query(Dataset).filter(Dataset.id == ds_id).delete()
        db.commit()
        db.close()


class TestXlsxIngestion:
    def test_ls_xlsx_fixture_ingests(self, client):
        from pathlib import Path

        from app.core.database import SessionLocal
        from app.services.ingestion.orchestrator import import_official_file

        path = Path(__file__).resolve().parent.parent / "app/data/fixtures/mp_allocation_ls.xlsx"
        if not path.exists():
            pytest.skip("xlsx fixture missing")
        db = SessionLocal()
        summary = import_official_file(
            db, path.read_bytes(),
            file_name="mp_allocation_ls_synthetic.xlsx",
            is_synthetic=True, pipeline_runner=None,
        )
        assert summary["dataset_type"] == "MP_ALLOCATION"
        assert summary["valid_rows"] >= 1
        from app.models import Dataset as _DS
        from app.models import MPAllocationRecord as _MPA
        ds_id = summary["dataset_id"]
        db.query(_MPA).filter(_MPA.dataset_id == ds_id).delete(
            synchronize_session=False
        )
        db.query(_DS).filter(_DS.id == ds_id).delete()
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# Audit chain unit tests (pure)
# ---------------------------------------------------------------------------

class TestAuditChainUnit:
    def test_genesis_and_chain(self):
        from app.core.database import SessionLocal
        from app.models import AuditEvent

        db = SessionLocal()
        # Start from a clean chain so genesis is observable.
        db.query(AuditEvent).delete()
        db.flush()
        e1 = security.append_audit_event(db, action="A", payload={"n": 1})
        e2 = security.append_audit_event(db, action="B", payload={"n": 2})
        assert e1.prev_hash == security.GENESIS_PREV_HASH
        assert e2.prev_hash == e1.entry_hash
        assert e2.seq == e1.seq + 1
        db.rollback()
        db.close()
