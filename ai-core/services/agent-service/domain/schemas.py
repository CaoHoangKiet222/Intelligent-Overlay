from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class AskRequest(BaseModel):
	query: str
	session_id: Optional[str] = None
	language: str = "auto"
	meta: Dict[str, Any] = {}


class AskResponse(BaseModel):
	session_id: Optional[str]
	answer: str
	citations: List[Dict[str, Any]]
	plan: Dict[str, Any]
	tool_result: Dict[str, Any]
	logs: List[str]


