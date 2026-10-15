"""Unit tests for SDAT Internal Observability & Telemetry Subsystem."""

from __future__ import annotations

import time

from sdat.telemetry.tracker import AuditTelemetry


def test_telemetry_initialization_and_timers():
    telem = AuditTelemetry(run_id="test_run_01")
    assert telem.run_id == "test_run_01"
    assert telem.audit_duration_ms == 0.0

    with telem.time_scanner("python"):
        time.sleep(0.01)

    assert "python" in telem.scanner_duration_ms
    assert telem.scanner_duration_ms["python"] > 5.0

    with telem.time_operation("aggregation"):
        time.sleep(0.01)

    assert telem.aggregation_duration_ms > 5.0


def test_telemetry_agent_lifecycle_and_failures():
    telem = AuditTelemetry(run_id="test_agent_lifecycle")

    with telem.time_agent("F-01"):
        assert "F-01" in telem.active_agents

    assert "F-01" not in telem.active_agents
    assert "F-01" in telem.agent_duration_ms

    telem.record_agent_failure("D-21", "Simulated crash", is_timeout=False)
    telem.record_agent_failure("D-02", "Timed out after 30s", is_timeout=True)

    assert len(telem.failed_agents) == 2
    assert telem.failed_agents[0]["agent_id"] == "D-21"
    assert telem.failed_agents[1]["is_timeout"] is True


def test_telemetry_cache_and_evidence_counters():
    telem = AuditTelemetry(run_id="test_counters")
    telem.record_cache_hit()
    telem.record_cache_hit()
    telem.record_cache_miss()
    telem.record_retry("F-04")
    telem.set_evidence_counts(raw=100, correlated=85, bundles=12)

    assert telem.cache_hits == 2
    assert telem.cache_misses == 1
    assert telem.retry_counts["F-04"] == 1
    assert telem.evidence_counts["bundles"] == 12

    telem.finalize()
    assert telem.audit_duration_ms >= 0.0

    data = telem.to_dict()
    assert data["cache_hits"] == 2
    assert data["evidence_counts"]["raw"] == 100

    summary_md = telem.render_markdown_summary()
    assert "Internal Observability & Telemetry" in summary_md
    assert "Cache Performance" in summary_md
