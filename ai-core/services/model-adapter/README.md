# Model Adapter Service

FastAPI service trừu tượng hoá đa LLM (Adapter + RouterPolicy), có Guardrails (PII masking + policy).

## Mục đích

- Cung cấp lớp trừu tượng cho nhiều nhà cung cấp LLM (OpenAI/Anthropic/Mistral/Ollama) theo chuẩn chung.
- Tuyến chọn provider theo policy (cost/latency/context/language).
- Bảo vệ đầu vào với Guardrails (mask PII, chặn jailbreak) và prepend system prompt.
- Xuất metrics/tracing để theo dõi hiệu năng và chi phí sử dụng LLM.

## Chạy nhanh (Docker)

- `docker compose up -d --build model-adapter`
- Health: `curl http://localhost:8081/healthz`
- Providers: `curl http://localhost:8081/providers`

## Chạy local (Python)

- `cd ai-core/services/model-adapter`
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`
- (tuỳ chọn) `python -m spacy download en_core_web_sm` để bật Presidio masking
- Chạy: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Thoát virtualenv: `deactivate`

## Env chính

- `PROVIDER_KEYS` (JSON), `SERVICE_NAME`, `OTLP_ENDPOINT`, `LOG_LEVEL`
- Guard: `GUARD_ENABLED`, `GUARD_JAILBREAK_STRICT`, `GUARD_REDACT_TYPES`

## Endpoints

- `GET /healthz`
- `GET /providers`
- `POST /model/generate` body:
  ```json
  {
    "prompt_ref": "key:demo.summary.v1",
    "variables": {"context": "...", "seeds": "..."},
    "task": "summary",
    "language": "vi",
    "provider_hint": "openai?"
  }
  ```
  Trả `{provider, model, output, tokens_in, tokens_out, latency_ms, cost_usd}`. Prompt được lấy từ Prompt Service theo `prompt_ref`, guardrails áp dụng trước khi gọi vendor.
- `POST /model/embed` body: `{ "texts": [...], "model_hint": "openai" }`
- Legacy (deprecated): `/generate`, `/embed` – chỉ dùng khi chưa chuyển kịp.

Ví dụ nhanh:
```bash
curl -X POST http://localhost:8081/model/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_ref": "key:demo.qa.v1",
    "variables": {
      "query": "Overlay giảm latency thế nào?",
      "context": "[seg:1] ...",
      "instructions": "Chỉ trả lời dựa vào ngữ cảnh."
    },
    "task": "qa",
    "language": "vi"
  }'
```

## Metrics/Tracing

- `GET /metrics` (Prometheus)
- OTel tự động khi đặt `OTLP_ENDPOINT`
