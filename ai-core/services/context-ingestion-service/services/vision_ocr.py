import base64
from typing import Optional
import sys
from pathlib import Path

ai_core_path = Path(__file__).parent.parent.parent.parent
if str(ai_core_path) not in sys.path:
	sys.path.insert(0, str(ai_core_path))

from services.models import OCRRequest
from clients.model_adapter import extract_text_from_image as model_adapter_ocr
import logging

logger = logging.getLogger(__name__)


async def extract_text_from_image(
	request: OCRRequest | str,
	lang_hint: Optional[str] = None
) -> str:
	"""
	Extract text from image using OCR.
	
	Args:
		request: OCRRequest model or base64 encoded image data string (backward compatible)
		lang_hint: Language hint (e.g., 'vi', 'en') - only used if request is string
	
	Returns:
		Extracted text from image
	
	Raises:
		ValueError: If image data is invalid
		RuntimeError: If OCR processing fails
	"""
	if isinstance(request, str):
		image_data = request
	else:
		image_data = request.image_data
		lang_hint = request.lang_hint or lang_hint

	try:
		image_bytes = base64.b64decode(image_data)
		if len(image_bytes) == 0:
			raise ValueError("Invalid image data: empty after decoding")
	except Exception as e:
		raise ValueError(f"Failed to decode image data: {str(e)}") from e

	logger.info(f"OCR request received, image size: {len(image_bytes)} bytes, lang_hint: {lang_hint}")

	return await model_adapter_ocr(image_data, lang_hint)

