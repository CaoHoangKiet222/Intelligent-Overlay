import os
import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry.trace import get_current_span


class OTELContextFilter(logging.Filter):
	def filter(self, record):
		span = get_current_span()
		ctx = span.get_span_context() if span else None
		if ctx and ctx.trace_id:
			record.trace_id = format(ctx.trace_id, "032x")
			record.span_id = format(ctx.span_id, "016x")
		return True


def setup_json_logger():
	handler = logging.StreamHandler(sys.stdout)
	formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(trace_id)s %(span_id)s")
	handler.setFormatter(formatter)
	root = logging.getLogger()
	root.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
	root.addFilter(OTELContextFilter())
	root.handlers = [handler]


