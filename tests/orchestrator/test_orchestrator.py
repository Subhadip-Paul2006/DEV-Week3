"""Tests for the Phase 0 orchestrator pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from sdat.models import Decision, DecisionStatus, Evidence, Priority
from sdat.orchestrator import _resolve_target
from sdat.renderer.renderer import render_gaps, render_inventory, render_misconfigurations


class TestResolveTarget:
    def test_valid_path(self, tmp_path: Path):
        result = _resolve_target(str(tmp_path))
        assert result == tmp_path.resolve()

    def test_drive_root_rejected(self):
        with pytest.raises(PermissionError):
            _resolve_target("C:\\")

    def test_relative_path_resolved(self, tmp_path: Path):
        import os
        old = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = _resolve_target(".")
            assert result == tmp_path.resolve()
        finally:
            os.chdir(old)


class TestRenderer:
    def test_inventory_empty(self, tmp_path: Path):
        out = render_inventory([], str(tmp_path))
        assert "Inventory" in out
        assert "No implemented concepts" in out

    def test_gaps_empty(self, tmp_path: Path):
        out = render_gaps([], str(tmp_path))
        assert "Gaps" in out

    def test_misconfig_empty(self, tmp_path: Path):
        out = render_misconfigurations([], str(tmp_path))
        assert "Misconfigurations" in out

    def test_inventory_with_implemented(self, tmp_path: Path):
        decisions = [
            Decision(
                concept_id="foundation.caching",
                concept_name="caching",
                status=DecisionStatus.IMPLEMENTED,
                confidence=0.9,
                priority=Priority.INFO,
                evidence=[Evidence(file="app.py", line=1, snippet="import redis")],
            )
        ]
        out = render_inventory(decisions, str(tmp_path))
        assert "caching" in out
        assert "app.py" in out

    def test_gaps_with_missing(self, tmp_path: Path):
        decisions = [
            Decision(
                concept_id="foundation.circuit-breaker",
                concept_name="circuit-breaker",
                status=DecisionStatus.MISSING,
                confidence=0.8,
                priority=Priority.CRITICAL,
                gaps=["No circuit-breaker library found"],
                recommendation="Add pybreaker.",
            )
        ]
        out = render_gaps(decisions, str(tmp_path))
        assert "circuit-breaker" in out
        assert "Add pybreaker" in out

    def test_misconfig_with_issue(self, tmp_path: Path):
        decisions = [
            Decision(
                concept_id="foundation.retries",
                concept_name="retries",
                status=DecisionStatus.MISCONFIGURED,
                confidence=0.85,
                priority=Priority.HIGH,
                evidence=[Evidence(file="app.py", line=10, snippet="time.sleep(1)")],
                misconfiguration="Fixed delay without jitter",
                recommendation="Use exponential backoff.",
            )
        ]
        out = render_misconfigurations(decisions, str(tmp_path))
        assert "retries" in out
        assert "Fixed delay" in out
        assert "exponential backoff" in out
