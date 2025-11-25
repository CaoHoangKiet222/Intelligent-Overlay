import os
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
try:
	from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except Exception:
	SQLAlchemyInstrumentor = None
try:
	from opentelemetry.instrumentation.aiokafka import AIOKafkaInstrumentor
except Exception:
	AIOKafkaInstrumentor = None

_PROVIDER_INITIALIZED = False
_HTTPX_INSTRUMENTED = False
_KAFKA_INSTRUMENTED = False


def init_otel(app=None, sqlalchemy_engine=None) -> None:
	global _PROVIDER_INITIALIZED, _HTTPX_INSTRUMENTED, _KAFKA_INSTRUMENTED

	if not _PROVIDER_INITIALIZED:
		svc = os.getenv("SERVICE_NAME", "aicore-service")
		res = Resource.create({"service.name": svc})
		provider = TracerProvider(resource=res)
		exporter = OTLPSpanExporter(endpoint=os.getenv("OTLP_ENDPOINT", "grpc://otel-collector:4317"))
		provider.add_span_processor(BatchSpanProcessor(exporter))
		trace.set_tracer_provider(provider)
		_PROVIDER_INITIALIZED = True

	if app is not None and not getattr(app.state, "_otel_instrumented", False):
		FastAPIInstrumentor.instrument_app(app)
		app.add_middleware(OpenTelemetryMiddleware)
		app.state._otel_instrumented = True

	if not _HTTPX_INSTRUMENTED:
		HTTPXClientInstrumentor().instrument()
		_HTTPX_INSTRUMENTED = True

	if sqlalchemy_engine is not None and SQLAlchemyInstrumentor:
		SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine, enable_commenter=True)

	if AIOKafkaInstrumentor and not _KAFKA_INSTRUMENTED:
		try:
			AIOKafkaInstrumentor().instrument()
			_KAFKA_INSTRUMENTED = True
		except Exception:
			pass


