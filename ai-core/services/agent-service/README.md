# Agent Service (LangGraph)

Pipeline: policy_guard → intake → retrieval → planner → tool_call → answer → fallback.

## Chạy nhanh (Docker)

- `docker compose up -d --build agent-service retrieval-service model-adapter`
- Health: `curl http://localhost:8084/healthz`
- Metrics: `curl http://localhost:8084/metrics`

## Chạy local

- `cd ai-core/services/agent-service`
- `pip install -r requirements.txt`
- Đặt env `MODEL_ADAPTER_BASE_URL`, `RETRIEVAL_BASE_URL`
- `python -m app.main` hoặc `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Endpoint

- `POST /agent/ask` body: `{query, session_id?, language?, meta?}`
- Kết quả: `{answer, citations, plan, tool_result, logs}`
