"""Comprehensive unit and integration tests for SDAT AI Layer.

Tests:
1. Provider-agnostic AIConfig resolution (OpenRouter as primary, AI_MODEL override, disabled defaults)
2. OpenRouter Adapter implementation (payload creation, authorization, choice parsing, error resilience)
3. AIGateway fail-open resilience and routing
4. AI Enrichment Engine (deterministic mode, offline caching, live inference handling)
5. Markdown report rendering with all required architectural cards
"""

from __future__ import annotations

import io
import json
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sdat.ai.adapters.openrouter import OpenRouterAdapter
from sdat.ai.config import AIConfig
from sdat.ai.enrichment import (
    enrich_findings,
    render_remediation_markdown,
)
from sdat.ai.gateway import AIEnrichmentResult, AIGateway, OpenRouterProvider, RemediationItem
from sdat.concepts import Priority
from sdat.models import Decision, DecisionStatus


def test_ai_config_openrouter_defaults():
    """Verify OpenRouter is auto-selected when OPENROUTER_API_KEY is present."""
    env = {
        "OPENROUTER_API_KEY": "sk-or-v1-testkey12345",
    }
    config = AIConfig.from_env(env)
    assert config.enabled is True
    assert config.provider == "openrouter"
    assert config.model == "qwen/qwen3-coder:free"
    assert config.api_key == "sk-or-v1-testkey12345"
    assert config.base_url == "https://openrouter.ai/api/v1"
    assert config.is_available is True


def test_ai_config_ai_model_override():
    """Verify AI_MODEL environment variable overrides default model ID."""
    env = {
        "OPENROUTER_API_KEY": "sk-or-v1-testkey12345",
        "AI_MODEL": "qwen/qwen3-coder:free",
    }
    config = AIConfig.from_env(env)
    assert config.model == "qwen/qwen3-coder:free"

    env_custom = {
        "OPENROUTER_API_KEY": "sk-or-v1-testkey12345",
        "AI_MODEL": "custom/coding-model-v2",
    }
    config_custom = AIConfig.from_env(env_custom)
    assert config_custom.model == "custom/coding-model-v2"


def test_ai_config_deterministic_default_when_no_keys():
    """Verify safe disabled state when no AI environment variables are provided."""
    config = AIConfig.from_env({})
    assert config.enabled is False
    assert config.provider == "none"
    assert config.is_available is False


