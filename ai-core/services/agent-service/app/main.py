from time import perf_counter
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from domain.schemas import AskRequest, AskResponse
from domain.state import AgentState
from graph.build import build_graph
from metrics.prometheus import metrics_app, latency, fallback_used, tool_errors


graph = build_graph()


def create_app() -> FastAPI:
	application = FastAPI(title="Agent Service (LangGraph)", version="0.1.0")
	application.mount("/metrics", metrics_app)

	@application.post("/agent/ask", response_model=AskResponse)
	async def ask(req: AskRequest):
		t0 = perf_counter()
		state = AgentState(original_query=req.query, session_id=req.session_id, language=req.language, meta=req.meta)
		try:
			out = await graph.ainvoke(state)
			took = int((perf_counter() - t0) * 1000)
			latency.observe(took)
			if out.plan.get("intent") == "tool" and out.tool_result and "error" in out.tool_result:
				tool_errors.inc()
			if out.logs and any("fallback: used" in x for x in out.logs):
				fallback_used.inc()
			return AskResponse(
				session_id=out.session_id,
				answer=out.answer or "",
				citations=out.citations,
				plan=out.plan,
				tool_result=out.tool_result,
				logs=out.logs,
			)
		except Exception as e:
			raise HTTPException(status_code=500, detail=str(e))

	@application.get("/healthz")
	async def healthz():
		return {"ok": True}

	return application


app = create_app()


if __name__ == "__main__":
	port = int(os.getenv("PORT", "8000"))
	uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)


