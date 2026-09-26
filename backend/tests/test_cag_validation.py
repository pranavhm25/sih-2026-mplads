"""CAG-grounded validation tests (docs/CAG_VALIDATION.md §7).

Verifies:
  - fixture provenance (synthetic, CAGV-prefixed, never official)
  - expected pattern characteristics survive ingestion
  - detector execution against the unmodified pipeline
  - result generation (flagged / not-validatable reported honestly)
  - no fabricated real-world identifiers (report language discipline)
  - API surface (report + summary endpoints)
"""
from __future__ import annotations

import pytest

from app.data.cag_catalog import CAG_PATTERNS, CAG_SOURCES
from app.services.validation.cag_validation import (
    PROVENANCE_STATEMENT,
    build_fixture_bytes,
    run_cag_validation,
    validate_fixture_provenance,
)


@pytest.fixture(scope="module", autouse=True)
def _cleanup_cag_dataset():
    """Remove the validation dataset after this module so later test files
    (dashboard/queue integration) see the demo dataset as the latest import
    — same discipline as test_backlog.py's in-test cleanup."""
    yield
    from app.api.v1 import cag_validation as cag_api
    from app.core.database import SessionLocal
    from app.models import (
        Dataset,
        DetectionRun,
        InvestigationCase,
        Project,
        ProjectSignal,
    )

    db = SessionLocal()
    try:
        for d in db.query(Dataset).filter(Dataset.version == "cag-validation-1").all():
            pids = [pid for (pid,) in db.query(Project.id)
                    .filter(Project.dataset_id == d.id).all()]
            if pids:
                db.query(InvestigationCase).filter(
                    InvestigationCase.project_id.in_(pids)
                ).delete(synchronize_session=False)
                db.query(ProjectSignal).filter(
                    ProjectSignal.project_id.in_(pids)
                ).delete(synchronize_session=False)
                db.query(Project).filter(Project.id.in_(pids)).delete(
                    synchronize_session=False
                )
            db.query(DetectionRun).filter(
                DetectionRun.dataset_id == d.id
            ).delete(synchronize_session=False)
            db.delete(d)
        db.commit()
    finally:
        db.close()
    # Invalidate the API cache so it never references deleted datasets.
    cag_api._cache.update({"report": None, "dataset_count": None})


# ---------------------------------------------------------------------------
# Catalog integrity — every pattern must be fully traceable
# ---------------------------------------------------------------------------
class TestCatalogIntegrity:
    def test_every_pattern_has_verified_source(self):
        source_ids = {s["source_id"] for s in CAG_SOURCES}
        for p in CAG_PATTERNS:
            assert p["source_id"] in source_ids, p["pattern_id"]

    def test_every_source_is_cag_gov_in(self):
        for s in CAG_SOURCES:
            assert s["authority"] == "Comptroller and Auditor General of India"
            assert s["source_url"].startswith("https://")
            assert "cag.gov.in" in s["source_url"] or "access_note" in s

    def test_every_pattern_has_detection_info(self):
        for p in CAG_PATTERNS:
            assert p["drishti_detector"], p["pattern_id"]
            assert p["validation_method"] in (
                "SYNTHETIC_DATASET", "NOT_VALIDATABLE", "DETECTOR_UNIT",
            )
            assert p["limitations"], p["pattern_id"]

    def test_validatable_patterns_have_fixture_works(self):
        for p in CAG_PATTERNS:
            if p["validation_method"] == "SYNTHETIC_DATASET":
                assert p["fixture_work_ids"], p["pattern_id"]
                assert p["drishti_signal_type"], p["pattern_id"]


