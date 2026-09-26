# Drishti — Demo Runbook (SIH 2026)

Operational guide for running the Drishti demo reliably, including against a
sleeping free-tier backend. Print this page or keep it open on a second device.

**Golden rule:** run the pre-warm script **15 minutes before** the demo, then
run the demo-check. If both pass, the demo will not be interrupted by
infrastructure.

Measured on the dev machine (Windows, local `uvicorn`, SQLite): **cold boot to
liveness ≈ 10.7 s, to READY ≈ 12.7 s** (interpreter + imports dominate; demo
seed + detection add ~2 s on an empty DB). Warm restart is the same (~12.8 s)
because imports dominate. A sleeping Render free-tier service needs an
additional **30–60 s** to wake (estimate — not measured here). Every endpoint
and command below is real and verified in this repository.

---

## 1. Before-demo checklist

- [ ] Backend pre-warmed and reporting **READY** (§2)
- [ ] `check` mode passes all 5 checks (§10)
- [ ] Logged in on screen: `ministry@drishti.demo` / `drishti-demo` (§4)
- [ ] Command Center loads with the synthetic demo dataset banner visible
- [ ] Flagship demo project open: **MPL-10281** ↔ **MPL-10412** duplicate pair
      (Project Intelligence shows Distance 7 m, Context HIGH)
- [ ] Case creation + report generation tested once beforehand
- [ ] Local fallback backend ready to start on port 8317 (§8)

## 2. Backend warm-up (pre-warm)

Wake the backend and wait for true readiness (DB + demo dataset):

```bash
python scripts/prewarm-demo.py                       # Render backend
python scripts/prewarm-demo.py --backend http://localhost:8317   # local
```

Polls `GET /api/v1/health` (liveness) then `GET /api/v1/health/ready`
(database + demo dataset). Exits 0 on READY, 1 on timeout (default 180 s,
`--max-wait 240` to extend). Run it again any time the demo pauses >15 min.

## 3. Health check

| Endpoint | Answers | Use |
|---|---|---|
| `GET /api/v1/health` | `{status, service}` | liveness — instant, no DB |
| `GET /api/v1/health/ready` | 200 `ready:true` or 503 `{status:"starting", checks}` | readiness — DB + demo data |

Both are read-only and never run the detection pipeline. The readiness probe
exists so tools (and the UI gate) can distinguish "backend waking up" from
"backend broken".

## 4. Login check

The login screen offers the seeded stakeholder demo accounts (enabled via
`DEMO_ACCOUNTS_ENABLED=true`). Verify one:

```bash
curl -s -X POST http://localhost:8317/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ministry@drishti.demo","password":"drishti-demo"}'
```

Expect 200 with a `token`. These are public demo credentials (documented in
docs/MEMORY.md), not secrets. The demo-check (§10) verifies this automatically.

## 5. Critical workflow check

The single most demo-critical API is the Command Center's:

```bash
curl -s http://localhost:8317/api/v1/dashboard/summary | head -c 200
```

Expect 200 + `"data"`. The demo-check calls exactly this endpoint. On the
demo dataset it answers in well under a second (measured 0.37 s warm,
0.47 s cold). If you plan to demonstrate case creation or report generation,
click through them once before the audience arrives.

## 6. What to do if the backend is sleeping (Render free tier)

The UI will show **"Drishti backend is starting. Retrying connection…"** —
this is expected behavior, not a crash. The frontend retries GET requests
with exponential backoff (~23 s window) and the page gate polls readiness
(~90 s window).

1. Run `python scripts/prewarm-demo.py` on your machine (or any machine).
2. Wait for `Backend is ready to serve the demo`.
3. Click **Retry connection** in the UI — or just wait; the gate recovers by
   itself.

If the gate gives up (backend down state), it still shows a Retry button and
runbook pointers — never a stack trace.

## 7. What to do if the frontend cannot connect

1. `check` mode tells you which side failed:
   `python scripts/prewarm-demo.py check --frontend http://localhost:5317`
2. Frontend down → `cd frontend && npm run dev` (port 5317), or
   `docker compose up` for the whole stack.
3. Backend down → `cd backend && py -m uvicorn app.main:app --port 8317`.
4. Backend up but "starting" → let it finish; check `/api/v1/health/ready`.
5. If `VITE_API_URL` is unset in production the frontend calls its own origin
   (nginx proxies `/api` in Docker; on Render configure the env var — see §9).

## 8. Backup / demo fallback procedure

If the hosted backend cannot be recovered in ~2 minutes:

```bash
# Local fallback backend (same code, same demo data):
cd backend
py -m uvicorn app.main:app --port 8317

# Frontend pointed at the local backend (new terminal):
cd frontend
# PowerShell:  $env:VITE_API_URL="http://localhost:8317"; npm run dev
# bash:        VITE_API_URL=http://localhost:8317 npm run dev
```

Then re-run the demo-check against localhost. Total local cold boot to READY
is ~13 s, so the fallback is fast. As a last resort the synthetic dataset and
detection results are reproducible offline at any time (`DEMO_AUTOSEED=true`)
— the demo never depends on a live external data source.

## 9. Environment variables

Backend (see `.env.example`; never commit real secrets):

| Var | Purpose for the demo |
|---|---|
| `DATABASE_URL` | `sqlite:///./drishti.db` (demo) or Postgres |
| `APP_ENV` | `production` on Render (alembic migrate at boot) |
| `SECRET_KEY` | token signing — keep stable or all sessions revoke |
| `CORS_ORIGINS` | frontend origin(s); render.yaml uses `*` for the demo |
| `DEMO_AUTOSEED` | `true` → seed demo dataset when DB is empty |
| `DEMO_ACCOUNTS_ENABLED` | `true` → enable §4 demo logins |
| `REPORT_STORAGE_PATH` | where generated PDFs are written |

Frontend:

| Var | Purpose |
|---|---|
| `VITE_API_URL` | backend base URL, e.g. the Render URL; empty = same origin |

## 10. Exact commands

```bash
# 1. Pre-warm (15 min before) — exits 0 when READY
python scripts/prewarm-demo.py

# 2. Verify the full stack (read-only)
python scripts/prewarm-demo.py check

# 3. Health probes by hand
curl -s https://mplads-drishti-codeholics-api.onrender.com/api/v1/health
curl -s https://mplads-drishti-codeholics-api.onrender.com/api/v1/health/ready

# 4. Critical API
curl -s https://mplads-drishti-codeholics-api.onrender.com/api/v1/dashboard/summary | head -c 200

# 5. Demo login
curl -s -X POST https://mplads-drishti-codeholics-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ministry@drishti.demo","password":"drishti-demo"}'

# Local stack
docker compose up                 # frontend :5317, backend :8317
cd backend && py -m uvicorn app.main:app --port 8317    # backend only
cd frontend && npm run dev                              # frontend only
```

Notes: the demo dataset is always labeled synthetic ("Controlled synthetic
demo — not official MPLADS records"); detection numbers are priorities for
investigation, never fraud verdicts. `check` mode performs only read-only
requests plus one demo login — it never mutates demo data.
