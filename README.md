# HostFlow

Unified inbox and messaging automation for Airbnb hosts. Manage guest conversations from WhatsApp, Gmail, and other channels in one place — with AI-drafted replies, message templates, and automated sends.

## Tech Stack

| Layer     | Technology                                    |
|-----------|-----------------------------------------------|
| Backend   | Python 3.12, FastAPI, SQLAlchemy 2 (asyncpg) |
| Frontend  | React 18, Vite, Tailwind CSS                 |
| Database  | PostgreSQL 16                                 |
| AI        | OpenAI GPT-4o / GPT-4o-mini                  |
| Payments  | Stripe                                        |
| Email     | Resend (transactional) + Gmail OAuth (inbox) |
| Messaging | WhatsApp Business Cloud API (Meta)           |
| Storage   | Local filesystem (dev) or S3 / Cloudflare R2 |

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (or Docker)
- `make` (Git Bash or WSL on Windows)

---

## First-Time Setup

```bash
# 1. Clone
git clone <repo-url>
cd HostFlow

# 2. Install all dependencies and create .env
make setup

# 3. Fill in your secrets
#    Open backend/.env and set at minimum:
#      SECRET_KEY, DATABASE_URL, OPENAI_API_KEY
nano backend/.env   # or any editor

# 4. Start the database
docker compose up db -d

# 5. Run migrations
make migrate-all

# 6. Start the app
make run
```