# ---------------------------------------------------------------------------
# Fixture provenance — synthetic, labelled, never official
# ---------------------------------------------------------------------------
class TestFixtureProvenance:
    def test_all_work_ids_cagv_prefixed(self):
        """Fixture rows carry a namespace that cannot collide with real
        work IDs — no fabricated real-world identifiers."""
        raw = build_fixture_bytes().decode("utf-8")
        lines = raw.strip().splitlines()
        for line in lines[1:]:
            work_id = line.split(",")[0]
            assert work_id.startswith("CAGV-"), work_id

    def test_fixture_has_all_required_columns(self):
        raw = build_fixture_bytes().decode("utf-8")
        header = raw.splitlines()[0]
        for col in ("Work ID", "Work Name", "State", "District",
                    "Sanctioned Amount", "Sanction Date"):
            assert col in header, col

    def test_imported_dataset_provenance(self, seeded_db):
        """After a validation run the dataset must be flagged synthetic and
        carry the synthetic_cag_pattern provenance marker."""
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            report = run_cag_validation(db)
            prov = validate_fixture_provenance(db, report["summary"]["dataset_id"])
            assert prov["exists"] is True
            assert prov["is_synthetic"] is True
            assert prov["source_type_matches_declaration"] is True
            assert prov["source_label_carries_cag_marker"] is True
            assert prov["work_ids_all_cagv_prefixed"] is True
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Detector execution — the unmodified pipeline must run and flag patterns
# ---------------------------------------------------------------------------
class TestDetectorExecution:
    @pytest.fixture(scope="class")
    def cag_report(self, seeded_db):
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            return run_cag_validation(db)
        finally:
            db.close()

    def test_pipeline_completes(self, cag_report):
        assert cag_report["summary"]["detection_run_status"] == "COMPLETED"

    def test_fixture_rows_imported(self, cag_report):
        # 6 pattern rows + 11 baseline rows in the fixture CSV.
        assert cag_report["summary"]["rows_imported"] == 17

    def test_inadmissible_work_flagged_compliance(self, cag_report):
        """CAG-PATTERN-001: prohibited-category work → COMPLIANCE signal."""
        r = next(r for r in cag_report["results"]
                 if r["pattern_id"] == "CAG-PATTERN-001")
        assert r["result"] == "FLAGGED"
        sigs = r["observed_signals"][0]["signals"]
        assert any(s["signal_type"] == "COMPLIANCE" for s in sigs)
        # Evidence carries the guideline citation (existing behavior preserved)
        assert any("guideline" in (s["explanation"] or "").lower() for s in sigs)

    def test_stalled_work_flagged_delay(self, cag_report):
        """CAG-PATTERN-003: long-elapsed low-progress work → DELAY signal."""
        r = next(r for r in cag_report["results"]
                 if r["pattern_id"] == "CAG-PATTERN-003")
        assert r["result"] == "FLAGGED"
        sigs = r["observed_signals"][0]["signals"]
        assert any(s["signal_type"] == "DELAY" for s in sigs)

    def test_progress_mismatch_flagged(self, cag_report):
        """CAG-PATTERN-004: fin 82 / phys 20 → FIN_PHYS_GAP signal."""
        r = next(r for r in cag_report["results"]
                 if r["pattern_id"] == "CAG-PATTERN-004")
        assert r["result"] == "FLAGGED"
        sigs = r["observed_signals"][0]["signals"]
        assert any(s["signal_type"] == "FIN_PHYS_GAP" for s in sigs)

    def test_duplicate_signature_flagged(self, cag_report):
        """CAG-PATTERN-007: near-identical pair → DUPLICATE candidates."""
        r = next(r for r in cag_report["results"]
                 if r["pattern_id"] == "CAG-PATTERN-007")
        assert r["result"] == "FLAGGED"
        pair_works = r["work_ids"]
        for wid in pair_works:
            entry = next(o for o in r["observed_signals"]
                         if o["work_id"] == wid)
            assert any(s["signal_type"] == "DUPLICATE"
                       for s in entry["signals"]), wid

    def test_spend_vs_progress_profile(self, cag_report):
        """CAG-PATTERN-006: statistical profile may be flagged by ML or
        converge via other signals — report honestly either way."""
        r = next(r for r in cag_report["results"]
                 if r["pattern_id"] == "CAG-PATTERN-006")
        assert r["result"] in ("FLAGGED", "PARTIAL", "MISSED")
        entry = r["observed_signals"][0]
        # evidence rows exist for whatever signals fired — no fabrication
        assert entry["evidence_rows"] >= 0

    def test_not_validatable_patterns_reported_honestly(self, cag_report):
        """Patterns requiring unavailable data are marked NOT_VALIDATABLE,
        never faked with synthetic stand-ins presented as validation."""
        for pid in ("CAG-PATTERN-002", "CAG-PATTERN-005", "CAG-PATTERN-009"):
            r = next(r for r in cag_report["results"] if r["pattern_id"] == pid)
            assert r["result"] == "NOT_VALIDATABLE", pid
            assert r["flagged"] is None
            assert r["reason"], pid

    def test_summary_counts_consistent(self, cag_report):
        counts = cag_report["summary"]
        assert counts["patterns_total"] == len(CAG_PATTERNS)
        total = (counts["FLAGGED"] + counts["PARTIAL"] + counts["MISSED"]
                 + counts["NOT_VALIDATABLE"])
        assert total == counts["patterns_total"]

    def test_flagged_works_enter_queue(self, cag_report):
        """Works whose expected signal fired must reach MEDIUM+ priority —
        i.e. the case would enter the investigation queue."""
        queue = cag_report["queue_entry_check"]["by_work_id"]
        for pid in ("CAG-PATTERN-001", "CAG-PATTERN-003", "CAG-PATTERN-004",
                    "CAG-PATTERN-007"):
            r = next(x for x in cag_report["results"] if x["pattern_id"] == pid)
            for wid in r["work_ids"]:
                assert queue[wid]["enters_queue"] is True, (pid, wid)


