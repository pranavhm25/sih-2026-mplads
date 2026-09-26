#!/usr/bin/env python3
"""Drishti demo pre-warm + readiness check (docs/DEMO_RUNBOOK.md).

Two modes, one script:

  pre-warm (default)  Wake a sleeping/cold backend and block until it can
                      serve the demo. Safe to run right before presenting.

  check               Full demo-stack verification: frontend reachable,
                      backend liveness, readiness (DB + demo dataset),
                      critical API, demo login. Read-only  -  never creates
                      cases, imports data, or mutates anything.

Stdlib-only (urllib), so it runs on any machine with Python 3.9+. No
secrets required: the demo login uses the public seeded demo account
(documented in docs/DEMO_RUNBOOK.md §9)  -  the script never reads or
prints credential material.

Usage (from repo root or backend/):
  python scripts/prewarm-demo.py                       # wake Render backend
  python scripts/prewarm-demo.py --backend http://localhost:8317
  python scripts/prewarm-demo.py check                 # verify full demo stack
  python scripts/prewarm-demo.py check --frontend http://localhost:5317

Exit codes: 0 = ready / all checks passed; 1 = timed out or a check failed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BACKEND = "https://mplads-drishti-codeholics-api.onrender.com"
DEFAULT_FRONTEND = "http://localhost:5317"
DEMO_EMAIL = "ministry@drishti.demo"
DEMO_PASSWORD = "drishti-demo"  # public seeded demo account, not a secret
TIMEOUT_S = 10

# The demo-critical read-only API: if this answers, the Command Center will load.
CRITICAL_API = "/api/v1/dashboard/summary"


def _request(
    url: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    token: str | None = None,
    timeout_s: float = TIMEOUT_S,
) -> tuple[int, dict | bytes | None]:
    """One HTTP request returning (status, parsed-json-or-raw). Never raises on HTTP errors."""
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                return resp.status, raw
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return e.code, None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"  [network] {type(e).__name__}: {e}")
        return 0, None


def prewarm(base: str, max_wait_s: float) -> int:
    """Poll liveness then readiness until the backend can serve the demo."""
    base = base.rstrip("/")
    print(f"Pre-warming Drishti backend at {base}")
    print("  Liveness:  GET /api/v1/health")
    print("  Readiness: GET /api/v1/health/ready (DB + demo dataset)\n")

    deadline = time.monotonic() + max_wait_s
    live_since = None
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        code, _ = _request(f"{base}/api/v1/health", timeout_s=TIMEOUT_S)
        if code != 200:
            remaining = deadline - time.monotonic()
            print(
                f"  [{attempt:3d}] backend not responding yet (status={code or 'network'})  -  "
                f"{max(0, int(remaining))}s left"
            )
            time.sleep(3)
            continue

        if live_since is None:
            live_since = time.monotonic()
            print(f"  [{attempt:3d}] liveness OK  -  process is up; waiting for readiness...")

        code, body = _request(f"{base}/api/v1/health/ready")
        if code == 404:
            # Deployment predates the readiness endpoint: liveness is the best
            # signal available. Do not spin  -  report clearly and succeed.
            print(
                "  [!] /api/v1/health/ready not found (older deployment). "
                "Treating liveness as sufficient; DB/demo-data state unverified."
            )
            print("\nBackend is up (readiness endpoint unavailable on this build).")
            return 0
        if code == 200 and isinstance(body, dict) and body.get("ready") is True:
            checks = body.get("checks", {})
            print(f"  [{attempt:3d}] READY: {json.dumps(checks)}")
            elapsed = max_wait_s - (deadline - time.monotonic())
            print(f"\nBackend is ready to serve the demo ({elapsed:.1f}s of waiting).")
            return 0

        detail = body.get("checks") if isinstance(body, dict) else None
        print(f"  [{attempt:3d}] starting (checks={json.dumps(detail)})")
        time.sleep(3)

    print(
        f"\nFAILED: backend did not become ready within {max_wait_s:.0f}s.\n"
        "  - If this is Render free tier, the service may still be cold-starting: "
        "wait 60s and re-run, or trigger a manual deploy from the Render dashboard.\n"
        "  - Local fallback: start the backend with\n"
        "      cd backend && py -m uvicorn app.main:app --port 8317"
    )
    return 1


def check(base: str, frontend: str) -> int:
    """Full read-only demo-stack verification."""
    base = base.rstrip("/")
    failures: list[str] = []

    print(f"Verifying Drishti demo stack\n  backend:  {base}\n  frontend: {frontend}\n")

    # 1. Frontend reachable.
    code, _ = _request(frontend)
    ok = code == 200
    print(f"1. Frontend reachable ........ {'PASS' if ok else 'FAIL'} (HTTP {code or 'network'})")
    if not ok:
        failures.append(
            f"frontend unreachable at {frontend}  -  start it with "
            "'cd frontend && npm run dev' (or 'docker compose up')"
        )

    # 2. Backend liveness.
    code, body = _request(f"{base}/api/v1/health")
    ok = code == 200 and isinstance(body, dict) and body.get("status") == "ok"
    print(f"2. Backend liveness .......... {'PASS' if ok else 'FAIL'} (HTTP {code or 'network'})")
    if not ok:
        failures.append("backend not live  -  run the pre-warm script first")

    # 3. Readiness: DB + demo dataset.
    checks: dict = {}
    if ok:
        code, body = _request(f"{base}/api/v1/health/ready")
        checks = body.get("checks", {}) if isinstance(body, dict) else {}
        ok = code == 200 and isinstance(body, dict) and body.get("ready") is True
        print(
            f"3. Readiness (DB + demo data)  {'PASS' if ok else 'FAIL'} "
            f"(HTTP {code or 'network'}, checks={json.dumps(checks)})"
        )
        if not ok:
            failures.append(
                "backend not ready  -  database unreachable or demo dataset missing "
                f"(checks={json.dumps(checks)})"
            )
    else:
        print("3. Readiness (DB + demo data)  SKIP (backend not live)")

    # 4. Critical demo API (the Command Center's exact call).
    if ok:
        code, body = _request(f"{base}{CRITICAL_API}")
        ok = code == 200 and isinstance(body, dict) and "data" in body
        n_works = None
        if ok and isinstance(body, dict):
            data = body.get("data") or {}
            n_works = data.get("total_works")
        print(f"4. Critical API {CRITICAL_API}  {'PASS' if ok else 'FAIL'}"
              f" (HTTP {code or 'network'}{'' if n_works is None else f', {n_works} works'})")
        if not ok:
            failures.append(f"critical API {CRITICAL_API} failed (HTTP {code})")
    else:
        print(f"4. Critical API {CRITICAL_API}  SKIP (backend not ready)")

    # 5. Demo login (public seeded demo account  -  verifies the auth path).
    if ok:
        code, body = _request(
            f"{base}/api/v1/auth/login",
            method="POST",
            body={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        )
        ok = code == 200 and isinstance(body, dict) and "token" in (body.get("data") or {})
        print(f"5. Demo login ............... {'PASS' if ok else 'FAIL'} (HTTP {code or 'network'})")
        if not ok:
            failures.append(
                "demo login failed  -  DEMO_ACCOUNTS_ENABLED may be false or the demo "
                "dataset is not seeded"
            )
    else:
        print("5. Demo login ............... SKIP (backend not ready)")

    print()
    if failures:
        print(f"DEMO NOT READY  -  {len(failures)} problem(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("DEMO READY  -  frontend, backend, database, demo data, critical API and login all verified.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drishti demo pre-warm + readiness check (docs/DEMO_RUNBOOK.md)."
    )
    parser.add_argument(
        "mode", nargs="?", default="prewarm", choices=["prewarm", "check"],
        help="prewarm (default): wake the backend and wait for readiness; "
             "check: verify the full demo stack",
    )
    parser.add_argument("--backend", default=DEFAULT_BACKEND, help="backend base URL")
    parser.add_argument("--frontend", default=DEFAULT_FRONTEND, help="frontend base URL")
    parser.add_argument(
        "--max-wait", type=float, default=180.0,
        help="seconds to wait for readiness in prewarm mode (default 180)",
    )
    args = parser.parse_args()

    if args.mode == "prewarm":
        return prewarm(args.backend, args.max_wait)
    return check(args.backend, args.frontend)


if __name__ == "__main__":
    sys.exit(main())
