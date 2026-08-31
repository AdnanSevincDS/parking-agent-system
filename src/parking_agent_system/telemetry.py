from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from openinference.instrumentation.langchain import LangChainInstrumentor

def setup_phoenix_telemetry():
    """Initializes Phoenix tracing for LangChain."""
    provider = TracerProvider()
    exporter = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    LangChainInstrumentor().instrument()