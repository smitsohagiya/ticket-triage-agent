"""OpenTelemetry tracing: one span per graph step, with the decision recorded as attributes.

Personal data never goes into a span: the agent only records categories, scores and the names of
guardrail signals, never ticket text.
"""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SpanExporter

tracer = trace.get_tracer("triage_agent")

_configured = False


def configure_tracing(exporter: str, service_name: str = "ticket-triage-agent") -> None:
    """Install a global tracer provider once. ``exporter`` is ``none``, ``console`` or ``otlp``.

    ``otlp`` sends spans over HTTP to ``OTEL_EXPORTER_OTLP_ENDPOINT`` (Jaeger, Grafana Tempo,
    Langfuse and others accept it).
    """
    global _configured
    if _configured or exporter == "none":
        return
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
    provider.add_span_processor(BatchSpanProcessor(_make_exporter(exporter)))
    trace.set_tracer_provider(provider)
    _configured = True


def _make_exporter(name: str) -> SpanExporter:
    if name == "console":
        return ConsoleSpanExporter()
    if name == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        return OTLPSpanExporter()
    raise ValueError(f"unknown trace exporter {name!r}; use none, console or otlp")
