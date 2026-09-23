"""Scale benchmark (backlog #8).

Generates BENCHMARK_ROW_COUNT synthetic work rows, imports them through the
full official ingestion pipeline (parse → detect → map → normalize → validate
→ persist), and reports wall-time and throughput.

Run:
    cd backend && py -m scripts.benchmark_scale

Result is printed and written to docs/benchmark_result.json for the deck.
The fixture is a SYNTHETIC load test — never presented as MPLADS data.
"""
from __future__ import annotations

import csv
import io
import json
import random
import time
from pathlib import Path

from app.core.constants import BENCHMARK_ROW_COUNT, BENCHMARK_SEED
from app.core.database import SessionLocal
from app.db import create_all
from app.services.ingestion.orchestrator import import_official_file

STATES = ["Karnataka", "Uttar Pradesh", "Bihar", "Maharashtra", "West Bengal",
          "Tamil Nadu", "Rajasthan", "Madhya Pradesh", "Kerala", "Odisha"]
DISTRICTS = ["North", "South", "East", "West", "Central", "Rural", "Urban", "Coastal"]
CATEGORIES = ["Education", "Health", "Roads", "Water Supply", "Electricity",
              "Sports", "Sanitation", "Buildings"]
DESCRIPTIONS = [
    "Construction of additional classrooms at government school",
    "Installation of street lights in ward",
    "Construction of community hall",
    "Providing drinking water facility",
    "Repair of approach road",
    "Construction of anganwadi building",
    "Development of playground",
    "Purchase of medical equipment for primary health centre",
]


def build_csv(rows: int) -> bytes:
    rng = random.Random(BENCHMARK_SEED)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["work_id", "state", "district", "work_name",
                     "sanctioned_amount", "expenditure", "physical_progress",
                     "financial_progress", "sanction_date", "status",
                     "implementing_agency", "category"])
    for i in range(rows):
        sanctioned = rng.randrange(5, 400) * 100_000
        expenditure = int(sanctioned * rng.uniform(0.2, 1.1))
        writer.writerow([
            f"BENCH-{i:07d}",
            rng.choice(STATES),
            f"{rng.choice(DISTRICTS)} District",
            rng.choice(DESCRIPTIONS),
            sanctioned,
            expenditure,
            rng.randrange(0, 101),
            rng.randrange(0, 101),
            f"2024-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}",
            rng.choice(["Ongoing", "Completed", "Sanctioned"]),
            "Public Works Division",
            rng.choice(CATEGORIES),
        ])
    return buf.getvalue().encode()


def run(row_count: int = BENCHMARK_ROW_COUNT) -> dict:
    create_all()
    raw = build_csv(row_count)
    db = SessionLocal()
    try:
        t0 = time.perf_counter()
        summary = import_official_file(
            db, raw, file_name="benchmark_synthetic_load_test.csv",
            dataset_type="WORK_LEVEL", is_synthetic=True, pipeline_runner=None,
        )
        elapsed = time.perf_counter() - t0
        result = {
            "rows": row_count,
            "elapsed_seconds": round(elapsed, 2),
            "rows_per_second": round(row_count / elapsed, 0),
            "valid_rows": summary["valid_rows"],
            "error_rows": summary["error_rows"],
            "quality_status": summary["quality_status"],
            "note": "Synthetic load test; full ingestion pipeline, detection excluded.",
        }
        out = Path(__file__).resolve().parent.parent.parent / "docs/benchmark_result.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        return result
    finally:
        db.close()


if __name__ == "__main__":
    run()
