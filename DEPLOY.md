# HostFlow — Production Deployment Guide

This document covers everything needed to deploy HostFlow to production and keep it running safely.

---

## Recommended Hosting Stack

| Component        | Service                  | Why                                                       |
|------------------|--------------------------|-----------------------------------------------------------|
| Backend (API)    | **Railway**              | Simple deploys, managed Postgres addon, built-in env vars |
| Frontend         | **Vercel**               | Free CDN, instant deploys from GitHub, zero config        |
| Database         | **Railway Postgres**     | Managed, automatic backups, same network as backend       |
| File storage     | **Cloudflare R2**        | S3-compatible, no egress fees, generous free tier         |
| Error tracking   | **Sentry**               | Free tier covers early-stage usage                        |
| Uptime monitoring| **BetterStack** (free tier) | Monitors `/health`, pages you on downtime             |
| Email            | **Resend**               | Simple API, good deliverability, free tier                |

> Railway is recommended because it handles Postgres, env vars, healthchecks, and rolling deploys in one place. Equivalent alternatives: Fly.io, Render.

---

## Domain Strategy

```
app.hostflow.com.br      → Vercel (frontend SPA)
api.hostflow.com.br      → Railway (FastAPI backend)
```

**Integration callback / webhook URLs (set in each provider dashboard):**

| Provider    | URL                                                          |
|-------------|--------------------------------------------------------------|
| Gmail OAuth | `https://api.hostflow.com.br/api/v1/gmail/callback`         |
| WhatsApp    | `https://api.hostflow.com.br/webhooks/whatsapp`             |
| Stripe      | `https://api.hostflow.com.br/webhooks/stripe`               |
| Inbound email | `https://api.hostflow.com.br/inbound/email`               |

---

## Environment Separation

| Environment | Backend URL                       | Frontend URL                    |
|-------------|-----------------------------------|---------------------------------|
| local       | http://localhost:8000             | http://localhost:5173           |
| staging     | https://api-staging.hostflow.com.br | https://staging.hostflow.com.br |
| production  | https://api.hostflow.com.br       | https://app.hostflow.com.br     |

Set `ENVIRONMENT=production` (or `staging`) in Railway / Vercel environment variables.

---

## First Production Deploy

### 1. Set up Railway

```bash
# Install Railway CLI
npm install -g @railway/cli
railway login

# Create project and link Postgres
railway new
railway add postgresql

# Link your local repo
railway link
```

### 2. Configure environment variables

```bash
# Copy the template
cp backend/.env.production.example .env.production
# Fill in all values — see sections below for generation commands

# Push all variables to Railway
railway variables set --from .env.production
```

Key variables to generate:

```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# GMAIL_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 3. Run database migrations

```bash
# Connect to Railway Postgres and run all migrations
railway run psql $DATABASE_URL -f backend/migrations/001_initial.sql
# ... repeat for each migration, or use make migrate-all with Railway's DATABASE_URL
```

Or from your local machine with Railway's DATABASE_URL:

```bash
export DATABASE_URL=$(railway variables get DATABASE_URL)
make migrate-all
```

### 4. Deploy

```bash
railway up --service backend
```

Railway auto-detects the Dockerfile in `./backend`. The healthcheck (`/health`) must return 200 before traffic is routed.

### 5. Deploy frontend to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

cd frontend
vercel --prod
```

Set in Vercel environment variables:
```
VITE_API_URL=https://api.hostflow.com.br/api/v1
```

---

## Service Topology (Production)

```
┌─────────────────────────────────────────────────────────┐
│  Vercel CDN                                             │
│  app.hostflow.com.br → React SPA (static)              │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS API calls
                     ▼
┌─────────────────────────────────────────────────────────┐
│  Railway                                                │
│  api.hostflow.com.br → FastAPI (uvicorn, 1 worker)      │
│                                                         │
│  In-process:                                           │
│    APScheduler (trial emails, Gmail sync)               │
└────────────┬────────────────────────────────────────────┘
             │
     ┌───────┴───────┐
     ▼               ▼
PostgreSQL        Cloudflare R2
(Railway addon)   (media storage)
```

**Scheduler note:** The APScheduler runs inside the single uvicorn worker. This is the right architecture at early SaaS scale. If you add Railway replicas, set `SCHEDULER_ENABLED=false` on all replicas except one to prevent duplicate job execution.

---

## Release Flow (Safe Deploy)

Follow this order every time you deploy a new version:

### 1. Prepare

- [ ] All migrations use `IF NOT EXISTS` (idempotent) — always true in this project
- [ ] No destructive column changes (prefer `ADD COLUMN` with a default over `DROP COLUMN`)
- [ ] New env vars added to `.env.production.example` and set in Railway

### 2. Run migrations first

```bash
# Migrations run against the live database BEFORE deploying new code.
# New code must be forward-compatible with the old schema during the deploy window.
export DATABASE_URL=$(railway variables get DATABASE_URL)
psql $DATABASE_URL -f backend/migrations/015_your_migration.sql
```

### 3. Deploy code

```bash
railway up --service backend --detach
```

Railway performs a rolling deploy: the old container stays up until the new one passes its healthcheck.

### 4. Verify

```bash
# Liveness
curl https://api.hostflow.com.br/health

# Readiness (DB check)
curl https://api.hostflow.com.br/health/ready

# Diagnostics (config summary)
curl https://api.hostflow.com.br/health/info
```

### 5. Rollback

Railway keeps previous deployments. To rollback:

```bash
railway rollback
```

