from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from shared.contracts import SpanRef


class AgentState(BaseModel):
	session_id: Optional[str] = None
	original_query: str
	language: str = "auto"
	meta: Dict[str, Any] = Field(default_factory=dict)
	redacted_query: Optional[str] = None
	guard_flags: Dict[str, Any] = Field(default_factory=dict)
	retrieved: List[Dict[str, Any]] = Field(default_factory=list)
	citations: List[SpanRef] = Field(default_factory=list)
	plan: Dict[str, Any] = Field(default_factory=dict)
	tool_result: Optional[Dict[str, Any]] = None
	answer: Optional[str] = None
	logs: List[str] = Field(default_factory=list)


