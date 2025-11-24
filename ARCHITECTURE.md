# Kiến trúc Intelligent-Overlay

## Tổng quan hệ thống

- Monorepo `ai-core` gom toàn bộ dịch vụ phục vụ chuỗi xử lý cao cấp cho sản phẩm Intelligent Overlay, xây dựng trên Python 3.11.
- Kiến trúc microservice tách biệt nhiệm vụ: quản lý prompt, truy hồi tri thức, chuẩn hóa truy cập mô hình, điều phối tác vụ phân tích và tác nhân hội thoại.
- Mỗi dịch vụ cung cấp REST API qua FastAPI, kèm endpoint `/metrics` cho Prometheus và `/healthz` cho kiểm tra tình trạng.
- Các thành phần chính giao tiếp qua HTTP nội bộ, Kafka và Ray; dữ liệu lâu dài lưu trên PostgreSQL, cache tại Redis, và lưu trữ nhị phân trên MinIO (S3 tương thích).

## Các dịch vụ lõi

### Model Adapter

- Vị trí: `ai-core/services/model-adapter`, entry `app/main.py`, config `app/config.py`.
- Endpoint chính (đã chuẩn hóa):
  - `POST /model/generate`: nhận `prompt_ref` + `variables`, lấy template từ Prompt Service, chạy guardrails (PII masking, secret filter, jailbreak policy) rồi mới gọi provider.
  - `POST /model/embed`: chuẩn hóa mọi embedding truy vấn.
  - Giữ `/generate`, `/embed` cũ ở trạng thái deprecated cho client legacy, khuyến nghị chuyển sang `/model/*`.
- Routing: `RouterPolicy` + `TASK_ROUTING` để map các tác vụ (`summary`, `qa` → OpenAI GPT-4o; `argument`, `logic_bias` → Anthropic Claude Sonnet nếu có key). Tự động fallback theo context window/cost/latency nếu không có cấu hình.
- Guardrails: pipeline `guardrails/pipeline.py` mask email/phone, chặn token nhạy cảm (AWS key, private key, sk-*), prepend system prompt cứng.
- Logging & metrics: ghi provider/model/tokens/latency/cost để theo dõi; retriable errors (429/5xx) được bọc tenacity tại provider (OpenAI/Anthropic...).
- Tích hợp Prompt Service bắt buộc: mọi generation phải cung cấp `prompt_ref`.

### Prompt Service

- Vị trí: `ai-core/services/prompt-service`.
- Cấu trúc: Entry point tại `app/main.py`, cấu hình tại `app/config.py`, dependencies tại `app/deps.py`.
- Chức năng: quản lý vòng đời prompt/template, lưu versioning, định nghĩa schema đầu vào/ra, cung cấp API đọc/ghi kèm caching Redis.
- Endpoint chính: `POST /prompts`, `POST /prompts/{id}/versions`, `GET /prompts/{id}` với tham số `version`.
- Sử dụng Alembic/PostgreSQL cho lưu trữ, chuẩn hóa template qua `domain.validators`.

### Retrieval Service

- Vị trí: `ai-core/services/retrieval-service`.
- Cấu trúc: Entry point tại `app/main.py`, cấu hình tại `app/config.py`, dependencies tại `app/deps.py`.
- Chức năng: ingest tài liệu, xây dựng kho embedding (pgvector) và tìm kiếm lai (vector + trigram).
- Endpoint chính: `POST /ingest`, `POST /search`.
- Luồng search gọi `model-adapter` để làm embedding truy vấn, sau đó thực thi truy vấn SQL lai (HYBRID) và tính highlight.
- Storage: PostgreSQL với extension pgvector; kết nối qua SQLAlchemy async.

### Agent Service

- Vị trí: `ai-core/services/agent-service`.
- Chức năng: tác nhân LangGraph (policy guard → intake → retrieval → planner → tool-call → answer/fallback) và một agent tối giản FR4.1 cho contextual Q&A.
- Endpoint:
  - `POST /agent/ask`: LangGraph đầy đủ.
  - `POST /agent/qa`: pipeline guard → Retrieval Service hybrid search → Model Adapter (`task=qa`) với prompt RAG “trả lời chỉ dựa context”.
- Tất cả prompts lấy từ Prompt Service, output chuẩn `{answer, citations[], confidence}`, dễ bổ sung tool mới (analysis bundle, external knowledge flag).

### Orchestrator

- Vị trí: `ai-core/services/orchestrator`.
- Fan-out 4 worker (summary, argument, implication+sentiment, logic-bias) qua Ray, mỗi worker gọi Model Adapter bằng `task` riêng.
- Aggregator lưu `analysis_runs` + `llm_calls`, quản lý idempotency, DLQ.
- Realtime API mới `/orchestrator/analyze`: build `WorkerCall`, chạy RealtimeOrchestrator để fan-in/out async, trả `AnalysisBundleResponse` + `worker_statuses` (ok/error/timeout) hỗ trợ tương lai streaming.

