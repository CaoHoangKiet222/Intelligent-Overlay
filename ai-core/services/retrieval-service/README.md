# Retrieval Service

Hybrid search (pgvector cosine + pg_trgm similarity) với citation spans.

## Mục đích

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

- `POST /retrieval/search`: Hybrid search trong context chunks
  - Body: `{context_id, query, top_k?, mode?, alpha?}`
  - Modes: `vector`, `lexical`, `hybrid` (default)
  - Trả về spans với scores và breakdown
- `GET /retrieval/context/{context_id}`: Lấy context chunks theo ID
  - Query params: `limit?` (default: 12, max: 100)

Embedding mọi truy vấn thông qua `model-adapter` (`POST /model/embed`) → đảm bảo guardrails + routing thống nhất.

## Lưu ý

- Ingestion logic (normalize, chunking, OCR, STT) đã được di chuyển sang `context-ingestion-service`
- Service này chỉ tập trung vào search/retrieval

## DB Indexes

- `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
- `GIN (text gin_trgm_ops)` cho segments.text
- `IVFFLAT (vector_cosine_ops)` cho embeddings.vector
