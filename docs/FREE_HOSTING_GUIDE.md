# Free Hosting & Deployment Guide (Vercel + Render) — Beginner Friendly

This is the **complete** guide to hosting **Drishti** online for **$0/month**, written for
first-time deployers. If you want the shortest possible path, read
[HOSTING_QUICKSTART.md](HOSTING_QUICKSTART.md) instead — everything below expands on it with
explanations, alternatives and troubleshooting.

---

## What you're about to build (and why it's split this way)

Drishti is a **full-stack** application, so it has two deployable parts:

| Part | What it is | Tech | Where we host it | Why there |
|---|---|---|---|---|
| **Frontend** | The dashboard in the user's browser | React + Vite → static files | **Vercel** | Static files are served free from a global CDN, with HTTPS, instantly |
| **Backend** | The API that detects signals, stores cases, generates PDFs | FastAPI (Python) | **Render** | Render runs real Python servers on a free plan (many hosts don't) |
| **Database** | SQLite file created & seeded at boot | SQLite | **Inside Render** | Zero setup. Data reseeds automatically on every restart |

```mermaid
flowchart LR
    Browser([User Browser]) -->|HTTPS| Vercel["Vercel (Frontend)<br/>React SPA (Global CDN)"]
    Vercel -->|VITE_API_URL / REST| Render["Render.com (Backend)<br/>FastAPI Web Service"]
    Render --> DB[("SQLite (Default Auto-seed)<br/>or Neon PostgreSQL")]
```

**URLs (pre-configured in this repo):**

| Service | Name | Live URL |
|---|---|---|
| Render backend | `mplads-drishti-codeholics-api` | `https://mplads-drishti-codeholics-api.onrender.com` |
| Vercel frontend | `mplads-drishti-codeholics` | `https://mplads-drishti-codeholics.vercel.app` |

> [!TIP]
> **On clean URLs:** a Render service's name **is** its URL forever (`<name>.onrender.com` —
> subdomains cannot be renamed after creation). If the exact name is taken, Render
> **silently appends random characters** (e.g. `mplads-drishti-codeholics-ab3x`). Decide the
> name *before* creating the service, and if you end up with a suffix, delete and recreate
> with a different name. Vercel is friendlier: project names can be renamed anytime under
> Project → Settings → General, and random-char URLs are just per-deployment preview
> aliases — your main `<project>.vercel.app` URL stays clean.

