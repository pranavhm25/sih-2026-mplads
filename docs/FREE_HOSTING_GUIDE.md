# Free Hosting & Deployment Guide (Vercel + Render)

This guide walks you through deploying **Drishti** completely **free of cost** ($0) using **Render** for the FastAPI backend and **Vercel** for the React frontend.

---

## Architecture Overview

```mermaid
flowchart LR
    Browser([User Browser]) -->|HTTPS| Vercel["Vercel (Frontend)<br/>React SPA (Global CDN)"]
    Vercel -->|VITE_API_URL / REST| Render["Render.com (Backend)<br/>FastAPI Web Service"]
    Render --> DB[("SQLite (Default Auto-seed)<br/>or Neon PostgreSQL")]
```

* **Frontend (Vercel)**: 100% Free, zero cold-starts, automatic SSL/HTTPS, instant deployments from GitHub.
* **Backend (Render)**: 100% Free Web Service (Python 3.11), auto-provisions with `render.yaml`.
* **Database**: Uses SQLite with deterministic auto-seeding on boot (`DEMO_AUTOSEED=true`), or a free cloud PostgreSQL database from [Neon](https://neon.tech) / [Supabase](https://supabase.com).

---

## Step 1: Deploy Backend to Render (Free)

### Method A: 1-Click Render Blueprint (Recommended)

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Configure free hosting with Vercel and Render"
   git push origin main
   ```
2. Log in to [Render.com](https://dashboard.render.com).
3. Click **New +** in the top navigation bar and select **Blueprint**.
4. Connect your GitHub repository (`sih-2026-mplads`).
5. Render detects [render.yaml](file:///home/venkatsaigs/Projects/sih-2026-mplads/render.yaml) automatically.
6. Click **Apply**.
7. Render will build and deploy the backend. Once deployment finishes, copy your live backend URL (e.g. `https://drishti-backend-xxxx.onrender.com`).

### Method B: Manual Web Service Setup on Render

If you prefer setting up manually without Blueprint:
1. Click **New +** -> **Web Service**.
2. Select your repository.
3. Configure the following fields:
   * **Name**: `drishti-backend`
   * **Region**: Any (e.g. `Oregon (US West)` or `Frankfurt`)
   * **Root Directory**: `backend`
   * **Runtime**: `Python 3`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   * **Instance Type**: `Free`
4. Expand **Advanced** -> **Add Environment Variable**:
   * `APP_ENV`: `production`
   * `DEMO_AUTOSEED`: `true`
   * `CORS_ORIGINS`: `*`
   * `DATABASE_URL`: `sqlite:///./drishti.db`
   * `PYTHON_VERSION`: `3.11.9`
5. Click **Create Web Service**.
6. Note down the public URL: `https://<service-name>.onrender.com`.
7. Verify it is running by visiting `https://<service-name>.onrender.com/api/v1/health` in your browser. It should respond with `{"status":"ok",...}`.

> [!NOTE]
> Render free web services spin down after 15 minutes of inactivity. When a request arrives, it takes ~45-50 seconds to wake up (cold start). For a live pitch or demo, open the backend URL in a browser 1 minute before your presentation to wake it up!

---

## Step 2: Deploy Frontend to Vercel (Free)

1. Log in to [Vercel.com](https://vercel.com).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository.
4. In the **Configure Project** screen:
   * **Project Name**: `drishti-mplads` (or any name)
   * **Framework Preset**: `Vite`
   * **Root Directory**: Click *Edit* and select `frontend` (or leave as root, both work with the included `vercel.json` files)
   * **Build and Output Settings**: Leave default (`npm run build`, `dist`)
5. Expand **Environment Variables**:
   * **Name**: `VITE_API_URL`
   * **Value**: Your Render backend URL (e.g., `https://drishti-backend-xxxx.onrender.com` without trailing slash)
6. Click **Deploy**.
7. In ~60 seconds, Vercel will give you a live production URL (e.g., `https://drishti-mplads.vercel.app`).

---

## Step 3: Optional Persistent Database (Neon / Supabase)

By default, the backend uses SQLite. On Render's free tier, the disk is ephemeral, meaning database changes reset when the container restarts. Because `DEMO_AUTOSEED=true`, all 76 works, demo officers, and cases will always automatically re-populate on every boot.

If you want **permanent database persistence** for judge feedback, case notes, and uploaded datasets:
1. Create a free PostgreSQL database on [Neon.tech](https://neon.tech) (instant, no credit card required).
2. Copy the Connection String (URI), e.g.:
   `postgresql://username:password@ep-xyz.neon.tech/neondb?sslmode=require`
3. In the Render Dashboard, go to your `drishti-backend` service -> **Environment**.
4. Edit `DATABASE_URL` and paste the connection string.
5. Click **Save Changes**. Render will automatically run Alembic migrations on startup and connect to your cloud PostgreSQL.

---

## Verification Checklist

- [ ] Visit `https://<your-backend>.onrender.com/api/v1/health` -> Returns JSON `{"status": "ok", ...}`
- [ ] Visit `https://<your-frontend>.vercel.app` -> Dashboard loads with summary metrics and Leaflet map
- [ ] Go to **Investigation Queue** -> Filter by priority or state
- [ ] Open **Project Intelligence** for work `MPL-10281` -> Verify evidence ledger and map marker
- [ ] Open **Cases** -> Create a case and generate an audit PDF report
- [ ] Refresh any deep page (e.g. `/queue`) -> Verify it loads without 404
