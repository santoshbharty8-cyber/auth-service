# ---------- Base image ----------
FROM python:3.11-slim

# ---------- ENV ----------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------- WORKDIR ----------
WORKDIR /app

# ---------- SYSTEM DEPENDENCIES ----------
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    gcc \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip tools
RUN pip install --upgrade pip setuptools wheel

# ---------- INSTALL DEPENDENCIES ----------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- COPY PROJECT ----------
COPY . .

# ---------- SECURITY (NON-ROOT USER) ----------
RUN useradd -m appuser
USER appuser

# ---------- EXPOSE ----------
EXPOSE 8000

# ---------- HEALTHCHECK (READINESS) ----------
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
CMD curl --fail http://localhost:8000/ready || exit 1

# ---------- START SERVER (ADVANCED PRODUCTION) ----------
CMD ["sh", "-c", "\
WORKERS=$((2 * $(nproc) + 1)) && \
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --workers $WORKERS \
  --timeout 30 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --preload \
"]