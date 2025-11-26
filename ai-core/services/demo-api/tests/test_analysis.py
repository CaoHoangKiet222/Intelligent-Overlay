from services.analysis_utils import (
	extract_segment_ids,
	parse_labeled_block,
	parse_implication_block,
	parse_sentiment,
	parse_logic_bias_line,
)


def test_extract_segment_ids():
	text = "- bullet referencing [seg:ABC] and [SEG:1234]"
	assert extract_segment_ids(text) == ["abc", "1234"]


def test_parse_labeled_block_defaults():
	claim, evidence, reasoning = parse_labeled_block("CLAIM: c\nEVIDENCE: e\nREASONING: r")
	assert claim == "c"
	assert evidence == "e"
	assert reasoning == "r"


def test_parse_implication_and_sentiment():
	text = "IMPLICATIONS:\n1. item [seg:abc]\nSENTIMENT: positive - good"
	implications, sentiment_line = parse_implication_block(text)
	assert implications == ["item [seg:abc]"]
	label, explanation = parse_sentiment(sentiment_line)
	assert label == "positive"
	assert "good" in explanation


def test_parse_logic_bias_line():
	line = "ISSUE: bias; SEG: seg:abc; SEVERITY: 2; NOTE: details"
	payload = parse_logic_bias_line(line)
	assert payload["issue_type"] == "bias"
	assert payload["severity"] == 2