## Luồng tương tác chính

- **Hỏi đáp tức thời**: Client → `agent-service` → guard/policy → `retrieval-service` (hybrid search) → planner quyết định dùng tool hay trả lời trực tiếp → `model-adapter` (LLM) → Agent trả lời, ghi log + metric.
- **Ingest & tìm kiếm nội dung**: Nguồn dữ liệu → `retrieval-service` (ingest) → lưu segment + embedding → `agent-service` hoặc client khác gọi `POST /search` để lấy kết quả kèm highlight.
- **Quản lý prompt**: Ops/API → `prompt-service` để tạo phiên bản mới → cache Redis → `agent-service` hoặc `model-adapter` tiêu thụ template qua API/kho dữ liệu.
- **Phân tích hàng loạt**: Hệ thống upstream phát sự kiện Kafka → `orchestrator` đọc, dùng Ray fan-out tới worker (gọi `model-adapter` nếu cần) → aggregate lưu Postgres → nếu thất bại gửi DLQ.
- **Quan sát & giám sát**: Mọi dịch vụ xuất số liệu tại `/metrics`, trace qua OpenTelemetry khi có `OTLP_ENDPOINT`, log JSON chuẩn cho Loki/Promtail.

```text
Client
  │
  ▼
Agent Service ──► Retrieval Service ──► PostgreSQL (pgvector)
  │                                ▲
  └────► Model Adapter ────────────┘
                 │
                 ▼
          Nhà cung cấp LLM
```

## Sơ đồ luồng kết nối

```mermaid
flowchart LR
  subgraph Client["Client/Apps"]
    UI[UI / API Client]
  end

  subgraph Agent["Agent Service (FastAPI + LangGraph)"]
    A1[Policy Guard]
    A2[Intake]
    A3[Retrieval Node]
    A4[Planner]
    A5[Tool Call]
    A6[Answer/Fallback]
  end

  subgraph Retrieval["Retrieval Service (FastAPI)"]
    R1[POST /search]
    DB[(PostgreSQL + pgvector)]
  end

  subgraph Adapter["Model Adapter (FastAPI)"]
    M1[POST /generate]
    M2[POST /embed]
    P["Guardrails + Routing Policy"]
    LLM[(Nhà cung cấp LLM)]
  end

  subgraph Prompt["Prompt Service (FastAPI)"]
    PR1[CRUD Prompt/Version]
    RED[(Redis Cache)]
  end

  subgraph Orchestrator["Orchestrator (FastAPI + Kafka + Ray)"]
    O1[Kafka Consumer]
    O2[Fan-out Workers (Ray)]
    O3[Aggregator]
    DLQ[(DLQ Producer)]
    ORDB[(PostgreSQL)]
  end

  subgraph Infra["Hạ tầng"]
    S3[(MinIO/S3)]
    METRICS[(Prometheus /metrics)]
    OTEL[(OpenTelemetry)]
  end

  %% Client -> Agent
  UI -->|/agent/ask| A1 --> A2 --> A3 --> A4 --> A5 --> A6

  %% Agent <-> Retrieval
  A3 -->|/search (hybrid)| R1 --> DB

  %% Agent/Workers <-> Model Adapter
  A5 -->|/generate| M1 --> P --> LLM
  R1 -. embedding .-> M2
  O2 -. may call .-> M1

  %% Prompt Service
  UI -->|manage prompts| PR1
  PR1 <--> RED

  %% Orchestrator
  UI -->|publish event| O1 --> O2 --> O3 --> ORDB
  O3 -->|on fail| DLQ

  %% Observability
  Agent --- METRICS
  Retrieval --- METRICS
  Adapter --- METRICS
  Prompt --- METRICS
  Orchestrator --- METRICS
  Agent --- OTEL
  Retrieval --- OTEL
  Adapter --- OTEL
  Prompt --- OTEL
  Orchestrator --- OTEL

  %% Artefacts
  Adapter --- S3
```

### Chuỗi Q&A chi tiết (trình tự)

```mermaid
sequenceDiagram
  participant C as Client
  participant AG as Agent Service
  participant RT as Retrieval Service
  participant DB as PostgreSQL (pgvector)
  participant MA as Model Adapter
  participant LLM as LLM Provider

  C->>AG: POST /agent/ask {query}
  AG->>AG: Policy Guard → Intake
  AG->>RT: POST /search {query, top_k,...}
  RT->>MA: POST /embed {texts:[query]}
  MA->>LLM: route + embed
  LLM-->>MA: vectors
  MA-->>RT: {vectors}
  RT->>DB: HYBRID SQL (vector + trigram)
  DB-->>RT: segments + scores
  RT-->>AG: SearchResponse {results}
  AG->>AG: Planner → quyết định intent
  AG->>MA: POST /model/generate {prompt_ref, variables, task=qa}
  MA->>LLM: route + guardrails + call
  LLM-->>MA: output
  MA-->>AG: {output}
  AG-->>C: AskResponse {answer, citations, plan}
```

