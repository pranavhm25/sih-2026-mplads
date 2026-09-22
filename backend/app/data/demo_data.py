"""Deterministic synthetic demo dataset — MPLADS-style works.

This is CONTROLLED SYNTHETIC DEMO DATA, clearly labelled as such everywhere
it appears (AGENTS_RULES.md Rule 6). It is generated deterministically with
a fixed seed so demos are reproducible.

The flagship case MPL-10281 deliberately exhibits five independent signals:
cost anomaly, financial/physical mismatch, delay, duplicate candidate and
ML anomaly — demonstrating multi-signal convergence (PRD §10).
"""
from __future__ import annotations

import random
from datetime import date, timedelta

REFERENCE_DATE = date(2026, 9, 1)  # fixed "today" for reproducibility

STATES: list[dict] = [
    {"state": "Karnataka", "districts": ["Bengaluru Urban", "Mysuru", "Belagavi"]},
    {"state": "Maharashtra", "districts": ["Pune", "Nashik", "Nagpur"]},
    {"state": "Tamil Nadu", "districts": ["Coimbatore", "Madurai", "Salem"]},
]

CATEGORIES: list[str] = [
    "Education",
    "Health",
    "Drinking Water",
    "Roads",
    "Community Infrastructure",
    "Sanitation",
]

AGENCIES: list[str] = [
    "District Rural Development Agency",
    "Municipal Corporation",
    "Zilla Panchayat Engineering Division",
    "Public Works Department",
]

DESCRIPTION_TEMPLATES: list[str] = [
    "Construction of {kind} at {place}",
    "Renovation of {kind} at {place}",
    "Providing {kind} facility at {place}",
    "Upgradation of {kind} in {place}",
]

KINDS: dict[str, list[str]] = {
    "Education": ["government school building", "school library", "computer lab", "classroom block"],
    "Health": ["primary health centre", "health sub-centre", "dispensary", "delivery ward"],
    "Drinking Water": ["overhead water tank", "borewell with storage", "water supply scheme", "summer storage tank"],
    "Roads": ["cement concrete road", "internal village road", "bituminous road", "footpath"],
    "Community Infrastructure": ["community hall", "village hall", "anganwadi building", "market shed"],
    "Sanitation": ["community toilet complex", "solid waste shed", "drainage system", "soak pits"],
}

PLACES: list[str] = [
    "Ward 12", "Ward 27", "Gandhi Nagar", "Nehru Colony", "Ambedkar Layout",
    "Old Town", "Bus Stand Area", "Market Street", "Hosur Road", "Lake View",
    "Temple Street", "Hill Colony", "Riverside", "Station Road", "Park Extension",
]

MpS: list[str] = [
    "R. Krishnamurthy", "Sunita Deshmukh", "A. Ramesh", "Farida Khan",
    "V. Balasubramanian", "Prakash Jadhav", "Meena Iyer", "T. Suresh Babu",
]


def _paise_to_lakh(value: float) -> float:
    """Round cost to look like a lakh figure (e.g. 24.2L → 2420000)."""
    return round(value * 100000, -3)


