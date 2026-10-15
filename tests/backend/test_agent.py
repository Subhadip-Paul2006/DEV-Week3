"""Tests for BackendAgent (D-01) and AGENTS.md contract conformance."""

from __future__ import annotations

from pathlib import Path

from sdat.backend.agent import BackendAgent
from sdat.models import EvidenceFact, EvidenceKind


def test_backend_agent_metadata() -> None:
    agent = BackendAgent()
    assert agent.agent_id == "D-01"
    assert agent.agent_name == "backend_agent"
    assert agent.domain == "backend"
    assert agent.knowledge_pack_id == "kp.backend"


def test_backend_agent_audit_contract() -> None:
    agent = BackendAgent()
    fact = EvidenceFact(
        kind=EvidenceKind.DECORATOR,
        subject="app.get",
        language="python",
        file_path=Path("main.py"),
        line_range=(10, 10),
        snippet="@app.get('/users')",
        framework="fastapi",
    )
    project_context = {
        "target_root": "isolated_test_root",
        "run_id": "test-run-123",
        "evidence_facts": [fact],
    }
    result = agent.audit(project_context)

    # Validate output schema against AGENTS.md §3
    assert result["agent_id"] == "D-01"
    assert result["agent_name"] == "backend_agent"
    assert result["run_id"] == "test-run-123"
    assert result["concepts_evaluated"] == 25
    assert "decisions" in result
    assert "backend_audit" in result

    decisions = result["decisions"]
    assert len(decisions) == 25
    for d in decisions:
        assert "concept_id" in d
        assert "concept_name" in d
        assert "status" in d
        assert "confidence" in d
        assert "evidence" in d
        assert "misconfiguration" in d
        assert "gaps" in d
        assert "recommendation" in d
        assert "priority" in d

    # BE-API-01 should be implemented due to route decorator
    api_dec = next(d for d in decisions if d["concept_id"] == "backend.api-architecture")
    assert api_dec["status"] == "implemented"
    assert len(api_dec["evidence"]) > 0
    assert api_dec["evidence"][0]["snippet"] == "@app.get('/users')"


def test_backend_agent_run_protocol_alias() -> None:
    agent = BackendAgent()
    project_context = {"target_root": "."}
    res_run = agent.run(project_context)
    assert res_run["agent_id"] == "D-01"
    assert res_run["concepts_evaluated"] == 25
