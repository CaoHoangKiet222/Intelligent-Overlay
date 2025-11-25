from __future__ import annotations

import re
from textwrap import shorten
from typing import List, Optional, Tuple

SEGMENT_LINE = re.compile(r"\[seg:(?P<id>[^\]]+)\]\s*(?P<text>.+)")
QUESTION_LINE = re.compile(r"Question:\s*(?P<question>.+)", re.IGNORECASE)


def generate_mock_output(provider_name: str, prompt: str) -> str:
	user_prompt = _extract_user_prompt(prompt)
	question = _extract_question(user_prompt)
	segments = _extract_segments(user_prompt)
	if segments:
		return _format_qa_response(question, segments)
	return f"[{provider_name}-mock] {user_prompt.strip()[:400]}"


def _extract_user_prompt(prompt: str) -> str:
	parts = prompt.split("User prompt:", 1)
	return parts[1] if len(parts) == 2 else prompt


def _extract_question(user_prompt: str) -> Optional[str]:
	match = QUESTION_LINE.search(user_prompt)
	if match:
		return match.group("question").strip()
	return None


def _extract_segments(user_prompt: str) -> List[Tuple[str, str]]:
	if "Context:" not in user_prompt:
		return []
	context = user_prompt.split("Context:", 1)[1]
	segments: List[Tuple[str, str]] = []
	for line in context.splitlines():
		line = line.strip()
		if not line:
			continue
		match = SEGMENT_LINE.match(line)
		if match:
			seg_id = match.group("id").strip().lower()
			text = match.group("text").strip()
			text = re.sub(r"^[\-\•]+\s*", "", text)
			segments.append((seg_id, text))
	return segments


def _format_qa_response(question: Optional[str], segments: List[Tuple[str, str]]) -> str:
	top_segments = segments[:2]
	descs = [shorten(text, width=160, placeholder="…") for _, text in top_segments]
	if question:
		answer_body = f"{question}".rstrip("?")
		if descs:
			answer_body = f"{answer_body}: " + "; ".join(descs)
	else:
		answer_body = "; ".join(descs) if descs else "Không có thông tin nổi bật."
	citations = ", ".join([f"seg:{seg_id}" for seg_id, _ in top_segments])
	confidence = 0.82 if top_segments else 0.55
	return f"ANSWER: {answer_body}\nCITATIONS: {citations or 'none'}\nCONFIDENCE: {confidence:.2f}"

