import pytest
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

from triage_agent.telemetry import _make_exporter, configure_tracing


def test_exporters_are_chosen_by_name() -> None:
    assert isinstance(_make_exporter("console"), ConsoleSpanExporter)
    assert isinstance(_make_exporter("otlp"), OTLPSpanExporter)


def test_unknown_exporters_are_rejected() -> None:
    with pytest.raises(ValueError, match="unknown trace exporter"):
        _make_exporter("zipkin")


def test_none_installs_nothing() -> None:
    configure_tracing("none")
