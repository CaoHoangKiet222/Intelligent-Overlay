# Hướng dẫn Debug Retrieval Service

## 1. Debug với VS Code / Cursor

### Cách 1: Sử dụng Launch Configuration

1. Mở file `.vscode/launch.json` (đã được tạo sẵn)
2. Chọn configuration "Python: Retrieval Service" từ dropdown
3. Đặt breakpoint trong code bằng cách click vào số dòng
4. Nhấn F5 hoặc click nút "Start Debugging"
5. Service sẽ chạy với auto-reload khi code thay đổi

### Cách 2: Debug với Reload Disabled

- Chọn "Python: Retrieval Service (No Reload)" nếu cần debug mà không muốn auto-reload
- Hữu ích khi debug các vấn đề liên quan đến state hoặc connection

### Cách 3: Debug Test Cases

- Chọn "Python: Pytest" để debug các test cases
- Đặt breakpoint trong test file hoặc code được test
- Nhấn F5 để chạy tests với debugger

## 2. Debug với Python Debugger (pdb)

### Sử dụng breakpoint() trong code

```python
def some_function():
    breakpoint()
    # code của bạn
```

Khi chạy, Python sẽ dừng tại breakpoint và bạn có thể:
- `n` (next): Chạy dòng tiếp theo
- `s` (step): Step into function
- `c` (continue): Tiếp tục chạy
- `p variable_name`: In giá trị biến
- `pp variable_name`: Pretty print
- `l` (list): Hiển thị code xung quanh
- `q` (quit): Thoát debugger

### Sử dụng pdb.set_trace()

```python
import pdb

def some_function():
    pdb.set_trace()
    # code của bạn
```

## 3. Debug với Logging

### Thiết lập logging level

Trong code, sử dụng logging:

```python
import logging

logger = logging.getLogger(__name__)

def some_function():
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
```

### Chạy với debug logging

```bash
export DEBUG=true
python3 -m app.main
```

Hoặc trong code:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 4. Debug với Environment Variables

### Chạy với debug mode

```bash
cd ai-core/services/retrieval-service
export DEBUG=true
export PORT=8083
python3 -m app.main
```

### Sử dụng script có sẵn

```bash
./scripts/run_service.sh retrieval-service 8083
```

## 5. Debug với Docker

### Chạy với debug port exposed

```bash
docker compose up -d --build retrieval-service
docker attach <container_id>
```

### Xem logs

```bash
docker compose logs -f retrieval-service
```

## 6. Debug API Requests

### Sử dụng curl với verbose

```bash
curl -v -X POST http://localhost:8083/retrieval/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

### Sử dụng httpie

```bash
http POST http://localhost:8083/retrieval/search query="test query"
```

### Sử dụng Postman hoặc Insomnia

- Import OpenAPI schema từ `/docs` endpoint
- Test các endpoints với breakpoints

## 7. Debug Database Queries

### Enable SQLAlchemy logging

Thêm vào code:

```python
import logging

logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

Hoặc trong environment:

```python
import os
os.environ['SQLALCHEMY_ECHO'] = 'true'
```

## 8. Debug Async Code

### Sử dụng asyncio debug mode

```python
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

### Debug async functions

Khi debug async code, đảm bảo:
- Sử dụng `await` đúng cách
- Kiểm tra event loop
- Sử dụng `asyncio.run()` hoặc `uvicorn` để chạy

## 9. Common Debug Scenarios

### Debug endpoint không hoạt động

1. Kiểm tra route đã được register chưa
2. Kiểm tra request/response schema
3. Đặt breakpoint ở đầu endpoint function
4. Kiểm tra logs để xem error

### Debug database connection

1. Kiểm tra DATABASE_URL trong .env
2. Test connection với psql hoặc asyncpg
3. Kiểm tra migrations đã chạy chưa
4. Xem SQLAlchemy logs

### Debug embedding issues

1. Kiểm tra MODEL_ADAPTER_BASE_URL
2. Test model-adapter service riêng
3. Kiểm tra embedding dimension
4. Xem response từ model-adapter

### Debug search performance

1. Sử dụng metrics endpoint `/metrics`
2. Kiểm tra vec_candidates và trgm_candidates
3. Xem query execution time trong logs
4. Kiểm tra database indexes

## 10. Tips và Best Practices

1. **Sử dụng type hints**: Giúp IDE và debugger hiểu code tốt hơn
2. **Đặt breakpoint ở exception**: Catch exception và đặt breakpoint
3. **Sử dụng conditional breakpoints**: Chỉ break khi điều kiện đúng
4. **Watch variables**: Theo dõi giá trị biến trong debugger
5. **Sử dụng call stack**: Xem call stack để hiểu flow
6. **Log important steps**: Log các bước quan trọng để trace
7. **Test với small data**: Test với dataset nhỏ trước
8. **Isolate issues**: Tách biệt vấn đề để debug dễ hơn

## 11. Debug Tools

### Python Debugger (pdb)
- Built-in Python debugger
- Có sẵn trong Python standard library

### ipdb
- Enhanced pdb với IPython features
- Install: `pip install ipdb`
- Sử dụng: `import ipdb; ipdb.set_trace()`

### debugpy
- Microsoft Python debugger
- Được sử dụng bởi VS Code
- Install: `pip install debugpy`

### pytest
- Test framework với debug support
- Chạy: `pytest --pdb` để drop vào debugger khi test fail

