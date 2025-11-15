# Python Projects Configuration trong Monorepo

## Cấu trúc

Mỗi Python service trong monorepo có cấu hình riêng:

```
ai-core/services/
├── agent-service/
│   ├── pyrightconfig.json    # Cấu hình Pylance cho service này
│   ├── .venv/                # Virtualenv riêng
│   └── requirements.txt
├── model-adapter/
│   ├── pyrightconfig.json
│   ├── .venv/
│   └── requirements.txt
└── ...
```

## Cách hoạt động

1. **Pylance tự động detect**: Khi mở file Python trong một service, Pylance sẽ:

   - Tìm `pyrightconfig.json` trong thư mục hiện tại hoặc thư mục cha
   - Đọc cấu hình `venv` và `venvPath`
   - Tự động load packages từ `.venv/lib/python3.14/site-packages/`

2. **Mỗi service độc lập**: Mỗi service có virtualenv và dependencies riêng, không ảnh hưởng lẫn nhau.

## Setup cho service mới

1. Tạo virtualenv:

```bash
cd ai-core/services/your-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Tạo `pyrightconfig.json`:

```json
{
  "venvPath": ".",
  "venv": ".venv",
  "pythonVersion": "3.14",
  "typeCheckingMode": "basic",
  "reportMissingImports": "warning",
  "pythonPlatform": "Darwin"
}
```

3. Reload Cursor: `Cmd+Shift+P` → "Reload Window"

## Chọn Python Interpreter trong Cursor

Khi làm việc với một service:

1. `Cmd+Shift+P` → "Python: Select Interpreter"
2. Chọn `.venv/bin/python3` của service bạn đang làm việc

Cursor sẽ tự động nhớ interpreter cho mỗi workspace folder.
