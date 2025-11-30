import httpx
import base64
from typing import List, Dict, Any, Optional
from app.config import MODEL_ADAPTER_BASE_URL, EMBED_MODEL_HINT
from shared.config.base import get_base_config
from domain.schemas import TranscriptSegment


async def embed_texts(texts: List[str]) -> Dict[str, Any]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.services.model_adapter
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.post(f"{MODEL_ADAPTER_BASE_URL}/model/embed", json={"texts": texts, "model_hint": EMBED_MODEL_HINT})
		r.raise_for_status()
		return r.json()


async def transcribe_audio(
	audio_bytes: bytes,
	lang_hint: Optional[str] = None
) -> List[TranscriptSegment]:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.services.model_adapter
	audio_data_base64 = base64.b64encode(audio_bytes).decode('utf-8')
	
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.post(
			f"{MODEL_ADAPTER_BASE_URL}/model/transcribe",
			json={
				"audio_data": audio_data_base64,
				"lang_hint": lang_hint,
				"provider_hint": "openai"
			}
		)
		r.raise_for_status()
		result = r.json()
		
		segments = result.get("segments", [])
		return [
			TranscriptSegment(
				text=seg.get("text", ""),
				start_ms=seg.get("start_ms", 0),
				end_ms=seg.get("end_ms", 0),
				speaker_label=seg.get("speaker_label")
			)
			for seg in segments
		]


async def extract_text_from_image(
	image_data_base64: str,
	lang_hint: Optional[str] = None
) -> str:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.services.model_adapter
	
	async with httpx.AsyncClient(timeout=timeout) as client:
		r = await client.post(
			f"{MODEL_ADAPTER_BASE_URL}/model/ocr",
			json={
				"image_data": image_data_base64,
				"lang_hint": lang_hint,
				"provider_hint": "openai"
			}
		)
		r.raise_for_status()
		result = r.json()
		return result.get("text", "")