> **Windows without `make`**: see the [Windows section](#windows-without-make) below.

---

## Running Locally (Recommended)

Run the database in Docker and everything else natively for fast hot-reload:

```bash
# Terminal 1 — database
docker compose up db

# Terminal 2 — backend (http://localhost:8000)
make run-backend

# Terminal 3 — frontend (http://localhost:5173)
make run-frontend
```

API docs are available at `http://localhost:8000/docs`.

## Running with Docker (Full Stack)

```bash
# Copy and fill in your .env first
cp backend/.env.example backend/.env

docker compose up --build
```

| Service  | URL                         |
|----------|-----------------------------|
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API Docs | http://localhost:8000/docs  |

---

## Database Migrations

Migrations are plain SQL files in `backend/migrations/`. They use `IF NOT EXISTS` so they are safe to re-run.

```bash
# Run all migrations in order
make migrate-all

# Run a specific migration
make migrate FILE=013_add_whatsapp.sql
```

---

## Environment Variables

Copy `.env.example` and fill in your values:

```bash
cp backend/.env.example backend/.env
```

### Required

| Variable         | Description                                                                 |
|------------------|-----------------------------------------------------------------------------|
| `SECRET_KEY`     | JWT signing key. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL`   | `postgresql+asyncpg://postgres:password@localhost:5432/hostflow`            |
| `OPENAI_API_KEY` | OpenAI key from platform.openai.com                                         |

### Optional (features disabled if missing)

| Variable                    | Feature                           |
|-----------------------------|-----------------------------------|
| `STRIPE_SECRET_KEY`         | Billing / subscriptions           |
| `RESEND_API_KEY`            | Transactional emails              |
| `GOOGLE_CLIENT_ID/SECRET`   | Gmail inbox integration           |
| `GMAIL_ENCRYPTION_KEY`      | Gmail OAuth token storage         |
| `WHATSAPP_ACCESS_TOKEN`     | WhatsApp Business fallback token  |
| `WHATSAPP_APP_SECRET`       | Webhook signature verification    |

See `backend/.env.example` for the full list with generation commands and format hints.

---

## Testing Integrations

### Gmail OAuth

1. Create OAuth 2.0 credentials in [Google Cloud Console](https://console.cloud.google.com/apis/credentials) (Web application type)
2. Add `http://localhost:8000/api/v1/gmail/callback` as an authorized redirect URI
3. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GMAIL_REDIRECT_URI`, `GMAIL_ENCRYPTION_KEY` in `.env`
4. Connect via the Integrations page in the app

### WhatsApp Webhook (with ngrok)

Meta requires a public HTTPS URL to deliver webhooks during development:

```bash
ngrok http 8000
```

1. Copy the `https://xxxx.ngrok.io` URL
2. Set `APP_URL=https://xxxx.ngrok.io` in `backend/.env`
3. In Meta for Developers, set the webhook URL to:
   `https://xxxx.ngrok.io/webhooks/whatsapp`
4. Use the `webhook_verify_token` from your WhatsApp credential record as the verify token

### Stripe CLI (local webhooks)

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
# Copy the printed webhook secret into STRIPE_WEBHOOK_SECRET in .env
```

---

## Project Structure

```
HostFlow/
├── backend/
│   ├── app/
│   │   ├── core/           # Config, database engine, startup validation
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── routes/         # FastAPI routers (one per feature area)
│   │   ├── schemas/        # Pydantic request / response models
│   │   └── services/       # Business logic (AI, storage, scheduler...)
│   ├── migrations/         # Plain SQL migration files (run in order)
│   ├── .env.example        # Template for environment variables
│   ├── Dockerfile
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route-level page components
│   │   ├── hooks/          # Custom React hooks
│   │   └── lib/            # API client, utilities
│   ├── Dockerfile
│   └── package.json
├── .vscode/
│   ├── settings.json       # Shared editor config (ruff, interpreter path)
│   └── extensions.json     # Recommended extensions
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## VS Code Setup

Open the workspace root in VS Code. You will be prompted to install the recommended extensions (defined in `.vscode/extensions.json`).

The workspace is pre-configured to:

- Use the `.venv` inside `backend/` as the Python interpreter
- Format Python with `ruff` on save
- Resolve imports from `backend/` (no `src.` prefix needed)

If VS Code shows "missing package" warnings after setup, select the correct interpreter:

1. `Ctrl+Shift+P` → **Python: Select Interpreter**
2. Choose `backend/.venv/Scripts/python.exe` (Windows) or `backend/.venv/bin/python` (Mac/Linux)

---

## Available `make` Commands

```
make setup          Full first-time setup: venv, deps, copy .env.example
make install        Install production dependencies only
make install-dev    Install dev dependencies (ruff, pytest, mypy, stubs)

make run-backend    Start FastAPI with hot-reload (port 8000)
make run-frontend   Start Vite dev server (port 5173)
make run            Start both in parallel

make migrate-all    Run all SQL migrations in order
make migrate FILE=  Run a specific migration file

make lint           Run ruff linter
make format         Auto-format with ruff
make check          Lint + mypy type check

make clean          Remove venv, caches, build artifacts
```

---

## Windows without `make`

```bash
# Setup
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env

# Backend
cd backend
.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## Troubleshooting

**`make: command not found`**
Install [Git for Windows](https://git-scm.com/download/win) and use Git Bash, or use WSL.

**`ModuleNotFoundError` on backend start**
The virtual environment is not activated or packages are not installed:
```bash
cd backend
.venv/Scripts/pip install -r requirements.txt   # Windows
.venv/bin/pip install -r requirements.txt        # Mac/Linux
```

**`Cannot connect to the database` on startup**
Ensure PostgreSQL is running: `docker compose up db`
Check that `DATABASE_URL` in `backend/.env` matches the database credentials.

**`SECRET_KEY is not set` on startup**
The startup validator blocks launch if `SECRET_KEY` is still at the default placeholder.
Generate a real key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**VS Code shows red squiggles on imports**
Select the correct interpreter: `backend/.venv/Scripts/python.exe`
See [VS Code Setup](#vs-code-setup) above.

**WhatsApp webhook returns 403**
- Verify the `webhook_verify_token` matches what is configured in Meta's dashboard
- Ensure `WHATSAPP_APP_SECRET` is set if signature verification is enabled
