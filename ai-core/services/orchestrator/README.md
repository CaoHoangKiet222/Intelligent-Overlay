# Orchestrator Service

Kafka consumer ➜ fan-out 4 Ray workers ➜ fan-in aggregate; lưu `llm_calls` + `analysis_runs`, DLQ khi cần.

## Mục đích

- Điều phối luồng phân tích đa tác vụ (summary/argument/sentiment/logic_bias) theo mô hình fan-out/fan-in.
- Đảm bảo idempotency theo `event_id`, ghi audit vào `llm_calls`, lưu kết quả hợp nhất vào `analysis_runs`.
- Tính bền bỉ: retry nội bộ ở worker, DLQ khi lỗi không phục hồi, partial khi một phần thất bại.
- Quan sát: metrics latency, failures, partial, DLQ; tracing Kafka + HTTP.

## Chạy nhanh (Docker)

- `docker compose up -d --build orchestrator ray-head ray-worker`
- Health: `curl http://localhost:8085/healthz`
- Metrics: `curl http://localhost:8085/metrics`

Yêu cầu Kafka broker/Topic: `analysis.tasks`, `analysis.dlq`, và Postgres.

## Chạy local

- `cd ai-core/services/orchestrator`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- Đặt env Kafka/DB/Model Adapter/Prompt Service
- `uvicorn app:app --host 0.0.0.0 --port 8000`
- Thoát virtualenv: `deactivate`

## Luồng xử lý

- Consumer đọc message `AnalysisTask`
- Ray tasks: summary, argument, sentiment, logic_bias (có retry nội bộ)
- Fan-in: hợp nhất kết quả, lưu DB; partial nếu có lỗi cục bộ; failed ➜ DLQ