## Dữ liệu, hạ tầng & tích hợp

- **PostgreSQL**: Cơ sở dữ liệu chính cho prompt, retrieval và orchestrator; migration quản lý qua các thư mục `data/migrations` từng service và gốc `ai-core/db`.
- **Redis**: Cache prompt, lưu trạng thái nhanh cho agent và orchestrator.
- **MinIO/S3**: Lưu trữ đối tượng phục vụ adapter (ví dụ model checkpoint, tệp trung gian).
- **Ray Cluster**: Khởi chạy từ Docker Compose (`ray-head`, `ray-worker`) cung cấp tài nguyên tính toán phân tán cho orchestrator và agent.
- **Kafka**: Được truy cập qua `orchestrator/kafka/*` cho luồng sự kiện phân tích; cấu hình endpoint qua biến môi trường.
- **Docker Compose**: File `docker-compose.yaml` dựng toàn bộ stack local (Postgres, Redis, MinIO, Ray, các service).
- **Helm Chart**: `charts/aicore-app` chứa manifest triển khai Kubernetes (Deployment, Service, HPA, Ingress, ServiceMonitor).
- **ArgoCD / GitOps**: Thư mục `deploy/apps/app-of-apps.yaml` cấu hình App-of-Apps và giá trị riêng cho môi trường (`deploy/values/staging/*.yaml`).

## Cấu trúc thư mục chuẩn

Mỗi service tuân theo cấu trúc thư mục nhất quán:

```
service-name/
├── app/                    # Entry point và cấu hình
│   ├── __init__.py
│   ├── main.py            # FastAPI app instance
│   ├── config.py          # Cấu hình từ environment variables
│   └── deps.py            # Dependencies injection (nếu có)
├── domain/                # Business logic và schemas
├── data/                  # Database models và repositories
├── controllers/           # API controllers (nếu có)
├── routers/               # FastAPI routers (nếu có)
├── services/              # Business services (nếu có)
├── tests/                 # Unit và integration tests
├── requirements.txt
├── Dockerfile
└── README.md
```

## Thư viện dùng chung

- `shared/telemetry`: cung cấp logger JSON, metrics registry, và tích hợp OpenTelemetry thống nhất.
- `libs/common-schemas`: nơi đặt model/dataclass được tái sử dụng giữa các service.
- `libs/tracing`: tiện ích tracing nội bộ (điều chỉnh trong tương lai).
- `ai-core/db`: cấu trúc chung cho migration liên service.

## Bảo mật & kiểm soát chất lượng

- Guardrails trước khi gọi LLM (mask PII, áp chính sách) thông qua pipeline trong `model-adapter/guardrails`.
- Agent policy guard kiểm tra guard flag trước khi tiếp tục đồ thị xử lý.
- Orchestrator áp dụng idempotency và đẩy thông điệp vào DLQ khi fan-in thất bại.
- Tests unit/functional sẵn có trong mỗi service: ví dụ `agent-service/tests/test_flow_basic.py`, `retrieval-service/tests/test_search_hybrid.py`.

## Scripts tiện ích

- `scripts/run_service.sh <service>`: khởi chạy nhanh từng service (agent, model-adapter, prompt-service, retrieval-service, orchestrator). Script tự cấu hình `.env` (MAP BASE_URL sang localhost) và log port (ví dụ `model-adapter` 8081).
- `scripts/check_service.sh <service>`: gọi `curl` tới `/healthz` để xác thực service đang chạy.
- `scripts/kill_service.sh <service>`: dừng tiến trình tương ứng (tmux + uvicorn) để giải phóng cổng.

## Triển khai

- **Local**: `docker-compose up` dựng đầy đủ Postgres, Redis, MinIO, Kafka, Ray + toàn bộ service. Chú ý export API keys trong `.env`.
- **Helm/Kubernetes**: sử dụng chart `charts/aicore-app` (Deployment/Service/HPA/Ingress/ServiceMonitor). ArgoCD App-of-Apps tại `deploy/apps/app-of-apps.yaml` + giá trị môi trường `deploy/values/<env>`.
- **Database migration**: chạy `alembic upgrade head` ở `ai-core/db` và từng service `data/migrations`.
- **Observability**: bật `SERVICE_NAME`, `OTLP_ENDPOINT`, log JSON; Prometheus scrape `/metrics`.
