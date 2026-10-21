# API backend image (FC38): FastAPI/uvicorn app from src/server.
# Runs the documented module entry (app.py __main__) so ServerSettings
# stays the single host/port source — bind 0.0.0.0 for container access.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=src \
    ADVISOR_HOST=0.0.0.0 \
    ADVISOR_PORT=8000 \
    # chromadb anonymous telemetry is noise for an offline demo (FC36 baseline)
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# src/ + data/: the app resolves seed data relative to itself
# (ADVISOR_DATA_DIR defaults to <repo>/data via dependencies.py — FC33).
COPY src/ src/
COPY data/ data/

# var/ holds SQLite + Chroma stores — bind-mounted as a named volume in
# docker-compose.yml so user-owned chat/plan data persists (FC34); seed-owned
# tables reload from data/ on every startup (FC33, ADVISOR_SEED_MODE=reload).
EXPOSE 8000

# First startup may download the ONNX MiniLM embedding model once
# (ADVISOR_EMBEDDING_FUNCTION=onnx default) — give it a generous start period.
HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=120s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

ENTRYPOINT ["python", "-m", "server.app"]