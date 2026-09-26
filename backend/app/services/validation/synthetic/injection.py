"""Deterministic baseline generator + anomaly injectors (Steps 2–3).

Determinism contract (verified by tests):
- a fixed seed produces byte-identical generation plans on every run
- every injected record carries explicit ground truth:
    {record_id, is_injected_anomaly, anomaly_type, injection_id,
     original_record_id (for variants), expected_detector}
- every non-injected record: {record_id, injected: False}

Design: the module produces plain row dicts in the canonical work-level
shape. The benchmark orchestrator serializes them to CSV and pushes them
through the REAL ingestion + detection pipeline — the model under test is
never short-circuited.

"Normal" bands (Scenario A must be clean; documented in the docstring of
`generate_baseline_dataset` and verified by the benchmark itself):
- cost within ±12% of the 25L band median   (COST trigger: +40% vs peers)
- fin/phys within ±12 pp of each other      (trigger: 25 pp gap)
- elapsed ≤ 200 days vs 300–420 expected    (trigger: 90 delay days)
- expenditure ≤ 60% of sanctioned while progress ≤ 60%
  (IF outliers emerge from joint feature extremes, not single fields)
- four agencies rotated; locations on a spread grid (no artificial
  concentration/duplication in the baseline)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

# Deterministic "today" so elapsed/delay arithmetic is reproducible.
REFERENCE_DATE = date(2026, 9, 1)

INJECTED_PREFIX = "SYA-"          # synthetic-anomaly work IDs
BASELINE_PREFIX = "SYB-"          # baseline work IDs

AGENCIES = [
    "District Rural Development Agency",
    "Zilla Panchayat Engineering Division",
    "Public Works Department",
    "Municipal Corporation",
]


@dataclass
class GroundTruth:
    """Ground-truth side table for one generated dataset (Step 4)."""

    entries: dict[str, dict] = field(default_factory=dict)

    def mark_baseline(self, record_id: str) -> None:
        self.entries[record_id] = {
            "record_id": record_id,
            "ground_truth": "normal",
            "injected": False,
            "anomaly_type": None,
            "injection_id": None,
            "original_record_id": None,
            "expected_detector": None,
        }

    def mark_injected(
        self,
        record_id: str,
        anomaly_type: str,
        injection_id: str,
        original_record_id: str | None,
        expected_detector: str,
    ) -> None:
        self.entries[record_id] = {
            "record_id": record_id,
            "ground_truth": "anomaly",
            "injected": True,
            "anomaly_type": anomaly_type,
            "injection_id": injection_id,
            "original_record_id": original_record_id,
            "expected_detector": expected_detector,
        }

    def as_list(self) -> list[dict]:
        return [self.entries[k] for k in sorted(self.entries)]


def _row(
    work_id: str,
    *,
    district: str = "Synthetic District",
    category: str = "Education",
    description: str,
    sanctioned: float,
    expenditure: float,
    fin: float,
    phys: float,
    sanction_date: date,
    expected_days: int = 300,
    agency: str = "District Rural Development Agency",
    location: str = "Ward 1",
    lat: float = 13.01,
    lon: float = 77.55,
    status: str = "In Progress",
    mp_name: str = "Synthetic MP",
) -> dict:
    return {
        "work_id": work_id,
        "description": description,
        "state": "Synthetic State",
        "district": district,
        "category": category,
        "status": status,
        "sanction_date": sanction_date.isoformat(),
        "start_date": (sanction_date + timedelta(days=15)).isoformat(),
        "expected_duration_days": expected_days,
        "physical_progress": phys,
        "financial_progress": fin,
        "sanctioned_amount": sanctioned,
        "estimated_cost": sanctioned,
        "expenditure": expenditure,
        "latitude": lat,
        "longitude": lon,
        "implementing_agency": agency,
        "mp_name": mp_name,
        "location_text": location,
    }


class SyntheticDatasetBuilder:
    """Deterministic baseline generator + injectors (Step 3 API).

    Every injector returns the injected rows and records ground truth;
    row creation is sequential with an internal counter and all sampling
    uses the configured `random.Random` — a given seed fully determines
    the dataset.
    """

    def __init__(self, seed: int = 26102, reference_date: date = REFERENCE_DATE):
        self.seed = seed
        self.rng = random.Random(seed)
        self.reference_date = reference_date
        self._counter = 0
        self.rows: list[dict] = []
        self.ground_truth = GroundTruth()
        self.injection_log: list[dict] = []
        self._pending_seed: dict[int, str | None] = {}

    # ------------------------------------------------------------------
    # baseline (Scenario A)
    # ------------------------------------------------------------------
    def generate_baseline_dataset(self, n: int = 60) -> list[dict]:
        """Clean synthetic works whose values stay inside normal bands.

        Text/geo spread matters as much as numeric bands: descriptions are
        drawn from kind × place × phrasing so no two clean rows are
        textually near-duplicates, and locations are laid out on a spaced
        grid (adjacent sites > 2 km apart) so the duplicate-candidate
        proximity component never fires on clean rows.
        """
        if self.rows:
            raise RuntimeError("baseline already generated for this builder")
        kinds = [
            "additional classrooms", "a library block", "a drinking water tank",
            "an internal village road", "an anganwadi building",
            "a community toilet complex", "a school boundary wall",
            "a primary health sub-centre", "a bus stop shelter",
            "a sports ground fencing", "a village pond renovation-free",
            "a panchayat hall extension",
        ]
        places = [
            "Government High School", "the village panchayat area",
            "the primary school campus", "the community health centre",
            "the market street", "the bus stand road",
            "the lake side lane", "the hill colony",
        ]
        templates = [
            "Construction of {k} at {p}",
            "Providing {k} facility near {p}",
            "Upgradation of {k} for {p}",
        ]
        for i in range(n):
            self._counter += 1
            wid = f"{BASELINE_PREFIX}{i + 1:04d}"
            median = 25.0 * 100000  # single shared band median → tight peers
            sanctioned = median * self.rng.uniform(0.88, 1.12)
            fin = self.rng.uniform(25.0, 55.0)
            phys = fin + self.rng.uniform(-12.0, 12.0)
            expenditure = sanctioned * self.rng.uniform(0.15, 0.55)
            expected = self.rng.choice([300, 330, 360, 390, 420])
            sanction = self.reference_date - timedelta(
                days=self.rng.randint(30, 200)
            )
            desc = self.rng.choice(templates).format(
                k=self.rng.choice(kinds), p=self.rng.choice(places)
            )
            # Spaced grid: columns of 0.02° (~2.2 km) so adjacent sites sit
            # beyond the duplicate-candidate 2 km proximity taper.
            lat = 12.90 + (i % 10) * 0.02 + self.rng.uniform(0.0, 0.004)
            lon = 77.40 + (i // 10) * 0.02 + self.rng.uniform(0.0, 0.004)
            row = _row(
                wid,
                description=f"{desc} (site {i + 1})",
                sanctioned=round(sanctioned, -3),
                expenditure=round(expenditure, -3),
                fin=round(fin, 1),
                phys=round(max(0.0, min(100.0, phys)), 1),
                sanction_date=sanction,
                expected_days=expected,
                agency=AGENCIES[i % len(AGENCIES)],
                location=f"Site {i + 1}",
                lat=round(lat, 5),
                lon=round(lon, 5),
            )
            self.rows.append(row)
            self.ground_truth.mark_baseline(wid)
        return self.rows

    # ------------------------------------------------------------------
    # injector helpers
    # ------------------------------------------------------------------
    def _next_id(self, tag: str) -> str:
        self._counter += 1
        return f"{INJECTED_PREFIX}{tag}{self._counter:04d}"

    def _register(
        self,
        rows: list[dict],
        anomaly_type: str,
        expected_detector: str,
        seed_row: dict | None = None,  # kept for signature stability; sources
                                       # flow via _link_seed/_pending_seed
    ) -> list[dict]:
        """Append rows and record ground truth for each."""
        injection_id = f"inj-{len(self.injection_log) + 1:03d}"
        logged: list[dict] = []
        for r in rows:
            self.rows.append(r)
            self.ground_truth.mark_injected(
                record_id=r["work_id"],
                anomaly_type=anomaly_type,
                injection_id=injection_id,
                original_record_id=self._pending_seed.pop(id(r), None),
                expected_detector=expected_detector,
            )
            logged.append({
                "injection_id": injection_id,
                "work_id": r["work_id"],
                "anomaly_type": anomaly_type,
                "expected_detector": expected_detector,
                "original_record_id": (
                    seed_row["work_id"] if seed_row else None
                ),
            })
        self.injection_log.extend(logged)
        return rows

    def _sample_baseline(self) -> dict:
        if not self.rows:
            raise RuntimeError("generate_baseline_dataset() must run first")
        return self.rng.choice(self.rows)

    def _link_seed(self, row: dict, seed_row: dict | None) -> None:
        """Stash the sampled baseline source on the pending row so
        `_register` can record `original_record_id` (None when the injector
        builds rows from scratch rather than varying a baseline record)."""
        self._pending_seed[id(row)] = seed_row["work_id"] if seed_row else None

    # ------------------------------------------------------------------
    # 1. cost inflation — expected detector: COST_ANOMALY (peer rule)
    # ------------------------------------------------------------------
    def inject_cost_anomalies(self, n: int = 6) -> list[dict]:
        """Peer median ≈ 25L band; inject works at ~2× median (≈ +100%
        deviation, far above the +40% trigger). Description/agency stay
        unremarkable so cost is the ONLY unusual dimension."""
        out: list[dict] = []
        for _ in range(n):
            seed = self._sample_baseline()
            row = _row(
                self._next_id("C"),
                description=seed["description"],
                sanctioned=round(25.0 * 100000 * 2.0, -3),
                expenditure=round(25.0 * 100000 * 2.0 * 0.4, -3),
                fin=self.rng.uniform(35.0, 50.0),
                phys=self.rng.uniform(32.0, 48.0),
                sanction_date=self.reference_date - timedelta(days=120),
                expected_days=360,
                agency=self.rng.choice(AGENCIES),
            )
            out.append(row)
            self._link_seed(row, seed)
        return self._register(out, "cost_inflation", "COST_ANOMALY")

    # ------------------------------------------------------------------
    # 2. duplicate/similar work — expected detector: DUPLICATE (NLP)
    # ------------------------------------------------------------------
    def inject_duplicate_anomalies(self, n: int = 3) -> list[dict]:
        """Each injection = a near-twin PAIR. Both rows are injected (the
        pair as a whole is the anomaly) and carry duplicate ground truth:
        near-identical description, cost within 1%, ~15 m apart, same
        category, overlapping time window."""
        out: list[dict] = []
        for _ in range(n):
            seed = self._sample_baseline()
            lat = 13.05 + self.rng.uniform(0.0005, 0.02)
            lon = 77.55 + self.rng.uniform(0.0005, 0.02)
            a = _row(
                self._next_id("D"),
                description=seed["description"],
                category=seed["category"],
                sanctioned=round(25.0 * 100000 * 1.005, -3),
                expenditure=round(25.0 * 100000 * 0.5, -3),
                fin=55.0,
                phys=50.0,
                sanction_date=self.reference_date - timedelta(days=150),
                expected_days=365,
                agency=self.rng.choice(AGENCIES),
                lat=lat,
                lon=lon,
                location="Duplicate Site Ward",
            )
            self._link_seed(a, seed)
            b = _row(
                self._next_id("D"),
                description=f"{seed['description']} block",
                category=seed["category"],
                sanctioned=round(25.0 * 100000 * 0.995, -3),
                expenditure=round(25.0 * 100000 * 0.5, -3),
                fin=52.0,
                phys=48.0,
                sanction_date=self.reference_date - timedelta(days=140),
                expected_days=365,
                agency=self.rng.choice(AGENCIES),
                lat=lat + 0.0001,
                lon=lon + 0.0001,
                location="Duplicate Site Ward",
            )
            self._link_seed(b, seed)
            out.extend([a, b])
        return self._register(out, "duplicate_similar_work", "DUPLICATE")

    # ------------------------------------------------------------------
    # 3. abnormal duration — expected detector: DELAY
    # ------------------------------------------------------------------
    def inject_delay_anomalies(self, n: int = 6) -> list[dict]:
        """Sanctioned ~500 days ago with 300-day expectation and minimal
        progress → elapsed − expected ≈ +200d (trigger ≥ 90d). Cost stays
        at band median so cost is not the flagging dimension."""
        out: list[dict] = []
        for _ in range(n):
            seed = self._sample_baseline()
            row = _row(
                self._next_id("T"),
                description=seed["description"],
                sanctioned=round(25.0 * 100000, -3),
                expenditure=round(25.0 * 100000 * 0.15, -3),
                fin=self.rng.uniform(8.0, 20.0),
                phys=self.rng.uniform(5.0, 15.0),
                sanction_date=self.reference_date - timedelta(days=500),
                expected_days=300,
                agency=self.rng.choice(AGENCIES),
            )
            out.append(row)
            self._link_seed(row, seed)
        return self._register(out, "abnormal_duration", "DELAY")

    # ------------------------------------------------------------------
    # 4. unusual spending pattern — expected detector: ML_ANOMALY
    # ------------------------------------------------------------------
    def inject_spending_pattern_anomalies(self, n: int = 6) -> list[dict]:
        """Extreme spend-vs-progress profile: expenditure ≈ 95–99% of
        sanctioned while physical progress ≈ 10–20% — an outlier across the
        IF feature space (expenditure_ratio + fin/phys gap + delay)."""
        out: list[dict] = []
        for _ in range(n):
            seed = self._sample_baseline()
            sanctioned = round(25.0 * 100000, -3)
            row = _row(
                self._next_id("S"),
                description=seed["description"],
                sanctioned=sanctioned,
                expenditure=round(sanctioned * self.rng.uniform(0.95, 0.99), -3),
                fin=self.rng.uniform(88.0, 97.0),
                phys=self.rng.uniform(10.0, 20.0),
                sanction_date=self.reference_date - timedelta(days=400),
                expected_days=360,
                agency=self.rng.choice(AGENCIES),
            )
            out.append(row)
            self._link_seed(row, seed)
        return self._register(out, "unusual_spending_pattern", "ML_ANOMALY")

    # ------------------------------------------------------------------
    # 5. suspicious attribute combination — expected: COMPLIANCE
    # ------------------------------------------------------------------
    def inject_pattern_anomalies(self, n: int = 4) -> list[dict]:
        """Works whose descriptions land in guideline-prohibited categories
        (temple/statue/office building) and one trust-implemented row —
        the categorical COMPLIANCE path, not a statistical one."""
        descriptions = [
            ("Construction of temple compound wall at Ward", False),
            ("Erection of memorial statue at Ward", False),
            ("Construction of office building for cooperative society", False),
            ("Library block under trust implementation at Ward", True),
        ]
        out: list[dict] = []
        for i in range(n):
            desc, is_trust = descriptions[i % len(descriptions)]
            seed = self._sample_baseline()
            row = _row(
                self._next_id("P"),
                description=f"{desc} {i + 1}",
                sanctioned=round(25.0 * 100000, -3),
                expenditure=round(25.0 * 100000 * 0.3, -3),
                fin=45.0,
                phys=40.0,
                sanction_date=self.reference_date - timedelta(days=150),
                expected_days=330,
                agency=(
                    "Sri Deva Trust for Rural Development"
                    if is_trust else "Public Works Department"
                ),
            )
            out.append(row)
            self._link_seed(row, seed)
        return self._register(out, "suspicious_attribute_combination", "COMPLIANCE")

    # ------------------------------------------------------------------
    # export
    # ------------------------------------------------------------------
    def build_csv(self) -> bytes:
        """Serialize the plan to the canonical work-level CSV (UTF-8)."""
        import csv
        import io

        headers = [
            "Work ID", "Work Name", "State", "District", "Category",
            "Status", "Sanction Date", "Start Date",
            "Expected Duration Days", "Physical Progress",
            "Financial Progress", "Sanctioned Amount (₹)", "Expenditure (₹)",
            "Latitude", "Longitude", "Implementing Agency", "MP Name",
            "Location",
        ]
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(headers)
        for r in self.rows:
            w.writerow([
                r["work_id"], r["description"], r["state"], r["district"],
                r["category"], r["status"], r["sanction_date"],
                r["start_date"], r["expected_duration_days"],
                r["physical_progress"], r["financial_progress"],
                int(r["sanctioned_amount"]), int(r["expenditure"]),
                r["latitude"], r["longitude"], r["implementing_agency"],
                r["mp_name"], r["location_text"],
            ])
        return buf.getvalue().encode("utf-8")
