from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from shared.contracts import ContextChunk


class ActivationSourceType(str, Enum):
	BROWSER = "browser"
	SHARE = "share"
	SELECTION = "selection"
	BUBBLE = "bubble"
	BACKTAP = "backtap"
	NOTI = "noti"
	IMAGE = "image"
	VIDEO = "video"


class TranscriptSegment(BaseModel):
	text: str
	start_ms: Optional[int] = Field(default=None, ge=0)
	end_ms: Optional[int] = Field(default=None, ge=0)
	speaker_label: Optional[str] = None


class ImageMetadata(BaseModel):
	width: Optional[int] = None
	height: Optional[int] = None
	format: Optional[str] = None
	size_bytes: Optional[int] = None


class ActivationPayload(BaseModel):
	source_type: ActivationSourceType
	raw_text: Optional[str] = None
	url: Optional[str] = None
	app_id: Optional[str] = None
	locale: Optional[str] = "auto"
	transcript_segments: List[TranscriptSegment] = Field(default_factory=list)
	image_metadata: Optional[ImageMetadata] = None
	image_data: Optional[str] = Field(default=None, description="Base64 encoded image data")
	audio_data: Optional[str] = Field(default=None, description="Base64 encoded audio data or URL")

	@model_validator(mode="after")
	def validate_payload(self):
		if self.source_type == ActivationSourceType.IMAGE:
			if not self.raw_text and not self.image_data:
				raise ValueError("image source requires either raw_text or image_data")
		elif self.source_type == ActivationSourceType.VIDEO:
			if not self.raw_text and not self.transcript_segments and not self.audio_data:
				raise ValueError("video source requires raw_text, transcript_segments, or audio_data")
		else:
			if not self.raw_text:
				raise ValueError(f"{self.source_type} source requires raw_text")
		return self


class IngestionRequest(BaseModel):
	payload: Optional[ActivationPayload] = None
	raw_text: Optional[str] = Field(default=None, min_length=1)
	url: Optional[str] = None
	locale: Optional[str] = "auto"

	@model_validator(mode="after")
	def validate_request(self):
		if not self.payload and not self.raw_text:
			raise ValueError("Either payload or raw_text must be provided")
		return self

	def get_activation_payload(self) -> ActivationPayload:
		if self.payload:
			return self.payload
		if not self.raw_text:
			raise ValueError("Either payload or raw_text must be provided")
		return ActivationPayload(
			source_type=ActivationSourceType.BROWSER,
			raw_text=self.raw_text,
			url=self.url,
			locale=self.locale or "auto",
		)


class IngestionResponse(BaseModel):
	context_id: str
	locale: Optional[str] = None
	chunk_count: int
	deduplicated: bool = False
	segments: List[ContextChunk] = Field(default_factory=list)