def build_demo_rows(reference_date: date = REFERENCE_DATE) -> list[dict]:
    """Build the deterministic demo rows. ~60 baseline + 1 flagship pair."""
    rng = random.Random(26102)  # SIH PS number as seed — fixed forever
    rows: list[dict] = []

    # --- Flagship anomaly case and its duplicate twin --------------------
    # 91% text similarity, 43 m apart, near-identical cost, category, time.
    rows.append({
        "work_id": "MPL-10281",
        "mp_name": "R. Krishnamurthy",
        "constituency": "Bengaluru South",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "location_text": "Near Ward 12, Gandhi Nagar, Bengaluru Urban",
        "latitude": 12.9762,
        "longitude": 77.5993,
        "category": "Community Infrastructure",
        "sector": "Rural Development",
        "description": "Construction of community hall building at Gandhi Nagar Ward 12",
        "estimated_cost": _paise_to_lakh(37.0),
        "sanctioned_cost": _paise_to_lakh(38.7),
        "expenditure": _paise_to_lakh(32.5),
        "financial_progress": 84.0,
        "physical_progress": 32.0,
        "sanction_date": date(2025, 4, 10),
        "start_date": date(2025, 5, 15),
        "completion_date": None,
        "status": "In Progress",
        "implementing_agency": "Zilla Panchayat Engineering Division",
        "contractor_name": "Sri Balaji Constructions",
        "expected_duration_days": 365,
    })
    rows.append({
        "work_id": "MPL-10412",
        "mp_name": "R. Krishnamurthy",
        "constituency": "Bengaluru South",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "location_text": "Ward 12, Gandhi Nagar, Bengaluru Urban",
        "latitude": 12.97624,
        "longitude": 77.59935,  # ~43 m from the flagship
        "category": "Community Infrastructure",
        "sector": "Rural Development",
        "description": "Construction of community hall at Gandhi Nagar Ward 12 Bengaluru",
        "estimated_cost": _paise_to_lakh(36.0),
        "sanctioned_cost": _paise_to_lakh(38.2),
        "expenditure": _paise_to_lakh(31.0),
        "financial_progress": 80.0,
        "physical_progress": 35.0,
        "sanction_date": date(2025, 5, 2),
        "start_date": date(2025, 6, 10),
        "completion_date": None,
        "status": "In Progress",
        "implementing_agency": "Zilla Panchayat Engineering Division",
        "contractor_name": "Sri Balaji Constructions",
        "expected_duration_days": 365,
    })

    # --- Baseline population ---------------------------------------------
    work_counter = 20001
    for st in STATES:
        for district in st["districts"]:
            for _ in range(7):
                category = rng.choice(CATEGORIES)
                kind = rng.choice(KINDS[category])
                place = rng.choice(PLACES)
                desc = rng.choice(DESCRIPTION_TEMPLATES).format(kind=kind, place=place)
                median_l = rng.uniform(12, 32)
                cost_l = median_l * rng.uniform(0.75, 1.3)
                fin = round(rng.uniform(15, 100), 1)
                phys = max(0.0, min(100.0, fin + rng.uniform(-12, 12)))
                sanction = reference_date - timedelta(days=rng.randint(150, 900))
                expected = rng.choice([240, 270, 300, 365, 420])
                elapsed_guess = (reference_date - sanction).days
                completed = phys >= 100 or rng.random() < 0.35
                completion = None
                if completed:
                    completion = sanction + timedelta(days=rng.randint(
                        expected - 40, expected + 30))
                    fin = 100.0
                    phys = 100.0
                rows.append({
                    "work_id": f"MPL-{work_counter}",
                    "mp_name": rng.choice(MpS),
                    "constituency": f"{district} Lok Sabha",
                    "state": st["state"],
                    "district": district,
                    "location_text": f"{place}, {district}",
                    "latitude": round(rng.uniform(8.5, 20.5), 5),
                    "longitude": round(rng.uniform(74.0, 80.5), 5),
                    "category": category,
                    "sector": rng.choice(["Rural Development", "Urban Development"]),
                    "description": desc,
                    "estimated_cost": _paise_to_lakh(cost_l),
                    "sanctioned_cost": _paise_to_lakh(cost_l * rng.uniform(0.95, 1.05)),
                    "expenditure": _paise_to_lakh(cost_l * (fin / 100.0) * rng.uniform(0.9, 1.05)),
                    "financial_progress": fin,
                    "physical_progress": phys,
                    "sanction_date": sanction,
                    "start_date": sanction + timedelta(days=rng.randint(10, 45)),
                    "completion_date": completion,
                    "status": "Completed" if completed else "In Progress",
                    "implementing_agency": rng.choice(AGENCIES),
                    "contractor_name": rng.choice([
                        "Sri Venkateshwara Builders", "Metro Infra Works",
                        "National Civil Contractors", "Sree Sai Constructions",
                        "Nova Engineering Works",
                    ]),
                    "expected_duration_days": expected,
                })
                work_counter += 1

    # --- Peer group for the flagship case ---------------------------------
    # Bengaluru Urban · Community Infrastructure needs ≥ 6 members so the
    # flagship's cost benchmark is real (₹38.7L vs ~₹22-24L median).
    for i in range(8):
        cost_l = rng.uniform(17.0, 26.5)
        fin = round(rng.uniform(45, 95), 1)
        phys = max(0.0, min(100.0, fin + rng.uniform(-10, 10)))
        sanction = reference_date - timedelta(days=rng.randint(200, 520))
        expected = rng.choice([300, 365, 420])
        rows.append({
            "work_id": f"MPL-{work_counter}",
            "mp_name": rng.choice(MpS),
            "constituency": "Bengaluru South Lok Sabha",
            "state": "Karnataka",
            "district": "Bengaluru Urban",
            "location_text": f"{rng.choice(PLACES)}, Bengaluru Urban",
            "latitude": round(rng.uniform(12.8, 13.1), 5),
            "longitude": round(rng.uniform(77.4, 77.7), 5),
            "category": "Community Infrastructure",
            "sector": "Rural Development",
            "description": rng.choice([
                "Construction of community hall at {p}",
                "Renovation of village hall at {p}",
                "Construction of anganwadi building at {p}",
                "Providing market shed facility at {p}",
            ]).format(p=rng.choice(PLACES)),
            "estimated_cost": _paise_to_lakh(cost_l),
            "sanctioned_cost": _paise_to_lakh(cost_l * rng.uniform(0.97, 1.04)),
            "expenditure": _paise_to_lakh(cost_l * (fin / 100.0)),
            "financial_progress": fin,
            "physical_progress": phys,
            "sanction_date": sanction,
            "start_date": sanction + timedelta(days=rng.randint(15, 40)),
            "completion_date": None,
            "status": "In Progress",
            "implementing_agency": rng.choice(AGENCIES),
            "contractor_name": rng.choice([
                "Sri Venkateshwara Builders", "Metro Infra Works",
                "National Civil Contractors", "Nova Engineering Works",
            ]),
            "expected_duration_days": expected,
        })
        work_counter += 1

    # --- Deliberate data-quality violations (demonstrate quality engine) --
    rows.append({
        "work_id": "MPL-10488",
        "mp_name": "Sunita Deshmukh",
        "constituency": "Pune Lok Sabha",
        "state": "Maharashtra",
        "district": "Pune",
        "location_text": "Ward 9, Kothrud, Pune",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "category": "Health",
        "sector": "Urban Development",
        "description": "Renovation of primary health centre at Kothrud Ward 9",
        "estimated_cost": _paise_to_lakh(22.0),
        "sanctioned_cost": _paise_to_lakh(22.0),
        "expenditure": _paise_to_lakh(24.5),  # expenditure > sanctioned
        "financial_progress": 100.0,
        "physical_progress": 100.0,
        "sanction_date": date(2025, 1, 20),
        "start_date": date(2025, 2, 5),
        "completion_date": date(2024, 12, 15),  # completion BEFORE sanction
        "status": "Completed",
        "implementing_agency": "Municipal Corporation",
        "contractor_name": "Metro Infra Works",
        "expected_duration_days": 240,
    })
    rows.append({
        "work_id": "MPL-10489",
        "mp_name": "A. Ramesh",
        "constituency": "Coimbatore Lok Sabha",
        "state": "Tamil Nadu",
        "district": "Coimbatore",
        "location_text": "Ward 5, Gandhipuram, Coimbatore",
        "latitude": 11.0183,
        "longitude": 76.9558,
        "category": "Education",
        "sector": "Rural Development",
        "description": "Construction of computer lab at Gandhipuram school",
        "estimated_cost": _paise_to_lakh(18.0),
        "sanctioned_cost": _paise_to_lakh(18.0),
        "expenditure": _paise_to_lakh(9.0),
        "financial_progress": 108.0,  # progress > 100%
        "physical_progress": 50.0,
        "sanction_date": date(2025, 6, 1),
        "start_date": date(2025, 7, 1),
        "completion_date": None,
        "status": "In Progress",
        "implementing_agency": "Zilla Panchayat Engineering Division",
        "contractor_name": None,
        "expected_duration_days": 300,
    })
    rows.append({
        "work_id": "MPL-10490",
        "mp_name": None,  # missing mandatory field
        "constituency": "Nashik Lok Sabha",
        "state": "Maharashtra",
        "district": "Nashik",
        "location_text": None,
        "latitude": None,  # missing geo
        "longitude": None,
        "category": None,  # missing mandatory field
        "sector": "Rural Development",
        "description": "Providing water supply scheme facility at Hill Colony",
        "estimated_cost": _paise_to_lakh(15.0),
        "sanctioned_cost": _paise_to_lakh(15.0),
        "expenditure": None,  # missing expenditure
        "financial_progress": 40.0,
        "physical_progress": 38.0,
        "sanction_date": date(2025, 3, 15),
        "start_date": date(2025, 4, 1),
        "completion_date": None,
        "status": "In Progress",
        "implementing_agency": "District Rural Development Agency",
        "contractor_name": None,
        "expected_duration_days": None,  # delay cannot be computed
    })

    return rows


FLAGSHIP_WORK_ID = "MPL-10281"
