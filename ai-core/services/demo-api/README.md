## Demo API — Vertical Slice AI-Core

Service FastAPI giúp dựng hai endpoint `/demo/analyze` và `/demo/qa` để chạy dọc kiến trúc AI-Core (ingestion → retrieval → prompts → model adapter → phân tích/QA). Đây là bản demo nên các worker vẫn còn heuristic đơn giản, nhưng toàn bộ luồng gọi Model Adapter, Prompt Service, Retrieval Service đều thật.

### Cách chạy nhanh

```bash
cd ai-core/services/demo-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env  # chỉnh lại URL service nếu cần
uvicorn app.main:app --reload --port 8090
```

- Health check: `GET /healthz`
- Metrics: `GET /metrics`

### Endpoint

1. `POST /demo/analyze`

   ```json
   {
     "raw_text": "nội dung...",
     "url": "https://example.com",
     "locale": "vi"
   }
   ```

   - Gọi Retrieval `/ingest`, lấy segments mới tạo → tạo ContextBundle.
   - Fan-out 4 worker (summary, argument, implication/sentiment, logic_bias) qua Model Adapter.
   - Trả `AnalysisBundle` chứa citations `segment_id` từ Retrieval.

2. `POST /demo/qa`
   ```json
   {
     "context_id": "<document_id từ /demo/analyze>",
     "query": "Câu hỏi?"
   }
   ```
   - Hybrid search giới hạn theo `context_id`.
   - Prompt QA nhúng segment marker, LLM trả câu trả lời + citations.

### Giới hạn & TODO

- Worker hiện chỉ phân tích dạng text → JSON heuristic; cần thay bằng pipeline Ray + Kafka khi orchestrator hoàn thiện.
- Chưa có auth/throttling.
- QA mới chỉ RAG nội bộ, chưa hỗ trợ conversation state/FR4.2.
- Prompt Service bắt buộc chạy vì demo sẽ auto bootstrap các prompt mặc định (key `demo.*`).

### Ví dụ cURL cho đội QC

1. Tạo context mới từ transcript kiểm thử nội bộ:

```bash
curl -X POST http://localhost:8090/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Meeting QA 2025-11-25:\n- Tester A phát hiện crash khi nhập \"@@@\" vào form.\n- Tester B cần model tóm tắt rõ severity và bước tái hiện.\n- Kỳ vọng đưa ra khuyến nghị fix trước release cuối tuần.",
    "url": "https://confluence.example.com/qc/meeting-2025-11-25",
    "locale": "vi"
  }'
```

2. Đặt câu hỏi chất lượng dựa trên `context_id` vừa trả về:

```bash
curl -X POST http://localhost:8090/demo/qa \
  -H "Content-Type: application/json" \
  -d '{
    "context_id": "0a9d1886-b8e0-4c1a-aa18-b1dd6a45b2db",
    "query": "Tổng hợp các lỗi blocker mà QA yêu cầu phải sửa trước khi phát hành?"
  }'
```
