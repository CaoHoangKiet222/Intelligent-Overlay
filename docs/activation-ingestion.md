# Activation & Context Ingestion

Tài liệu này mô tả hệ thống Activation & Context Ingestion cho Intelligent Overlay, bao gồm các API contracts, data models, và hướng dẫn tích hợp cho mobile và browser clients.

## Tổng quan

Hệ thống Activation & Context Ingestion cho phép:

- **Browser (PC)**: Extension icon / context menu / selection để kích hoạt overlay
- **Mobile (Android/iOS)**: Share Sheet, Text Selection, Floating Bubble (Android), Back Tap (iOS), Persistent Notification (Android)
- **Text Ingestion**: Đọc và trích xuất text từ DOM (browser) hoặc Accessibility Service (mobile)
- **Video/Audio Ingestion**: Lấy subtitles hoặc thực hiện Speech-to-Text (STT)
- **Image Input**: Từ screenshot hoặc photo → sử dụng OCR/Vision service để lấy text

## Data Models

### ActivationPayload

Schema chính cho activation request:

```python
class ActivationPayload(BaseModel):
    source_type: ActivationSourceType  # browser, share, selection, bubble, backtap, noti, image, video
    raw_text: Optional[str] = None
    url: Optional[str] = None
    app_id: Optional[str] = None  # Mobile host app identifier
    locale: Optional[str] = "auto"  # e.g., "vi-VN", "en-US"
    transcript_segments: List[TranscriptSegment] = []  # For video transcripts
    image_metadata: Optional[ImageMetadata] = None
    image_data: Optional[str] = None  # Base64 encoded image
    audio_data: Optional[str] = None  # Base64 encoded audio or URL
```

### ActivationSourceType

```python
class ActivationSourceType(str, Enum):
    BROWSER = "browser"
    SHARE = "share"
    SELECTION = "selection"
    BUBBLE = "bubble"
    BACKTAP = "backtap"
    NOTI = "noti"
    IMAGE = "image"
    VIDEO = "video"
```

### TranscriptSegment

```python
class TranscriptSegment(BaseModel):
    text: str
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
    speaker_label: Optional[str] = None
```

## API Endpoints

### POST /ingestion/normalize_and_index

Normalize và index context từ ActivationPayload.

**Request:**

```json
{
  "payload": {
    "source_type": "browser",
    "raw_text": "Text content here...",
    "url": "https://example.com/article",
    "locale": "vi-VN"
  }
}
```

Hoặc backward compatible với format cũ:

```json
{
  "raw_text": "Text content here...",
  "url": "https://example.com/article",
  "locale": "vi-VN"
}
```

**Response:**

```json
{
  "context_id": "uuid-here",
  "locale": "vi-VN",
  "chunk_count": 5,
  "deduplicated": false,
  "segments": [...]
}
```

## Mobile Client Integration

### Android (Kotlin)

#### Share Sheet Integration

```kotlin
class ShareReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val sharedText = intent.getStringExtra(Intent.EXTRA_TEXT)
        val sharedUrl = intent.getStringExtra(Intent.EXTRA_TEXT)
        
        val payload = ActivationPayload(
            sourceType = "share",
            rawText = sharedText,
            url = sharedUrl,
            appId = getCurrentAppId(),
            locale = Locale.getDefault().toString()
        )
        
        sendToIngestionAPI(payload)
    }
}
```

#### Text Selection Menu

```kotlin
class TextSelectionActivity : AppCompatActivity() {
    fun onTextSelected(selectedText: String) {
        val payload = ActivationPayload(
            sourceType = "selection",
            rawText = selectedText,
            appId = getCurrentAppId(),
            locale = Locale.getDefault().toString()
        )
        
        sendToIngestionAPI(payload)
    }
}
```

#### Floating Bubble (Accessibility Service)

```kotlin
class OverlayAccessibilityService : AccessibilityService() {
    fun captureVisibleText() {
        val rootNode = rootInActiveWindow ?: return
        val visibleText = extractTextFromNode(rootNode)
        
        val payload = ActivationPayload(
            sourceType = "bubble",
            rawText = visibleText,
            appId = getCurrentAppId(),
            locale = Locale.getDefault().toString()
        )
        
        sendToIngestionAPI(payload)
    }
}
```

#### Image from Share Sheet

