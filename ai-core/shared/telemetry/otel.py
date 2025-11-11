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


def init_otel(app=None, sqlalchemy_engine=None) -> None:
	svc = os.getenv("SERVICE_NAME", "aicore-service")
	res = Resource.create({"service.name": svc})
	provider = TracerProvider(resource=res)
	exporter = OTLPSpanExporter(endpoint=os.getenv("OTLP_ENDPOINT", "grpc://otel-collector:4317"))
	provider.add_span_processor(BatchSpanProcessor(exporter))
	trace.set_tracer_provider(provider)

	if app is not None:
		FastAPIInstrumentor.instrument_app(app)
		app.add_middleware(OpenTelemetryMiddleware)

	HTTPXClientInstrumentor().instrument()
	if sqlalchemy_engine is not None and SQLAlchemyInstrumentor:
		SQLAlchemyInstrumentor().instrument(engine=sqlalchemy_engine, enable_commenter=True)
	if AIOKafkaInstrumentor:
		try:
			AIOKafkaInstrumentor().instrument()
		except Exception:
			pass


