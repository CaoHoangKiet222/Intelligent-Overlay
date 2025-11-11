from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field

WorkerType = Literal["summary", "argument", "sentiment", "logic_bias"]


class AnalysisTask(BaseModel):
	event_id: str
	bundle_id: Optional[str] = None
	query: Optional[str] = None
	segments: List[Dict[str, Any]] = Field(default_factory=list)
	language: Literal["vi", "en", "auto"] = "auto"
	prompt_ids: Dict[WorkerType, str] = Field(default_factory=dict)
	meta: Dict[str, Any] = Field(default_factory=dict)


class WorkerResult(BaseModel):
	worker: WorkerType
	ok: bool
	output: Optional[Dict[str, Any]] = None
	error: Optional[str] = None
	llm_call_id: Optional[str] = None


class AggregatedResult(BaseModel):
	event_id: str
	status: Literal["partial", "complete", "failed"]
	summary_json: Optional[Dict[str, Any]] = None
	argument_json: Optional[Dict[str, Any]] = None
	sentiment_json: Optional[Dict[str, Any]] = None
	logic_bias_json: Optional[Dict[str, Any]] = None
	citations: Optional[List[Dict[str, Any]]] = None
	error_summary: Optional[str] = None


