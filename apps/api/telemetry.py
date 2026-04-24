import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


def setup_telemetry() -> None:
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    provider = TracerProvider(resource=Resource.create({"service.name": "ai-parliament-api"}))
    trace.set_tracer_provider(provider)
    logging.getLogger("api.telemetry").info("OpenTelemetry tracer initialized")

