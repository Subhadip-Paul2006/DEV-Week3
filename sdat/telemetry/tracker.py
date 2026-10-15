"""SDAT Internal Observability & Telemetry Subsystem.

Tracks and records structured telemetry for every audit phase:
- audit, scanner, agent, aggregation, and report durations
- queue depth and active/failed agent lifecycle
- transient retry counts with backoff tracking
- cache hit/miss rates
- evidence pipeline volume (raw, correlated, bundled)
- memory/resource utilization
- AI request latency and failure isolation tracking

Thread-safe: protected by an internal re-entrant lock (RLock) to allow safe
concurrent mutation across multiple parallel agent worker threads.
"""

from __future__ import annotations

import threading
import time
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Generator


@dataclass
class AuditTelemetry:
    """Structured, thread-safe telemetry metrics container for an SDAT audit execution."""

    run_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    start_time: float = field(default_factory=time.perf_counter)
    audit_duration_ms: float = 0.0
    scanner_duration_ms: dict[str, float] = field(default_factory=dict)
    agent_duration_ms: dict[str, float] = field(default_factory=dict)
    queue_depth: int = 0
    active_agents: list[str] = field(default_factory=list)
    failed_agents: list[dict[str, Any]] = field(default_factory=list)
    retry_counts: dict[str, int] = field(default_factory=dict)
    cache_hits: int = 0
    cache_misses: int = 0
    evidence_counts: dict[str, int] = field(default_factory=lambda: {"raw": 0, "correlated": 0, "bundles": 0})
    aggregation_duration_ms: float = 0.0
    memory_mb: float = 0.0
    ai_request_duration_ms: float = 0.0
    ai_failures: int = 0
    research_failures: int = 0
    report_generation_duration_ms: float = 0.0

    def __post_init__(self) -> None:
        self._lock = threading.RLock()
        if not tracemalloc.is_tracing():
            try:
                tracemalloc.start()
            except Exception:
                pass

    @contextmanager
    def time_operation(self, metric_name: str) -> Generator[None, None, None]:
        """Context manager to measure the duration of a general operation."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                if metric_name == "aggregation":
                    self.aggregation_duration_ms += elapsed_ms
                elif metric_name == "report_generation":
                    self.report_generation_duration_ms += elapsed_ms
                elif metric_name == "ai_request":
                    self.ai_request_duration_ms += elapsed_ms

    @contextmanager
    def time_scanner(self, scanner_name: str) -> Generator[None, None, None]:
        """Context manager to measure execution time for a specific language scanner."""
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                self.scanner_duration_ms[scanner_name] = round(
                    self.scanner_duration_ms.get(scanner_name, 0.0) + elapsed_ms, 2
                )

    @contextmanager
    def time_agent(self, agent_id: str) -> Generator[None, None, None]:
        """Context manager to track active agent lifecycle and execution duration."""
        with self._lock:
            if agent_id not in self.active_agents:
                self.active_agents.append(agent_id)
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            with self._lock:
                self.agent_duration_ms[agent_id] = round(
                    self.agent_duration_ms.get(agent_id, 0.0) + elapsed_ms, 2
                )
                if agent_id in self.active_agents:
                    self.active_agents.remove(agent_id)

    def record_agent_failure(self, agent_id: str, error: str, is_timeout: bool = False) -> None:
        """Record an isolated agent failure with diagnostic details."""
        with self._lock:
            self.failed_agents.append({
                "agent_id": agent_id,
                "error": str(error),
                "is_timeout": is_timeout,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            })

    def record_retry(self, agent_id: str) -> None:
        """Record an agent execution retry attempt."""
        with self._lock:
            self.retry_counts[agent_id] = self.retry_counts.get(agent_id, 0) + 1

    def record_cache_hit(self) -> None:
        """Increment the internal cache hit counter."""
        with self._lock:
            self.cache_hits += 1

    def record_cache_miss(self) -> None:
        """Increment the internal cache miss counter."""
        with self._lock:
            self.cache_misses += 1

    def set_evidence_counts(self, raw: int, correlated: int, bundles: int) -> None:
        """Record the volume of evidence facts across aggregation phases."""
        with self._lock:
            self.evidence_counts = {
                "raw": raw,
                "correlated": correlated,
                "bundles": bundles,
            }

    def record_ai_failure(self) -> None:
        """Record an isolated AI provider or research failure."""
        with self._lock:
            self.ai_failures += 1

    def record_research_failure(self) -> None:
        """Record a web/peer research agent failure."""
        with self._lock:
            self.research_failures += 1

    def finalize(self) -> None:
        """Finalize telemetry calculations before reporting."""
        with self._lock:
            self.audit_duration_ms = round((time.perf_counter() - self.start_time) * 1000.0, 2)
            if tracemalloc.is_tracing():
                try:
                    _current, peak = tracemalloc.get_traced_memory()
                    self.memory_mb = round(peak / (1024.0 * 1024.0), 2)
                except Exception:
                    self.memory_mb = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize telemetry metrics to a JSON-compatible dictionary."""
        with self._lock:
            return {
                "run_id": self.run_id,
                "timestamp": self.timestamp,
                "audit_duration_ms": self.audit_duration_ms,
                "scanner_duration_ms": dict(self.scanner_duration_ms),
                "agent_duration_ms": dict(self.agent_duration_ms),
                "queue_depth": self.queue_depth,
                "active_agents": list(self.active_agents),
                "failed_agents": list(self.failed_agents),
                "retry_counts": dict(self.retry_counts),
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "evidence_counts": dict(self.evidence_counts),
                "aggregation_duration_ms": round(self.aggregation_duration_ms, 2),
                "memory_mb": self.memory_mb,
                "ai_request_duration_ms": round(self.ai_request_duration_ms, 2),
                "ai_failures": self.ai_failures,
                "research_failures": self.research_failures,
                "report_generation_duration_ms": round(self.report_generation_duration_ms, 2),
            }

    def render_markdown_summary(self) -> str:
        """Render a readable markdown summary of the telemetry metrics."""
        with self._lock:
            total_scanner_ms = sum(self.scanner_duration_ms.values())
            total_agent_ms = sum(self.agent_duration_ms.values())
            failed_count = len(self.failed_agents)
            cache_total = self.cache_hits + self.cache_misses
            cache_rate = (self.cache_hits / cache_total * 100.0) if cache_total > 0 else 0.0

            lines = [
                "## SDAT Internal Observability & Telemetry",
                "",
                f"- **Audit Total Duration:** {self.audit_duration_ms:.2f} ms",
                f"- **Peak Memory Usage:** {self.memory_mb:.2f} MB",
                f"- **Scanner Processing:** {total_scanner_ms:.2f} ms across {len(self.scanner_duration_ms)} scanners",
                f"- **Evidence Pipeline:** {self.evidence_counts.get('raw', 0)} raw facts $\\rightarrow$ {self.evidence_counts.get('correlated', 0)} correlated $\\rightarrow$ {self.evidence_counts.get('bundles', 0)} concept bundles ({self.aggregation_duration_ms:.2f} ms)",
                f"- **Agent Swarm Duration:** {total_agent_ms:.2f} ms across {len(self.agent_duration_ms)} evaluated agents",
                f"- **Agent Health & Failures:** {failed_count} failures, {sum(self.retry_counts.values())} retries",
                f"- **Cache Performance:** {self.cache_hits} hits, {self.cache_misses} misses ({cache_rate:.1f}% hit rate)",
                f"- **AI Resilience:** {self.ai_failures} AI failures, {self.research_failures} research failures",
                f"- **Report Generation:** {self.report_generation_duration_ms:.2f} ms",
            ]

            if self.failed_agents:
                lines.append("\n### Isolated Agent Failures")
                for f in self.failed_agents:
                    to_tag = " (Timeout)" if f.get("is_timeout") else ""
                    lines.append(f"- **Agent {f.get('agent_id')}**{to_tag}: {f.get('error')}")

            return "\n".join(lines)