```kotlin
fun handleSharedImage(imageUri: Uri) {
    val imageBytes = readImageBytes(imageUri)
    val base64Image = Base64.encodeToString(imageBytes, Base64.NO_WRAP)
    
    val imageMetadata = ImageMetadata(
        width = getImageWidth(imageUri),
        height = getImageHeight(imageUri),
        format = getImageFormat(imageUri),
        sizeBytes = imageBytes.size
    )
    
    val payload = ActivationPayload(
        sourceType = "image",
        imageData = base64Image,
        imageMetadata = imageMetadata,
        appId = getCurrentAppId(),
        locale = Locale.getDefault().toString()
    )
    
    sendToIngestionAPI(payload)
}
```

#### API Client

```kotlin
suspend fun sendToIngestionAPI(payload: ActivationPayload): IngestionResponse {
    val client = HttpClient {
        baseUrl = "http://your-backend:8083"
    }
    
    val response = client.post("/ingestion/normalize_and_index") {
        contentType(ContentType.Application.Json)
        body = mapOf("payload" to payload)
    }
    
    return response.body<IngestionResponse>()
}
```

### iOS (Swift)

#### Share Sheet Extension

```swift
class ShareViewController: UIViewController {
    func handleSharedContent() {
        guard let extensionItem = extensionContext?.inputItems.first as? NSExtensionItem else { return }
        
        for itemProvider in extensionItem.attachments ?? [] {
            if itemProvider.hasItemConformingToTypeIdentifier("public.text") {
                itemProvider.loadItem(forTypeIdentifier: "public.text", options: nil) { (item, error) in
                    if let text = item as? String {
                        let payload = ActivationPayload(
                            sourceType: "share",
                            rawText: text,
                            appId: self.getCurrentAppId(),
                            locale: Locale.current.identifier
                        )
                        self.sendToIngestionAPI(payload: payload)
                    }
                }
            } else if itemProvider.hasItemConformingToTypeIdentifier("public.image") {
                itemProvider.loadItem(forTypeIdentifier: "public.image", options: nil) { (item, error) in
                    if let image = item as? UIImage {
                        let imageData = image.jpegData(compressionQuality: 0.8)
                        let base64Image = imageData?.base64EncodedString()
                        
                        let payload = ActivationPayload(
                            sourceType: "image",
                            imageData: base64Image,
                            appId: self.getCurrentAppId(),
                            locale: Locale.current.identifier
                        )
                        self.sendToIngestionAPI(payload: payload)
                    }
                }
            }
        }
    }
}
```

#### Back Tap (Shortcuts)

```swift
func handleBackTap() {
    let payload = ActivationPayload(
        sourceType: "backtap",
        rawText: getCurrentScreenText(),
        appId: getCurrentAppId(),
        locale: Locale.current.identifier
    )
    
    sendToIngestionAPI(payload: payload)
}
```

#### API Client

```swift
func sendToIngestionAPI(payload: ActivationPayload) async throws -> IngestionResponse {
    let url = URL(string: "http://your-backend:8083/ingestion/normalize_and_index")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
    
    let body = ["payload": payload.dictionary]
    request.httpBody = try JSONSerialization.data(withJSONObject: body)
    
    let (data, _) = try await URLSession.shared.data(for: request)
    return try JSONDecoder().decode(IngestionResponse.self, from: data)
}
```

## Browser Extension Integration

### Content Script

```javascript
// content.js
function extractVisibleText() {
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: (node) => {
                const parent = node.parentElement;
                if (!parent) return NodeFilter.FILTER_REJECT;
                
                const style = window.getComputedStyle(parent);
                if (style.display === 'none' || 
                    style.visibility === 'hidden' ||
                    parent.classList.contains('ad') ||
                    parent.classList.contains('advertisement')) {
                    return NodeFilter.FILTER_REJECT;
                }
                
                return NodeFilter.FILTER_ACCEPT;
            }
        }
    );
    
    const texts = [];
    let node;
    while (node = walker.nextNode()) {
        const text = node.textContent.trim();
        if (text.length > 0) {
            texts.push(text);
        }
    }
    
    return texts.join('\n');
}

function getVideoSubtitles() {
    const video = document.querySelector('video');
    if (!video) return null;
    
    const track = video.textTracks?.[0];
    if (!track || track.kind !== 'subtitles') return null;
    
    const cues = Array.from(track.cues || []);
    return cues.map(cue => ({
        text: cue.text,
        start_ms: Math.floor(cue.startTime * 1000),
        end_ms: Math.floor(cue.endTime * 1000)
    }));
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extractText') {
        const text = extractVisibleText();
        const url = window.location.href;
        
        const payload = {
            source_type: 'browser',
            raw_text: text,
            url: url,
            locale: navigator.language
        };
        
        sendToIngestionAPI(payload).then(response => {
            sendResponse({ success: true, context_id: response.context_id });
        });
        
        return true;
    }
    
    if (request.action === 'extractVideo') {
        const subtitles = getVideoSubtitles();
        const url = window.location.href;
        
        if (subtitles && subtitles.length > 0) {
            const payload = {
                source_type: 'video',
                transcript_segments: subtitles,
                url: url,
                locale: navigator.language
            };
            
            sendToIngestionAPI(payload).then(response => {
                sendResponse({ success: true, context_id: response.context_id });
            });
        } else {
            attachAudioStreamForSTT(url).then(transcript => {
                const payload = {
                    source_type: 'video',
                    raw_text: transcript,
                    url: url,
                    locale: navigator.language
                };
                
                sendToIngestionAPI(payload).then(response => {
                    sendResponse({ success: true, context_id: response.context_id });
                });
            });
        }
        
        return true;
    }
});
```

