"""Tests for D-21 FrontendAgent contract conformance."""

from __future__ import annotations

from pathlib import Path

from sdat.frontend.agent import FrontendAgent


def test_frontend_agent_contract(tmp_path: Path):
    # Setup sample project files
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "page.tsx").write_text("""export default function Home() {
    return <main className="sm:p-4 md:p-8"><h1>Home</h1></main>;
}
""", encoding="utf-8")

    agent = FrontendAgent()
    assert agent.agent_id == "D-21"
    assert agent.agent_name == "frontend_agent"

    project_context = {
        "target_root": str(tmp_path),
        "run_id": "test-run-001",
        "evidence_facts": [],
    }

    result = agent.audit(project_context)

    # Verify AGENTS.md §3 contract fields
    assert result["agent_id"] == "D-21"
    assert result["agent_name"] == "frontend_agent"
    assert result["run_id"] == "test-run-001"
    assert result["target_root"] == str(tmp_path)
    assert result["concepts_evaluated"] >= 14
    assert isinstance(result["decisions"], list)
    assert len(result["decisions"]) >= 14

    for decision in result["decisions"]:
        assert "concept_id" in decision
        assert "status" in decision
        assert "confidence" in decision
        assert "priority" in decision
        assert "evidence" in decision

    # Verify frontend_audit structure
    fa = result["frontend_audit"]
    assert "pages" in fa
    assert len(fa["pages"]) == 1
    assert "dimension_scores" in fa
    assert fa["overall_score"] is not None
    assert fa["overall_status"] == "evaluated"
