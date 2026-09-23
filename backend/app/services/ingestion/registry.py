"""Source field registry (Prompt-3 §13/§14).

Declares, per known official source schema, how observed source columns map
to canonical fields — with data type, requiredness and transformation labels.
The registry is data, not code paths: adding a new official export means
adding a SourceSchema entry, not rewriting the ingestion engine.

Detection is deterministic string matching on normalized header keys.
No LLM and no fuzzy guessing: a header either matches a registered alias
or it does not, and unmatched columns are reported.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.constants import DatasetType
from app.services.ingestion.normalizers import normalize_text


@dataclass(frozen=True)
class FieldMapping:
    """One source column → canonical field declaration."""

    canonical: str              # canonical field name (target schema)
    source_columns: tuple[str, ...]  # normalized alias keys, e.g. "allocated_amount (rs.)"
    data_type: str              # text | int | monetary | percentage | date
    required: bool = False
    nullable: bool = True
    transformation: str = "text"  # normalization label shown to developers


@dataclass(frozen=True)
class SourceSchema:
    """A known official source schema for one dataset type."""

    dataset_type: DatasetType
    schema_id: str              # e.g. "ls_allocation_v1"
    label: str
    fields: tuple[FieldMapping, ...]

    def match_score(self, headers: set[str]) -> int:
        """Deterministic match score: number of required fields present.

        A schema matches a file only if ALL required fields are found —
        otherwise the file is rejected as an unrecognized schema.
        """
        score = 0
        for f in self.fields:
            if any(alias in headers for alias in f.source_columns):
                score += 1
            elif f.required:
                return 0
        return score


def _key(header: str) -> str:
    """Deterministic header key: trim, lowercase, collapse non-alphanumerics."""
    text = normalize_text(header) or ""
    out: list[str] = []
    prev_us = False
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
            prev_us = False
        elif not prev_us:
            out.append("_")
            prev_us = True
    return ("".join(out)).strip("_")


# ---------------------------------------------------------------------------
# Registry — known official export structures
# ---------------------------------------------------------------------------

# Observed MPLADS e-SAKSHI Lok Sabha allocation export (Prompt-3 §3):
#   Sr. No. | State | Hon'ble Members of Parliament | Constituency
#   | Allocated Amount (₹)
LS_ALLOCATION = SourceSchema(
    dataset_type=DatasetType.MP_ALLOCATION,
    schema_id="ls_allocation_v1",
    label="MPLADS e-SAKSHI Lok Sabha MP allocation export",
    fields=(
        FieldMapping("serial_number", ("sr_no", "s_no", "serial_no", "sr_number"),
                     "int", transformation="int"),
        FieldMapping("state", ("state", "state_name", "state_ut"),
                     "text", required=True, transformation="text"),
        FieldMapping("mp_name", ("hon_ble_members_of_parliament",
                                 "honble_members_of_parliament",
                                 "member_of_parliament", "mp_name", "mp"),
                     "text", required=True, transformation="text"),
        FieldMapping("constituency", ("constituency", "constituency_name",
                                      "parliamentary_constituency"),
                     "text", transformation="text"),
        FieldMapping("allocated_amount", ("allocated_amount_rs_",
                                          "allocated_amount", "amount_allocated_rs_"),
                     "monetary", required=True, transformation="currency:raw rupees"),
    ),
)

# Observed Rajya Sabha allocation export adds Elected/Nominated and has no
# Constituency column (Prompt-3 §3). RS rows must keep constituency NULL.
RS_ALLOCATION = SourceSchema(
    dataset_type=DatasetType.MP_ALLOCATION,
    schema_id="rs_allocation_v1",
    label="MPLADS e-SAKSHI Rajya Sabha MP allocation export",
    fields=(
        FieldMapping("serial_number", ("sr_no", "s_no", "serial_no", "sr_number"),
                     "int", transformation="int"),
        FieldMapping("state", ("state", "state_name", "state_ut"),
                     "text", required=True, transformation="text"),
        FieldMapping("mp_name", ("hon_ble_members_of_parliament",
                                 "honble_members_of_parliament",
                                 "member_of_parliament", "mp_name", "mp"),
                     "text", required=True, transformation="text"),
        FieldMapping("elected_nominated", ("elected_nominated", "elected_or_nominated",
                                           "elected nominated"),
                     "text", transformation="text"),
        FieldMapping("allocated_amount", ("allocated_amount_rs_",
                                          "allocated_amount", "amount_allocated_rs_"),
                     "monetary", required=True, transformation="currency:raw rupees"),
    ),
)

# Dashboard-level aggregate metrics (Prompt-3 §16). Accepts the observed
# dashboard labels; monetary fields keep their declared unit (Crore).
SCHEME_AGGREGATE = SourceSchema(
    dataset_type=DatasetType.SCHEME_AGGREGATE,
    schema_id="scheme_aggregate_v1",
    label="MPLADS e-SAKSHI scheme aggregate statistics",
    fields=(
        FieldMapping("house", ("house", "lok_sabha_rajya_sabha", "segment"),
                     "text", transformation="text"),
        FieldMapping("allocated_limit", ("allocated_limit_for_hon_ble_mps",
                                         "allocated_limit_for_honble_mps",
                                         "allocated_limit"),
                     "monetary", transformation="currency:as displayed"),
        FieldMapping("amount_consented_for_calamity",
                     ("amount_consented_for_calamity",),
                     "monetary", transformation="currency:as displayed"),
        FieldMapping("works_recommended", ("works_recommended",),
                     "int", transformation="int"),
        FieldMapping("works_sanctioned", ("works_sanctioned",),
                     "int", transformation="int"),
        FieldMapping("works_completed", ("works_completed",),
                     "int", transformation="int"),
        FieldMapping("expenditure_completed_and_ongoing",
                     ("expenditure_on_completed_and_ongoing_works",
                      "expenditure_completed_and_ongoing"),
                     "monetary", transformation="currency:as displayed"),
        FieldMapping("as_of_date", ("as_of_date", "as_on_date", "date"),
                     "date", transformation="date"),
    ),
)

# Future official work-level export (Prompt-3 §17). Extensible: fields the
# source actually provides get mapped; everything else stays NULL.
WORK_LEVEL = SourceSchema(
    dataset_type=DatasetType.WORK_LEVEL,
    schema_id="work_level_v1",
    label="MPLADS official work-level export (extensible)",
    fields=(
        FieldMapping("work_id", ("work_id", "workid", "work_no"),
                     "text", required=True, transformation="text"),
        FieldMapping("mp_name", ("mp_name", "hon_ble_members_of_parliament",
                                 "honble_members_of_parliament", "member_of_parliament"),
                     "text", transformation="text"),
        FieldMapping("constituency", ("constituency", "constituency_name"),
                     "text", transformation="text"),
        FieldMapping("state", ("state", "state_name"), "text",
                     required=True, transformation="text"),
        FieldMapping("district", ("district", "district_name"), "text",
                     required=True, transformation="text"),
        FieldMapping("description", ("work_name", "work_description", "description",
                                     "work"),
                     "text", required=True, transformation="text"),
        FieldMapping("estimated_cost", ("estimated_cost", "estimated_cost_rs_"),
                     "monetary", transformation="currency:as displayed"),
        FieldMapping("sanctioned_amount", ("sanctioned_amount", "sanctioned_cost",
                                           "sanctioned_amount_rs_"),
                     "monetary", required=True, transformation="currency:as displayed"),
        FieldMapping("expenditure", ("expenditure", "expenditure_rs_"),
                     "monetary", transformation="currency:as displayed"),
        FieldMapping("physical_progress", ("physical_progress",),
                     "percentage", transformation="percentage"),
        FieldMapping("financial_progress", ("financial_progress",),
                     "percentage", transformation="percentage"),
        FieldMapping("sanction_date", ("sanction_date",), "date", transformation="date"),
        FieldMapping("completion_date", ("completion_date",), "date",
                     transformation="date"),
        FieldMapping("implementing_agency", ("implementing_agency", "agency"),
                     "text", transformation="text"),
        FieldMapping("latitude", ("latitude", "lat"), "text",
                     transformation="decimal"),
        FieldMapping("longitude", ("longitude", "lon", "lng"), "text",
                     transformation="decimal"),
        # Extensible optional fields — mapped only when the source provides
        # them (Prompt-3 §17). Absent columns leave canonical fields NULL.
        FieldMapping("category", ("category", "work_category"),
                     "text", transformation="text"),
        FieldMapping("sector", ("sector",), "text", transformation="text"),
        FieldMapping("status", ("status", "work_status"),
                     "text", transformation="text"),
        FieldMapping("contractor_name", ("contractor_name", "contractor", "vendor"),
                     "text", transformation="text"),
        FieldMapping("expected_duration_days", ("expected_duration_days",
                                                "expected_duration"),
                     "int", transformation="int"),
        FieldMapping("start_date", ("start_date",), "date", transformation="date"),
        FieldMapping("location_text", ("location", "location_text", "village_town"),
                     "text", transformation="text"),
        # Payments layer (backlog #5) — mapped only when a source provides
        # payment rows; otherwise these columns never exist and the layer
        # stays empty. Never fabricated (Prompt-3 §4).
        FieldMapping("payment_ref", ("payment_ref", "payment_id", "payment_no"),
                     "text", transformation="text"),
        FieldMapping("payment_amount", ("payment_amount", "amount_paid",
                                        "payment_amount_rs_"),
                     "monetary", transformation="currency:as displayed"),
        FieldMapping("paid_on", ("paid_on", "payment_date"), "date",
                     transformation="date"),
        FieldMapping("payee", ("payee", "paid_to", "vendor_name"),
                     "text", transformation="text"),
        FieldMapping("payment_stage", ("payment_stage", "stage"),
                     "text", transformation="text"),
    ),
)

SCHEMAS: tuple[SourceSchema, ...] = (
    LS_ALLOCATION, RS_ALLOCATION, SCHEME_AGGREGATE, WORK_LEVEL,
)


def detect_schema(headers: list[str]) -> tuple[SourceSchema | None, dict[str, str]]:
    """Deterministically pick the best-matching registered schema.

    Returns (schema, column_map) where column_map maps each source header
    (as it appeared) to its canonical field. Ambiguity is resolved by match
    score, then registry order; ties between allocation schemas are broken
    by which one found more of its non-required fields.
    """
    header_keys = {_key(h) for h in headers}
    best: SourceSchema | None = None
    best_map: dict[str, str] = {}
    best_score = -1
    for schema in SCHEMAS:
        score = schema.match_score(header_keys)
        if score == 0:
            continue
        cmap = map_headers(schema, headers)
        if score > best_score or (score == best_score and len(cmap) > len(best_map)):
            best, best_map, best_score = schema, cmap, score
    return best, best_map


def map_headers(schema: SourceSchema, headers: list[str]) -> dict[str, str]:
    """Map each observed source header to its canonical field (§13).

    Unmatched headers are absent from the result — the caller records them
    as unmapped. First alias wins; aliases are tried in registry order.
    """
    result: dict[str, str] = {}
    for header in headers:
        k = _key(header)
        for f in schema.fields:
            if k in f.source_columns:
                result[header] = f.canonical
                break
    return result


def build_source_schema_record(
    schema: SourceSchema | None,
    headers: list[str],
    column_map: dict[str, str],
) -> dict[str, Any]:
    """Provenance record of what the source actually contained (§14)."""
    mapped_sources = {src: tgt for src, tgt in column_map.items()}
    unmapped = [h for h in headers if h not in mapped_sources]
    return {
        "schema_id": schema.schema_id if schema else None,
        "label": schema.label if schema else "unrecognized",
        "detected_columns": [
            {"source_column": src, "canonical_field": tgt}
            for src, tgt in mapped_sources.items()
        ],
        "unmapped_columns": unmapped,
    }


def unmatched_required_fields(
    schema: SourceSchema, headers: list[str]
) -> list[str]:
    """Required canonical fields with no matching source column."""
    header_keys = {_key(h) for h in headers}
    missing: list[str] = []
    for f in schema.fields:
        if f.required and not any(a in header_keys for a in f.source_columns):
            missing.append(f.canonical)
    return missing
