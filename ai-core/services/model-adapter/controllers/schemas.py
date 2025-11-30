from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any, Literal


class HealthResponse(BaseModel):
	status: str
	service: str


class ModelGenerateRequest(BaseModel):
	prompt_ref: str
	variables: Dict[str, Any] = Field(default_factory=dict)
	task: Literal["summary", "qa", "argument", "logic_bias", "sentiment", "default"] = "default"
	language: Optional[str] = None
	context_len: Optional[int] = None
	provider_hint: Optional[str] = None


class ModelGenerateResponse(BaseModel):
	provider: str
	model: str
	output: str
	tokens_in: Optional[int] = None
	tokens_out: Optional[int] = None
	latency_ms: Optional[int] = None
	cost_usd: Optional[float] = None


class LegacyGenerateRequest(BaseModel):
	prompt: str
	language: Optional[str] = None
	context_len: Optional[int] = None
	provider_hint: Optional[str] = None


class EmbedRequest(BaseModel):
	texts: List[str]
	model_hint: Optional[str] = None
	model_config = ConfigDict(protected_namespaces=())


class EmbedResponse(BaseModel):
	provider: str
	model: str
	dim: int
	vectors: List[List[float]]


class TranscribeRequest(BaseModel):
	audio_data: str = Field(description="Base64 encoded audio data")
	lang_hint: Optional[str] = Field(default=None, description="Language hint (e.g., 'vi-VN', 'en-US')")
	provider_hint: Optional[str] = Field(default="openai", description="Provider hint")


class TranscriptSegmentResponse(BaseModel):
	text: str
	start_ms: int
	end_ms: int
	speaker_label: Optional[str] = None


class TranscribeResponse(BaseModel):
	provider: str
	model: str
	segments: List[TranscriptSegmentResponse]
	latency_ms: Optional[int] = None


class OCRRequest(BaseModel):
	image_data: str = Field(description="Base64 encoded image data")
	lang_hint: Optional[str] = Field(default=None, description="Language hint (e.g., 'vi', 'en')")
	provider_hint: Optional[str] = Field(default="openai", description="Provider hint")


class OCRResponse(BaseModel):
	provider: str
	model: str
	text: str
	latency_ms: Optional[int] = None

