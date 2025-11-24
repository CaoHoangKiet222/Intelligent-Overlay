from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from shared.contracts import ContextBundle, ContextChunk as SharedContextChunk, SpanRef

ContextChunk = SharedContextChunk


class SummaryBullet(BaseModel):
	text: str
	citations: List[SpanRef] = Field(default_factory=list)


class ArgumentEntry(BaseModel):
	claim: str
	evidence: List[SpanRef] = Field(default_factory=list)
	reasoning: str
	confidence: float = Field(default=0.6, ge=0.0, le=1.0)


class ImplicationItem(BaseModel):
	text: str
	citations: List[SpanRef] = Field(default_factory=list)


class SentimentResult(BaseModel):
	label: Literal["positive", "neutral", "negative", "mixed"]
	explanation: str
	citations: List[SpanRef] = Field(default_factory=list)


class LogicBiasIssue(BaseModel):
	type: str
	severity: int = Field(ge=1, le=3)
	explanation: str
	citations: List[SpanRef] = Field(default_factory=list)


class AnalysisBundle(BaseModel):
	context_id: str
	summary: List[SummaryBullet] = Field(default_factory=list)
	arguments: List[ArgumentEntry] = Field(default_factory=list)
	implications: List[ImplicationItem] = Field(default_factory=list)
	sentiment: Optional[SentimentResult] = None
	logic_bias: List[LogicBiasIssue] = Field(default_factory=list)


class DemoAnalyzeRequest(BaseModel):
	raw_text: str = Field(min_length=1)
	url: Optional[str] = None
	locale: Optional[str] = "auto"


class DemoAnalyzeResponse(AnalysisBundle):
	context_id: str


class DemoQARequest(BaseModel):
	context_id: str
	query: str = Field(min_length=1)


class DemoQAResponse(BaseModel):
	answer: str
	citations: List[SpanRef] = Field(default_factory=list)
	confidence: float = Field(default=0.5, ge=0.0, le=1.0)

