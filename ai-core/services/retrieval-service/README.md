# Retrieval Service

Hybrid search (pgvector cosine + pg_trgm similarity), ingestion PDF/Text/Transcript, citation spans.

## Mục đích

- Cung cấp dịch vụ ingest tài liệu, segment + embed để phục vụ RAG.
- Tìm kiếm hybrid (vector + trigram) tối ưu latency và chất lượng, trả spans/offset cho citation.
- Bộc lộ metrics latency/candidates để theo dõi hiệu năng và tuning.

## Chạy nhanh (Docker)

- `docker compose up -d --build retrieval-service`
- Health: `curl http://localhost:8083/healthz`
- Metrics: `curl http://localhost:8083/metrics`

## Chạy local

- `cd ai-core/services/retrieval-service`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- Copy `env.example` → `.env`
- `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Thoát virtualenv: `deactivate`

## Endpoints

- `POST /ingest` (form/json): source_type=text|pdf|transcript
- `POST /search` body: `{context_id?, query, alpha?, top_k?, vec_k?, trgm_k?, filter_document_ids?}`
- Embedding mọi truy vấn thông qua `model-adapter` (`POST /model/embed`) → đảm bảo guardrails + routing thống nhất.

## DB Indexes

- `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
- `GIN (text gin_trgm_ops)` cho segments.text
- `IVFFLAT (vector_cosine_ops)` cho embeddings.vector
