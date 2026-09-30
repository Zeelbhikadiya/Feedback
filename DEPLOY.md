# LeaderPulse — Deploy Guide

Repo: https://github.com/Zeelbhikadiya/Feedback.git

## Architecture

```
Vercel (Next.js frontend)
        │
        ▼ REST
Railway / Render (FastAPI backend)
        │
        ▼
PostgreSQL (Railway/Render/Neon)
```

---

## 1) Backend — Railway (recommended)

1. Open [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
2. Select `Zeelbhikadiya/Feedback`
3. Set **Root Directory** = `backend`
4. Add a **PostgreSQL** plugin/service in the same project
5. In the API service, set variables:

| Variable | Value |
|----------|--------|
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway variable reference) |
| `SECRET_KEY` | long random string |
| `CORS_ORIGINS` | your Vercel URL, e.g. `https://feedback-xxx.vercel.app` |
| `FRONTEND_URL` | same Vercel URL |
| `SEED_ON_STARTUP` | `true` (first deploy only, then set `false`) |
| `PORT` | Railway usually injects this |

6. Deploy → copy public API URL, e.g. `https://leaderpulse-api.up.railway.app`
7. Confirm health: `https://YOUR-API/api/health`

Docker uses `backend/Dockerfile` + `start.sh` (creates tables, optional seed, starts uvicorn).

### Backend — Render (alternative)

1. [render.com](https://render.com) → New → Blueprint
2. Connect the GitHub repo
3. It can use `backend/render.yaml`
4. Set `CORS_ORIGINS` and `FRONTEND_URL` after Vercel URL is known
5. First deploy with `SEED_ON_STARTUP=true`

---

## 2) Frontend — Vercel

1. Open [vercel.com](https://vercel.com) → **Add New Project** → import `Zeelbhikadiya/Feedback`
2. Configure:
   - **Root Directory:** `frontend`
   - Framework: Next.js
3. Environment variable:

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_API_URL` | your Railway/Render API URL (no trailing slash) |

4. Deploy
5. Copy the Vercel URL → go back to backend and update `CORS_ORIGINS` + `FRONTEND_URL`
6. Redeploy backend once CORS is updated

---

## 3) First login (after seed)

Password: `Password123!`

- `hr@company.local` — Management
- `admin@company.local` — Admin
- `e1@company.local` — Employee
- `grouphead@company.local` — Group Head

Then set `SEED_ON_STARTUP=false` and change the admin password in production.

---

## 4) Local production-like test (Docker)

```powershell
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000/docs
- DB: Postgres on `localhost:5432`

---

## 5) Checklist

- [ ] Postgres connected (not SQLite)
- [ ] Strong `SECRET_KEY`
- [ ] `CORS_ORIGINS` matches exact Vercel URL (https)
- [ ] `NEXT_PUBLIC_API_URL` points to live API
- [ ] Health check `/api/health` returns `{"status":"ok"}`
- [ ] Seed once, then disable
- [ ] Optional: `OPENAI_API_KEY`, SMTP, OIDC for full features

---

## Env templates

- Backend: `backend/.env.example`
- Frontend: `frontend/.env.example`
