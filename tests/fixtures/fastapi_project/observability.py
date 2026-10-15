"""Observability, structured logging, Prometheus metrics, and distributed tracing."""

from __future__ import annotations

import logging
import sys

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import Counter, Histogram

# 1. Structured Application Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("ecommerce_service")

# 2. Observability: Prometheus Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total count of HTTP requests processed by endpoint and status",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request execution latency distribution in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

DB_QUERY_DURATION = Histogram(
    "database_query_duration_seconds",
    "Latency of database interactions",
    ["query_type"],
)

# 3. Distributed Tracing with OpenTelemetry
provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("ecommerce.tracer")


def init_alerting_system() -> None:
    """Initialize error monitoring and alerts (e.g. Sentry / PagerDuty)."""
    try:
        import sentry_sdk  # type: ignore
        sentry_sdk.init(
            dsn="https://example_key@o0.ingest.sentry.io/0",
            traces_sample_rate=0.2,
        )
        logger.info("Sentry alerting system initialized")
    except ImportError:
        logger.warning("Sentry SDK not installed; falling back to standard alerting")
