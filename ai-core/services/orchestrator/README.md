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
- `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Thoát virtualenv: `deactivate`

## Luồng xử lý

1. **Kafka fan-out**  
   - Consumer đọc `AnalysisTask` từ topic.  
   - Ray chạy 4 worker song song (summary, argument, implication+sentiment, logic_bias); mỗi worker gọi Model Adapter bằng `prompt_ref` + `task` tương ứng.  
   - Fan-in aggregate → Postgres (`analysis_runs`), ghi `llm_calls`, partial tolerant; lỗi toàn phần đẩy DLQ.

2. **Realtime API**  
   - `POST /orchestrator/analyze` body: `{context_id, language?, segments?, prompt_ids?}`  
   - Service dựng `WorkerCall`, chạy `RealtimeOrchestrator` fan-out nội bộ (không Kafka) để trả ngay `AnalysisBundleResponse`:
     ```json
     {
       "summary": {...},
       "arguments": {...},
       "implications": [...],
       "sentiment": {...},
       "logic_bias": {...},
       "worker_statuses": {"summary": "ok", "argument": "error", ...}
     }
     ```
   - Hữu ích cho demo UI muốn lấy toàn bộ bundle trong một request; thiết kế tương lai có thể stream khi từng worker xong.
