from __future__ import annotations

import json
from pathlib import Path

from sdat.ai.config import AIConfig
from sdat.ai.enrichment import enrich_findings
from sdat.ai.gateway import AIGateway
from sdat.ai.research import ResearchAgent
from sdat.config import load_config
from sdat.evidence.aggregator import EvidenceAggregator
from sdat.models import (
    Decision,
    DecisionStatus,
    EvidenceBundle,
    EvidenceFact,
    EvidenceKind,
    Priority,
)
from sdat.orchestrator import run_audit_pipeline
from sdat.swarm.agents.foundation import FoundationAgent
from sdat.swarm.merger import MergedOutput
from sdat.swarm.orchestrator import SwarmOrchestrator


def test_config_loads_agent_map_and_runtime_limits(tmp_path: Path):
    config_path = tmp_path / "sdat.yaml"
    config_path.write_text(
        """
scanners:
  enabled: [go]
  max_files_per_scan: 12
  file_size_limit_mb: 2
auditor:
  provider: ollama
  timeout_seconds: 19
  context_budget_tokens: 800
  max_output_tokens: 300
agents:
  max_concurrent_agents: 2
  foundation:
    enabled: [F-05]
  domain:
    enabled: [D-01]
agent_map: swarm.yaml
""",
        encoding="utf-8",
    )
    (tmp_path / "swarm.yaml").write_text(
        "foundation:\n  agents:\n    - id: F-05\n      concept_ids: [resilience.retries]\ndomain:\n  agents:\n    - id: D-01\n",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.scanners == ("go",)
    assert config.max_files_per_scan == 12
    assert config.max_workers == 2
    assert config.ai_provider == "ollama"
    assert config.agent_map["foundation"]["agents"][0]["concept_ids"] == ["resilience.retries"]


def test_pipeline_dispatch_and_scanners_follow_selected_config(tmp_path: Path, monkeypatch):
    agent_map = tmp_path / "agents.yaml"
    agent_map.write_text(
        """
foundation:
  agents:
    - id: F-01
      concept_ids: [foundation.caching]
domain:
  agents:
    - id: D-01
      category: backend
    - id: D-21
      category: frontend
""",
        encoding="utf-8",
    )
    config_path = tmp_path / "sdat.yaml"
    config_path.write_text(
        f"""
project_type: frontend
scanners:
  enabled: [go]
agents:
  foundation:
    enabled: [F-01]
  domain:
    enabled: [D-21]
agent_map: "{agent_map.as_posix()}"
""",
        encoding="utf-8",
    )
    config = load_config(config_path)
    seen: dict[str, object] = {}

    def capture(self, agents, project_context):
        seen["agent_ids"] = {agent.agent_id for agent in agents}
        seen["fact_languages"] = {fact.language for fact in project_context["evidence_facts"]}
        seen["bundles"] = project_context["bundles"]
        return MergedOutput(decisions=[], warnings=[])

    monkeypatch.setattr(SwarmOrchestrator, "run_swarm", capture)
    run_audit_pipeline(
        target_root=Path("tests/fixtures/go_project"),
        output_dir=tmp_path / "reports",
        project_type=config.project_type,
        config=config,
        enable_ai=False,
    )

    assert seen["agent_ids"] == {"F-01", "D-21"}
    assert seen["fact_languages"] == {"go"}
    assert isinstance(seen["bundles"], list)


def test_foundation_agent_consumes_synthesized_absence_bundle(tmp_path: Path):
    call = EvidenceFact(
        kind=EvidenceKind.CALL,
        subject="requests.post",
        language="python",
        file_path=tmp_path / "client.py",
        line_range=(8, 8),
        snippet="requests.post(url)",
        call_target="requests.post",
        timeout_observed=False,
    )
    bundle = next(
        item for item in EvidenceAggregator().aggregate([call])
        if item.concept_id == "resilience.retries"
    )
    fact = next(item for item in bundle.facts if item.kind == EvidenceKind.ABSENT_PATTERN)

    output = FoundationAgent(owned_concepts=["resilience.retries"]).run(
        {"target_root": str(tmp_path), "bundles": [bundle], "signals": []}
    )

    decision = next(item for item in output["decisions"] if item["concept_id"] == "resilience.retries")
    assert decision["status"] == "missing"
    assert decision["evidence"][0]["line"] == 8
    assert decision["evidence"][0]["snippet"] == fact.snippet


def test_enrichment_routes_through_gateway_and_obeys_prompt_budget(tmp_path: Path, monkeypatch):
    config = AIConfig(
        enabled=True,
        provider="openrouter",
        model="test-model",
        api_key="test-secret",
        context_budget_tokens=1_000,
        max_retries=0,
    )
    decision = Decision(
        concept_id="backend.idempotency",
        concept_name="Idempotency",
        status=DecisionStatus.MISSING,
        priority=Priority.HIGH,
        confidence=0.9,
        recommendation="Require an idempotency key.",
    )
    response = json.dumps({"executive_summary": "Bounded response.", "items": []})
    observed: dict[str, str] = {}

    def complete(self, prompt, system_prompt=None, fallback=""):
        observed["prompt"] = prompt
        observed["system"] = system_prompt or ""
        return response

    monkeypatch.setattr(AIGateway, "complete", complete)
    result = enrich_findings([decision], tmp_path, ai_config=config)

    assert result.available is True
    assert result.provider == "openrouter"
    assert result.model == "test-model"
    assert len(observed["prompt"]) + len(observed["system"]) <= config.context_budget_tokens * 4


def test_enrichment_gateway_failure_keeps_deterministic_output(tmp_path: Path, monkeypatch):
    config = AIConfig(enabled=True, provider="openrouter", api_key="test-secret", max_retries=0)
    decision = Decision(
        concept_id="backend.idempotency",
        concept_name="Idempotency",
        status=DecisionStatus.MISSING,
        priority=Priority.HIGH,
        confidence=0.9,
        recommendation="Require an idempotency key.",
    )

    def fail(self, prompt, system_prompt=None, fallback=""):
        return fallback

    monkeypatch.setattr(AIGateway, "complete", fail)
    result = enrich_findings([decision], tmp_path, ai_config=config)

    assert result.available is False
    assert len(result.remediations) == 1
    assert result.remediations[0].recommended_solution


def test_optional_research_contract_is_model_context_without_sources(tmp_path: Path, monkeypatch):
    config = AIConfig(enabled=True, provider="ollama", model="local-model")
    decision = Decision(
        concept_id="backend.idempotency",
        concept_name="Idempotency",
        status=DecisionStatus.MISSING,
        priority=Priority.HIGH,
        confidence=0.9,
        gaps=["No request key observed"],
    )
    observed: dict[str, str] = {}

    def complete(self, prompt, system_prompt=None, fallback=""):
        observed["prompt"] = prompt
        return json.dumps({"context": {"backend.idempotency": {"peer_patterns": ["deduplicate writes"]}}})

    monkeypatch.setattr(AIGateway, "complete", complete)
    report = ResearchAgent(config).research([decision], target_root=str(tmp_path))

    assert report["origin"] == "model_prior_knowledge"
    assert report["sources"] == []
    assert report["context"]["backend.idempotency"]["peer_patterns"] == ["deduplicate writes"]
    assert str(tmp_path) not in observed["prompt"]


def test_swarm_cache_key_includes_concept_bundle_contents(tmp_path: Path):
    orchestrator = SwarmOrchestrator()
    base_fact = EvidenceFact(
        kind=EvidenceKind.ABSENT_PATTERN,
        subject="retries",
        language="python",
        file_path=tmp_path / "client.py",
        line_range=(8, 8),
        snippet="No retry mechanism observed",
    )
    changed_fact = EvidenceFact(
        kind=EvidenceKind.ABSENT_PATTERN,
        subject="retries",
        language="python",
        file_path=tmp_path / "client.py",
        line_range=(8, 8),
        snippet="No retry strategy configured",
    )
    base = {"target_root": str(tmp_path), "bundles": [EvidenceBundle("resilience.retries", (base_fact,))]}
    changed = {"target_root": str(tmp_path), "bundles": [EvidenceBundle("resilience.retries", (changed_fact,))]}

    assert orchestrator._compute_task_cache_key("F-01", base) != orchestrator._compute_task_cache_key("F-01", changed)
