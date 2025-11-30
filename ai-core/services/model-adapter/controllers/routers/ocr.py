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
from controllers.schemas import OCRRequest, OCRResponse


def create_ocr_router(gen_service: GenerationService) -> APIRouter:
	router = APIRouter(tags=["ocr"])
	logger = logging.getLogger("model-adapter")

	@router.post("/model/ocr", response_model=OCRResponse)
	async def model_ocr(req: OCRRequest) -> OCRResponse:
		try:
			image_bytes = base64.b64decode(req.image_data)
			if len(image_bytes) == 0:
				raise HTTPException(status_code=400, detail="Invalid image data: empty after decoding")
		except Exception as e:
			raise HTTPException(status_code=400, detail=f"Failed to decode image data: {str(e)}") from e

		provider_name = req.provider_hint or "openai"
		try:
			result = gen_service.extract_text_from_image(provider_name, req.image_data, req.lang_hint)
			return OCRResponse(
				provider=provider_name,
				model=result.model,
				text=result.text,
				latency_ms=result.latency_ms,
			)
		except ValueError as e:
			raise HTTPException(status_code=422, detail=str(e)) from e
		except Exception as e:
			logger.error(f"OCR error: {str(e)}", exc_info=True)
			raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}") from e

	return router

