# ── Stage 1: dependency install ───────────────────────────────────────────────
# Separate stage so the layer is cached unless requirements.txt changes.
FROM python:3.12-slim AS deps

WORKDIR /deps

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime image ────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Install curl for the Docker healthcheck (minimal addition, no dev tools)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

# Non-root user — never run application code as root
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from the deps stage
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application source
COPY --chown=appuser:appuser . .

USER appuser

# Expose the port the app listens on
EXPOSE 8000

# Health check for Docker / Railway / Fly
# Gives the app 30 s to start, then checks every 30 s with a 5 s timeout.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Production start command ───────────────────────────────────────────────────
# Single worker is intentional: the APScheduler runs in-process on the same
# async event loop. Multiple workers would fire scheduler jobs N times.
# Scale horizontally by adding more Railway / Fly replicas with SCHEDULER_ENABLED=false
# on all but one instance, or migrate scheduler to a dedicated worker service.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--no-access-log"]

