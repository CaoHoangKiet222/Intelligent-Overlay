import base64
import httpx
from typing import List, Optional
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from domain.schemas import TranscriptSegment
from clients.model_adapter import transcribe_audio as model_adapter_transcribe
from shared.config.base import get_base_config
import logging

logger = logging.getLogger(__name__)


async def _download_audio_from_url(url: str) -> bytes:
	timeout_config = get_base_config().timeout_config
	timeout = timeout_config.http_default.to_httpx_timeout()
	async with httpx.AsyncClient(timeout=timeout) as client:
		response = await client.get(url)
		response.raise_for_status()
		return response.content


async def transcribe_audio(
	audio_data: str,
	lang_hint: Optional[str] = None,
	format: Optional[str] = None
) -> List[TranscriptSegment]:
	"""
	Transcribe audio to text with timestamps.
	
	Args:
		audio_data: Base64 encoded audio data or URL
		lang_hint: Language hint (e.g., 'vi-VN', 'en-US')
		format: Audio format (e.g., 'wav', 'mp3', 'm4a')
	
	Returns:
		List of transcript segments with timestamps
	
	Raises:
		ValueError: If audio data is invalid
		RuntimeError: If STT processing fails
	"""
	audio_bytes: bytes
	
	try:
		if audio_data.startswith("http://") or audio_data.startswith("https://"):
			logger.info(f"STT request received for URL: {audio_data}, lang_hint: {lang_hint}")
			audio_bytes = await _download_audio_from_url(audio_data)
			if len(audio_bytes) == 0:
				raise ValueError("Invalid audio data: empty after downloading from URL")
		else:
			audio_bytes = base64.b64decode(audio_data)
			if len(audio_bytes) == 0:
				raise ValueError("Invalid audio data: empty after decoding")
			logger.info(f"STT request received, audio size: {len(audio_bytes)} bytes, lang_hint: {lang_hint}")
	except Exception as e:
		raise ValueError(f"Failed to decode audio data: {str(e)}") from e

	return await model_adapter_transcribe(audio_bytes, lang_hint)

