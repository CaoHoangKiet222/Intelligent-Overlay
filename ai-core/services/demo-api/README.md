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
