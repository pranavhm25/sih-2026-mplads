"""Run the synthetic injection benchmark and write the results artifact.

Usage (from backend/):
    py scripts/run_synthetic_validation.py                # default seed
    py scripts/run_synthetic_validation.py --seed 12345
    py scripts/run_synthetic_validation.py --out path.json

Writes docs/synthetic_validation_results.json by default. Every number in
docs/SYNTHETIC_VALIDATION.md comes from this artifact — never hand-written.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Synthetic Model Validation — controlled injection benchmark"
    )
    parser.add_argument("--seed", type=int, default=26102)
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="output JSON path (default: docs/synthetic_validation_results.json)",
    )
    args = parser.parse_args()

    # Deterministic scratch database — the benchmark cleans up after itself,
    # and a throwaway file DB keeps the run self-contained.
    scratch = tempfile.mkdtemp(prefix="drishti-synval-")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{scratch}/synval.db")
    os.environ["DEMO_AUTOSEED"] = "false"
    os.environ["REPORT_STORAGE_PATH"] = os.path.join(scratch, "reports")

    import app.models  # noqa: F401 — register models before create_all
    from app.core.database import Base, SessionLocal, engine

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        from app.services.validation.synthetic.benchmark import run_full_benchmark

        report = run_full_benchmark(seed=args.seed, db=db)
    finally:
        db.close()

    out_path = (
        Path(args.out)
        if args.out
        else BACKEND_DIR.parent / "docs" / "synthetic_validation_results.json"
    )
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    o = report["overall"]
    m = o["metrics"]

    def fmt(v):
        return "n/a" if v is None else f"{v:.4f}"

    print("Synthetic Model Validation — controlled injection benchmark")
    print(f"  seed: {args.seed}  scenarios: {len(report['scenarios'])}")
    print(f"  overall: TP={o['cm']['tp']} FP={o['cm']['fp']} "
          f"TN={o['cm']['tn']} FN={o['cm']['fn']} "
          f"(injected={o['total_injected']})")
    print(f"  precision={fmt(m['precision'])} recall={fmt(m['recall'])} "
          f"f1={fmt(m['f1'])} fpr={fmt(m['false_positive_rate'])} "
          f"detection_rate={fmt(m['detection_rate'])}")
    for name, s in report["scenarios"].items():
        sm = s["metrics"]
        print(f"  {name:22s} P={fmt(sm['precision'])} R={fmt(sm['recall'])} "
              f"F1={fmt(sm['f1'])} FPR={fmt(sm['false_positive_rate'])}")
    print(f"  results written to: {out_path}")
    print("  NOTE: controlled synthetic benchmark — NOT real-world "
          "fraud detection accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