**The one free-tier trade-off:** Render's free plan sleeps your backend after 15 idle minutes;
the next visitor waits ~50 seconds (a "cold start"). For demos and judging, open your backend
health URL one minute before you present — or enable the keep-alive workflow
(see [§10](#10-optional-keep-alive-say-goodbye-to-cold-starts)).

---

## Step 1: Deploy Backend to Render (Free)

### Method A: 1-Click Render Blueprint (Recommended)

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Configure free hosting with Vercel and Render"
   git push origin main
   ```
2. Log in to [Render.com](https://dashboard.render.com) (sign up with GitHub).
3. Click **New +** in the top navigation bar and select **Blueprint**.
4. Connect your GitHub repository (`sih-2026-mplads`).
5. Render detects [render.yaml](../render.yaml) automatically and shows what it will create.
6. Click **Apply**.
7. Render will build and deploy the backend. Once deployment finishes, copy your live backend URL: `https://mplads-drishti-codeholics-api.onrender.com` (if Render appended random characters because the name was taken, recreate the service with a different clean name — see the URL note above).

### Method B: Manual Web Service Setup on Render

If you prefer setting up manually without Blueprint:
1. Click **New +** → **Web Service**.
2. Select your repository.
3. Configure the following fields:
   * **Name**: `mplads-drishti-codeholics-api`
   * **Region**: Any (e.g. `Oregon (US West)` or `Frankfurt` — pick the one closest to your users)
   * **Root Directory**: `backend`
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   * **Instance Type**: `Free`
4. Expand **Advanced** → **Add Environment Variable** and add:
   * `APP_ENV`: `production`
   * `DEMO_AUTOSEED`: `true`
   * `CORS_ORIGINS`: `*` (tighten to your Vercel URL after Step 2)
   * `DATABASE_URL`: `sqlite:///./drishti.db`
   * `SECRET_KEY`: any long random string (Render can generate one)
   * `PYTHON_VERSION`: `3.11.9`
5. Click **Create Web Service**.
6. Note down the public URL: `https://mplads-drishti-codeholics-api.onrender.com`.
7. Verify it is running by visiting `https://mplads-drishti-codeholics-api.onrender.com/api/v1/health` in your browser. It should respond with `{"status":"ok",...}`.

> [!NOTE]
> Render free web services spin down after 15 minutes of inactivity. When a request arrives, it takes ~45-50 seconds to wake up (cold start). For a live pitch or demo, open the backend URL in a browser 1 minute before your presentation to wake it up!

**What happens automatically on first boot:**
- Alembic migrations run (production mode) → tables are created.
- `DEMO_AUTOSEED=true` loads the deterministic demo dataset (works, signals, cases) and runs the full detection pipeline.
- Demo sign-in accounts are created (password `drishti-demo`): `ministry@drishti.demo`, `snl@drishti.demo`, `district@drishti.demo`, `mp@drishti.demo`, `admin@drishti.demo`.

---

## Step 2: Deploy Frontend to Vercel (Free)

1. Log in to [Vercel.com](https://vercel.com) (sign up with GitHub).
2. Click **Add New...** → **Project**.
3. Import your GitHub repository.
4. In the **Configure Project** screen:
   * **Project Name**: `mplads-drishti-codeholics`
   * **Framework Preset**: `Vite`
   * **Root Directory**: Click *Edit* and select `frontend`
   * **Build and Output Settings**: Leave default (`npm run build`, `dist`)
5. Expand **Environment Variables**:
   * **Name**: `VITE_API_URL`
   * **Value**: `https://mplads-drishti-codeholics-api.onrender.com` — **no trailing slash**, no `/api`
6. Click **Deploy**.
7. In ~60 seconds, Vercel will give you a live production URL: `https://mplads-drishti-codeholics.vercel.app`.

**How the frontend finds the backend:** `frontend/src/services/api.ts` reads `VITE_API_URL`
at build time and prefixes every API call with it. Locally it's empty (Vite proxies to
localhost); in production Vercel injects it before building. If you ever change it, you must
**redeploy** — it's baked into the bundle, not read live.

### Step 2.5: Lock down CORS (do not skip)

While `CORS_ORIGINS=*` any website could call your API. Once you know your Vercel URL:

1. Render Dashboard → `mplads-drishti-codeholics-api` → **Environment**.
2. Set `CORS_ORIGINS` to `https://mplads-drishti-codeholics.vercel.app` (comma-separate extra URLs if needed).
3. **Save Changes** → Render redeploys automatically.

---

## Step 3: Optional Persistent Database (Neon / Supabase)

By default, the backend uses SQLite. On Render's free tier, the disk is **ephemeral** —
database changes (uploaded datasets, case notes, officer feedback) reset when the container
redeploys, restarts, or wakes from sleep. Because `DEMO_AUTOSEED=true`, all demo works,
officers and cases always re-populate on every boot — so the demo is *self-healing*, but
genuinely new data is lost.

If you want **permanent persistence** for judge feedback, case notes, and uploaded datasets:
1. Create a free PostgreSQL database on [Neon.tech](https://neon.tech) (instant, no credit card required; free tier: ~0.5 GB storage, scales to zero after 5 min idle) or [Supabase](https://supabase.com) (500 MB, no sleep, but projects pause after 1 week of inactivity).
2. Copy the Connection String (URI), e.g.:
   `postgresql://username:password@ep-xyz.neon.tech/neondb?sslmode=require`
3. In the Render Dashboard, go to your `mplads-drishti-codeholics-api` service → **Environment**.
4. Edit `DATABASE_URL` and paste the connection string (append `?sslmode=require` if not present).
5. Click **Save Changes**. Render will automatically run Alembic migrations on startup and connect to your cloud PostgreSQL.

> The backend includes `psycopg2-binary`, so PostgreSQL works out of the box. You can switch
> back to SQLite anytime by restoring the SQLite URL.

**Not a Postgres option — known limitation:** Render's *own* free Postgres **expires after
30 days** (then 14-day grace, then deletion) and can't take backups. Use Render Postgres only
for throwaway testing; prefer Neon/Supabase for anything you want to keep.

---

## Free-tier limits & reality check (as of 2026)

| Provider | Free allowance | Sleep behaviour | Key catches |
|---|---|---|---|
| **Vercel** (frontend) | Hobby plan: 100 GB bandwidth/mo | Never (static CDN) | Non-commercial use only; 60s function limit (unused here) |
| **Render** (backend) | 750 free instance-hours/mo per workspace | Sleeps after **15 min idle**; ~50 s wake | Ephemeral disk (SQLite resets); suspends services if you exceed hours/bandwidth |
| **Neon** (Postgres) | ~0.5 GB storage | Pauses after 5 min idle; ~1 s cold resume | Some connection overhead on resume |
| **Supabase** (Postgres) | 500 MB DB | Never sleeps | Projects pause after **1 week of inactivity** (restore from dashboard) |
| **Render Postgres** | 1 GB, 1 per workspace | Never | **Expires after 30 days** — testing only |

**750 instance-hours = one service running 24/7** (31 days × 24 h ≈ 744). A second free
service would exceed the budget and get suspended. Keep-alive (§10) therefore consumes your
entire allowance — fine for a single demo deployment.

**Avoid render-suspension while pinging:** don't ping faster than every ~10 minutes; short
intervals burn instance-hours and can trip Render's service-initiated-traffic detection.
The keep-alive workflow in this repo uses 10-minute intervals for exactly this reason.

---

## Other free options compared

| Option | Effort | Pros | Cons | Verdict for Drishti |
|---|---|---|---|---|
| **Vercel + Render** (this guide) | Low | Auto-deploy from GitHub, real Python support, blueprint file included | Cold starts on free tier | ✅ **Recommended** |
| **Vercel + Koyeb** | Low | Koyeb free web service, no credit card | Free instance also scales to zero (cold start); memory limits | Good Render alternative |
| **Fly.io** | Medium | VMs, persistent volumes, generous historical free allowances | Credit card required; free-allowance terms have shifted repeatedly in 2025-26 | Good if you want persistence |
| **Hugging Face Spaces** | Low | Simple, well-known | Free CPU Spaces sleep; Docker SDK on Spaces is now a **paid** feature (mid-2026), so this FastAPI container no longer fits free | ❌ Not viable free anymore |
| **Railway** | Low | Excellent DX | Free one-time trial credit only — no ongoing free plan | ❌ Not $0 ongoing |
| **Heroku** | Low | Classic | Free tier abolished (2022); paid only | ❌ |
| **PythonAnywhere** | Low | Always-on free Python web apps | Free tier is HTTP-only, heavy apps constrained, async/uvicorn support poor | ❌ Poor fit for FastAPI |
| **Oracle Cloud Always Free** | High | Genuinely free VM (ARM, 24 GB RAM total) | Requires credit card, capacity often unavailable, you manage the whole VM | Power-user option |

---

## Verification Checklist

- [ ] Visit `https://mplads-drishti-codeholics-api.onrender.com/api/v1/health` → Returns JSON `{"status": "ok", ...}`
- [ ] Visit `https://mplads-drishti-codeholics.vercel.app` → Dashboard loads with summary metrics and Leaflet map
- [ ] Go to **Investigation Queue** → Filter by priority or state
- [ ] Open **Project Intelligence** for work `MPL-10281` → Verify evidence ledger and map marker
- [ ] Open **Cases** → Create a case and generate an audit PDF report
- [ ] Refresh any deep page (e.g. `/queue`) → Verify it loads without 404

---

## 🔧 Troubleshooting

<details>
<summary><strong>“Network Error” / no data in the frontend</strong></summary>

1. Open the deployed frontend → browser DevTools → **Console** and **Network** tabs.
2. Failing request to `undefined/api/v1/...` or `localhost:8317` → `VITE_API_URL` wasn't set when Vercel built.
   Fix: Vercel → Settings → Environment Variables → add it → **Deployments → ⋯ → Redeploy** (must be set *before* the build).
3. Failing request to the correct Render URL but status 0 / CORS error → backend CORS check (next item).
4. Backend URL itself times out for ~50 s then works → normal free-tier cold start.
</details>

<details>
<summary><strong>CORS error in the browser console (“blocked by CORS policy”)</strong></summary>

- `CORS_ORIGINS` on Render must **exactly** match the origin shown in your browser address bar:
  scheme included (`https://`), **no trailing slash**, correct subdomain.
- Vercel preview deployments get their own URLs (`…-abc123.vercel.app`). Either add them to the
  comma-separated `CORS_ORIGINS` list, or set `*` temporarily while demoing.
- After changing env vars on Render, wait for the auto-redeploy to finish before retesting.
</details>

<details>
<summary><strong>Backend deployment fails on Render (build or crash loop)</strong></summary>

- Read the **Logs** tab — the failing line is usually near the bottom.
- Build fails on pip install → a dependency or Python version mismatch; `PYTHON_VERSION=3.11.9` is pinned in render.yaml.
- App crashes at boot → missing env var. Required set: `APP_ENV`, `DEMO_AUTOSEED`, `CORS_ORIGINS`, `DATABASE_URL`, `SECRET_KEY`.
- "Migrations failed" warning at startup → the app falls back to `create_all` automatically; harmless on a fresh database.
</details>

<details>
<summary><strong>502 / service suspended on Render</strong></summary>

- Suspended service + email from Render → you exceeded 750 instance-hours (more than one always-on free service) or bandwidth. Wait for the 1st of the month, or remove the extra service.
- 502 right after waking → the service is still mid-startup; retry in ~30 s.
</details>

<details>
<summary><strong>404 when refreshing a deep link (e.g. /queue) on Vercel</strong></summary>

Should not happen — `frontend/vercel.json` rewrites all routes to `index.html`. If it does,
confirm the file is committed and that **Root Directory** was set to `frontend` (the rewrite
must ship inside the deployed output).
</details>

<details>
<summary><strong>Cannot log in on the deployed site</strong></summary>

Demo accounts exist only when `DEMO_AUTOSEED=true` and `DEMO_ACCOUNTS_ENABLED=true` (both
default on). Password for all demo accounts: `drishti-demo`. If you connected a fresh Postgres
database, wait for first-boot seeding to complete (watch the Render logs for the seed message).
</details>

<details>
<summary><strong>Health check passes but the PDF report download fails</strong></summary>

PDFs are written to a local `reports/` directory. On Render's ephemeral disk they survive
until the next restart/sleep. This is acceptable for demos; for persistence, connect a
Postgres database and/or treat reports as regenerable artifacts.
</details>

---

## Step 10 (optional): Keep-alive — say goodbye to cold starts

This repo includes an optional GitHub Actions workflow (`.github/workflows/keep-alive.yml`)
that pings `https://mplads-drishti-codeholics-api.onrender.com/api/v1/health` every 10
minutes, keeping Render awake around the clock. See the note at the top of that file for
setup (it's off by default).

**Trade-off:** 24/7 keep-alive consumes ~744 of your 750 monthly free instance-hours — it
fits exactly one service. Don't enable it if you also run other free services on the same
Render workspace. Never shorten the interval below 10 minutes (see [§Free-tier limits](#free-tier-limits--reality-check-as-of-2026)).

For a one-off demo day, simply waking the backend manually one minute before is cheaper
and simpler.
