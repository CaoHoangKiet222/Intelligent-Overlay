# Model Adapter Service

FastAPI service trừu tượng hoá đa LLM (Adapter + RouterPolicy), có Guardrails (PII masking + policy).

## Chạy nhanh (Docker)

- `docker compose up -d --build model-adapter`
- Health: `curl http://localhost:8081/healthz`
- Providers: `curl http://localhost:8081/providers`

## Chạy local (Python)

- `cd ai-core/services/model-adapter`
- `pip install -r requirements.txt`
- (tuỳ chọn) `python -m spacy download en_core_web_sm` để bật Presidio masking
- Chạy: `uvicorn controllers.api:app --host 0.0.0.0 --port 8000`

## Env chính

- `PROVIDER_KEYS` (JSON), `SERVICE_NAME`, `OTLP_ENDPOINT`, `LOG_LEVEL`
- Guard: `GUARD_ENABLED`, `GUARD_JAILBREAK_STRICT`, `GUARD_REDACT_TYPES`

## Endpoints

- `GET /healthz`
- `GET /providers`
- `POST /generate` body: `{prompt, language?, context_len?, cost_target?, latency_target_ms?, provider_hint?}`
- `POST /embed` body: `{texts, model_hint?}`

## Metrics/Tracing

- `GET /metrics` (Prometheus)
- OTel tự động khi đặt `OTLP_ENDPOINT`
