"""CAG pattern catalog — data, not code (single source of truth).

The catalog records irregularity PATTERNS documented in real CAG audits of
MPLADS, together with the Drishti detector that could identify each pattern
and the validation method used to demonstrate the capability.

Layer discipline (mirrors docs/CAG_VALIDATION.md §1):

  1. SOURCE       — verified CAG finding (report number, paragraph, quote)
  2. MAPPING      — Drishti's interpretation: which detector targets the pattern
  3. VALIDATION   — controlled synthetic reproduction of the pattern's
                    structural characteristics

Nothing in this file is a real MPLADS work record. Fixture data lives in
app/data/fixtures/cag_patterns.csv and is always ingested with
is_synthetic=True (AGENTS_RULES.md Rule 6).
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Verified CAG sources. Each entry is traceable to cag.gov.in or the
# published report text. NEVER extend this list without a verifiable source.
# ---------------------------------------------------------------------------
CAG_SOURCES: list[dict] = [
    {
        "source_id": "CAG-2001-3A",
        "title": (
            "Audit Report (Civil) — Union Government: Performance Appraisal "
            "of the Member of Parliament Local Area Development Scheme"
        ),
        "report_no": "3A of 2001",
        "period_covered": "1993–2000",
        "authority": "Comptroller and Auditor General of India",
        "source_url": "https://cag.gov.in/en/audit-report",
        "access_note": (
            "Findings quoted via Frontline (The Hindu), 5 Nov 2004, "
            "'The case against MPLADS', summarizing the CAG report; the "
            "report itself is listed on cag.gov.in."
        ),
    },
    {
        "source_id": "CAG-2010-31",
        "title": (
            "Report No. 31 of 2010 — Performance Audit of Civil on Member of "
            "Parliament Local Area Development Scheme"
        ),
        "report_no": "31 of 2010 (2010-11 audit cycle)",
        "period_covered": "2004-05 to 2008-09",
        "tabled": "18 March 2011",
        "authority": "Comptroller and Auditor General of India",
        "source_url": "https://cag.gov.in/en/audit-report/details/2341",
        "access_note": (
            "Report page and chapter PDFs on cag.gov.in; major findings "
            "summary (paras 3.2–3.4, 4.2, 6.1–6.3, 7.1) as published in the "
            "report's Executive Summary."
        ),
    },
    {
        "source_id": "CAG-2025-22",
        "title": (
            "Report No. 22 of 2025 — Compliance Audit (Civil & Commercial), "
            "Union Government"
        ),
        "report_no": "22 of 2025",
        "period_covered": "compliance audit observations tabled September 2025",
        "authority": "Comptroller and Auditor General of India",
        "source_url": (
            "https://cag.gov.in/uploads/download_audit_report/2025/"
            "Report-No.-22-of-2025_CAO-(Civil)_English-(03-10-2025)-"
            "06943aa88578c10.37125079.pdf"
        ),
        "access_note": (
            "Para 3.1 (page 49): 'Unfruitful expenditure of ₹62.61 lakh on "
            "construction of Indoor Sports Hall under MPLADS' — full "
            "paragraph text extracted directly from the published PDF."
        ),
    },
]

# ---------------------------------------------------------------------------
# Pattern catalog. Each pattern = one documented irregularity TYPE mapped to
# the Drishti detector that could identify it.
#
# validation_method:
#   DETECTOR_UNIT      — deterministic detector exercised directly on a
#                        representative record construction
#   SYNTHETIC_DATASET  — full pipeline run on a controlled synthetic dataset
#   NOT_VALIDATABLE    — pattern needs data Drishti does not have; reported
#                        honestly as a validation gap (never faked)
# ---------------------------------------------------------------------------
CAG_PATTERNS: list[dict] = [
    {
        "pattern_id": "CAG-PATTERN-001",
        "title": "Inadmissible/prohibited works executed",
        "source_id": "CAG-2010-31",
        "finding_reference": "Para 3.3",
        "documented_pattern": (
            "Scheme guidelines prohibit certain work types (government office/"
            "residential buildings, works benefiting religious institutions, "
            "commercial organizations, individuals/families, renovation/repair/"
            "maintenance). Yet sampled District Authorities incurred ₹73.76 "
            "crore on 2,340 such works during 2004–09."
        ),
        "cag_quote": (
            "The Scheme guidelines prohibited the execution of certain types of "
            "work such as construction of office and residential buildings of "
            "Government departments and cooperative societies, all works "
            "benefiting commercial organizations, an individual or a family, "
            "works within the premises of religious institutions, all works of "
            "renovation, repair and maintenance. Yet, in 100 sampled districts "
            "of 29 States/UTs, expenditure of ₹73.76 crore was incurred on "
            "2340 such works during 2004-09."
        ),
        "irregularity_type": "CATEGORICAL_COMPLIANCE",
        "required_data_fields": ["work description", "implementing agency"],
        "drishti_detector": "COMPLIANCE rule pack (app/rules/compliance.py)",
        "drishti_signal_type": "COMPLIANCE",
        "validation_method": "SYNTHETIC_DATASET",
        "fixture_work_ids": ["CAGV-001-A"],
        "expected_trigger": "COMPLIANCE signal (prohibited-category keyword match)",
        "limitations": (
            "Drishti matches guidebook categories on description text only; "
            "the real audit verified actual work nature on the ground."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-002",
        "title": "Works executed without MP recommendation / irregular sanction",
        "source_id": "CAG-2010-31",
        "finding_reference": "Para 3.2",
        "documented_pattern": (
            "District Authorities executed 700 works costing ₹9.45 crore "
            "without receiving any recommendation from the MPs concerned; "
            "150 works were executed on the recommendation of MP "
            "representatives rather than the MPs; 260 works were sanctioned "
            "at costs exceeding what the MP indicated."
        ),
        "cag_quote": (
            "In the sampled districts of eight States, DAs executed 700 works "
            "costing ₹9.45 crore without receiving any recommendations from "
            "the MPs concerned. In three States DAs executed 150 works costing "
            "₹2.44 crore on the recommendation of the representatives of the "
            "MPs rather than the MPs themselves. In seven States, 10 DAs "
            "sanctioned 260 works whose cost exceeded the cost indicated by "
            "the concerned MP by ₹2.49 crore."
        ),
        "irregularity_type": "PROCESS_IRREGULARITY",
        "required_data_fields": [
            "MP recommendation record", "sanction trail", "indicated cost",
        ],
        "drishti_detector": "None today — requires recommendation/sanction trail",
        "drishti_signal_type": None,
        "validation_method": "NOT_VALIDATABLE",
        "fixture_work_ids": [],
        "expected_trigger": None,
        "limitations": (
            "Work-level exports available to Drishti carry no MP-recommendation "
            "or sanction-approval trail, so this pattern cannot be validated "
            "without data that does not exist in the current pipeline. Reported "
            "as a detection gap, not a failure to be patched."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-003",
        "title": "Abandoned/suspended incomplete works — unfruitful expenditure",
        "source_id": "CAG-2010-31",
        "finding_reference": "Para 4.2.2 (Executive Summary item vii)",
        "documented_pattern": (
            "305 incomplete works worth ₹8.50 crore were abandoned or "
            "suspended across 11 States/UTs, rendering expenditure unfruitful."
        ),
        "cag_quote": (
            "In 11 States/UTs, 305 incomplete works of ₹8.50 crore had been "
            "abandoned or suspended, thereby rendering the expenditure "
            "incurred on these works unfruitful."
        ),
        "irregularity_type": "IMPLEMENTATION_FAILURE",
        "required_data_fields": [
            "sanction date", "expected duration", "physical progress", "status",
        ],
        "drishti_detector": "DELAY rule + FIN_PHYS_GAP rule + fusion priority",
        "drishti_signal_type": "DELAY",
        "validation_method": "SYNTHETIC_DATASET",
        "fixture_work_ids": ["CAGV-003-A"],
        "expected_trigger": "DELAY signal (elapsed ≫ expected duration, low physical progress)",
        "limitations": (
            "Drishti infers stalling from elapsed-vs-expected duration and "
            "progress gap; the audit verified abandonment from site records. "
            "A stalled work that is within its expected duration is not "
            "detectable from these fields alone."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-004",
        "title": "Financial progress misreported ahead of physical progress",
        "source_id": "CAG-2001-3A",
        "finding_reference": "Findings on misreporting of financial progress",
        "documented_pattern": (
            "The first CAG review (1993–2000) documented misreporting of "
            "financial progress, mostly with inflated cost estimates — funds "
            "shown spent while the physical work lagged."
        ),
        "cag_quote": (
            "Misreporting of financial progress, mostly with inflated cost "
            "estimates; irregular clubbing of work under MPLADS with other "
            "inadmissible projects; diversion of funds to other projects… "
            "were the other irregularities that the CAG report highlighted."
        ),
        "irregularity_type": "REPORTING_INTEGRITY",
        "required_data_fields": ["financial progress", "physical progress"],
        "drishti_detector": "FIN_PHYS_GAP rule (financial ≫ physical gap)",
        "drishti_signal_type": "FIN_PHYS_GAP",
        "validation_method": "SYNTHETIC_DATASET",
        "fixture_work_ids": ["CAGV-004-A"],
        "expected_trigger": "FIN_PHYS_GAP signal (gap ≥ 25 pp)",
        "limitations": (
            "Detects the observable signature (fin ≫ phys), not the intent to "
            "misreport. A work can have a large gap for operational reasons."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-005",
        "title": "Unutilized funds / low utilization with large unspent balances",
        "source_id": "CAG-2010-31",
        "finding_reference": "Para 6.1",
        "documented_pattern": (
            "Utilization of funds ranged between 37.43 and 52.44 per cent of "
            "funds available with District Authorities during 2004–09, leaving "
            "closing balances of ₹1,788–2,137 crore outside the Consolidated "
            "Fund."
        ),
        "cag_quote": (
            "The utilization of funds ranged between 37.43 and 52.44 percent of "
            "the funds available with the DAs during the last five years "
            "(2004-09) leaving substantial closing balances (₹1788 crore to "
            "₹2137 crore) in various bank accounts outside the Consolidated "
            "Fund of the Union and/or States."
        ),
        "irregularity_type": "FUNDS_UTILIZATION",
        "required_data_fields": ["funds available", "expenditure per district/authority"],
        "drishti_detector": "Partial — works with zero/low spend vs cost surface via "
                            "metrics and ML features, but Drishti has no "
                            "authority-level fund ledger",
        "drishti_signal_type": None,
        "validation_method": "NOT_VALIDATABLE",
        "fixture_work_ids": [],
        "expected_trigger": None,
        "limitations": (
            "Fund utilization is a property of District Authority ledgers, not "
            "of individual works. Drishti's schema (by design) does not model "
            "authority-level accounts, so this pattern is out of scope without "
            "an official fund-flow dataset."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-006",
        "title": "Completed works not put to intended use — unfruitful outcome",
        "source_id": "CAG-2025-22",
        "finding_reference": "Para 3.1",
        "documented_pattern": (
            "Substantial unauthorized changes to a sanctioned work's scope "
            "without MP/District Authority concurrence exhausted the sanctioned "
            "amount before completion; the work was foreclosed after ₹62.61 "
            "lakh had been spent, rendering the expenditure unfruitful."
        ),
        "cag_quote": (
            "Road Construction Division, Andaman Public Works Department, "
            "Wimberlygunj made substantial changes in the scope and requirement "
            "of work without concurrence of the Member of Parliament and the "
            "District Authority, resulting in exhaustion of sanctioned amount "
            "prior to completion of the work. The work was foreclosed after "
            "incurring expenditure of ₹62.61 lakh thereby rendering the "
            "expenditure unfruitful."
        ),
        "irregularity_type": "IMPLEMENTATION_FAILURE",
        "required_data_fields": [
            "sanctioned cost", "expenditure", "physical progress", "status",
        ],
        "drishti_detector": "Isolation Forest feature profile (high expenditure ratio "
                            "with low physical progress) + fusion priority",
        "drishti_signal_type": "ML_ANOMALY",
        "validation_method": "SYNTHETIC_DATASET",
        "fixture_work_ids": ["CAGV-006-A"],
        "expected_trigger": "ML unusualness on the spend-vs-progress profile "
                            "(signals converging on the same work)",
        "limitations": (
            "Scope-change documents are not in the work-level schema; Drishti "
            "sees only the statistical signature (spend ≫ physical progress), "
            "which is suggestive, not conclusive."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-007",
        "title": "Suspected fraud and misappropriation in executed works",
        "source_id": "CAG-2001-3A",
        "finding_reference": "Findings on suspected frauds and misappropriation",
        "documented_pattern": (
            "The first CAG review documented 'suspected frauds and "
            "misappropriation' detected in works worth ₹118.36 lakh, plus "
            "₹161 crore of expenditure across 111 sampled constituencies not "
            "supported by any document."
        ),
        "cag_quote": (
            "Besides, 'suspected frauds and misappropriation' were detected in "
            "works worth Rs.118.36 lakhs."
        ),
        "irregularity_type": "FRAUD_INDICATOR",
        "required_data_fields": [
            "payment records", "invoices", "execution evidence",
        ],
        "drishti_detector": "Partial — duplicate-candidate + ML signals target "
                            "statistical signatures; document-level verification "
                            "is out of MVP scope",
        "drishti_signal_type": "DUPLICATE",
        "validation_method": "SYNTHETIC_DATASET",
        "fixture_work_ids": ["CAGV-007-A", "CAGV-007-B"],
        "expected_trigger": "DUPLICATE candidate pair (near-identical works) as one "
                            "verifiable signature class",
        "limitations": (
            "Fraud/misappropriation requires document and payment evidence that "
            "work-level exports do not carry. The duplicate-pair fixture "
            "validates one signature class only — it does NOT reproduce the "
            "actual fraud cases from the report, and no such claim is made."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-008",
        "title": "Ineligible trusts/societies funded beyond ceilings",
        "source_id": "CAG-2010-31",
        "finding_reference": "Para 3.4",
        "documented_pattern": (
            "₹14.40 crore was sanctioned for works of 34 trusts/societies "
            "exceeding the ₹25 lakh-per-trust ceiling by ₹5.90 crore; ₹5.94 "
            "crore went to 145 trusts/societies that were ineligible or whose "
            "eligibility was never verified."
        ),
        "cag_quote": (
            "In 10 States, ₹14.40 crore was sanctioned for works pertaining to "
            "34 trusts/societies, which exceeded the ceiling of ₹25 lakh per "
            "trust/society fixed under the Scheme by ₹5.90 crore. In seven "
            "states, DAs sanctioned ₹5.94 crore to 145 Trusts/Societies, which "
            "were either ineligible as per the Scheme guidelines or whose "
            "eligibility had not been verified by the DAs."
        ),
        "irregularity_type": "CATEGORICAL_COMPLIANCE",
        "required_data_fields": ["implementing agency", "agency registration/approval status"],
        "drishti_detector": "COMPLIANCE rule pack — ineligible-payee indicator "
                            "(trust/society agencies require approval)",
        "drishti_signal_type": "COMPLIANCE",
        "validation_method": "SYNTHETIC_DATASET",
        "fixture_work_ids": ["CAGV-008-A"],
        "expected_trigger": "COMPLIANCE signal (UNAPPROVED_TRUST payee indicator)",
        "limitations": (
            "Flags the agency TYPE; verifying actual approval status or "
            "ceiling accumulation needs a register Drishti does not hold."
        ),
    },
    {
        "pattern_id": "CAG-PATTERN-009",
        "title": "Missing asset/works registers — no accountability records",
        "source_id": "CAG-2010-31",
        "finding_reference": "Para 5.1",
        "documented_pattern": (
            "90 per cent of audited District Authorities did not maintain "
            "asset/works registers, undermining the Scheme's accountability "
            "structures."
        ),
        "cag_quote": (
            "Basic internal control records such as asset registers, works "
            "registers etc. underpinning accountability structures within the "
            "Scheme were missing in a number of instances with 90 per cent of "
            "the audited DAs not maintaining asset/works registers."
        ),
        "irregularity_type": "RECORDS_GOVERNANCE",
        "required_data_fields": ["asset register", "works register"],
        "drishti_detector": "None — institutional records gap",
        "drishti_signal_type": None,
        "validation_method": "NOT_VALIDATABLE",
        "fixture_work_ids": [],
        "expected_trigger": None,
        "limitations": (
            "A records-keeping deficit is not detectable from work-level data "
            "rows. It motivates Drishti's DATA_QUALITY signal family but "
            "cannot be validated as a detector against this finding."
        ),
    },
]


def patterns_by_method(method: str) -> list[dict]:
    return [p for p in CAG_PATTERNS if p["validation_method"] == method]


def get_pattern(pattern_id: str) -> dict | None:
    for p in CAG_PATTERNS:
        if p["pattern_id"] == pattern_id:
            return p
    return None
