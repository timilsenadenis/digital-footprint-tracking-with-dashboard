# ── Stage 1: base image ───────────────────────────────────────────────
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: install Python dependencies ─────────────────────────────
FROM base AS dependencies

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Stage 3: final image ──────────────────────────────────────────────
FROM dependencies AS final

# Copy application source code
COPY . .

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Expose Flask port
EXPOSE 5000

# Health check — pings the API every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Start Flask (use gunicorn in production)
CMD ["python", "app.py"]

# ── Production override (uncomment for deployment) ────────────────────
# RUN pip install gunicorn==21.2.0
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
