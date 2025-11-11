from typing import List, Dict, Any
from domain.schemas import WorkerResult, AggregatedResult


def aggregate(event_id: str, results: List[WorkerResult]) -> AggregatedResult:
	out: Dict[str, Any] = {
		"summary_json": None,
		"argument_json": None,
		"sentiment_json": None,
		"logic_bias_json": None,
		"citations": None,
	}
	fails = []
	for r in results:
		if r.worker == "summary" and r.ok:
			out["summary_json"] = r.output
		elif r.worker == "argument" and r.ok:
			out["argument_json"] = r.output
		elif r.worker == "sentiment" and r.ok:
			out["sentiment_json"] = r.output
		elif r.worker == "logic_bias" and r.ok:
			out["logic_bias_json"] = r.output
		else:
			if not r.ok:
				fails.append({r.worker: r.error})
	if all([out["summary_json"], out["argument_json"], out["sentiment_json"], out["logic_bias_json"]]):
		status = "complete"
	elif any([out["summary_json"], out["argument_json"], out["sentiment_json"], out["logic_bias_json"]]):
		status = "partial"
	else:
		status = "failed"
	err = None if status != "failed" else str(fails[:3])
	return AggregatedResult(event_id=event_id, status=status, error_summary=err, **out)


