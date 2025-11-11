from typing import Set, Dict, Any
from jinja2 import Environment, meta
from fastapi import HTTPException, status


def extract_placeholders(template: str) -> Set[str]:
	env = Environment()
	ast = env.parse(template)
	return set(meta.find_undeclared_variables(ast))


def validate_template(template: str, variables: Dict[str, Any]) -> None:
	placeholders = extract_placeholders(template)
	required = set(variables.get("required", []))
	optional = set(variables.get("optional", []))
	allowed = required.union(optional)

	missing = required - placeholders
	extra = placeholders - allowed

	if missing:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail={"code": "MISSING_PLACEHOLDER", "missing": sorted(list(missing))},
		)
	if extra:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail={"code": "UNDECLARED_PLACEHOLDER", "extra": sorted(list(extra))},
		)


