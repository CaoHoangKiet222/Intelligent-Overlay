import pytest
from domain.validators import validate_template
from fastapi import HTTPException


def test_validate_ok():
	tpl = "Hello {{ name }}, tone={{ tone|default('neutral') }}"
	vars = {"required": ["name"], "optional": ["tone"]}
	validate_template(tpl, vars)


def test_missing_placeholder_400():
	tpl = "Hello {{ name }}"
	vars = {"required": ["name", "company"], "optional": []}
	with pytest.raises(HTTPException) as e:
		validate_template(tpl, vars)
	assert e.value.status_code == 400
	assert e.value.detail["code"] == "MISSING_PLACEHOLDER"


def test_extra_placeholder_400():
	tpl = "Hello {{ name }} from {{ company }} and {{ extra }}"
	vars = {"required": ["name"], "optional": ["company"]}
	with pytest.raises(HTTPException) as e:
		validate_template(tpl, vars)
	assert e.value.status_code == 400
	assert e.value.detail["code"] == "UNDECLARED_PLACEHOLDER"