Or from the Railway dashboard: Deployments → select previous → Redeploy.

If you also ran a migration, you need to reverse it manually (write a compensating migration). This is why migrations must always be backward-compatible.

---

## Webhook Setup

### Stripe

1. Go to [Stripe Webhooks](https://dashboard.stripe.com/webhooks) → Add endpoint
2. URL: `https://api.hostflow.com.br/webhooks/stripe`
3. Events to listen for:
   - `checkout.session.completed`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook signing secret → set `STRIPE_WEBHOOK_SECRET` in Railway

### WhatsApp (Meta)

1. Go to Meta for Developers → your App → WhatsApp → Configuration
2. Webhook URL: `https://api.hostflow.com.br/webhooks/whatsapp`
3. Verify token: use the `webhook_verify_token` from the user's `whatsapp_credentials` record
4. Subscribe to: `messages`

### Gmail OAuth

1. In Google Cloud Console → OAuth 2.0 Credentials → your Web client
2. Add Authorized Redirect URI: `https://api.hostflow.com.br/api/v1/gmail/callback`

### Inbound Email (Resend / SendGrid Inbound Parse)

- Inbound email endpoint: `https://api.hostflow.com.br/inbound/email`
- Configure in your email provider's inbound routing settings

---

## Rotating Secrets

### SECRET_KEY (JWT signing key)

Rotating this key immediately invalidates **all active user sessions**. Users will be logged out.

```bash
# Generate new key
python -c "import secrets; print(secrets.token_hex(32))"

# Update in Railway
railway variables set SECRET_KEY=<new_value>

# Redeploy (required for the new value to take effect)
railway up --service backend
```

### GMAIL_ENCRYPTION_KEY (Fernet token encryption)

Rotating this key makes all stored Gmail OAuth tokens **unreadable**. All users will need to reconnect Gmail.

Only rotate if the key is compromised. Back up the old key before rotating.

### Stripe / Resend API keys

Rotate in the respective provider dashboards, then update in Railway variables and redeploy.

---

## Checking Logs

### Railway CLI

```bash
# Live logs
railway logs --service backend --tail

# Filter by level (grep works on JSON output)
railway logs --service backend | grep '"level":"ERROR"'

# Filter by path
railway logs --service backend | grep '"path":"/api/v1/gmail"'
```

### Railway Dashboard

Project → Service → Logs tab. Supports keyword filtering.

---

## Restarting Services

```bash
# Restart backend (triggers a new deployment without code change)
railway redeploy --service backend
```

Or: Railway Dashboard → Service → Deployments → current deployment → Redeploy.

---

## Common Production Issues

**`Cannot connect to the database` on startup**
- Check `DATABASE_URL` in Railway Variables
- Ensure the Postgres service is running: Railway Dashboard → Postgres → Status
- Verify the connection string uses `postgresql+asyncpg://` scheme

**`SECRET_KEY is not set`**
- The startup validator blocks launch if SECRET_KEY is missing or at a default value
- Set it in Railway Variables and redeploy

**`STORAGE_PROVIDER=local is not suitable for production`**
- Set `STORAGE_PROVIDER=s3` and fill in R2/S3 credentials

**Webhook 403 from Stripe**
- `STRIPE_WEBHOOK_SECRET` is missing or wrong
- Verify it matches the secret shown in Stripe Dashboard → Webhooks → your endpoint

**WhatsApp webhook GET 403**
- The `webhook_verify_token` sent by Meta does not match the one stored in `whatsapp_credentials`
- Each user has their own verify token — ensure you are using the correct one when registering the webhook in Meta

**Gmail sync stops**
- Check `GMAIL_ENCRYPTION_KEY` is set and unchanged
- Check `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` credentials are valid
- Look for `[scheduler] job_gmail_sync` errors in logs

**Sentry not receiving events**
- Check `SENTRY_DSN` is set correctly in Railway Variables
- Verify the DSN format: `https://<key>@<org>.ingest.sentry.io/<project>`
- Trigger a test error: `GET /api/v1/nonexistent` should create a 404 event in Sentry

---

## Observability Checklist

- [ ] `SENTRY_DSN` configured — errors visible in Sentry dashboard
- [ ] BetterStack (or equivalent) uptime monitor on `https://api.hostflow.com.br/health`
- [ ] Railway log retention configured (Dashboard → Settings)
- [ ] `SENTRY_TRACES_SAMPLE_RATE=0.1` (10% of requests traced — adjust as needed)
- [ ] Alert on `health/ready` returning 503

---

## Deployment Checklist (Every Release)

- [ ] New migrations written and tested locally
- [ ] `.env.production.example` updated with any new variables
- [ ] New variables set in Railway before deploying code
- [ ] Migrations run against production DB (`psql $DATABASE_URL -f migration.sql`)
- [ ] Code deployed (`railway up`)
- [ ] Health endpoints return 200 (`/health`, `/health/ready`)
- [ ] `/health/info` shows expected environment and integration status
- [ ] Key user flow manually tested (login, inbox, send message)
- [ ] Sentry shows no new error spike

---

## Staging Environment (Optional)

If you want a staging environment:

1. Create a second Railway project (or a second service in the same project)
2. Use a separate Postgres database
3. Set `ENVIRONMENT=staging` — this enables `/docs`, uses text logging (not JSON), and relaxes some production-only checks
4. Point a subdomain: `api-staging.hostflow.com.br`
5. Use Stripe test keys (`sk_test_...`) in staging

Vercel automatically creates preview deployments for each PR — use those as your staging frontend.
