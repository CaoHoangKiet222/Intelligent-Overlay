# Activation & Ingestion - Example Requests

Tài liệu này cung cấp các ví dụ curl requests cho các scenarios khác nhau.

## Prerequisites

Backend service chạy tại: `http://localhost:8083`

## Example 1: Browser Text

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "browser",
      "raw_text": "This is a sample article from a web page. It contains multiple paragraphs and sentences that will be chunked and indexed.",
      "url": "https://example.com/article",
      "locale": "en-US"
    }
  }'
```

## Example 2: Mobile Share Text

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "share",
      "raw_text": "Shared text from mobile news app",
      "app_id": "com.example.news",
      "locale": "vi-VN"
    }
  }'
```

## Example 3: Text Selection

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "selection",
      "raw_text": "Selected text from user",
      "app_id": "com.example.reader",
      "locale": "en-US"
    }
  }'
```

## Example 4: Image with OCR (Base64 encoded)

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "image",
      "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
      "image_metadata": {
        "width": 1920,
        "height": 1080,
        "format": "png",
        "size_bytes": 245760
      },
      "locale": "vi-VN"
    }
  }'
```

**Note:** Image data trong ví dụ trên là một 1x1 pixel PNG (placeholder). Trong thực tế, bạn cần encode image thật thành base64.

## Example 5: Video with Transcript Segments

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "video",
      "url": "https://youtube.com/watch?v=example",
      "transcript_segments": [
        {
          "text": "Welcome to this video tutorial.",
          "start_ms": 0,
          "end_ms": 3000,
          "speaker_label": null
        },
        {
          "text": "Today we will learn about machine learning.",
          "start_ms": 3000,
          "end_ms": 8000,
          "speaker_label": null
        },
        {
          "text": "Let us start with the basics.",
          "start_ms": 8000,
          "end_ms": 12000,
          "speaker_label": null
        }
      ],
      "locale": "en-US"
    }
  }'
```

## Example 6: Video with Audio URL (STT)

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "video",
      "url": "https://example.com/video.mp4",
      "audio_data": "https://example.com/audio.mp3",
      "locale": "vi-VN"
    }
  }'
```

## Example 7: Backward Compatible Format

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Simple text ingestion",
    "url": "https://example.com",
    "locale": "en-US"
  }'
```

## Example 8: Floating Bubble (Accessibility Service)

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "bubble",
      "raw_text": "Text captured from accessibility service",
      "app_id": "com.example.app",
      "locale": "en-US"
    }
  }'
```

## Example 9: Back Tap (iOS)

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "backtap",
      "raw_text": "Text from iOS back tap shortcut",
      "app_id": "com.example.app",
      "locale": "en-US"
    }
  }'
```

## Example 10: Persistent Notification (Android)

```bash
curl -X POST http://localhost:8083/ingestion/normalize_and_index \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "source_type": "noti",
      "raw_text": "Text from persistent notification",
      "app_id": "com.example.app",
      "locale": "vi-VN"
    }
  }'
```

## Expected Responses

### Success Response

```json
{
  "context_id": "550e8400-e29b-41d4-a716-446655440000",
  "locale": "en-US",
  "chunk_count": 3,
  "deduplicated": false,
  "segments": [
    {
      "segment_id": "seg-1",
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "First chunk text...",
      "start_offset": 0,
      "end_offset": 100,
      "sentence_index": 0,
      "metadata": {
        "position": 0
      }
    }
  ]
}
```

### Error Response (400 Bad Request)

```json
{
  "detail": "browser source requires raw_text"
}
```

### Error Response (422 Validation Error)

```json
{
  "detail": [
    {
      "loc": ["body", "payload", "source_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Testing OCR Service Directly

```bash
curl -X POST http://localhost:8086/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    "lang_hint": "vi"
  }'
```

## Testing STT Service Directly

```bash
curl -X POST http://localhost:8087/transcribe \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "https://example.com/audio.mp3",
    "lang_hint": "vi-VN",
    "format": "mp3"
  }'
```

## Notes

- Tất cả các services cần được chạy trước khi test
- OCR và STT services hiện tại là stubs, sẽ trả về placeholder text
- Image data cần được encode thành base64 trước khi gửi
- Audio data có thể là base64 hoặc URL

