import os
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

import base64
import logging
from fastapi import APIRouter, HTTPException
from services.generation_service import GenerationService
from controllers.schemas import TranscribeRequest, TranscribeResponse, TranscriptSegmentResponse


def create_transcribe_router(gen_service: GenerationService) -> APIRouter:
	router = APIRouter(tags=["transcribe"])
	logger = logging.getLogger("model-adapter")

	@router.post("/model/transcribe", response_model=TranscribeResponse)
	async def model_transcribe(req: TranscribeRequest) -> TranscribeResponse:
		try:
			audio_bytes = base64.b64decode(req.audio_data)
			if len(audio_bytes) == 0:
				raise HTTPException(status_code=400, detail="Invalid audio data: empty after decoding")
		except Exception as e:
			raise HTTPException(status_code=400, detail=f"Failed to decode audio data: {str(e)}") from e

		provider_name = req.provider_hint or "openai"
		try:
			result = gen_service.transcribe(provider_name, audio_bytes, req.lang_hint)
			segments = [
				TranscriptSegmentResponse(
					text=seg.text,
					start_ms=seg.start_ms,
					end_ms=seg.end_ms,
					speaker_label=seg.speaker_label
				)
				for seg in result.segments
			]
			return TranscribeResponse(
				provider=provider_name,
				model=result.model,
				segments=segments,
				latency_ms=result.latency_ms,
			)
		except ValueError as e:
			raise HTTPException(status_code=422, detail=str(e)) from e
		except Exception as e:
			logger.error(f"Transcription error: {str(e)}", exc_info=True)
			raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}") from e

	return router

