from __future__ import annotations

from typing import Sequence, Dict, Any


def estimate_confidence(results: Sequence[Dict[str, Any]], answer: str) -> float:
	if not results:
		return 0.3
	top_score = 0.0
	for item in results:
		score = item.get("score")
		if score is None:
			span = item.get("span") or {}
			score = span.get("score")
		if score:
			try:
				top_score = max(top_score, float(score))
			except (TypeError, ValueError):
				continue
	base = 0.55 + 0.08 * min(len(results), 3)
	if top_score:
		base += 0.1 * min(top_score, 1.0)
	lower = (answer or "").lower()
	if "không chắc" in lower or "khong chac" in lower or "does not know" in lower:
		base = min(base, 0.5)
	return round(min(0.95, base), 2)