# ---------------------------------------------------------------------------
# Language discipline — no claim of detecting real CAG cases
# ---------------------------------------------------------------------------
class TestReportLanguageDiscipline:
    @pytest.fixture(scope="class")
    def cag_report(self, seeded_db):
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            return run_cag_validation(db)
        finally:
            db.close()

    def test_report_carries_provenance_statement(self, cag_report):
        assert cag_report["data_limitations"]["provenance_statement"] == (
            PROVENANCE_STATEMENT
        )
        assert "not the original CAG dataset" in PROVENANCE_STATEMENT
        assert "does not claim that Drishti detected any real CAG case" in (
            PROVENANCE_STATEMENT
        )

    def test_disclaimer_present(self, cag_report):
        assert "not original CAG case data" in cag_report["disclaimer"]

    def test_no_accuracy_against_real_data_claimed(self, cag_report):
        assert cag_report["data_limitations"]["underlying_records_available"] is False
        assert "No accuracy metrics" in cag_report["data_limitations"]["note"]

    def test_report_never_says_drishti_detected_cag_case(self, cag_report):
        """The word 'detected' must never bind Drishti to a real CAG case."""
        blob = str(cag_report).lower()
        assert "detected a real cag case" not in blob
        assert "drishti detected the cag" not in blob

    def test_patterns_cite_verified_reports(self, cag_report):
        valid_source_ids = {s["source_id"] for s in cag_report["cag_sources"]}
        for p in cag_report["patterns"]:
            assert p["source_id"] in valid_source_ids


# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------
class TestCagValidationAPI:
    def test_report_endpoint(self, client):
        resp = client.get("/api/v1/validation/cag")
        assert resp.status_code == 200
        body = resp.json()
        assert body["meta"]["is_synthetic"] is True
        data = body["data"]
        assert data["report_version"] == "cag-validation-1"
        assert data["generated_at"]
        assert len(data["results"]) == len(CAG_PATTERNS)

    def test_summary_endpoint(self, client):
        resp = client.get("/api/v1/validation/cag/summary")
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]
        assert data["disclaimer"]
        assert data["provenance"]
        assert {"pattern_id", "result", "flagged"} <= set(data["patterns"][0])

    def test_summary_endpoint_cached_and_consistent(self, client):
        r1 = client.get("/api/v1/validation/cag/summary").json()["data"]
        r2 = client.get("/api/v1/validation/cag/summary").json()["data"]
        assert r1["summary"] == r2["summary"]
