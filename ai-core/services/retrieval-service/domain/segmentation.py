import re
from typing import List, Dict, Any


def segment_text(text: str, max_chars: int = 1000, overlap: int = 100) -> List[Dict[str, Any]]:
	parts = re.split(r'(?<=[.!?。！？])\s+', text.strip())
	segments: List[Dict[str, Any]] = []
	buf = ""
	start = 0
	for p in parts:
		if not p:
			continue
		candidate = (buf + " " + p).strip() if buf else p
		if len(candidate) <= max_chars:
			buf = candidate
			continue
		if buf:
			end = start + len(buf)
			segments.append({"text": buf, "start_offset": start, "end_offset": end})
			overlap_text = buf[-overlap:] if overlap > 0 and len(buf) > overlap else ""
			start = end - len(overlap_text)
			buf = (overlap_text + " " + p).strip()
		else:
			chunks = [p[i:i + max_chars] for i in range(0, len(p), max_chars)]
			for c in chunks:
				end = start + len(c)
				segments.append({"text": c, "start_offset": start, "end_offset": end})
				start = end
			buf = ""
	if buf:
		end = start + len(buf)
		segments.append({"text": buf, "start_offset": start, "end_offset": end})
	return segments


