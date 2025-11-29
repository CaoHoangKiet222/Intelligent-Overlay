## Demo API — Vertical Slice AI-Core

Service FastAPI giúp dựng hai endpoint `/demo/analyze` và `/demo/qa` để chạy dọc kiến trúc AI-Core (ingestion → retrieval → prompts → model adapter → phân tích/QA). Đây là bản demo nên các worker vẫn còn heuristic đơn giản, nhưng toàn bộ luồng gọi Model Adapter, Prompt Service, Retrieval Service đều thật.

**QA Integration**: Endpoint `/demo/qa` mặc định sử dụng Agent Service với LangGraph pipeline (policy guard, tool calling, conversation state). Nếu Agent Service không available, tự động fallback về direct RAG implementation.

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

1. `POST /demo/analyze` — tạo context & enqueue phân tích async qua Kafka

   **Request body (real-world sample: meeting sản phẩm nội bộ)**

   ```json
   {
     "raw_text": "Product meeting 2025-11-25:\n- Người dùng than phiền thời gian load dashboard > 5s trong giờ cao điểm.\n- Team marketing cần số liệu chính xác về conversion trong 7 ngày gần nhất.\n- PM đề nghị phân tích nguyên nhân chậm và đề xuất 2-3 hướng tối ưu cụ thể.",
     "url": "https://confluence.example.com/product/meeting-2025-11-25",
     "locale": "vi"
   }
   ```

   - Gọi Retrieval `/ingest`, lấy segments mới tạo → tạo ContextBundle.
   - Fan-out 4 worker (summary, argument, implication/sentiment, logic_bias) qua Model Adapter.
   - Trả `AnalysisBundle` chứa citations `segment_id` từ Retrieval.

2. `POST /demo/analyze_direct` — phân tích sync, gọi thẳng Orchestrator

   **Request body (cùng nội dung với analyze, nhưng trả kết quả trực tiếp)**

   ```json
   {
     "raw_text": "Incident report #INC-2025-1125:\n- Lỗi timeout khi gọi API /v1/payments vào tối thứ Sáu.\n- 5% giao dịch bị retry nhiều lần trước khi thành công.\n- Cần phân tích nguyên nhân gốc rễ và đề xuất cách giảm tỉ lệ timeout.",
     "url": "https://pagerduty.example.com/incidents/INC-2025-1125",
     "locale": "en"
   }
   ```

   - Payload giống `POST /demo/analyze`.
   - Thay vì enqueue qua Kafka, service sẽ gọi trực tiếp Orchestrator `/orchestrator/analyze` và trả về kết quả cuối cùng.

3. `GET /demo/analyze/{event_id}` — lấy kết quả phân tích theo `event_id`

   - **Không có request body**.
   - Ví dụ URL:  
     `GET http://localhost:8090/demo/analyze/3f9bdb0f-7a0c-4f3b-a9e2-8a7a3e4fb001`
   - Response là `DemoAnalyzeResultResponse` do Orchestrator trả về (status, summary_json, argument_json, sentiment_json, logic_bias_json, citations, ...).

4. `POST /demo/analyze/callback` — callback từ Orchestrator về Demo API

   **Request body (ví dụ payload callback hoàn chỉnh)**

   ```json
   {
     "event_id": "3f9bdb0f-7a0c-4f3b-a9e2-8a7a3e4fb001",
     "status": "complete",
     "summary_json": {
       "bullets": [
         "Dashboard hiện tại bị chậm trong giờ cao điểm do truy vấn chưa tối ưu.",
         "Marketing cần số liệu conversion 7 ngày gần nhất để ra quyết định chiến dịch."
       ]
     },
     "argument_json": {
       "items": [
         {
           "claim": "Cần tối ưu truy vấn dashboard để giữ trải nghiệm người dùng.",
           "reasoning": "Thời gian phản hồi > 5s dễ khiến người dùng thoát.",
           "evidence": []
         }
       ]
     },
     "sentiment_json": {
       "label": "mixed",
       "explanation": "Người dùng có trải nghiệm tiêu cực về tốc độ nhưng vẫn tin tưởng sản phẩm."
     },
     "logic_bias_json": null,
     "citations": [],
     "error_summary": null
   }
   ```

   - Thực tế hệ thống Orchestrator sẽ gọi endpoint này; ở demo, payload chỉ được log lại.

5. `POST /demo/qa` — đặt câu hỏi trên context đã tạo

   **Request body (real-world sample: hỏi lại nội dung cuộc họp)**

   ```json
   {
     "context_id": "0a9d1886-b8e0-4c1a-aa18-b1dd6a45b2db",
     "query": "Tóm tắt lại các hành động cần làm sau buổi họp product này?"
   }
   ```

   - **Mặc định**: Gọi Agent Service với LangGraph pipeline (policy guard, retrieval, tool calling, fallback).
   - **Fallback**: Nếu Agent Service không available, tự động fallback về direct RAG (Retrieval + Model Adapter).
   - Hybrid search giới hạn theo `context_id`.
   - Trả về `{answer, citations[], confidence}` với citations từ segment markers.

6. `GET /healthz`

   - **Không có request body**.
   - Ví dụ: `curl http://localhost:8090/healthz`

### Configuration

**Environment Variables:**

- `USE_AGENT_SERVICE`: `true` (default) để dùng Agent Service, `false` để dùng direct RAG
- `AGENT_SERVICE_BASE_URL`: URL của Agent Service (default: `http://agent-service:8000`)
- `MODEL_ADAPTER_BASE_URL`: URL của Model Adapter
- `RETRIEVAL_SERVICE_BASE_URL`: URL của Retrieval Service
- `PROMPT_SERVICE_BASE_URL`: URL của Prompt Service
- `ORCHESTRATOR_BASE_URL`: URL của Orchestrator

### Giới hạn & TODO

- Worker hiện chỉ phân tích dạng text → JSON heuristic; cần thay bằng pipeline Ray + Kafka khi orchestrator hoàn thiện.
- Chưa có auth/throttling.
- QA đã tích hợp Agent Service với LangGraph pipeline (policy guard, tool calling, conversation state).
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
