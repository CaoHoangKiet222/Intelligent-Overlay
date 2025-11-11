from typing import Optional, Dict


def find_local_span(segment_text: str, query: str) -> Optional[Dict[str, int]]:
	s = segment_text.lower()
	q = query.lower().strip()
	if not q:
		return None
	idx = s.find(q)
	if idx == -1:
		toks = [t for t in q.split() if len(t) >= 3]
		for t in toks:
			i = s.find(t)
			if i != -1:
				return {"start": i, "end": i + len(t)}
		return None
	return {"start": idx, "end": idx + len(q)}


