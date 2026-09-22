"""Integration tests: ingestion, quality, pipeline, API surfaces."""
from __future__ import annotations

from datetime import date

from app.core import constants as C
from app.data.demo_data import FLAGSHIP_WORK_ID, build_demo_rows
from app.services.ingestion.ingestion import ingest_rows, map_columns, parse_numeric


class TestIngestion:
    def test_column_mapping_aliases(self):
        row = {"Work ID": "X1", "District": "Pune", "Sanctioned Cost": "10"}
        mapped = map_columns(row)
        assert mapped["work_id"] == "X1"
        assert mapped["district"] == "Pune"
        assert mapped["sanctioned_cost"] == "10"

    def test_parse_numeric_formats(self):
        assert float(parse_numeric("24.2L")) == 2420000
        assert float(parse_numeric("1.5CR")) == 15000000
        assert float(parse_numeric("₹1,000")) == 1000
        assert parse_numeric("n/a") is None

    def test_demo_rows_build(self):
        rows = build_demo_rows()
        assert any(r["work_id"] == FLAGSHIP_WORK_ID for r in rows)
        assert len(rows) >= 60

    def test_ingest_rejects_missing_mandatory(self, seeded_db):
        """A row missing mandatory fields must be rejected and counted."""
        from app.models import Dataset
        ds = ingest_rows(
            seeded_db,
            [{"work_id": "T-1", "state": "X", "description": "d",
              "estimated_cost": "1", "sanctioned_cost": "1",
              "financial_progress": "10", "physical_progress": "10"}],
            name="t", source_label="t", is_synthetic=True,
        )
        assert ds.row_count == 0
        assert ds.quality_summary["rows_rejected"] == 1
        # Delete so the demo dataset remains the latest for other tests.
        seeded_db.delete(ds)
        seeded_db.commit()


class TestQualityAndDetectionOnDemo:
    def test_flagship_has_five_signals(self, seeded_db):
        from app.models import Project, ProjectSignal
        p = seeded_db.query(Project).filter(Project.work_id == FLAGSHIP_WORK_ID).first()
        assert p is not None
        types = {s.signal_type for s in p.signals if s.triggered}
        assert C.SignalType.FIN_PHYS_GAP in types
        assert C.SignalType.COST_ANOMALY in types
        assert C.SignalType.DELAY in types
        assert C.SignalType.DUPLICATE in types
        assert C.SignalType.ML_ANOMALY in types

    def test_flagship_evidence_present(self, seeded_db):
        from app.models import Project
        p = seeded_db.query(Project).filter(Project.work_id == FLAGSHIP_WORK_ID).first()
        for s in p.signals:
            if s.triggered:
                assert len(s.evidence) >= 1
                assert s.explanation

    def test_duplicate_pair_is_symmetric(self, seeded_db):
        from app.models import Project
        a = seeded_db.query(Project).filter(Project.work_id == FLAGSHIP_WORK_ID).first()
        b = seeded_db.query(Project).filter(Project.work_id == "MPL-10412").first()
        sa = [s for s in a.signals if s.signal_type == C.SignalType.DUPLICATE]
        sb = [s for s in b.signals if s.signal_type == C.SignalType.DUPLICATE]
        assert sa and sb  # both sides flagged

    def test_quality_violations_detected(self, seeded_db):
        from app.models import Project, ProjectSignal
        # MPL-10488: expenditure > sanctioned AND completion before sanction.
        p = seeded_db.query(Project).filter(Project.work_id == "MPL-10488").first()
        explanations = " ".join(s.explanation for s in p.signals)
        assert "exceeds sanctioned" in explanations
        assert "precedes sanction" in explanations
        # MPL-10489: progress > 100%
        p2 = seeded_db.query(Project).filter(Project.work_id == "MPL-10489").first()
        exp2 = " ".join(s.explanation for s in p2.signals)
        assert "above 100%" in exp2

    def test_fusion_priorities_computed(self, seeded_db):
        from app.models import Project
        from app.services.detection.fusion import compute_priorities
        projects = seeded_db.query(Project).all()
        fusion = compute_priorities(seeded_db, projects)
        flagship = [f for pid, f in fusion.items()
                    if seeded_db.get(Project, pid).work_id == FLAGSHIP_WORK_ID][0]
        assert flagship["level"] in (C.Priority.HIGH, C.Priority.CRITICAL)
        assert flagship["signal_count"] >= 5


