from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PromptCreate(BaseModel):
	key: str
	name: str
	description: Optional[str] = None
	tags: Optional[List[str]] = None
	is_active: bool = True


class PromptVersionCreate(BaseModel):
	template: str
	variables: Dict[str, Any] = Field(default_factory=dict)
	input_schema: Optional[Dict[str, Any]] = None
	output_schema: Optional[Dict[str, Any]] = None
	notes: Optional[str] = None


class PromptDTO(BaseModel):
	id: str
	key: str
	name: str
	description: Optional[str] = None
	tags: Optional[List[str]] = None
	is_active: bool
	created_at: str
	updated_at: str


class PromptVersionDTO(BaseModel):
	id: str
	prompt_id: str
	version: int
	template: str
	variables: Dict[str, Any]
	input_schema: Optional[Dict[str, Any]]
	output_schema: Optional[Dict[str, Any]]
	created_at: str


class PromptResolvedDTO(BaseModel):
	prompt: PromptDTO
	version: PromptVersionDTO


