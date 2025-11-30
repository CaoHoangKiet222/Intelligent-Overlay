from pydantic import BaseModel, Field
from typing import Optional, List


class OCRRequest(BaseModel):
	image_data: str = Field(description="Base64 encoded image data")
	lang_hint: Optional[str] = Field(default=None, description="Language hint (e.g., 'vi', 'en')")


class OCRResponse(BaseModel):
	text: str
	confidence: Optional[float] = None
	metadata: dict = Field(default_factory=dict)


class STTRequest(BaseModel):
	audio_data: str = Field(description="Base64 encoded audio data or URL")
	lang_hint: Optional[str] = Field(default=None, description="Language hint (e.g., 'vi-VN', 'en-US')")
	format: Optional[str] = Field(default=None, description="Audio format (e.g., 'wav', 'mp3', 'm4a')")


class STTSegment(BaseModel):
	text: str
	start_ms: int = Field(ge=0)
	end_ms: int = Field(ge=0)
	speaker_label: Optional[str] = None


class STTResponse(BaseModel):
	segments: List[STTSegment]
	metadata: dict = Field(default_factory=dict)

