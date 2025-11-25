from time import perf_counter
import os
import logging
import uvicorn
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
	out = await graph.ainvoke(state)
	took = int((perf_counter() - t0) * 1000)
	latency.observe(took)
	if out.plan.get("intent") == "tool" and out.tool_result and "error" in out.tool_result:
		tool_errors.inc()
	if out.logs and any("fallback: used" in x for x in out.logs):
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
			answer = out.answer or "Xin lỗi, tôi không tìm thấy đủ thông tin trong ngữ cảnh được cung cấp."
			confidence = estimate_confidence(out.retrieved, answer)
			return QaResponse(
				conversation_id=req.conversation_id,
				answer=answer,
				citations=out.citations,
				confidence=confidence,
				used_external=out.used_external,
			)
		except Exception as exc:
			logger.error("qa_error", exc_info=exc)
			raise HTTPException(status_code=500, detail="qa_failed") from exc

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
				session_id=out.session_id,
				answer=out.answer or "",
				citations=out.citations,
				plan=out.plan,
				tool_result=out.tool_result,
				logs=out.logs,
			)
		except Exception as e:
			logger.error(f"Error in ask: {e}")
			raise HTTPException(status_code=500, detail=str(e))

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


