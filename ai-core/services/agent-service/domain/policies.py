import re
from typing import Tuple, Dict, Any


EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(\\+?\\d[\\d\\-\\s]{7,}\\d)")


def redact_pii(text: str) -> Tuple[str, Dict[str, Any]]:
	flags: Dict[str, Any] = {}
	red = EMAIL.sub("[EMAIL]", text)
	if red != text:
		flags["email_masked"] = True
	tmp = PHONE.sub("[PHONE]", red)
	if tmp != red:
		flags["phone_masked"] = True
	# TODO: Need to define other PII types
	return tmp, flags