class TestAPI:
    def test_health(self, client):
        assert client.get("/api/health").status_code == 200

    def test_dashboard_summary(self, client):
        r = client.get("/api/v1/dashboard/summary")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["total_works"] >= 60
        assert set(d["risk_distribution"]) == {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        assert r.json()["meta"]["is_synthetic"] is True  # demo data labelled

    def test_queue_filters_by_signal(self, client):
        r = client.get("/api/v1/projects", params={"signal_type": "FIN_PHYS_GAP"})
        assert r.status_code == 200
        for item in r.json()["data"]["items"]:
            assert "FIN_PHYS_GAP" in item["primary_signals"]

    def test_queue_filter_priority(self, client):
        r = client.get("/api/v1/projects", params={"priority": "CRITICAL"})
        assert r.status_code == 200
        for item in r.json()["data"]["items"]:
            assert item["priority"]["level"] == "CRITICAL"

    def test_project_detail_contract(self, client):
        q = client.get("/api/v1/projects").json()["data"]["items"]
        pid = q[0]["id"]
        r = client.get(f"/api/v1/projects/{pid}")
        assert r.status_code == 200
        d = r.json()["data"]
        for key in ("signals", "peers", "related", "metrics", "why_flagged"):
            assert key in d

    def test_project_404(self, client):
        r = client.get("/api/v1/projects/nope")
        assert r.status_code == 404
        assert "error" in r.json() or "detail" in r.json()

    def test_case_lifecycle(self, client):
        q = client.get("/api/v1/projects").json()["data"]["items"]
        target = next(i for i in q if i["case_status"] is None)
        officers = client.get("/api/v1/officers").json()["data"]
        r = client.post("/api/v1/cases", json={
            "project_id": target["id"],
            "assigned_officer_id": officers[0]["id"],
            "note": "Opening investigation.",
        })
        assert r.status_code == 201
        case = r.json()["data"]
        assert case["status"] == "OPEN"
        assert case["case_number"].startswith("DRSHY-C-")
        assert len(case["events"]) >= 1

        # Duplicate active case rejected
        r2 = client.post("/api/v1/cases", json={"project_id": target["id"]})
        assert r2.status_code == 409

        # Valid transition
        r3 = client.patch(f"/api/v1/cases/{case['id']}",
                          json={"status": "UNDER_REVIEW"})
        assert r3.status_code == 200
        assert r3.json()["data"]["status"] == "UNDER_REVIEW"

        # Invalid transition rejected
        r4 = client.patch(f"/api/v1/cases/{case['id']}", json={"status": "OPEN"})
        assert r4.status_code == 409

        # Resolve requires classification
        r5 = client.patch(f"/api/v1/cases/{case['id']}", json={"status": "RESOLVED"})
        assert r5.status_code in (400, 409)

    def test_feedback_endpoint(self, client):
        q = client.get("/api/v1/projects").json()["data"]["items"]
        target = next(i for i in q if i["case_status"] is None)
        officers = client.get("/api/v1/officers").json()["data"]
        case = client.post("/api/v1/cases", json={"project_id": target["id"]}).json()["data"]
        client.patch(f"/api/v1/cases/{case['id']}", json={"status": "UNDER_REVIEW"})
        r = client.post(f"/api/v1/cases/{case['id']}/feedback", json={
            "resolution_type": "FALSE_POSITIVE",
            "officer_id": officers[0]["id"],
            "summary": "Verified on site; values correct.",
        })
        assert r.status_code == 200
        assert r.json()["data"]["resolution_type"] == "FALSE_POSITIVE"

    def test_report_generation_and_download(self, client):
        q = client.get("/api/v1/projects").json()["data"]["items"]
        target = next(i for i in q if i["case_status"] is None)
        case = client.post("/api/v1/cases", json={"project_id": target["id"]}).json()["data"]
        r = client.post(f"/api/v1/cases/{case['id']}/report")
        assert r.status_code == 201
        report = r.json()["data"]["report"]
        assert report["report_number"].startswith("DRSHY-R-")
        dl = client.get(f"/api/v1/reports/{report['id']}/download")
        assert dl.status_code == 200
        assert dl.headers["content-type"] == "application/pdf"
        assert dl.content[:4] == b"%PDF"

    def test_csv_import_roundtrip(self, client):
        csv_content = (
            "work_id,state,district,description,estimated_cost,sanctioned_cost,"
            "expenditure,financial_progress,physical_progress,status\n"
            "TST-1,Karnataka,Mysuru,Construction of school library,10L,10L,5L,50,45,In Progress\n"
        )
        r = client.post("/api/v1/datasets/import",
                        files={"file": ("demo_synthetic.csv", csv_content, "text/csv")})
        assert r.status_code == 200
        assert r.json()["data"]["row_count"] == 1
        assert r.json()["meta"]["is_synthetic"] is True
