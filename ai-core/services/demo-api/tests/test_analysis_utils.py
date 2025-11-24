from services.analysis import (
	_extract_segment_ids,
	_parse_labeled_block,
	_parse_implication_block,
	_parse_sentiment,
	_parse_logic_bias_line,
)


def test_extract_segment_ids():
	text = "- bullet referencing [seg:ABC] and [SEG:1234]"
	assert _extract_segment_ids(text) == ["abc", "1234"]


def test_parse_labeled_block_defaults():
	claim, evidence, reasoning = _parse_labeled_block("CLAIM: c\nEVIDENCE: e\nREASONING: r")
	assert claim == "c"
	assert evidence == "e"
	assert reasoning == "r"


def test_parse_implication_and_sentiment():
	text = "IMPLICATIONS:\n1. item [seg:abc]\nSENTIMENT: positive - good"
	implications, sentiment_line = _parse_implication_block(text)
	assert implications == ["item [seg:abc]"]
	label, explanation = _parse_sentiment(sentiment_line)
	assert label == "positive"
	assert "good" in explanation


def test_parse_logic_bias_line():
	line = "ISSUE: bias; SEG: seg:abc; SEVERITY: 2; NOTE: details"
	payload = _parse_logic_bias_line(line)
	assert payload["issue_type"] == "bias"
	assert payload["severity"] == 2

