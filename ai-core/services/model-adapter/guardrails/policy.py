import re
from typing import Tuple, Optional

INJECTION_PATTERNS = [
	r"ignore (all|previous) instructions",
	r"disregard (all|previous) instructions",
	r"you are (now )?dan",
	r"do anything now",
	r"reveal (system|hidden) prompt",
	r"act as (developer|sysadmin) and",
]
DISALLOWED_TOPICS = [
	r"how to (make|build|buy).*(weapon|bomb|drug|explosive)",
	r"bypass.*(security|paywall|copyright)",
	r"steal|stolen|credential|password dump",
]


def detect_jailbreak(text: str) -> bool:
	t = text.lower()
	return any(re.search(p, t) for p in INJECTION_PATTERNS)


def detect_disallowed(text: str) -> Optional[str]:
	t = text.lower()
	for p in DISALLOWED_TOPICS:
		if re.search(p, t):
			return p
	return None


def run_policy(redacted_prompt: str) -> Tuple[bool, Optional[str]]:
	if detect_jailbreak(redacted_prompt):
		return False, "jailbreak"
	dis = detect_disallowed(redacted_prompt)
	if dis:
		return False, "disallowed_content"
	return True, None


