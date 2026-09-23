"""Prompt-3 tests: parsers, normalizers, source registry, validation,
partial validity, provenance, hashing and the dataset APIs."""
from __future__ import annotations

import io
from decimal import Decimal

import pytest

from app.core import constants as C
from app.services.ingestion.normalizers import (
    normalize_date,
    normalize_int,
    normalize_monetary,
    normalize_percentage,
    normalize_text,
    to_rupees,
)
from app.services.ingestion.parsers import FileParseError, parse_file
from app.services.ingestion.registry import (
    LS_ALLOCATION,
    RS_ALLOCATION,
    detect_schema,
    map_headers,
)
from app.services.ingestion.validation import (
    normalize_mp_allocation_row,
    validate_mp_allocation_rows,
)

LS_HEADERS = ["Sr. No.", "State", "Hon'ble Members of Parliament",
              "Constituency", "Allocated Amount (₹)"]
RS_HEADERS = ["Sr. No.", "State", "Hon'ble Members of Parliament",
              "Elected/Nominated", "Allocated Amount (₹)"]
LS_COLMAP = map_headers(LS_ALLOCATION, LS_HEADERS)
RS_COLMAP = map_headers(RS_ALLOCATION, RS_HEADERS)


@pytest.fixture()
def clean_imports(client):
    """Remove non-demo datasets after each import test.

    The duplicate-upload guard is content-hash based and the test session
    shares one database, so each test must start without prior imports.
    """
    yield
    from app.core.database import SessionLocal
    from app.models import (
        CaseEvent, CaseEvidence, CaseNote, Dataset, DetectionRun,
        InvestigationCase, MPAllocationRecord, Project, ProjectMetrics,
        ProjectPeer, ProjectSignal, RelatedProject, Report, SchemeAggregate,
        SignalEvidence, ValidationIssue,
    )

    db = SessionLocal()
    try:
        keep_ids = [d.id for d in db.query(Dataset).filter(
            Dataset.version == "demo-01").all()]
        doomed = [d.id for d in db.query(Dataset).all() if d.id not in keep_ids]
        if not doomed:
            return
        pids = [p.id for p in db.query(Project).filter(
            Project.dataset_id.in_(doomed)).all()]
        if pids:
            db.query(RelatedProject).filter(
                RelatedProject.project_id.in_(pids)
            ).delete(synchronize_session=False)
            db.query(ProjectPeer).filter(ProjectPeer.project_id.in_(pids)).delete(synchronize_session=False)
            case_ids = [c.id for c in db.query(InvestigationCase).filter(
                InvestigationCase.project_id.in_(pids)).all()]
            if case_ids:
                db.query(Report).filter(Report.case_id.in_(case_ids)).delete(synchronize_session=False)
                db.query(CaseEvent).filter(CaseEvent.case_id.in_(case_ids)).delete(synchronize_session=False)
                db.query(CaseNote).filter(CaseNote.case_id.in_(case_ids)).delete(synchronize_session=False)
                db.query(CaseEvidence).filter(CaseEvidence.case_id.in_(case_ids)).delete(synchronize_session=False)
                db.query(InvestigationCase).filter(
                    InvestigationCase.id.in_(case_ids)).delete(synchronize_session=False)
            sig_ids = [s.id for s in db.query(ProjectSignal).filter(
                ProjectSignal.project_id.in_(pids)).all()]
            if sig_ids:
                db.query(SignalEvidence).filter(SignalEvidence.signal_id.in_(sig_ids)).delete(synchronize_session=False)
            db.query(ProjectSignal).filter(ProjectSignal.project_id.in_(pids)).delete(synchronize_session=False)
            db.query(ProjectMetrics).filter(ProjectMetrics.project_id.in_(pids)).delete(synchronize_session=False)
            db.query(Project).filter(Project.id.in_(pids)).delete(synchronize_session=False)
        db.query(DetectionRun).filter(DetectionRun.dataset_id.in_(doomed)).delete(synchronize_session=False)
        db.query(ValidationIssue).filter(ValidationIssue.dataset_id.in_(doomed)).delete(synchronize_session=False)
        db.query(MPAllocationRecord).filter(MPAllocationRecord.dataset_id.in_(doomed)).delete(synchronize_session=False)
        db.query(SchemeAggregate).filter(SchemeAggregate.dataset_id.in_(doomed)).delete(synchronize_session=False)
        db.query(Dataset).filter(Dataset.id.in_(doomed)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Normalization (§18–22, §37)
# ---------------------------------------------------------------------------


class TestMonetaryNormalization:
    def test_crore_display_value(self):
        value, unit = normalize_monetary("₹ 4,324.08 Crore")
        assert value == Decimal("4324.08")
        assert unit == "CRORE"

    def test_crore_abbreviated(self):
        value, unit = normalize_monetary("1.5CR")
        assert value == Decimal("1.5")
        assert unit == "CRORE"

    def test_raw_rupees(self):
        value, unit = normalize_monetary("73421449")
        assert value == Decimal("73421449")
        assert unit == "RUPEE"

    def test_indian_comma_grouping(self):
        value, unit = normalize_monetary("1,09,747")
        assert value == Decimal("109747")
        assert unit == "RUPEE"

    def test_lakh_suffix(self):
        value, unit = normalize_monetary("24.2L")
        assert value == Decimal("24.2")
        assert unit == "LAKH"

    def test_rupee_symbol_only(self):
        value, unit = normalize_monetary("₹1,000")
        assert value == Decimal("1000")
        assert unit == "RUPEE"

    def test_null_tokens(self):
        value, unit = normalize_monetary("N/A")
        assert value is None

    def test_to_rupees_conversion(self):
        assert to_rupees(Decimal("4324.08"), "CRORE") == Decimal("43240800000.00")
        assert to_rupees(Decimal("24.2"), "LAKH") == Decimal("2420000.00")
        assert to_rupees(Decimal("500"), "RUPEE") == Decimal("500")
        assert to_rupees(None, "CRORE") is None

    def test_units_are_never_silently_merged(self):
        """A Crore figure and a raw-rupee figure must not normalize alike."""
        crore_val, crore_unit = normalize_monetary("₹ 500 Crore")
        rupee_val, rupee_unit = normalize_monetary("500")
        assert crore_unit != rupee_unit
        assert to_rupees(crore_val, crore_unit) != rupee_val


class TestOtherNormalizers:
    def test_int_counts(self):
        assert normalize_int("No. 109747") == 109747
        assert normalize_int("1,234") == 1234
        assert normalize_int("42") == 42
        assert normalize_int("n/a") is None
        assert normalize_int("abc") is None

    def test_text(self):
        assert normalize_text("  Karnataka  ") == "Karnataka"
        assert normalize_text("Bengaluru    South") == "Bengaluru South"
        assert normalize_text("-") is None
        assert normalize_text("") is None
        assert normalize_text(None) is None

    def test_percentage(self):
        assert normalize_percentage("84%") == Decimal("84")
        assert normalize_percentage("84") == Decimal("84")
        assert normalize_percentage("84.0") == Decimal("84.0")
        assert normalize_percentage("108%") == Decimal("108")  # never clamped

    def test_dates(self):
        assert str(normalize_date("2025-04-10")) == "2025-04-10"
        assert str(normalize_date("10-04-2025")) == "2025-04-10"
        assert normalize_date("not a date") is None


# ---------------------------------------------------------------------------
# File parsing (§10)
# ---------------------------------------------------------------------------


class TestParsers:
    def test_valid_csv(self):
        raw = b"A,B\n1,2\n3,4\n"
        parsed = parse_file(raw, "file.csv")
        assert parsed.headers == ["A", "B"]
        assert parsed.row_count == 2
        assert parsed.file_kind == "CSV"

    def test_valid_xlsx(self):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Sr. No.", "State"])
        ws.append([1, "Karnataka"])
        buf = io.BytesIO()
        wb.save(buf)
        parsed = parse_file(buf.getvalue(), "allocation.xlsx")
        assert parsed.headers == ["Sr. No.", "State"]
        assert parsed.rows[0]["State"] == "Karnataka"

    def test_empty_file(self):
        with pytest.raises(FileParseError) as exc:
            parse_file(b"", "empty.csv")
        assert exc.value.code == "EMPTY_FILE"

    def test_malformed_csv(self):
        # Not really CSV-parseable as a table with a header
        with pytest.raises(FileParseError) as exc:
            parse_file(b"\xff\xfe\xfa", "bad.csv")
        assert exc.value.code == "INVALID_FILE"

    def test_unsupported_extension(self):
        with pytest.raises(FileParseError) as exc:
            parse_file(b"data", "virus.exe")
        assert exc.value.code == "UNSUPPORTED_FILE"

    def test_no_data_rows(self):
        with pytest.raises(FileParseError) as exc:
            parse_file(b"A,B\n", "headeronly.csv")
        assert exc.value.code == "EMPTY_FILE"


# ---------------------------------------------------------------------------
# Schema registry / mapping (§13, §14)
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_detect_ls_allocation(self):
        schema, colmap = detect_schema(LS_HEADERS)
        assert schema is not None and schema.schema_id == "ls_allocation_v1"
        assert colmap["Allocated Amount (₹)"] == "allocated_amount"
        assert colmap["Hon'ble Members of Parliament"] == "mp_name"
        assert colmap["Constituency"] == "constituency"

    def test_detect_rs_allocation(self):
        schema, colmap = detect_schema(RS_HEADERS)
        assert schema is not None and schema.schema_id == "rs_allocation_v1"
        assert colmap["Elected/Nominated"] == "elected_nominated"

    def test_detect_aggregate(self):
        headers = ["House", "Allocated Limit for Hon'ble MPs",
                   "Works Recommended", "Works Sanctioned", "Works Completed",
                   "Expenditure on Completed and Ongoing Works"]
        schema, colmap = detect_schema(headers)
        assert schema is not None and schema.dataset_type == C.DatasetType.SCHEME_AGGREGATE

    def test_unknown_schema_rejected(self):
        schema, _ = detect_schema(["foo", "bar", "baz"])
        assert schema is None

    def test_mapping_preserves_source_terminology(self):
        schema, _ = detect_schema(LS_HEADERS)
        colmap = map_headers(schema, LS_HEADERS)
        assert set(colmap) == set(LS_HEADERS)  # source headers kept verbatim


# ---------------------------------------------------------------------------
# MP allocation validation (§24)
# ---------------------------------------------------------------------------


def _norm(rows, colmap=LS_COLMAP):
    return [normalize_mp_allocation_row(r, colmap, i)
            for i, r in enumerate(rows, start=1)]


class TestMPAllocationValidation:
    def _rows(self):
        return [
            {"Sr. No.": "1", "State": "Karnataka",
             "Hon'ble Members of Parliament": "A", "Constituency": "X",
             "Allocated Amount (₹)": "73421449"},
            {"Sr. No.": "2", "State": "",
             "Hon'ble Members of Parliament": "B", "Constituency": "Y",
             "Allocated Amount (₹)": "50000000"},
            {"Sr. No.": "3", "State": "Maharashtra",
             "Hon'ble Members of Parliament": "", "Constituency": "Z",
             "Allocated Amount (₹)": "50000000"},
            {"Sr. No.": "4", "State": "Maharashtra",
             "Hon'ble Members of Parliament": "C", "Constituency": "Z",
             "Allocated Amount (₹)": "not-a-number"},
            {"Sr. No.": "5", "State": "Maharashtra",
             "Hon'ble Members of Parliament": "D", "Constituency": "Z",
             "Allocated Amount (₹)": "-500000"},
        ]

    def test_missing_state_is_error(self):
        report = validate_mp_allocation_rows(_norm(self._rows()))
        rules = {(i.rule, i.severity) for i in report.issues}
        assert ("missing_state", C.IssueSeverity.ERROR) in rules

    def test_missing_mp_name_is_error(self):
        report = validate_mp_allocation_rows(_norm(self._rows()))
        rules = {(i.rule, i.severity) for i in report.issues}
        assert ("missing_mp_name", C.IssueSeverity.ERROR) in rules

    def test_invalid_and_negative_amounts_are_errors(self):
        report = validate_mp_allocation_rows(_norm(self._rows()))
        rules = {i.rule for i in report.issues}
        assert "invalid_amount" in rules
        assert "negative_amount" in rules

    def test_duplicate_serial_is_warning(self):
        rows = [
            {"Sr. No.": "1", "State": "A", "Hon'ble Members of Parliament": "X",
             "Allocated Amount (₹)": "10000000"},
            {"Sr. No.": "1", "State": "A", "Hon'ble Members of Parliament": "Y",
             "Allocated Amount (₹)": "10000000"},
        ]
        report = validate_mp_allocation_rows(_norm(rows))
        dupes = [i for i in report.issues if i.rule == "duplicate_serial"]
        assert dupes and dupes[0].severity == C.IssueSeverity.WARNING
        assert report.valid_rows == 2  # warnings never exclude rows

    def test_duplicate_mp_record_flagged_not_deleted(self):
        rows = [
            {"Sr. No.": "1", "State": "A", "Hon'ble Members of Parliament": "X",
             "Allocated Amount (₹)": "10000000"},
            {"Sr. No.": "2", "State": "A", "Hon'ble Members of Parliament": "X",
             "Allocated Amount (₹)": "10000000"},
        ]
        report = validate_mp_allocation_rows(_norm(rows))
        assert any(i.rule == "duplicate_mp_record" for i in report.issues)
        assert report.valid_rows == 2

    def test_house_specific_fields(self):
        """RS rows keep constituency NULL; LS rows keep elected_nominated NULL."""
        rs_row = {"Sr. No.": "1", "State": "Maharashtra",
                  "Hon'ble Members of Parliament": "P", "Elected/Nominated": "Nominated",
                  "Allocated Amount (₹)": "97500000"}
        norm = normalize_mp_allocation_row(rs_row, RS_COLMAP, 1)
        assert norm["elected_nominated"] == "Nominated"
        assert norm["constituency"] is None  # never invented

    def test_whitespace_is_normalized_on_ingest(self, client):
        """Text normalization applies through the full pipeline (§21)."""
        csv_content = (
            "Sr. No.,State,Hon'ble Members of Parliament,Constituency,Allocated Amount (₹)\n"
            "1,  Karnataka  ,A.   Ramesh,Bengaluru   South,50000000\n"
        ).encode("utf-8")
        r = client.post(
            "/api/v1/datasets/import",
            files={"file": ("ws.csv", csv_content, "text/csv")},
        )
        ds_id = r.json()["data"]["dataset_id"]
        rec = client.get(f"/api/v1/datasets/{ds_id}/records").json()["data"]["records"][0]
        assert rec["state"] == "Karnataka"
        assert rec["mp_name"] == "A. Ramesh"
        assert rec["constituency"] == "Bengaluru South"


# ---------------------------------------------------------------------------
# Quality status scale (§28, §29)
# ---------------------------------------------------------------------------


def test_aggregate_consistency_warning_only():
    """Completed > sanctioned is an aggregate consistency issue (§25), a
    WARNING that degrades status without excluding the row."""
    from app.services.ingestion.validation import (
        normalize_aggregate_row, validate_aggregate_rows,
    )
    headers = {"House": "House",
               "Allocated Limit for Hon'ble MPs": "allocated_limit",
               "Works Recommended": "works_recommended",
               "Works Sanctioned": "works_sanctioned",
               "Works Completed": "works_completed",
               "Expenditure on Completed and Ongoing Works":
                   "expenditure_completed_and_ongoing"}
    from app.services.ingestion.registry import SCHEME_AGGREGATE, map_headers

    agg_headers = ["House", "Allocated Limit for Hon'ble MPs",
                   "Works Recommended", "Works Sanctioned", "Works Completed",
                   "Expenditure on Completed and Ongoing Works"]
    colmap = map_headers(SCHEME_AGGREGATE, agg_headers)
    rows = [{
        "House": "Test House",
        "Allocated Limit for Hon'ble MPs": "₹ 500 Crore",
        "Works Recommended": "1200",
        "Works Sanctioned": "900",
        "Works Completed": "1200",
        "Expenditure on Completed and Ongoing Works": "₹ 210 Crore",
    }]
    normalized = [normalize_aggregate_row(r, colmap, 1) for r in rows]
    report = validate_aggregate_rows(normalized)
    issues = [i for i in report.issues if i.rule == "aggregate_consistency_issue"]
    assert issues and issues[0].severity == C.IssueSeverity.WARNING
    assert report.valid_rows == 1


def test_aggregate_clean_rows_good():
    from app.services.ingestion.registry import SCHEME_AGGREGATE, map_headers
    from app.services.ingestion.validation import (
        normalize_aggregate_row, validate_aggregate_rows,
    )
    agg_headers = ["House", "Allocated Limit for Hon'ble MPs",
                   "Works Recommended", "Works Sanctioned", "Works Completed",
                   "Expenditure on Completed and Ongoing Works"]
    colmap = map_headers(SCHEME_AGGREGATE, agg_headers)
    rows = [{
        "House": "Lok Sabha",
        "Allocated Limit for Hon'ble MPs": "₹ 8,341.87 Crore",
        "Works Recommended": "109747",
        "Works Sanctioned": "91350",
        "Works Completed": "70218",
        "Expenditure on Completed and Ongoing Works": "₹ 4,324.08 Crore",
    }]
    normalized = [normalize_aggregate_row(r, colmap, 1) for r in rows]
    report = validate_aggregate_rows(normalized)
    assert report.issues == []
    assert report.quality_status() == "GOOD"


class TestQualityScale:
    def test_good(self):
        from app.services.ingestion.validation import ValidationReport
        r = ValidationReport(10)
        assert r.quality_status() == "GOOD"

    def test_acceptable(self):
        from app.services.ingestion.validation import Issue, ValidationReport
        r = ValidationReport(100)
        for n in (1, 2):
            r.add(Issue(n, "x", "invalid_amount", C.IssueSeverity.ERROR, "m", "v"))
        assert r.quality_status() == "ACCEPTABLE"

    def test_degraded(self):
        from app.services.ingestion.validation import Issue, ValidationReport
        r = ValidationReport(100)
        for n in range(1, 11):  # 10% error rate — exactly at the threshold
            r.add(Issue(n, "x", "invalid_amount", C.IssueSeverity.ERROR, "m", "v"))
        assert r.quality_status() == "DEGRADED"

    def test_failed(self):
        from app.services.ingestion.validation import Issue, ValidationReport
        r = ValidationReport(100)
        for n in range(1, 21):  # 20% error rate
            r.add(Issue(n, "x", "invalid_amount", C.IssueSeverity.ERROR, "m", "v"))
        assert r.quality_status() == "FAILED"

    def test_reasons_are_explainable(self):
        from app.services.ingestion.validation import Issue, ValidationReport
        r = ValidationReport(10)
        r.add(Issue(1, "mp_name", "missing_mp_name", C.IssueSeverity.ERROR, "m", None))
        reasons = r.reasons()
        assert reasons == ["1 record with missing mp name"]


# ---------------------------------------------------------------------------
# Import API — partial validity, provenance, hashing (§12, §27, §43)
# ---------------------------------------------------------------------------


class TestImportAPI:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_imports):
        yield

    @staticmethod
    def _import(client, path="app/data/fixtures/mp_allocation_ls.csv"):
        with open(path, "rb") as fh:
            return client.post(
                "/api/v1/datasets/import",
                files={"file": ("ls_alloc.csv", fh.read(), "text/csv")},
            )

    def test_import_response_contract(self, client):
        r = self._import(client)
        assert r.status_code == 200
        d = r.json()["data"]
        for key in ("dataset_id", "dataset_type", "source_type", "status",
                    "row_count", "valid_rows", "warning_rows", "error_rows",
                    "quality_status", "is_synthetic", "file_hash"):
            assert key in d
        assert d["dataset_type"] == "MP_ALLOCATION"
        assert d["status"] == "IMPORTED"
        assert d["row_count"] == 10  # 14 source rows − 4 error rows

    def test_partial_validity(self, client):
        d = self._import(client).json()["data"]
        assert d["error_rows"] == 4
        assert d["valid_rows"] == 10
        assert d["row_count"] == 10
        # Issues preserved for every rejected row (§27)
        q = client.get(f"/api/v1/datasets/{d['dataset_id']}/quality").json()["data"]
        assert q["issue_count"] >= 4
        severities = {i["severity"] for i in q["issues"]}
        assert "ERROR" in severities

    def test_official_provenance(self, client):
        d = self._import(client).json()["data"]
        assert d["is_synthetic"] is False
        assert d["source_type"] == "OFFICIAL_FILE_UPLOAD"
        ds_list = client.get("/api/v1/datasets").json()["data"]["items"]
        row = next(x for x in ds_list if x["id"] == d["dataset_id"])
        assert row["source_label"] == "MPLADS e-SAKSHI"
        assert row["file_hash"]
        assert len(row["file_hash"]) == 64  # sha256 hex

    def test_duplicate_upload_rejected(self, client):
        self._import(client)
        r2 = self._import(client)
        assert r2.status_code == 400
        assert r2.json()["error"]["code"] == "DUPLICATE_DATASET"

    def test_synthetic_filename_flagged(self, client):
        with open("app/data/fixtures/mp_allocation_rs.csv", "rb") as fh:
            raw = fh.read()
        r = client.post(
            "/api/v1/datasets/import",
            files={"file": ("demo_synthetic_alloc.csv", raw, "text/csv")},
        )
        assert r.json()["data"]["is_synthetic"] is True
        assert r.json()["data"]["source_type"] == "SYNTHETIC_FIXTURE"

    def test_forced_dataset_type(self, client):
        with open("app/data/fixtures/mp_allocation_rs.csv", "rb") as fh:
            raw = fh.read()
        r = client.post(
            "/api/v1/datasets/import?dataset_type=MP_ALLOCATION",
            files={"file": ("alloc_rs.csv", raw, "text/csv")},
        )
        assert r.status_code == 200
        assert r.json()["data"]["dataset_type"] == "MP_ALLOCATION"

    def test_invalid_dataset_type_rejected(self, client):
        with open("app/data/fixtures/mp_allocation_rs.csv", "rb") as fh:
            raw = fh.read()
        r = client.post(
            "/api/v1/datasets/import?dataset_type=NOT_A_TYPE",
            files={"file": ("alloc.csv", raw, "text/csv")},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_DATASET_TYPE"

    def test_unrecognized_schema_rejected(self, client):
        r = client.post(
            "/api/v1/datasets/import",
            files={"file": ("x.csv", b"foo,bar\n1,2\n", "text/csv")},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "INVALID_DATASET"

    def test_empty_file_rejected(self, client):
        r = client.post(
            "/api/v1/datasets/import",
            files={"file": ("x.csv", b"", "text/csv")},
        )
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "EMPTY_FILE"

    def test_xlsx_import(self, client):
        openpyxl = pytest.importorskip("openpyxl")
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(LS_HEADERS)
        ws.append([1, "Karnataka", "Test MP", "Test Constituency", 50000000])
        buf = io.BytesIO()
        wb.save(buf)
        r = client.post(
            "/api/v1/datasets/import",
            files={"file": ("ls_allocation.xlsx", buf.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["dataset_type"] == "MP_ALLOCATION"
        assert d["quality_status"] == "GOOD"
        assert d["row_count"] == 1

    def test_fixture_ingest_is_synthetic(self, client):
        r = client.post("/api/v1/datasets/fixtures/mp_allocation_ls/ingest")
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["is_synthetic"] is True
        assert d["source_type"] == "SYNTHETIC_FIXTURE"
        assert d["file_name"].startswith("mp_allocation_ls")


# ---------------------------------------------------------------------------
# Records browsing (§32, §34) + quality API (§31)
# ---------------------------------------------------------------------------


class TestRecordsAPI:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_imports):
        yield

    def _alloc_dataset(self, client) -> str:
        with open("app/data/fixtures/mp_allocation_ls.csv", "rb") as fh:
            r = client.post(
                "/api/v1/datasets/import",
                files={"file": ("ls.csv", fh.read(), "text/csv")},
            )
        return r.json()["data"]["dataset_id"]

    def test_records_are_type_safe(self, client):
        ds_id = self._alloc_dataset(client)
        r = client.get(f"/api/v1/datasets/{ds_id}/records")
        d = r.json()["data"]
        assert d["dataset_type"] == "MP_ALLOCATION"
        assert "mp_name" in d["fields"]
        assert "work_id" not in d["fields"]       # never reshaped into works
        assert "sanctioned_cost" not in d["fields"]
        assert d["records"][0]["allocated_amount"] == 73421449.0
        assert d["records"][0]["constituency"] == "Bengaluru South"
        assert d["records"][0]["elected_nominated"] is None  # LS has no such column

    def test_error_rows_not_in_records_but_in_quality(self, client):
        ds_id = self._alloc_dataset(client)
        records = client.get(f"/api/v1/datasets/{ds_id}/records").json()["data"]
        q = client.get(f"/api/v1/datasets/{ds_id}/quality").json()["data"]
        amounts = [r["allocated_amount"] for r in records["records"]]
        assert None not in amounts and -500000 not in amounts  # error rows excluded
        assert q["error_rows"] == 4
        rules = {i["rule"] for i in q["issues"]}
        assert "negative_amount" in rules
        assert "missing_mp_name" in rules

    def test_quality_report_shape(self, client):
        ds_id = self._alloc_dataset(client)
        q = client.get(f"/api/v1/datasets/{ds_id}/quality").json()["data"]
        for key in ("quality_status", "total_rows", "valid_rows", "warning_rows",
                    "error_rows", "reasons", "issues", "missing_field_counts",
                    "invalid_field_counts", "duplicate_counts"):
            assert key in q
        assert q["total_rows"] == 14
        assert q["quality_status"] == "FAILED"

    def test_pagination(self, client):
        ds_id = self._alloc_dataset(client)
        r = client.get(f"/api/v1/datasets/{ds_id}/records?limit=5&offset=0")
        d = r.json()["data"]
        assert len(d["records"]) == 5
        assert d["total"] == 10

    def test_aggregate_records_preserve_units(self, client):
        r = client.post("/api/v1/datasets/fixtures/scheme_aggregate/ingest")
        ds_id = r.json()["data"]["dataset_id"]
        d = client.get(f"/api/v1/datasets/{ds_id}/records").json()["data"]
        first = d["records"][0]
        assert first["house"] == "Lok Sabha"
        assert first["monetary_unit"] == "CRORE"
        assert first["allocated_limit"] == 8341.87
        assert first["works_recommended"] == 109747

    def test_work_level_fixture_runs_detection(self, client):
        r = client.post("/api/v1/datasets/fixtures/work_level/ingest")
        d = r.json()["data"]
        assert d["dataset_type"] == "WORK_LEVEL"
        assert d["row_count"] == 8
        # Detection pipeline ran on import (work-level only)
        runs = client.get("/api/v1/detection/runs").json()["data"]
        assert len(runs) >= 1
        # Queue now reflects the work-level fixture
        queue = client.get("/api/v1/projects").json()["data"]
        assert queue["total"] == 8


# ---------------------------------------------------------------------------
# Provenance separation (§8, §40)
# ---------------------------------------------------------------------------


class TestProvenanceSeparation:
    @pytest.fixture(autouse=True)
    def _clean(self, clean_imports):
        yield

    def test_official_and_synthetic_never_confused(self, client):
        # Official upload
        with open("app/data/fixtures/mp_allocation_rs.csv", "rb") as fh:
            official = client.post(
                "/api/v1/datasets/import",
                files={"file": ("alloc.csv", fh.read(), "text/csv")},
            ).json()["data"]
        # Synthetic fixture (different file, same schema)
        synthetic = client.post(
            "/api/v1/datasets/fixtures/mp_allocation_ls/ingest"
        ).json()["data"]
        assert official["is_synthetic"] is False
        assert official["source_type"] == "OFFICIAL_FILE_UPLOAD"
        assert synthetic["is_synthetic"] is True
        assert synthetic["source_type"] == "SYNTHETIC_FIXTURE"

    def test_identical_bytes_are_guarded_regardless_of_label(self, client):
        """Same file uploaded twice → duplicate rejection (§43)."""
        with open("app/data/fixtures/mp_allocation_rs.csv", "rb") as fh:
            raw = fh.read()
        first = client.post(
            "/api/v1/datasets/import",
            files={"file": ("alloc.csv", raw, "text/csv")},
        )
        assert first.status_code == 200
        second = client.post(
            "/api/v1/datasets/import",
            files={"file": ("alloc_again.csv", raw, "text/csv")},
        )
        assert second.status_code == 400
        body = second.json()["error"]
        assert body["code"] == "DUPLICATE_DATASET"
        assert body["details"]["existing_dataset_id"]
