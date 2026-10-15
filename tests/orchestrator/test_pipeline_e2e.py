"""End-to-end tests for SDAT pipeline, telemetry generation, and self-auditing dogfooding."""

from __future__ import annotations

import json
from pathlib import Path

from sdat.orchestrator import run_audit_pipeline


def test_pipeline_execution_on_fixture(tmp_path: Path):
    target = Path("tests/fixtures/go_project")
    out_dir = tmp_path / "audit_out"

    result = run_audit_pipeline(
        target_root=target,
        output_dir=out_dir,
        project_type="backend",
        max_workers=2,
        enable_cache=True,
    )

    assert result.target_root == str(target.resolve())
    assert result.total_decisions > 0
    assert result.inventory_path is not None
    assert Path(result.inventory_path).exists()
    assert result.telemetry_path is not None
    assert Path(result.telemetry_path).exists()

    # Verify telemetry JSON output
    telemetry_data = json.loads(Path(result.telemetry_path).read_text(encoding="utf-8"))
    assert telemetry_data["audit_duration_ms"] >= 0.0
    assert "evidence_counts" in telemetry_data
    assert "scanner_duration_ms" in telemetry_data

    # Verify telemetry section in inventory report
    inventory_content = Path(result.inventory_path).read_text(encoding="utf-8")
    assert "Internal Observability & Telemetry" in inventory_content
    assert "Audit Total Duration:" in inventory_content


def test_sdat_self_audit_dogfooding(tmp_path: Path):
    """SDAT must be capable of auditing its own repository without errors.

    Verifies dogfooding capability:
    - Scans Python core, tests, configs, fixtures
    - Computes evidence facts across multiple languages
    - Discovers frontend components/rules
    - Executes the Agent Swarm with bounded workers
    - Produces reports and telemetry
    """
    out_dir = tmp_path / "self_audit_out"

    result = run_audit_pipeline(
        target_root=".",
        output_dir=out_dir,
        project_type="backend",
        max_workers=4,
        enable_cache=True,
    )

    assert result.total_decisions > 0
    assert Path(result.inventory_path).exists()
    assert Path(result.gaps_path).exists()
    assert Path(result.misconfigurations_path).exists()
    assert Path(result.telemetry_path).exists()

    telemetry_data = json.loads(Path(result.telemetry_path).read_text(encoding="utf-8"))
    assert telemetry_data["evidence_counts"]["raw"] > 0
    assert len(telemetry_data["scanner_duration_ms"]) > 0
    assert telemetry_data["audit_duration_ms"] > 0.0


def test_telemetry_write_failure_safety(tmp_path: Path):
    """Telemetry write failure must not terminate or corrupt the overall audit pipeline."""
    target = Path("tests/fixtures/go_project")
    out_dir = tmp_path / "telemetry_fail_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Block telemetry.json by creating it as a directory to force an OSError on write
    blocked_path = out_dir / "telemetry.json"
    blocked_path.mkdir()

    result = run_audit_pipeline(
        target_root=target,
        output_dir=out_dir,
        project_type="backend",
        max_workers=2,
    )

    # Audit completes successfully despite telemetry file write failure
    assert result.total_decisions > 0
    assert result.inventory_path is not None
    assert Path(result.inventory_path).exists()
    assert result.telemetry_path is None

