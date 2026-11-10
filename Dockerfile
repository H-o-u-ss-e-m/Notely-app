# ==============================================================================
# Notely backend — image unique pour `api` (gunicorn) et `worker` (celery).
# Dépendances installées depuis requirements.lock (versions épinglées).
# Optimisé CPU pour production légère (< 1.5 Go au lieu de > 6.5 Go avec CUDA).
# ==============================================================================
FROM python:3.10-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PYTHONPATH=/app/backend \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Bibliothèques système : OpenCV, ReportLab/Pillow (+ polices arabes pour l'export PDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    fonts-noto-core \
    fonts-noto-ui-core \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.lock /app/requirements.lock
# Installation prioritaire de la version CPU allégée de PyTorch puis des dépendances verrouillées
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /app/requirements.lock

COPY backend /app/backend
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

# Utilisateur non-root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

WORKDIR /app/backend
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=4)" || exit 1

# Commande par défaut (surchargée par docker-compose pour le worker)
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "-b", "0.0.0.0:8000", "--timeout", "120"]
