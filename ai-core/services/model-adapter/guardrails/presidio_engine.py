from typing import List, Tuple, Dict
try:
	from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern, RecognizerRegistry
	from presidio_anonymizer import AnonymizerEngine
	from presidio_analyzer.nlp_engine import SpacyNlpEngine
	_PRESIDIO_AVAILABLE = True
except Exception:
	_PRESIDIO_AVAILABLE = False


def _build_analyzer():
	if not _PRESIDIO_AVAILABLE:
		return None
	nlp_engine = SpacyNlpEngine(models={"en": "en_core_web_sm"})
	registry = RecognizerRegistry()
	registry.load_predefined_recognizers()
	vn_phone_pattern = Pattern("VN_PHONE", r"(?:\\+?84|0)(?:\\s|-)?[1-9]\\d{1}(?:\\s|-)?\\d{3}(?:\\s|-)?\\d{4}", 0.5)
	vn_phone_recog = PatternRecognizer(supported_entity="PHONE_NUMBER", patterns=[vn_phone_pattern])
	registry.add_recognizer(vn_phone_recog)
	return AnalyzerEngine(nlp_engine=nlp_engine, registry=registry, supported_languages=["en"])


def _build_anonymizer():
	if not _PRESIDIO_AVAILABLE:
		return None
	return AnonymizerEngine()


ANALYZER = _build_analyzer()
ANONYMIZER = _build_anonymizer()


def redact(text: str, entities: List[str] | None = None) -> Tuple[str, int, Dict[str, int]]:
	if not text:
		return text, 0, {}
	if not ANALYZER or not ANONYMIZER:
		return text, 0, {}
	entities = entities or ["EMAIL_ADDRESS", "PHONE_NUMBER"]
	results = ANALYZER.analyze(text=text, entities=entities, language="en")
	if not results:
		return text, 0, {}
	operators = {
		"EMAIL_ADDRESS": {"type": "replace", "new_value": "[EMAIL]"},
		"PHONE_NUMBER": {"type": "replace", "new_value": "[PHONE]"},
	}
	res = ANONYMIZER.anonymize(text=text, analyzer_results=results, operators=operators)
	counts: Dict[str, int] = {}
	for r in results:
		k = r.entity_type
		counts[k] = counts.get(k, 0) + 1
	return res.text, len(results), counts


