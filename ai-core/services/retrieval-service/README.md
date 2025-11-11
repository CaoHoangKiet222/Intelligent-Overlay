# Retrieval Service

Hybrid search (pgvector cosine + pg_trgm similarity), ingestion PDF/Text/Transcript, citation spans.

## Chạy nhanh (Docker)

- `docker compose up -d --build retrieval-service`
- Health: `curl http://localhost:8083/healthz`
- Metrics: `curl http://localhost:8083/metrics`

## Chạy local

- `cd ai-core/services/retrieval-service`
- `pip install -r requirements.txt`
- Copy `env.example` → `.env`
- `uvicorn app:app --host 0.0.0.0 --port 8000`

## Endpoints

- `POST /ingest` (form/json): source_type=text|pdf|transcript
- `POST /search` body: `{query, alpha?, top_k?, vec_k?, trgm_k?, filter_document_ids?}`

## DB Indexes

- `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
- `GIN (text gin_trgm_ops)` cho segments.text
- `IVFFLAT (vector_cosine_ops)` cho embeddings.vector
