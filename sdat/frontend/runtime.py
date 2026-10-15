"""Runtime performance layer for frontend auditing.

Provides the interface and collector for optional browser runtime telemetry.
Strictly maintains the separation between static potential hazards and
actual runtime metrics (FCP, LCP, CLS, TTFB, INP).
"""

from __future__ import annotations

from typing import Any, Protocol

from sdat.frontend.models import RuntimeMetrics


class BrowserRuntimeCollector(Protocol):
    """Protocol for collecting or ingesting browser runtime telemetry."""

    def collect(self, url: str | None = None) -> RuntimeMetrics:
        """Collect runtime metrics for a target frontend URL."""
        ...


class OfflineRuntimeCollector:
    """Default runtime collector for offline static audits.

    Does NOT fabricate runtime metrics; explicitly records that runtime
    testing is unmeasured/unavailable so downstream scoring marks
    runtime metrics as unmeasured rather than guessing.
    """

    def collect(self, url: str | None = None) -> RuntimeMetrics:
        return RuntimeMetrics(
            measured=False,
            notes="Runtime browser measurements unmeasured: audit executed in offline static mode",
        )


class ProvidedRuntimeCollector:
    """Collector that accepts verified browser telemetry observations."""

    def __init__(self, metrics_data: dict[str, Any]) -> None:
        self._data = metrics_data

    def collect(self, url: str | None = None) -> RuntimeMetrics:
        return RuntimeMetrics(
            measured=True,
            fcp_ms=self._data.get("fcp_ms"),
            lcp_ms=self._data.get("lcp_ms"),
            cls=self._data.get("cls"),
            ttfb_ms=self._data.get("ttfb_ms"),
            inp_ms=self._data.get("inp_ms"),
            dom_nodes=self._data.get("dom_nodes"),
            request_count=self._data.get("request_count"),
            transferred_bytes=self._data.get("transferred_bytes"),
            notes=self._data.get("notes", "Collected from active browser runtime session"),
        )
