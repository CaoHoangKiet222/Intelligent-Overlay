from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from shared.contracts import SpanRef


class AskRequest(BaseModel):
	query: str
	session_id: Optional[str] = None
	language: str = "auto"
	meta: Dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
	session_id: Optional[str]
	answer: str
	citations: List[SpanRef]
	plan: Dict[str, Any]
	tool_result: Optional[Dict[str, Any]] = None
	logs: List[str]


class QaRequest(BaseModel):
	context_id: str = Field(min_length=1)
	query: str = Field(min_length=1, max_length=1024)
	conversation_id: Optional[str] = None
	language: str = "auto"
	allow_external: bool = False


class QaResponse(BaseModel):
	conversation_id: Optional[str] = None
	answer: str
	citations: List[SpanRef] = Field(default_factory=list)
	confidence: float = Field(ge=0.0, le=1.0)
	used_external: bool = False