### Background Script

```javascript
// background.js
async function sendToIngestionAPI(payload) {
    const response = await fetch('http://your-backend:8083/ingestion/normalize_and_index', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ payload })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

chrome.contextMenus.create({
    id: 'activateOverlay',
    title: 'Activate Intelligent Overlay',
    contexts: ['selection', 'page']
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'activateOverlay') {
        chrome.tabs.sendMessage(tab.id, {
            action: info.selectionText ? 'extractSelection' : 'extractText'
        });
    }
});

chrome.action.onClicked.addListener((tab) => {
    chrome.tabs.sendMessage(tab.id, { action: 'extractText' });
});
```

## OCR & STT Integration

### OCR Service

**Endpoint:** `POST /ocr`

**Request:**
```json
{
  "image_data": "base64_encoded_image",
  "lang_hint": "vi"
}
```

**Response:**
```json
{
  "text": "Extracted text from image",
  "confidence": 0.95,
  "metadata": {}
}
```

### STT Service

**Endpoint:** `POST /transcribe`

**Request:**
```json
{
  "audio_data": "base64_encoded_audio_or_url",
  "lang_hint": "vi-VN",
  "format": "mp3"
}
```

**Response:**
```json
{
  "segments": [
    {
      "text": "Transcribed text",
      "start_ms": 0,
      "end_ms": 1000,
      "speaker_label": null
    }
  ],
  "metadata": {}
}
```

## Example Flows

### Flow 1: Mobile Share Text

1. User shares text from any app via Share Sheet
2. Mobile app receives shared text
3. Build `ActivationPayload` with `source_type: "share"`
4. Call `POST /ingestion/normalize_and_index`
5. Backend normalizes, chunks, and stores text
6. Returns `context_id`
7. Mobile app opens overlay panel with `context_id`

### Flow 2: Browser DOM Text

1. User clicks extension icon or context menu
2. Content script extracts visible DOM text
3. Build `ActivationPayload` with `source_type: "browser"`
4. Call `POST /ingestion/normalize_and_index`
5. Backend processes and stores
6. Extension opens overlay UI with `context_id`

### Flow 3: Image OCR

1. User shares image via Share Sheet
2. Mobile app receives image
3. Build `ActivationPayload` with `source_type: "image"` and `image_data`
4. Backend calls OCR service to extract text
5. Normalize and index extracted text
6. Return `context_id`

### Flow 4: Video with Subtitles

1. User activates overlay on video page
2. Content script checks for available subtitles
3. If subtitles exist, extract SRT/VTT data
4. Build `ActivationPayload` with `source_type: "video"` and `transcript_segments`
5. Backend processes transcript segments with timestamps
6. Return `context_id`

### Flow 5: Video without Subtitles (STT)

1. User activates overlay on video page
2. Content script detects no subtitles
3. Attach to audio stream and send to STT service
4. STT service returns transcript segments
5. Build `ActivationPayload` with transcript
6. Backend processes and stores
7. Return `context_id`

## Error Handling

- **400 Bad Request**: Invalid payload (missing required fields, invalid source_type)
- **500 Internal Server Error**: OCR/STT service failure, database error

## Notes

- OCR và STT services hiện tại là stubs. Cần tích hợp thực tế với:
  - OCR: Tesseract, PaddleOCR, OpenCV+OCR, hoặc OpenAI Vision
  - STT: Whisper, Deepgram, Google Speech-to-Text, hoặc OpenAI Whisper API
- Embeddings được tính toán tự động trong ingestion pipeline
- Context deduplication dựa trên content hash

