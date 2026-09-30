# LeaderPulse — FREE Deploy Guide

Badhu **free tier** par: Vercel (frontend) + Render (API) + Neon (Postgres).

Repo: https://github.com/Zeelbhikadiya/Feedback.git

```
Vercel Free  →  Next.js UI
Render Free  →  FastAPI API
Neon Free    →  PostgreSQL
```

> Note: free API idle pachi sleep thai shake (cold start 30–60s). Paid nathi joi.

---

## Step 1 — Free Postgres (Neon) ~3 min

1. https://neon.tech → Sign up (GitHub OK)
2. **Create project** → name: `leaderpulse`
3. **Connection string** copy karo (URI), jem ke:

```text
postgresql://user:password@ep-xxxx.aws.neon.tech/neondb?sslmode=require
```

App automatically `postgresql://` ne SQLAlchemy form ma convert kare.

---

## Step 2 — Free API (Render) ~7 min

1. https://render.com → Sign up (GitHub)
2. **New** → **Web Service**
3. Connect repo: `Zeelbhikadiya/Feedback`
4. Settings:

| Field | Value |
|--------|--------|
| Name | `leaderpulse-api` |
| Region | closest to you |
| Root Directory | `backend` |
| Runtime | **Docker** |
| Instance type | **Free** |
| Health Check Path | `/api/health` |

5. **Environment** variables:

| Key | Value |
|-----|--------|
| `DATABASE_URL` | Neon connection string (Step 1) |
| `SECRET_KEY` | koi pan long random text (20+ chars) |
| `SEED_ON_STARTUP` | `true` |
| `CORS_ORIGINS` | `*` (temporary; Vercel URL pachi update) |
| `FRONTEND_URL` | `https://placeholder.vercel.app` (pachi update) |

6. **Create Web Service** → wait until Live
7. URL copy: `https://leaderpulse-api.onrender.com`
8. Test: `https://YOUR-API.onrender.com/api/health` → `{"status":"ok"}`

---

## Step 3 — Free Website (Vercel) ~5 min

1. https://vercel.com → Sign up (GitHub)
2. **Add New Project** → import `Feedback`
3. Configure:

| Field | Value |
|--------|--------|
| Framework | Next.js |
| Root Directory | `frontend` (Edit → select) |
| Build | default |

4. Environment Variable:

| Key | Value |
|-----|--------|
| `NEXT_PUBLIC_API_URL` | Render API URL, e.g. `https://leaderpulse-api.onrender.com` |

5. **Deploy**
6. Site URL copy: `https://feedback-xxxx.vercel.app`

---

## Step 4 — CORS link (important)

Render → Environment → update:

| Key | Value |
|-----|--------|
| `CORS_ORIGINS` | your exact Vercel URL (no trailing slash) |
| `FRONTEND_URL` | same Vercel URL |
| `SEED_ON_STARTUP` | `false` (seed ek vaar thai gayu hoy to) |

**Manual Deploy** / restart API.

---

## Step 5 — Login

Open Vercel URL → login:

| Email | Password |
|--------|----------|
| `hr@company.local` | `Password123!` |
| `admin@company.local` | `Password123!` |
| `e1@company.local` | `Password123!` |

---

## Free limits (reality)

| Service | Free |
|---------|------|
| Vercel | Hobby — OK for this app |
| Render | Free web — sleeps after ~15 min idle |
| Neon | Free DB — enough for demo/small team |

First open after sleep: API 30–60s late thai shake — normal free tier.

---

## Optional: local free Docker test

PC par Docker Desktop free:

```powershell
docker compose up --build
```

- http://localhost:3000
- http://localhost:8000/docs

---

## Stuck?

1. API health fail → `DATABASE_URL` / Docker build logs check
2. Login fail / CORS error → `CORS_ORIGINS` exact Vercel URL
3. Frontend blank API errors → `NEXT_PUBLIC_API_URL` wrong / redeploy frontend after changing it
