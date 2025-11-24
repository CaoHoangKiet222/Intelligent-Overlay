from typing import Optional, Dict, List, Literal
from pydantic import BaseModel, Field
from shared.contracts import ContextChunk, SpanRef

WorkerType = Literal["summary", "argument", "sentiment", "logic_bias"]


class AnalysisTask(BaseModel):
	event_id: str
	bundle_id: Optional[str] = None
	query: Optional[str] = None
	segments: List[ContextChunk] = Field(default_factory=list)
	language: Literal["vi", "en", "auto"] = "auto"
	prompt_ids: Dict[WorkerType, str] = Field(default_factory=dict)
	meta: Dict[str, object] = Field(default_factory=dict)


class WorkerResult(BaseModel):
	worker: WorkerType
	ok: bool
	output: Optional[Dict[str, object]] = None
	error: Optional[str] = None
	llm_call_id: Optional[str] = None


class AggregatedResult(BaseModel):
	event_id: str
	status: Literal["partial", "complete", "failed"]
	summary_json: Optional[Dict[str, object]] = None
	argument_json: Optional[Dict[str, object]] = None
	sentiment_json: Optional[Dict[str, object]] = None
	logic_bias_json: Optional[Dict[str, object]] = None
	citations: Optional[List[SpanRef]] = None
	error_summary: Optional[str] = None


class SummaryWorkerBullet(BaseModel):
	bullet: str
	spans: List[SpanRef]
	confidence: float = Field(default=0.75, ge=0.0, le=1.0)


class SummaryWorkerOutput(BaseModel):
	context_id: str
	bullets: List[SummaryWorkerBullet] = Field(default_factory=list)
	seed_sentences: List[str] = Field(default_factory=list)


class SummaryWorkerRequest(BaseModel):
	context_id: str
	language: Literal["vi", "en", "auto"] = "auto"
	segments: List[ContextChunk] = Field(default_factory=list)
	prompt_ref: Optional[str] = None


class ArgumentClaim(BaseModel):
	claim: str
	evidence_spans: List[SpanRef] = Field(default_factory=list)
	reasoning: str
	confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class ArgumentWorkerOutput(BaseModel):
	context_id: str
	claims: List[ArgumentClaim] = Field(default_factory=list)


class ArgumentWorkerRequest(BaseModel):
	context_id: str
	language: Literal["vi", "en", "auto"] = "auto"
	segments: List[ContextChunk] = Field(default_factory=list)
	claim_prompt_ref: Optional[str] = None
	reason_prompt_ref: Optional[str] = None


class SentimentResult(BaseModel):
	label: Literal["positive", "negative", "neutral", "mixed", "unknown"] = "neutral"
	score: float = Field(default=0.5, ge=0.0, le=1.0)
	sarcasm_flag: Optional[bool] = None
	explanation: Optional[str] = None


class ImplicationItem(BaseModel):
	text: str
	spans: List[SpanRef] = Field(default_factory=list)
	confidence: float = Field(default=0.65, ge=0.0, le=1.0)


class ImplicationSentimentOutput(BaseModel):
	context_id: str
	implications: List[ImplicationItem] = Field(default_factory=list)
	sentiment: SentimentResult


class ImplicationSentimentRequest(BaseModel):
	context_id: str
	language: Literal["vi", "en", "auto"] = "auto"
	segments: List[ContextChunk] = Field(default_factory=list)
	implication_prompt_ref: Optional[str] = None
	sentiment_prompt_ref: Optional[str] = None


class LogicBiasFinding(BaseModel):
	type: str
	span: SpanRef
	explanation: str
	severity: int = Field(ge=1, le=3)


class LogicBiasOutput(BaseModel):
	context_id: str
	findings: List[LogicBiasFinding] = Field(default_factory=list)


class LogicBiasRequest(BaseModel):
	context_id: str
	language: Literal["vi", "en", "auto"] = "auto"
	segments: List[ContextChunk] = Field(default_factory=list)
	prompt_ref: Optional[str] = None


class OrchestratorAnalyzeRequest(BaseModel):
	context_id: str
	language: Literal["vi", "en", "auto"] = "auto"
	segments: List[ContextChunk] = Field(default_factory=list)
	prompt_ids: Dict[str, str] = Field(default_factory=dict)


class AnalysisBundleResponse(BaseModel):
	summary: Optional[SummaryWorkerOutput] = None
	arguments: Optional[ArgumentWorkerOutput] = None
	implications: List[ImplicationItem] = Field(default_factory=list)
	sentiment: Optional[SentimentResult] = None
	logic_bias: Optional[LogicBiasOutput] = None
	worker_statuses: Dict[str, Literal["ok", "error", "timeout"]] = Field(default_factory=dict)


