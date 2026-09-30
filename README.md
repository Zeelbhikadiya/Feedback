# LeaderPulse — Leader Feedback, Poll & Grade System

Internal campaign-based feedback platform from the product requirements PDF.

## Stack

| Layer | Tech |
|--------|------|
| Frontend | Next.js 14 + TypeScript + Tailwind + Recharts |
| Backend | Python FastAPI |
| Database | SQLite (dev) / PostgreSQL via `DATABASE_URL` |
| Auth | JWT email/password + SSO stub (OIDC-ready) |
| AI themes | OpenAI when `OPENAI_API_KEY` set, else rule-based |
| Export | PDF + Excel |
| Jobs | APScheduler (auto open/close + final reminders) |

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# if bcrypt/passlib conflict: pip install bcrypt==4.2.1
python seed.py
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

## Demo logins

Password for all: `Password123!`

| Email | Role |
|--------|------|
| admin@company.local | System Admin |
| hr@company.local | Management / HR |
| grouphead@company.local | Group Head |
| e1@company.local … e5@company.local | Employees (poll voters) |
| leader@company.local | Poll target leader |
| viewer@company.local | Result Viewer |

Seeded open campaigns:

- **Production Leader Review - Q4** (Poll)
- **Production Team Ranking - Sept** (Grade)

## PDF features covered

- Roles & campaign lifecycle (Draft → Archived)
- Poll + Comment (1–10, comment rules, one response)
- Grade unique 1–N locking, draft + final submit
- Named / Anonymous Result / Strict Anonymous
- Management dashboard, pending list, reminders
- AI/theme comment analysis, leader trends
- PDF/Excel export, calendar `.ics`
- Audit + notification logs
- Multi-language UI (EN / GU / HI)
- SSO wiring (dev login + OIDC env placeholders)
- Auto open/close via scheduler

## Config (`backend/.env`)

- `DATABASE_URL` — default SQLite; set Postgres URL for production
- `OPENAI_API_KEY` — optional AI summaries
- `SMTP_*` — optional real email
- `OIDC_*` — company SSO

## Production notes

- Change `SECRET_KEY`
- Use PostgreSQL
- Configure real OIDC callback (replace `/api/auth/sso/dev-login`)
- Put frontend and API behind HTTPS
