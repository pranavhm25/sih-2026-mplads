# 🚀 Drishti — Free Hosting in 30 Minutes (Beginner Quickstart)

> **New to hosting?** Start here. This guide assumes you know **nothing** about deployment.
> After these steps you will have a public website you can share with anyone:
> a **frontend** (the app you see) on Vercel and a **backend** (the API brain) on Render — both 100% free.
>
> For deeper explanations, troubleshooting and other free options, see the full guide:
> [FREE_HOSTING_GUIDE.md](FREE_HOSTING_GUIDE.md)

---

## 0. What you need before starting (2 minutes)

| Prerequisite | How to check | If you don't have it |
|---|---|---|
| Your code is on **GitHub** | You have a repo URL like `github.com/you/sih-2026-mplads` | See "Push to GitHub" below |
| A **GitHub account** | — | Sign up free at [github.com](https://github.com) |
| Nothing else! | — | No credit card needed anywhere in this guide |

### Push your code to GitHub (if you haven't already)

```bash
# Inside the project folder:
git add .
git commit -m "Prepare for free cloud deployment"
git push origin main
```

> Never committed before? Git will ask for your name/email first: `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`. When pushing, GitHub no longer accepts your account password — use a **Personal Access Token** (GitHub → Settings → Developer settings → Personal access tokens) as the password, or just use **GitHub Desktop** (graphical, no terminal needed).

---

## 1. Deploy the backend on Render (~10 minutes)

The backend is the FastAPI server that powers detection, cases and reports.

1. Go to **[dashboard.render.com](https://dashboard.render.com)** → sign up with your **GitHub** account (fastest — no password to remember).
2. Click **New +** → **Web Service**.
3. If asked, click **Connect** next to your GitHub repository (`sih-2026-mplads`).
4. Fill in the form **exactly** like this:

   | Field | Value |
   |---|---|
   | Name | `drishti-backend-h2c8` |
   | Language / Runtime | `Python 3` |
   | Branch | `main` |
   | Root Directory | `backend` |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |

5. Click **Add Environment Variable** and add these **five** rows:

   | Key | Value |
   |---|---|
   | `APP_ENV` | `production` |
   | `DEMO_AUTOSEED` | `true` |
   | `CORS_ORIGINS` | `*` (temporarily — you'll tighten this in Step 2.5) |
   | `DATABASE_URL` | `sqlite:///./drishti.db` |
   | `PYTHON_VERSION` | `3.11.9` |

   *(Render auto-generates `SECRET_KEY` when using the render.yaml blueprint; if deploying manually, also add `SECRET_KEY` with any long random text.)*

6. Click **Create Web Service** (or **Deploy Web Service**). The first build takes ~5 minutes — grab a coffee ☕.
7. When the status turns **Live**, click the URL at the top: **`https://drishti-backend-h2c8.onrender.com`**.
8. **Verify:** open `https://drishti-backend-h2c8.onrender.com/api/v1/health` → you should see `{"status":"ok","service":"drishti-api"}`.
   **Write this URL down — you need it in Step 2.**

> 💡 **Faster option:** if your repo contains `render.yaml` (it does!), you can instead click **New + → Blueprint**, pick the repo, and Render fills in everything above automatically.

---

## 2. Deploy the frontend on Vercel (~5 minutes)

The frontend is the React dashboard your users see.

1. Go to **[vercel.com](https://vercel.com)** → sign up with **GitHub**.
2. Click **Add New...** → **Project**.
3. Click **Import** next to `sih-2026-mplads`.
4. Configure:
   - **Framework Preset:** `Vite` (usually auto-detected)
   - **Root Directory:** click **Edit** → select `frontend`
   - **Build Command / Output:** leave defaults (`npm run build` → `dist`)
5. Open **Environment Variables** and add **one** row:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://drishti-backend-h2c8.onrender.com` |

   ⚠️ **No trailing slash**, no `/api` at the end — just the bare URL.

6. Click **Deploy** and wait ~60 seconds.
7. **Verify:** open **`https://mplads-drishti-codeholics.vercel.app`** → the Drishti Command Center should load with summary metrics and a map.

### 🏷️ Why URLs sometimes get random characters (and how to avoid it)

- **Render:** the service name **is** the URL, forever — `<name>.onrender.com` can never be
  renamed after creation. If the exact name is already taken (globally, across all Render
  users), Render **silently appends random characters** like `mplads-drishti-codeholics-ab3x`.
  So decide the name **before** clicking Create. If you already deployed with a suffix, just
  delete the service and recreate it with a different name — free tier, so it only costs ~5
  minutes. Stuck for alternatives? Try `mplads-drishti`, `drishti-codeholics` or add a year
  like `mplads-drishti-codeholics-2026`.
- **Vercel:** the project name becomes `<project>.vercel.app` and **can be renamed anytime**
  (Project → Settings → General → Project Name). Extra random-char URLs such as
  `project-abc123.vercel.app` are per-deployment preview aliases — your main URL stays clean,
  so you can ignore them.

**This repo is pre-configured for:**

| Service | Name | Live URL |
|---|---|---|
| Render backend | `drishti-backend-h2c8` | `https://drishti-backend-h2c8.onrender.com` |
| Vercel frontend | `mplads-drishti-codeholics` | `https://mplads-drishti-codeholics.vercel.app` |

---

## 2.5. Secure the backend (2 minutes, do not skip)

Right now the API accepts requests from any website. Lock it to your frontend only:

1. Render Dashboard → your `drishti-backend-h2c8` service → **Environment** (left sidebar).
2. Edit `CORS_ORIGINS` → set it to your Vercel URL:
   ```
   https://mplads-drishti-codeholics.vercel.app
   ```
3. **Save Changes** — Render redeploys automatically (~2 min).

*(Hosting multiple frontends later? CORS accepts a comma-separated list, e.g. `https://a.vercel.app,https://b.vercel.app`.)*

---

## 3. Sign in to your live site 🎉

The demo dataset is seeded automatically on first boot. Sign in on your deployed site with any of these demo accounts (password for all: `drishti-demo`):

| Account | Email |
|---|---|
| Ministry Reviewer | `ministry@drishti.demo` |
| State Nodal Officer | `snl@drishti.demo` |
| District Authority | `district@drishti.demo` |
| Hon'ble MP (demo) | `mp@drishti.demo` |
| Platform Admin | `admin@drishti.demo` |

---

## 4. The one quirk you must know: cold starts ❄️

Render's **free** tier puts your backend to sleep after **15 minutes without traffic**. The next visitor waits **~50 seconds** on a "spinning up" screen. This is normal and free.

**Two easy fixes:**
- **Before a demo/presentation:** open `https://drishti-backend-h2c8.onrender.com/api/v1/health` in a browser tab ~1 minute before you start. It wakes the server.
- **Fully automatic:** this repo ships an optional GitHub Actions workflow (`.github/workflows/keep-alive.yml`) that pings your backend every 10 minutes so it never sleeps. To switch it on, see the short note at the top of that file. Keep-alive runs your service 24/7, which consumes ~744 of the 750 free instance-hours Render grants each workspace per month — fine for one service, but don't enable it if you also run other free services on the same account.

**Why not just pay?** Upgrading the Render instance to paid (~$7/mo) removes cold starts entirely — but this guide is about $0.

---

## 5. Done — what you built

```
GitHub repo ──(auto-deploy on every push)──►  Vercel (frontend)  ──HTTPS──►  Render (backend)
                                                    │                            │
                                              Free SSL + CDN             SQLite + demo data
                                                                           (reseeds on boot)
```

Every `git push` to `main` now automatically redeploys both sides. **Total cost: $0.**

---

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| Frontend loads but no data / "Network Error" | `VITE_API_URL` wrong or missing → fix it in Vercel → Settings → Environment Variables, then **Deployments → ⋯ → Redeploy** |
| Browser console says "CORS policy" blocked | `CORS_ORIGINS` on Render must exactly match your Vercel URL (https, no trailing slash) — or set `*` while debugging |
| Backend URL shows "spinning up" for a minute | Normal cold start — wait, or set up keep-alive |
| Build fails on Render | Check the **Logs** tab; the most common cause is a missing dependency in `requirements.txt` |
| 404 when refreshing a page on Vercel | Should not happen — `frontend/vercel.json` already rewrites all routes to `index.html`. If it does, confirm the file is committed |
| Login says invalid credentials | Demo accounts are seeded only when `DEMO_AUTOSEED=true` and `DEMO_ACCOUNTS_ENABLED=true` (both are the defaults) |

More help: [FREE_HOSTING_GUIDE.md → Troubleshooting](FREE_HOSTING_GUIDE.md#-troubleshooting).
