from typing import Dict, Any
from fastapi import HTTPException, status
from .presidio_engine import redact
from .policy import run_policy
from .system_prompt import HARD_SYSTEM_PROMPT
from metrics.prometheus import guard_pii_masked, guard_blocked, guard_jailbreak
import re

SENSITIVE_PATTERNS = [
	re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS key
	re.compile(r"-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----"),
	re.compile(r"sk-[A-Za-z0-9]{32,}"),  # API keys
]


def normalize(s: str | None) -> str:
	return (s or "").strip()


def _ensure_no_sensitive(text: str) -> None:
	for pattern in SENSITIVE_PATTERNS:
		if pattern.search(text):
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Blocked: sensitive_secret_detected")


def apply_guardrails(payload: Dict[str, Any]) -> Dict[str, Any]:
	prompt = normalize(payload.get("prompt"))
	context = normalize(payload.get("context"))

	_ensure_no_sensitive(prompt)
	if context:
		_ensure_no_sensitive(context)

	red_prompt, _, counts1 = redact(prompt)
	red_context, _, counts2 = redact(context) if context else (context, 0, {})
	for k, v in {**counts1, **counts2}.items():
		guard_pii_masked.labels(entity_type=k).inc(v)

	allowed, reason = run_policy(f"{red_prompt}\n{red_context or ''}")
	if not allowed:
		if reason == "jailbreak":
			guard_jailbreak.inc()
		guard_blocked.labels(reason=reason).inc()
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Blocked by policy: {reason}")

	payload["prompt"] = f"{HARD_SYSTEM_PROMPT.strip()}\n\nUser prompt:\n{red_prompt}"
	payload["context"] = red_context
	return payload


