FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/ai-core:$PYTHONPATH

RUN apt-get update && apt-get install -y --no-install-recommends curl build-essential libffi-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY services/orchestrator/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/orchestrator /app
COPY shared /app/ai-core/shared

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --retries=5 CMD curl -f http://localhost:8000/healthz || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


