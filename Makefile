# HostFlow — Development commands
# Usage: make <target>
# Requires: make, Python 3.12+, Node.js 20+
#
# Windows users: use Git Bash or WSL, or run the equivalent commands manually.
# See README.md → "Windows without make" for alternatives.

.PHONY: help install install-dev setup \
        run-backend run-frontend run \
        migrate migrate-all \
        lint format check \
        clean

# ── Detect Python / pip inside .venv ─────────────────────────────────────────

VENV     := backend/.venv
# Windows (Git Bash) uses Scripts; Unix uses bin
ifeq ($(OS),Windows_NT)
  PYTHON := $(VENV)/Scripts/python
  PIP    := $(VENV)/Scripts/pip
else
  PYTHON := $(VENV)/bin/python
  PIP    := $(VENV)/bin/pip
endif

# ── Help ─────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

$(VENV):
	cd backend && python -m venv .venv

install: $(VENV) ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	cd frontend && npm install

install-dev: $(VENV) ## Install dev dependencies (includes linters, pytest, etc.)
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements-dev.txt
	cd frontend && npm install

setup: install-dev ## Full first-time setup: venv + deps + copy .env.example
	@if [ ! -f backend/.env ]; then \
	  cp backend/.env.example backend/.env; \
	  echo ""; \
	  echo "  ✓ Created backend/.env from .env.example"; \
	  echo "  → Open backend/.env and fill in your secrets before running"; \
	  echo ""; \
	else \
	  echo "  ✓ backend/.env already exists — skipping copy"; \
	fi

# ── Run ───────────────────────────────────────────────────────────────────────

run-backend: ## Start FastAPI dev server (hot-reload)
	cd backend && $(PYTHON) -m uvicorn app.main:app --reload --port 8000

run-frontend: ## Start Vite dev server
	cd frontend && npm run dev

run: ## Start backend + frontend in parallel (requires two terminals or a process manager)
	@echo "Starting backend and frontend in parallel..."
	@$(MAKE) -j2 run-backend run-frontend

# ── Migrations ────────────────────────────────────────────────────────────────

# Run a single migration file: make migrate FILE=001_add_properties.sql
migrate: ## Run a specific migration (FILE=xxx.sql)
	@if [ -z "$(FILE)" ]; then echo "Usage: make migrate FILE=001_add_properties.sql"; exit 1; fi
	$(PYTHON) -c "\
import asyncio, asyncpg, os; \
from dotenv import load_dotenv; \
load_dotenv('backend/.env'); \
url = os.getenv('DATABASE_URL','').replace('+asyncpg',''); \
sql = open('backend/migrations/$(FILE)').read(); \
asyncio.run(asyncpg.connect(url))" \
	|| psql "$(shell grep DATABASE_URL backend/.env | cut -d= -f2- | sed 's/+asyncpg//')" \
	   -f backend/migrations/$(FILE)

migrate-all: ## Run ALL migrations in order (safe — uses IF NOT EXISTS)
	@echo "Running all migrations..."
	@for f in backend/migrations/*.sql; do \
	  echo "  → $$f"; \
	  psql "$$(grep DATABASE_URL backend/.env | cut -d= -f2- | sed 's/+asyncpg//')" -f "$$f" || exit 1; \
	done
	@echo "Done."

# ── Code quality ──────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	$(PYTHON) -m ruff check backend/app

format: ## Auto-format with ruff
	$(PYTHON) -m ruff format backend/app
	$(PYTHON) -m ruff check --fix backend/app

check: lint ## Run all checks (lint + type check)
	$(PYTHON) -m mypy backend/app --ignore-missing-imports

# ── Clean ─────────────────────────────────────────────────────────────────────

clean: ## Remove venv, caches, and build artifacts
	rm -rf backend/.venv
	rm -rf backend/__pycache__ backend/app/**/__pycache__
	rm -rf backend/.ruff_cache backend/.mypy_cache backend/.pytest_cache
	rm -rf frontend/node_modules frontend/dist
	@echo "Clean complete."
