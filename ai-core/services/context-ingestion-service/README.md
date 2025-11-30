# Context Ingestion Service

Service chuyên trách xử lý ingestion của ActivationPayload, normalize text/transcripts, chunking, và persist ContextBundle + ContextChunks với embeddings vào PostgreSQL.

## Chức năng

- Nhận ActivationPayload từ clients
- Normalize text và transcripts
- Chunking text thành ContextChunks
- Persist ContextBundle + ContextChunk vào PostgreSQL
- Compute embeddings và lưu vào pgvector

## Cấu trúc

```
context-ingestion-service/
├── app/
│   ├── __init__.py
│   ├── config.py          # Config loading từ shared config
│   └── main.py            # FastAPI app entrypoint
├── routers/
│   └── contexts.py        # /contexts/ingest endpoint
├── domain/
│   ├── schemas.py         # Request/Response schemas (ActivationPayload, etc.)
│   ├── context_pipeline.py # IngestionService logic
│   └── segmentation.py    # Text segmentation logic
├── data/
│   ├── db.py              # DB connection & extensions
│   ├── models.py          # SQLAlchemy models (Document, Segment, Embedding)
│   └── repositories.py    # DB operations
├── clients/
│   └── model_adapter.py   # Client để gọi model-adapter cho embeddings
├── services/
│   ├── stt.py             # Speech-to-Text service
│   ├── vision_ocr.py      # OCR service
│   └── models.py          # STT/OCR request/response models
├── metrics/
│   └── prometheus.py      # Prometheus metrics
├── Dockerfile
├── requirements.txt
└── env.example
```

## Chạy service

### Local development

```bash
./scripts/run_service.sh context-ingestion-service
```

Service sẽ chạy trên port 8086 (mặc định).

### Docker

```bash
docker-compose up context-ingestion-service
```

## Environment Variables

Xem `env.example` để biết các biến môi trường cần thiết:

- `DATABASE_URL`: PostgreSQL connection string (asyncpg)
- `MODEL_ADAPTER_BASE_URL`: URL của model-adapter service
- `EMBED_MODEL_HINT`: Model hint cho embedding
- `EMBEDDING_DIM`: Dimension của embedding vectors

## API Endpoints

### POST /contexts/ingest

Ingest ActivationPayload và persist ContextBundle + ContextChunks với embeddings.

**Request:**
```json
{
  "payload": {
    "source_type": "browser",
    "raw_text": "Text content...",
    "url": "https://example.com",
    "locale": "vi-VN"
  }
}
```

Hoặc backward compatible với format cũ:
```json
{
  "raw_text": "Text content...",
  "url": "https://example.com",
  "locale": "vi-VN"
}
```

**Response:**
```json
{
  "context_id": "uuid",
  "locale": "vi-VN",
  "chunk_count": 5,
  "deduplicated": false,
  "segments": [...]
}
```

## Health Check

```bash
curl http://localhost:8086/healthz
```

## Metrics

Prometheus metrics available tại `/metrics`:

- `context_ingestion_latency_ms`: Latency của ingestion process
- `context_ingestion_errors`: Số lỗi theo error_type
- `context_chunks_created`: Tổng số chunks đã tạo
- `context_embeddings_computed`: Tổng số embeddings đã compute

