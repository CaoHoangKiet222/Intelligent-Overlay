# Agent Service (LangGraph)

Pipeline: policy_guard → intake → retrieval → planner → tool_call → answer → fallback.

## Mục đích

- Xây dựng pipeline agent có thể mở rộng bằng LangGraph, tách rõ từng bước xử lý.
- Tích hợp RAG (retrieval) và tool calling để trả lời chính xác và có trích dẫn.
- Ghi log từng bước giúp dễ quan sát và gỡ lỗi; có fallback khi tool lỗi.

## Chạy nhanh (Docker)

- `docker compose up -d --build agent-service retrieval-service model-adapter`
- Health: `curl http://localhost:8084/healthz`
- Metrics: `curl http://localhost:8084/metrics`

## Chạy local

- `cd ai-core/services/agent-service`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- Đặt env `MODEL_ADAPTER_BASE_URL`, `RETRIEVAL_BASE_URL`
- `python -m app.main` hoặc `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Thoát virtualenv: `deactivate`

## Endpoint

- `POST /agent/ask` body: `{query, session_id?, language?, meta?}`
- Kết quả: `{answer, citations, plan, tool_result, logs}`

### Ví dụ curl

```bash
curl -X POST http://localhost:8000/agent/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the weather today?",
    "session_id": "session-123",
    "language": "en",
    "meta": {
      "user_id": "user-456",
      "source": "web"
    }
  }'
```

Ví dụ tối giản (chỉ có query bắt buộc):

```bash
curl -X POST http://localhost:8000/agent/ask \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the weather today?"
  }'
```