def test_openrouter_adapter_mocked_completion():
    """Verify OpenRouterAdapter correctly constructs requests and extracts completion."""
    adapter = OpenRouterAdapter(
        model="qwen/qwen3-coder:free",
        api_key="sk-or-test-key",
    )
    assert adapter.is_configured() is True

    fake_response_data = {
        "id": "gen-12345",
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"executive_summary": "Solid architecture.", "items": []}',
                }
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(fake_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = adapter.complete(prompt="Analyze this system.", system_prompt="You are an auditor.")

        assert '{"executive_summary": "Solid architecture.", "items": []}' in result
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://openrouter.ai/api/v1/chat/completions"
        assert req.get_header("Authorization") == "Bearer sk-or-test-key"
        assert req.get_header("Content-type") == "application/json"

        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "qwen/qwen3-coder:free"
        assert len(body["messages"]) == 2
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"


def test_openrouter_adapter_error_resilience():
    """Verify OpenRouterAdapter wraps HTTP errors in informative RuntimeErrors."""
    adapter = OpenRouterAdapter(
        model="qwen/qwen3-coder:free",
        api_key="sk-or-invalid",
    )

    http_error = urllib.error.HTTPError(
        url="https://openrouter.ai/api/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b'{"error": "Invalid API Key"}'),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(RuntimeError) as exc_info:
            adapter.complete("Test prompt")
        assert "HTTP 401" in str(exc_info.value)


def test_ai_gateway_routing_and_fail_open():
    """Verify AIGateway routes to OpenRouter and fails open gracefully on error."""
    config = AIConfig(
        enabled=True,
        provider="openrouter",
        model="qwen/qwen3-coder:free",
        api_key="test-key",
        max_retries=0,
    )
    gateway = AIGateway(config=config)
    assert isinstance(gateway._provider, OpenRouterProvider)

    # When provider raises an error, gateway must fail open and return fallback
    with patch.object(gateway._provider, "complete", side_effect=RuntimeError("Connection refused")):
        fallback_msg = "Deterministic fallback content"
        res = gateway.complete("Test prompt", fallback=fallback_msg)
        assert res == fallback_msg


def test_enrich_findings_deterministic_mode(tmp_path: Path):
    """When enable_ai is False (--no-ai), deterministic remediation is returned immediately."""
    decisions = [
        Decision(
            concept_id="backend.idempotency",
            concept_name="Idempotency for Mutating Operations",
            status=DecisionStatus.MISSING,
            priority=Priority.HIGH,
            confidence=0.85,
            evidence=[],
            gaps=["No idempotency keys or deduplication observed"],
            recommendation="Require an Idempotency-Key header on mutating endpoints",
        )
    ]

    res = enrich_findings(
        decisions=decisions,
        target_root=tmp_path,
        enable_ai=False,
    )

    assert res.available is False
    assert res.provider == "deterministic"
    assert len(res.remediations) == 1
    assert "Idempotency" in res.remediations[0].concept_name
    assert res.remediations[0].ai_reasoning != ""
    assert res.remediations[0].recommended_solution != ""


def test_enrich_findings_cached_artifact_resolution(tmp_path: Path):
    """When API keys are absent, offline cached artifacts are loaded for demo safety."""
    cache_dir = tmp_path / "docs" / "audit"
    cache_dir.mkdir(parents=True)
    cache_file = cache_dir / "cached_qwen_enrichment.json"

    cached_content = {
        "available": True,
        "provider": "openrouter",
        "model": "qwen/qwen3-coder:free",
        "executive_summary": "Cached Qwen3-Coder analysis.",
        "remediations": [
            {
                "concept_id": "backend.idempotency",
                "concept_name": "Idempotency for Mutating Operations",
                "severity": "high",
                "status": "missing",
                "confidence": 0.92,
                "finding": "Missing request deduplication",
                "evidence": [],
                "why_it_matters": "Prevents phantom writes.",
                "architectural_impact": "Double charges under retries.",
                "ai_reasoning": "Qwen3-Coder verified absence of idempotency tokens.",
                "gemma_reasoning": "Qwen3-Coder verified absence of idempotency tokens.",
                "recommended_solution": "Use Redis SETNX.",
                "implementation_steps": ["Step 1", "Step 2"],
                "validation": "Send 2 concurrent requests with same key.",
                "diagram_before": "Client -> API -> Duplicate",
                "diagram_after": "Client -> Gatekeeper -> Unique",
            }
        ],
    }
    cache_file.write_text(json.dumps(cached_content), encoding="utf-8")

    decisions = [
        Decision(
            concept_id="backend.idempotency",
            concept_name="Idempotency for Mutating Operations",
            status=DecisionStatus.MISSING,
            priority=Priority.HIGH,
            confidence=0.85,
        )
    ]

    with patch.dict("os.environ", {}, clear=True):
        res = enrich_findings(
            decisions=decisions,
            target_root=tmp_path,
            enable_ai=True,
            output_dir=cache_dir,
        )

    assert res.available is True
    assert res.is_cached is True
    assert res.model == "qwen/qwen3-coder:free"
    assert "Cached Qwen3-Coder analysis" in res.executive_summary
    assert res.remediations[0].ai_reasoning == "Qwen3-Coder verified absence of idempotency tokens."


def test_render_remediation_markdown():
    """Verify 04-remediation.md markdown generator produces all required sections."""
    item = RemediationItem(
        concept_id="backend.idempotency",
        concept_name="Idempotency for Mutating Operations",
        severity="high",
        status="missing",
        confidence=0.92,
        finding="State-mutating endpoints lack idempotency key deduplication.",
        evidence=[{"file": "app/main.py", "line": 42, "snippet": "@app.post('/items')"}],
        why_it_matters="Network blips cause duplicate transactions.",
        architectural_impact="Race conditions and phantom writes.",
        ai_reasoning="Qwen3-Coder observed lack of Idempotency-Key validation.",
        recommended_solution="Introduce an IdempotencyMiddleware utilizing Redis SETNX.",
        implementation_steps=[
            "1. Intercept POST requests for Idempotency-Key",
            "2. Acquire Redis lock with TTL",
        ],
        validation="Run pytest sending two identical requests.",
        diagram_before="Client -> Handler -> Duplicate DB Record",
        diagram_after="Client -> Redis Gatekeeper -> At-Most-Once DB Write",
    )

    enrichment = AIEnrichmentResult(
        available=True,
        provider="openrouter",
        model="qwen/qwen3-coder:free",
        executive_summary="Solid baseline with high-priority gap in idempotency.",
        remediations=[item],
        is_cached=False,
    )

    md = render_remediation_markdown(enrichment, [], target_root="test_project")

    assert "# 04 — Architectural Remediation Guide" in md
    assert "qwen/qwen3-coder:free" in md
    assert "Live Inference via Openrouter" in md
    assert "Solid baseline with high-priority gap in idempotency." in md
    assert "### 1. [HIGH] Idempotency For Mutating Operations" in md
    assert "app/main.py:42" in md
    assert "Why It Matters" in md
    assert "Architectural Impact" in md
    assert "Architectural Reasoning (qwen/qwen3-coder:free)" in md
    assert "Qwen3-Coder observed lack of Idempotency-Key validation." in md
    assert "Recommended Solution" in md
    assert "BEFORE: Client -> Handler -> Duplicate DB Record" in md
    assert "AFTER:  Client -> Redis Gatekeeper -> At-Most-Once DB Write" in md
    assert "Validation Criteria" in md
