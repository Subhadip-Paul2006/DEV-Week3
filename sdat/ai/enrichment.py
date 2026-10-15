"""AI Enrichment & Remediation Engine.

Combines deterministic findings with open-weight model reasoning (primary: Qwen3-Coder 480B A35B
via OpenRouter, with secondary Gemma support) to produce:
1. Executive Architectural Summary
2. In-depth Remediation Plans with concrete implementation steps and validation criteria
3. Architectural Impact & Cascading Failure Mode Analysis
4. Before & After Architecture Diagrams

Conforms to AGENTS.md §11 Invariants:
- Deterministic findings are authoritative (evidence, status, line citations).
- AI reasons ABOUT findings without inventing or hallucinating code files.
- Resilient fallback when AI is disabled or unconfigured (--no-ai).
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, List, Optional

from sdat.ai.config import AIConfig
from sdat.ai.gateway import AIEnrichmentResult, AIGateway, RemediationItem
from sdat.concepts import CONCEPTS_BY_ID, Priority
from sdat.models import Decision, DecisionStatus

logger = logging.getLogger("sdat.ai.enrichment")

CACHE_FILE_NAMES = [
    "cached_qwen_enrichment.json",
    "cached_ai_enrichment.json",
    "cached_gemma_enrichment.json",
]
CACHE_FILE_NAME = "cached_qwen_enrichment.json"


def _extract_top_findings(decisions: List[Decision], limit: int = 5) -> List[Decision]:
    """Select the most critical architectural issues (missing or misconfigured)."""
    priority_weights = {
        Priority.CRITICAL: 0,
        Priority.HIGH: 1,
        Priority.MEDIUM: 2,
        Priority.LOW: 3,
        Priority.INFO: 4,
        Priority.N_A: 5,
    }

    issues = [
        d for d in decisions
        if d.status in (DecisionStatus.MISSING, DecisionStatus.MISCONFIGURED)
    ]
    issues.sort(key=lambda d: (priority_weights.get(d.priority, 99), d.concept_name))
    return issues[:limit]


def _build_deterministic_remediation(decision: Decision) -> RemediationItem:
    """Generate high-fidelity deterministic remediation when AI is unavailable."""
    concept = CONCEPTS_BY_ID.get(decision.concept_id)
    name = decision.concept_name.replace("-", " ").title()
    status_label = decision.status.value.upper()

    evidence_dicts = [
        {
            "file": ev.file,
            "line": ev.line,
            "snippet": ev.snippet,
            "note": ev.note,
        }
        for ev in decision.evidence
    ]

    why_it_matters_map = {
        "foundation.rate-limiting": (
            "Without rate limiting, public API endpoints are vulnerable to denial-of-service, "
            "credential stuffing, and runaway resource consumption from unbounded clients."
        ),
        "resilience.dead-letter": (
            "Without a dead-letter queue or fallback storage, transient consumer errors cause poison pills "
            "or permanently lost asynchronous tasks."
        ),
        "performance.cdn": (
            "Serving static assets directly from application instances wastes compute cycles and increases "
            "p99 response latency for globally distributed users."
        ),
        "security.cors": (
            "Permissive wildcard CORS headers allow unauthorized cross-origin web applications to interact "
            "with authenticated API endpoints using user session credentials."
        ),
        "foundation.error-handling": (
            "Bare except handlers catch system exit signals and silently suppress critical debugging context, "
            "leaving the application in an indeterminate state."
        ),
        "backend.idempotency": (
            "Mutating operations without idempotency controls risk duplicate executions, phantom records, "
            "and transactional corruption when clients retry over unstable connections."
        ),
    }

    impact_map = {
        "foundation.rate-limiting": (
            "High vulnerability to noisy-neighbor effects, memory starvation under traffic spikes, "
            "and database connection pool exhaustion."
        ),
        "resilience.dead-letter": (
            "Unrecoverable data loss during message processing errors and silent job queue blockage."
        ),
        "performance.cdn": (
            "High origin server egress costs, elevated backend CPU utilization, and sub-optimal Core Web Vitals."
        ),
        "security.cors": (
            "Potential cross-site request forgery and token exfiltration by malicious browser origins."
        ),
        "foundation.error-handling": (
            "Silent failures during unexpected edge cases, corrupting transactional state."
        ),
        "backend.idempotency": (
            "Duplicate orders, multiple billing transactions, and race conditions between concurrent mutations."
        ),
    }

    steps_map = {
        "foundation.rate-limiting": [
            "1. Install slowapi (FastAPI) or flask-limiter: `pip install slowapi`",
            "2. Initialize Limiter backed by existing Redis cache: `limiter = Limiter(key_func=get_remote_address, storage_uri='redis://localhost:6379')`",
            "3. Apply `@limiter.limit('60/minute')` decorator to sensitive and public endpoints",
            "4. Return HTTP 429 Too Many Requests with standard Retry-After headers",
        ],
        "resilience.dead-letter": [
            "1. Configure a dedicated dead-letter exchange/queue (e.g. `dlq_tasks`) with retention policy",
            "2. Set max delivery retry count (e.g. 3 attempts) before forwarding unroutable messages to DLQ",
            "3. Implement an alert trigger when DLQ depth exceeds 0",
            "4. Provide a replay script or worker to inspect and re-process failed payloads",
        ],
        "performance.cdn": [
            "1. Offload static asset directories (images, styles, compiled JS) to Cloud Storage or S3",
            "2. Place Cloudflare, AWS CloudFront, or Fastly in front of static origins",
            "3. Configure Cache-Control headers: `public, max-age=31536000, immutable` for hashed assets",
            "4. Verify cache hit ratio using telemetry or CDN metrics dashboard",
        ],
        "backend.idempotency": [
            "1. Create an Idempotency middleware or header dependency inspecting 'Idempotency-Key'",
            "2. Atomically check and lock the key in Redis with a TTL (e.g. SET key IN_PROGRESS NX EX 120)",
            "3. Return previously cached response if the key has already been resolved",
            "4. Cache response status and body in Redis upon successful completion with a 24-hour expiration",
        ],
    }

    diagram_before_map = {
        "foundation.rate-limiting": "Client (Unchecked Request Storm) ──► FastAPI Service ──► DB Exhaustion",
        "resilience.dead-letter": "Producer ──► Queue ──► Consumer (Failure) ──► [Silent Message Loss]",
        "performance.cdn": "User Browser ──► [Direct Network Request] ──► FastAPI Backend (Static Asset Overhead)",
        "backend.idempotency": "Client ──► [POST /items (Network Retry)] ──► Handler ──► [Duplicate Database Record]",
    }

    diagram_after_map = {
        "foundation.rate-limiting": "Client ──► SlowAPI Limiter (Redis Token Bucket) ──► [200 OK or 429 Throttle] ──► Backend",
        "resilience.dead-letter": "Producer ──► Queue ──► Consumer (3 Retries) ──► DLQ (Storage + Alerting)",
        "performance.cdn": "User Browser ──► CDN Edge Cache (99% Hit Rate) ──► [Cache Miss Only] ──► Origin Storage",
        "backend.idempotency": "Client (Idempotency-Key) ──► Redis Gatekeeper (SETNX) ──► [At-Most-Once DB Write + Cached Return]",
    }

    validation_map = {
        "foundation.rate-limiting": (
            "Execute automated locust or vegeta load test with 100 req/sec from a single IP. "
            "Verify requests exceeding limit return HTTP 429 with Retry-After header within 100ms."
        ),
        "resilience.dead-letter": (
            "Inject a synthetic ValueError in the consumer. Verify that after 3 failed attempts, "
            "the message appears in the dead-letter queue and an alert is recorded."
        ),
        "performance.cdn": (
            "Run curl -I https://cdn.example.com/asset.js and verify `cf-cache-status: HIT` or `x-cache: Hit from cloudfront`."
        ),
        "backend.idempotency": (
            "Execute concurrent requests using pytest-asyncio and httpx with the same Idempotency-Key. "
            "Verify only 1 database insert occurs and both receive identical 201 responses."
        ),
    }

    rec = decision.recommendation or (concept.description if concept else "Implement standard pattern.")
    why = why_it_matters_map.get(decision.concept_id, concept.question if concept else f"Ensure {name} meets standard reliability.")
    impact = impact_map.get(decision.concept_id, f"Unmitigated risks in {name} may cause system instability or downtime.")
    steps = steps_map.get(decision.concept_id, [f"1. Review system requirements for {name}", "2. Adopt canonical libraries and configuration", f"3. Add integration test covering {name} behavior"])
    validation = validation_map.get(decision.concept_id, f"Run automated tests verifying {name} operates under stress conditions.")
    reasoning_text = (
        f"Deterministic rule engine identified {decision.concept_id} as {status_label}. "
        f"{'Gaps observed: ' + ', '.join(decision.gaps) if decision.gaps else ''}"
    )

    return RemediationItem(
        concept_id=decision.concept_id,
        concept_name=decision.concept_name,
        severity=decision.priority.value,
        status=decision.status.value,
        confidence=decision.confidence,
        finding=f"{name} is currently {status_label.lower()}.",
        evidence=evidence_dicts,
        why_it_matters=why,
        architectural_impact=impact,
        ai_reasoning=reasoning_text,
        gemma_reasoning=reasoning_text,
        recommended_solution=rec,
        implementation_steps=steps,
        validation=validation,
        diagram_before=diagram_before_map.get(decision.concept_id),
        diagram_after=diagram_after_map.get(decision.concept_id),
    )


def enrich_findings(
    decisions: List[Decision],
    target_root: str | Path,
    enable_ai: bool = True,
    model_override: Optional[str] = None,
    output_dir: Optional[Path] = None,
    provider_override: Optional[str] = None,
    ai_config: AIConfig | None = None,
    research_report: dict[str, Any] | None = None,
) -> AIEnrichmentResult:
    """Run AI reasoning pass over deterministic findings with fallback and caching."""
    start_time = time.time()
    target_path = Path(target_root).resolve()
    target_name = target_path.name

    top_issues = _extract_top_findings(decisions, limit=5)
    implemented = [d for d in decisions if d.status == DecisionStatus.IMPLEMENTED]

    # If AI explicitly disabled
    if not enable_ai:
        remediations = [_build_deterministic_remediation(d) for d in top_issues]
        exec_summary = (
            f"Deterministic audit completed for {target_name}. Found {len(implemented)} implemented "
            f"architectural patterns and {len(top_issues)} high-priority risks requiring remediation. "
            f"(AI reasoning was disabled via --no-ai)."
        )
        return AIEnrichmentResult(
            available=False,
            provider="deterministic",
            model="none",
            executive_summary=exec_summary,
            remediations=remediations,
            is_cached=False,
            duration_seconds=time.time() - start_time,
        )

    # Resolve AI config
    env_dict = dict(os.environ)
    if model_override:
        env_dict["AI_MODEL"] = model_override
    if provider_override:
        env_dict["SDAT_AI_PROVIDER"] = provider_override

    config = ai_config or AIConfig.from_env(env_dict)
    gateway = AIGateway(config=config)
    provider_name = config.provider
    model_name = config.model or "none"

    # If adapter is not configured, check offline cache artifacts
    if not config.is_available or not gateway._provider.is_configured():
        candidate_dirs = [target_path / "docs" / "audit"]
        if output_dir:
            requested_cache_dir = Path(output_dir).resolve()
            if requested_cache_dir == target_path or target_path in requested_cache_dir.parents:
                candidate_dirs.insert(0, requested_cache_dir)
        for cdir in candidate_dirs:
            if not cdir:
                continue
            for cname in CACHE_FILE_NAMES:
                cpath = cdir / cname
                if cpath.exists():
                    try:
                        cached_data = json.loads(cpath.read_text(encoding="utf-8"))
                        remediations = [
                            RemediationItem(**item) for item in cached_data.get("remediations", [])
                        ]
                        return AIEnrichmentResult(
                            available=True,
                            provider=cached_data.get("provider", provider_name),
                            model=cached_data.get("model", model_name),
                            executive_summary=cached_data.get("executive_summary", ""),
                            remediations=remediations,
                            is_cached=True,
                            duration_seconds=time.time() - start_time,
                        )
                    except Exception as exc:
                        logger.warning("Failed to load cached AI output from %s: %s", cpath, exc)

        # Fallback to deterministic recommendations
        remediations = [_build_deterministic_remediation(d) for d in top_issues]
        exec_summary = (
            f"Deterministic audit completed for {target_name}. Found {len(implemented)} implemented "
            f"architectural patterns and {len(top_issues)} high-priority risks. "
            f"AI Reasoning was unavailable (OPENROUTER_API_KEY not configured). "
            f"Remediation generated from verified rule definitions."
        )
        return AIEnrichmentResult(
            available=False,
            provider="deterministic_fallback",
            model=model_name,
            executive_summary=exec_summary,
            remediations=remediations,
            is_cached=False,
            error=f"AI provider '{config.provider}' is disabled, unsupported, or missing credentials",
            duration_seconds=time.time() - start_time,
        )

    # Prepare structured prompt for Qwen3-Coder / AI model
    model_display = model_name
    system_instruction = (
        f"You are {model_display}, an expert system-design and cloud architecture auditor. "
        "You receive structured, verified repository facts from deterministic scanners. "
        "Your role is to reason ABOUT the existing evidence, explain root causes, describe cascading "
        "architectural failure modes, and provide concrete, actionable remediation steps. "
        "DO NOT invent source files or claim patterns exist without evidence. "
        "Return your analysis in valid JSON conforming to the requested schema."
    )

    findings_payload = []
    for d in top_issues:
        findings_payload.append({
            "concept_id": d.concept_id,
            "concept_name": d.concept_name,
            "status": d.status.value,
            "severity": d.priority.value,
            "confidence": d.confidence,
            "gaps": list(d.gaps),
            "recommendation": d.recommendation,
            "evidence": [
                {"file": e.file, "line": e.line, "snippet": e.snippet}
                for e in d.evidence[:3]
            ],
        })

    safe_research_context = {}
    if research_report and research_report.get("origin") == "model_prior_knowledge":
        context = research_report.get("context", {})
        if isinstance(context, dict):
            safe_research_context = {str(key): value for key, value in list(context.items())[:3]}

    static_prompt = f"""
