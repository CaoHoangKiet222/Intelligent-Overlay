from time import perf_counter
import os
import logging
import uvicorn
import json
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from domain.schemas import AskRequest, AskResponse, QaRequest, QaResponse
from domain.state import AgentState
from graph.build import build_graph
from metrics.prometheus import metrics_app, latency, fallback_used, tool_errors
from services.qa_utils import estimate_confidence


logger = logging.getLogger(__name__)
graph = build_graph()


async def _execute_graph(state: AgentState) -> AgentState:
	t0 = perf_counter()
	try:
		out_dict = await graph.ainvoke(state)
		# LangGraph returns AddableValuesDict, convert to AgentState
		if isinstance(out_dict, dict):
			out = AgentState.model_validate(out_dict)
		else:
			out = out_dict
	except Exception as e:
		logger.error(
			"graph_execution_error",
			extra={
				"error_type": type(e).__name__,
				"error_message": str(e),
				"state_query": state.original_query,
				"state_context_id": state.context_id,
				"state_language": state.language,
			},
			exc_info=True,
		)
		raise
	
	took = int((perf_counter() - t0) * 1000)
	latency.observe(took)
	
	# Safely access plan attribute
	plan = getattr(out, "plan", {}) or {}
	if isinstance(plan, dict) and plan.get("intent") == "tool":
		tool_result = getattr(out, "tool_result", None)
		if tool_result and isinstance(tool_result, dict) and "error" in tool_result:
			tool_errors.inc()
	
	logs = getattr(out, "logs", []) or []
	if logs and any("fallback: used" in str(x) for x in logs):
		fallback_used.inc()
	
	return out


def create_app() -> FastAPI:
	application = FastAPI(title="Agent Service (LangGraph)", version="0.1.0")
	application.mount("/metrics", metrics_app)

	@application.post("/agent/qa", response_model=QaResponse)
	async def agent_qa(req: QaRequest):
		state = AgentState(
			session_id=req.conversation_id,
			original_query=req.query,
			language=req.language,
			meta={"source": "agent_qa", "context_id": req.context_id, "allow_external": req.allow_external},
			context_id=req.context_id,
			allow_external=req.allow_external,
		)
		try:
			out = await _execute_graph(state)
			answer = getattr(out, "answer", None) or "Xin lỗi, tôi không tìm thấy đủ thông tin trong ngữ cảnh được cung cấp."
			retrieved = getattr(out, "retrieved", []) or []
			confidence = estimate_confidence(retrieved, answer)
			citations = getattr(out, "citations", []) or []
			used_external = getattr(out, "used_external", False)
			
			return QaResponse(
				conversation_id=req.conversation_id,
				answer=answer,
				citations=citations,
				confidence=confidence,
				used_external=used_external,
			)
		except HTTPException:
			raise
		except Exception as exc:
			logger.error(
				"qa_error",
				extra={
					"error_type": type(exc).__name__,
					"error_message": str(exc),
					"request_query": req.query,
					"request_context_id": req.context_id,
					"request_conversation_id": req.conversation_id,
					"request_language": req.language,
					"request_allow_external": req.allow_external,
				},
				exc_info=True,
			)
			raise HTTPException(
				status_code=500,
				detail=f"qa_failed: {type(exc).__name__}: {str(exc)}"
			) from exc

	@application.post("/agent/ask", response_model=AskResponse)
	async def ask(req: AskRequest):
		logger.warning("/agent/ask is deprecated; use /agent/qa instead")
		state = AgentState(
			original_query=req.query,
			session_id=req.session_id,
			language=req.language,
			meta=req.meta,
			allow_external=True,
		)
		try:
			out = await _execute_graph(state)
			return AskResponse(
				session_id=getattr(out, "session_id", None),
				answer=getattr(out, "answer", None) or "",
				citations=getattr(out, "citations", []) or [],
				plan=getattr(out, "plan", {}) or {},
				tool_result=getattr(out, "tool_result", None),
				logs=getattr(out, "logs", []) or [],
			)
		except HTTPException:
			raise
		except Exception as e:
			logger.error(
				"ask_error",
				extra={
					"error_type": type(e).__name__,
					"error_message": str(e),
					"request_query": req.query,
					"request_session_id": req.session_id,
					"request_language": req.language,
					"request_meta": json.dumps(req.meta) if req.meta else None,
				},
				exc_info=True,
			)
			raise HTTPException(
				status_code=500,
				detail=f"ask_failed: {type(e).__name__}: {str(e)}"
			) from e

	@application.get("/healthz")
	async def healthz():
		return {"ok": True}

	return application


app = create_app()


if __name__ == "__main__":
	import logging
	
	port = int(os.getenv("PORT", "8000"))
	logging.basicConfig(level=logging.INFO)
	logger = logging.getLogger(__name__)
	logger.info(f"Starting Agent Service on port {port}")
	logger.info(f"Health check: http://localhost:{port}/healthz")
	logger.info(f"Metrics: http://localhost:{port}/metrics")
	
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