Project Name: {target_name}
Target Path: {target_path}
Total Implemented Architectural Concepts: {len(implemented)}
Key Implemented Patterns: {', '.join([d.concept_name for d in implemented[:8]])}
Model-prior context (unverified; not repository evidence; no live research sources):
{json.dumps(safe_research_context, separators=(',', ':'))}

Please analyze these architectural findings and return a JSON object with this exact structure:
{{
  "executive_summary": "2-3 sentences summarizing the architectural posture, major strengths, and top vulnerabilities.",
  "items": [
    {{
      "concept_id": "concept_id_from_input",
      "why_it_matters": "Why this is critical for reliability/performance/security in this specific architecture.",
      "architectural_impact": "What failure modes, bottlenecks, or cascading outages occur if left unaddressed.",
      "ai_reasoning": "Your architectural inference synthesizing the evidence and project context.",
      "recommended_solution": "Direct architectural design change to implement.",
      "implementation_steps": [
        "Step 1: Concrete package/library to install or file to create",
        "Step 2: Configuration or code changes",
        "Step 3: Integration details"
      ],
      "validation": "How the engineer can verify the fix (curl, load test, or unit test)",
      "diagram_before": "Before architecture flow (e.g. Client -> Service -> Failure)",
      "diagram_after": "After architecture flow with solution pattern inserted"
    }}
  ]
}}
"""

    context_chars = max(0, config.context_budget_tokens * 4 - len(system_instruction) - len(static_prompt) - 64)
    bounded_findings: list[dict[str, Any]] = []
    for finding in findings_payload:
        candidate = bounded_findings + [finding]
        if len(json.dumps(candidate, separators=(",", ":"))) > context_chars:
            break
        bounded_findings = candidate
    prompt = (
        f"Top Architectural Gaps / Misconfigurations:\n"
        f"{json.dumps(bounded_findings, separators=(',', ':'))}\n\n{static_prompt}"
    )

    try:
        if len(system_instruction) + len(prompt) > config.context_budget_tokens * 4:
            raise RuntimeError("Configured AI context budget is too small for the required prompt")
        raw_response = gateway.complete(prompt=prompt, system_prompt=system_instruction, fallback="")
        if not raw_response:
            raise RuntimeError("AI Gateway returned no response; deterministic fallback used")

        # Parse JSON from response
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        exec_summary = parsed.get("executive_summary", "")
        item_map = {it["concept_id"]: it for it in parsed.get("items", []) if "concept_id" in it}

        remediations: List[RemediationItem] = []
        for d in top_issues:
            ai_data = item_map.get(d.concept_id)
            if ai_data:
                reasoning = ai_data.get("ai_reasoning") or ai_data.get("gemma_reasoning") or f"Inferred by {model_name}."
                remediations.append(
                    RemediationItem(
                        concept_id=d.concept_id,
                        concept_name=d.concept_name,
                        severity=d.priority.value,
                        status=d.status.value,
                        confidence=d.confidence,
                        finding=f"{d.concept_name.replace('-', ' ').title()} is {d.status.value}.",
                        evidence=[{"file": e.file, "line": e.line, "snippet": e.snippet, "note": e.note} for e in d.evidence],
                        why_it_matters=ai_data.get("why_it_matters", d.recommendation or ""),
                        architectural_impact=ai_data.get("architectural_impact", "System reliability risk."),
                        ai_reasoning=reasoning,
                        gemma_reasoning=reasoning,
                        recommended_solution=ai_data.get("recommended_solution", d.recommendation or ""),
                        implementation_steps=ai_data.get("implementation_steps", [d.recommendation or "Implement pattern"]),
                        validation=ai_data.get("validation", "Verify via test suite."),
                        diagram_before=ai_data.get("diagram_before"),
                        diagram_after=ai_data.get("diagram_after"),
                    )
                )
            else:
                remediations.append(_build_deterministic_remediation(d))

        res = AIEnrichmentResult(
            available=True,
            provider=provider_name,
            model=model_name,
            executive_summary=exec_summary,
            remediations=remediations,
            is_cached=False,
            duration_seconds=time.time() - start_time,
        )

        # Cache successful live output for demo safety and offline reliability
        try:
            target_cache_dir = output_dir or (target_path / "docs" / "audit")
            target_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = target_cache_dir / CACHE_FILE_NAME
            cache_file.write_text(json.dumps(res.to_dict(), indent=2), encoding="utf-8")
        except Exception:
            pass

        return res

    except Exception as exc:
        logger.warning("AI invocation failed (%s); falling back to deterministic recommendations", model_name)
        remediations = [_build_deterministic_remediation(d) for d in top_issues]
        exec_summary = (
            f"Deterministic audit completed for {target_name}. Found {len(implemented)} implemented "
            f"architectural patterns and {len(top_issues)} high-priority risks. "
            f"AI inference failed ({exc}). Continuing with deterministic recommendations."
        )
        return AIEnrichmentResult(
            available=False,
            provider="deterministic_fallback",
            model=model_name,
            executive_summary=exec_summary,
            remediations=remediations,
            is_cached=False,
            error=str(exc),
            duration_seconds=time.time() - start_time,
        )


# Backward-compatible alias
enrich_with_gemma = enrich_findings


def render_remediation_markdown(
    enrichment: AIEnrichmentResult,
    decisions: List[Decision],
    target_root: str,
) -> str:
    """Render 04-remediation.md report."""
    target_name = Path(target_root).name
    provider_title = enrichment.provider.replace("_", " ").title()
    provider_badge = (
        f"**AI Reasoning Engine:** `{enrichment.model}` ({'Live Inference via ' + provider_title if not enrichment.is_cached else 'Offline Cached Artifact'})"
        if enrichment.available
        else f"**AI Reasoning Engine:** Disabled / Unavailable ({enrichment.error or 'Deterministic Mode'})"
    )

    lines = [
        "# 04 — Architectural Remediation Guide",
        "",
        "> **तन्त्रविन्यास-निरीक्षा (निरीक्षा)** — System Design Audit Tool",
        f"> *Target:* `{target_name}` | *Path:* `{target_root}`",
        f"> {provider_badge}",
        "",
        "---",
        "",
        "## Executive Architectural Summary",
        "",
        enrichment.executive_summary or "Audit completed. See below for prioritized remediation plans.",
        "",
        "---",
        "",
        "## Prioritized Architectural Action Plans",
        "",
    ]

    for idx, item in enumerate(enrichment.remediations, start=1):
        lines.append(f"### {idx}. [{item.severity.upper()}] {item.concept_name.replace('-', ' ').title()}")
        lines.append("")
        lines.append(f"**Concept ID:** `{item.concept_id}` | **Status:** `{item.status}` | **Confidence:** `{item.confidence:.2f}`")
        lines.append("")
        lines.append("#### Finding")
        lines.append(item.finding)
        lines.append("")
        lines.append("#### Evidence")
        if item.evidence:
            for ev in item.evidence:
                loc = f"`{ev.get('file', '')}:{ev.get('line', '')}`" if ev.get("file") else "Repository scan"
                snip = ev.get("snippet", "").strip()
                lines.append(f"- Location: {loc}")
                if snip:
                    lines.append(f"  ```text\n  {snip}\n  ```")
        else:
            lines.append("- *(No implementation evidence found in scanned source files)*")
        lines.append("")
        lines.append("#### Why It Matters")
        lines.append(item.why_it_matters)
        lines.append("")
        lines.append("#### Architectural Impact")
        lines.append(item.architectural_impact)
        lines.append("")
        reasoning_text = item.ai_reasoning or item.gemma_reasoning
        lines.append(f"#### Architectural Reasoning ({enrichment.model})")
        lines.append(f"> {reasoning_text}")
        lines.append("")
        lines.append("#### Recommended Solution")
        lines.append(item.recommended_solution)
        lines.append("")
        if item.diagram_before and item.diagram_after:
            lines.append("#### Architectural Transformation")
            lines.append("```text")
            lines.append(f"BEFORE: {item.diagram_before}")
            lines.append(f"AFTER:  {item.diagram_after}")
            lines.append("```")
            lines.append("")
        lines.append("#### Concrete Implementation Steps")
        for step in item.implementation_steps:
            lines.append(f"- {step}")
        lines.append("")
        lines.append("#### Validation Criteria")
        lines.append(item.validation)
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("")
    lines.append("### Note on Verification")
    lines.append("SDAT remediation guidance is generated to assist architectural evolution. All recommended steps ")
    lines.append("should be tested in staging environments before production deployment.")
    lines.append("")
    lines.append("*Developed by shubh06 — तन्त्रविन्यास-निरीक्षा*")

    return "\n".join(lines)
