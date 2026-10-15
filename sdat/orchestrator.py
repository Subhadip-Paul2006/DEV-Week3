"""SDAT Orchestrator — wires together discovery, multi-language scanning, evidence aggregation, swarm agents, and reporting.

Production-Grade System Design:
1. Multi-language scanning with registry discovery, caching, and per-scanner timers.
2. Content-hashed caching to avoid redundant file scans and guarantee idempotency.
3. Common Evidence Model (EvidenceFact $\\rightarrow$ EvidenceAggregator $\\rightarrow$ EvidenceBundle).
4. Resilient Swarm Orchestrator with bounded concurrency, per-agent timeouts, failure isolation, and retries.
5. Structured telemetry capturing duration, memory, evidence counts, active/failed agents, and cache performance.
6. Deterministic result merging and report generation.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Set

from sdat.ai.enrichment import enrich_findings, render_remediation_markdown
from sdat.ai.gateway import AIEnrichmentResult
from sdat.ai.research import ResearchAgent
from sdat.backend.agent import BackendAgent
from sdat.cache.store import ContentCache
from sdat.config import SDATConfig, load_config
from sdat.evidence.aggregator import EvidenceAggregator
from sdat.frontend.agent import FrontendAgent
from sdat.knowledge import build_canonical_registry
from sdat.ml.knowledge_pack import MLKnowledgePack
from sdat.models import Decision, DecisionStatus, EvidenceFact, EvidenceKind, SignalBridge
from sdat.nlp.knowledge_pack import NLPKnowledgePack
from sdat.renderer.renderer import (
    render_gaps,
    render_inventory,
    render_misconfigurations,
)
from sdat.scanners.registry import REGISTRY
from sdat.swarm.agents.foundation import FoundationAgent
from sdat.swarm.agents.knowledge_pack import KnowledgePackAgent
from sdat.swarm.orchestrator import SwarmOrchestrator
from sdat.telemetry.tracker import AuditTelemetry


def _resolve_target(target: str | Path) -> Path:
    """Resolve a target path to an absolute Path, rejecting dangerous roots."""
    p = Path(target).resolve()
    # Reject drive roots (e.g., C:\) as too broad / dangerous
    if p.parent == p or str(p) in (r"\\", "/"):
        raise PermissionError(f"Target path too broad or unsafe: {p}")
    return p


@dataclass(frozen=True)
class AuditResult:
    """Final output of an SDAT audit run."""
    target_root: str
    timestamp: str
    decisions: List[Decision] = field(default_factory=list)
    inventory_path: Optional[str] = None
    gaps_path: Optional[str] = None
    misconfigurations_path: Optional[str] = None
    remediation_path: Optional[str] = None
    telemetry_path: Optional[str] = None
    telemetry: Optional[AuditTelemetry] = None
    ai_enrichment: Optional[AIEnrichmentResult] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def total_decisions(self) -> int:
        return len(self.decisions)

    @property
    def implemented_count(self) -> int:
        return sum(1 for d in self.decisions if d.status == DecisionStatus.IMPLEMENTED)

    @property
    def missing_count(self) -> int:
        return sum(1 for d in self.decisions if d.status == DecisionStatus.MISSING)

    @property
    def misconfigured_count(self) -> int:
        return sum(1 for d in self.decisions if d.status == DecisionStatus.MISCONFIGURED)


FORBIDDEN_SECRET_NAMES = {
    ".env", ".env.local", ".env.production", ".env.staging", ".env.test",
    "id_rsa", "id_ed25519", "id_ecdsa", "id_dsa",
}
FORBIDDEN_SECRET_EXTENSIONS = {
    "key", "pem", "p12", "pfx", "pkcs12", "keystore", "jks",
}


def is_secret_file(p: Path) -> bool:
    """Return True if path points to a secret or credential file per SECURITY.md."""
    name_lower = p.name.lower()
    if name_lower in FORBIDDEN_SECRET_NAMES or name_lower.startswith(".env"):
        return True
    ext = p.suffix.lower().lstrip(".")
    if ext in FORBIDDEN_SECRET_EXTENSIONS:
        return True
    return False


def discover_files(
    target_root: str | Path,
    extensions: Set[str],
    exclude_dirs: Optional[Set[str]] = None,
) -> List[Path]:
    """Return all files under *target_root* matching one of *extensions*."""
    if exclude_dirs is None:
        exclude_dirs = {"venv", ".venv", "__pycache__", "node_modules", ".git", "dist", "build", ".sdat_cache"}
    root = Path(target_root)
    if not root.exists():
        return []
    return [
        f
        for f in root.rglob("*")
        if f.is_file()
        and f.suffix.lower().lstrip(".") in extensions
        and not any(part in exclude_dirs for part in f.parts)
        and not is_secret_file(f)
    ]


def run_audit_pipeline(
    target_root: str | Path,
    output_dir: str | Path = "docs/audit",
    project_type: str | None = None,
    max_workers: int = 4,
    enable_cache: bool = True,
    cache_dir: Optional[str | Path] = None,
    agent_timeout_seconds: float = 30.0,
    enable_ai: bool = True,
    ai_model: Optional[str] = None,
    gemma_model: Optional[str] = None,
    config: SDATConfig | None = None,
) -> AuditResult:
    """Run a complete production-grade SDAT audit and write reports to *output_dir*.

    Args:
        target_root: Root of the project to audit.
        output_dir: Directory to write report files into.
        project_type: Project category (backend, frontend, ml, etc.).
        max_workers: Bounded concurrency worker limit for scanners and swarm.
        enable_cache: Whether to use content-hashed caching for scans and tasks.
        cache_dir: Optional directory for persistent disk caching.
        agent_timeout_seconds: Timeout limit per agent before cancellation.
        enable_ai: Whether to run AI reasoning and remediation enrichment.
        ai_model: Optional model identifier override (e.g. qwen/qwen3-coder:free).
        gemma_model: Backward-compatible alias for ai_model.

    Returns:
        AuditResult with decisions, paths, and structured telemetry.
    """
    config = config or load_config(Path(__file__).resolve().parent.parent / "config" / "sdat.config.yaml")
    project_type = project_type or config.project_type
    target_root = _resolve_target(target_root)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    run_id = f"audit_{int(time.time())}"
    telemetry = AuditTelemetry(run_id=run_id)
    cache = ContentCache(cache_dir=cache_dir or (output_dir / ".sdat_cache"), telemetry=telemetry) if enable_cache else None

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 1: Multi-Language Scanning with Registry & Caching
    # ─────────────────────────────────────────────────────────────────────────
    all_facts: list[EvidenceFact] = []

    for lang_name, conf in REGISTRY.items():
        if lang_name not in config.scanners or not conf.get("enabled", False):
            continue
        scanner_cls = conf.get("scanner_class")
        if not scanner_cls:
            continue

        try:
            scanner = scanner_cls()
        except Exception:
            continue

        default_excludes = {
            "venv", ".venv", "__pycache__", "node_modules", ".git", "dist",
            "build", ".sdat_cache", ".sdat-cache", ".ruff_cache", ".pytest_cache",
            ".gemini", ".kilo", *config.exclude_paths,
        }
        try:
            discovered = scanner.discover_files(target_root, exclude_dirs=default_excludes)
        except TypeError:
            discovered = scanner.discover_files(target_root)
        discovered = discovered[:config.max_files_per_scan]
        size_limit = config.file_size_limit_mb * 1024 * 1024
        accepted_files: list[Path] = []
        for path in discovered:
            try:
                if path.stat().st_size <= size_limit:
                    accepted_files.append(path)
            except OSError:
                continue
        discovered = accepted_files
        if not discovered:
            continue

        for file_path in discovered:
            if is_secret_file(file_path):
                continue
            file_hash = ContentCache.hash_file(file_path)
            cache_key = f"scan_{scanner.language_id}_{file_hash}"

            cached_facts_data: list[dict[str, Any]] | None = cache.get(cache_key) if cache and file_hash else None
            if cached_facts_data is not None:
                # Reconstitute cached facts
                for fd in cached_facts_data:
                    try:
                        fact = EvidenceFact.from_dict(fd)
                        all_facts.append(fact)
                    except Exception:
                        pass
                continue

            # Uncached: run scanner with telemetry timer
            with telemetry.time_scanner(scanner.language_id):
                try:
                    facts = scanner.scan_file_evidence(file_path)
                    all_facts.extend(facts)

                    if cache and file_hash:
                        cache.put(cache_key, [f.to_dict() for f in facts])
                except Exception as exc:
                    telemetry.record_agent_failure(f"scanner_{scanner.language_id}", str(exc))
                    continue

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 2: Evidence Aggregation
    # ─────────────────────────────────────────────────────────────────────────
    with telemetry.time_operation("aggregation"):
        aggregator = EvidenceAggregator()
        correlated_facts = aggregator.correlate(all_facts)
        bundles = aggregator.aggregate(all_facts)
        telemetry.set_evidence_counts(
            raw=len(all_facts),
            correlated=len(correlated_facts),
            bundles=len(bundles),
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 3: Agent Swarm Dispatch
    # ─────────────────────────────────────────────────────────────────────────
    knowledge_registry = build_canonical_registry()
    registry_warnings = knowledge_registry.validate_integrity()
    project_context: dict[str, Any] = {
        "target_root": str(target_root),
        "run_id": run_id,
        "project_type": project_type,
        "evidence_facts": correlated_facts,
        "signals": [SignalBridge.to_legacy_signal(fact) for fact in correlated_facts],
        "bundles": bundles,
    }

    swarm_agents: list[Any] = []
    foundation_enabled = set(config.foundation_agents)
    if foundation_enabled:
        swarm_agents.append(FoundationAgent(
            agent_id=sorted(foundation_enabled)[0],
            agent_name="configured_foundation_rules_agent",
        ))

    domain_enabled = set(config.domain_agents)
    domain_entries = config.agent_map.get("domain", {}).get("agents", [])
    enabled_domain_ids = {entry.get("id") for entry in domain_entries if entry.get("id") in domain_enabled}
    workload = project_type.lower().replace("_", "-")
    backend_workload = workload in {"backend", "backend-web", "api", "mixed", "full-stack"}
    frontend_workload = workload in {"frontend", "frontend-web", "full-stack", "mixed"}
    if "D-01" in enabled_domain_ids and backend_workload:
        swarm_agents.append(BackendAgent(agent_id="D-01", agent_name="backend_agent"))

    frontend_markers = ("react", "next", "vue", "angular", "svelte")
    has_frontend_evidence = any(
        any(marker in value.lower() for marker in frontend_markers)
        for fact in correlated_facts
        for value in (
            fact.library or "",
            fact.framework or "",
            fact.subject if fact.kind in (EvidenceKind.IMPORT, EvidenceKind.DEPENDENCY, EvidenceKind.FRAMEWORK_MARKER) else "",
        )
    )
    if (frontend_workload or has_frontend_evidence) and "D-21" in enabled_domain_ids:
        swarm_agents.append(FrontendAgent(agent_id="D-21"))

    if project_type.lower() in {"ml", "machine-learning", "nlp"} and "D-22" in enabled_domain_ids:
        if knowledge_registry.get_knowledge_pack("kp.machine-learning"):
            swarm_agents.append(KnowledgePackAgent("D-22", "ml_knowledge_pack_agent", MLKnowledgePack()))
    if project_type.lower() == "nlp" and "D-23" in enabled_domain_ids:
        if knowledge_registry.get_knowledge_pack("kp.natural-language-processing"):
            swarm_agents.append(KnowledgePackAgent("D-23", "nlp_knowledge_pack_agent", NLPKnowledgePack()))

    orchestrator = SwarmOrchestrator(
        max_workers=max_workers,
        agent_timeout_seconds=agent_timeout_seconds,
        max_retries=2,
        backoff_base_seconds=0.25,
        cache=cache,
        telemetry=telemetry,
    )

    merged_output = orchestrator.run_swarm(swarm_agents, project_context)
    decisions = merged_output.decisions
    warnings = merged_output.warnings
    warnings.extend(f"Knowledge registry validation: {warning}" for warning in registry_warnings)
    unsupported_domain_ids = domain_enabled - {"D-01", "D-21", "D-22", "D-23"}
    warnings.extend(
        f"Configured domain agent {agent_id} has no runtime implementation and was skipped."
        for agent_id in sorted(unsupported_domain_ids)
    )

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 4: AI Reasoning & Solution Remediation (Qwen3-Coder / Open-Weight Models)
    # ─────────────────────────────────────────────────────────────────────────
    ai_enrichment: Optional[AIEnrichmentResult] = None
    with telemetry.time_operation("ai_enrichment"):
        try:
            model_choice = ai_model or gemma_model
            ai_config = config.to_ai_config(model_choice)
            research_report: dict[str, Any] | None = None
            if config.research_enabled and enable_ai and ai_config.is_available:
                with telemetry.time_operation("research_context"):
                    research_report = ResearchAgent(ai_config, telemetry).research(
                        decisions, target_root=str(target_root), max_concepts=3
                    )
            ai_enrichment = enrich_findings(
                decisions=decisions,
                target_root=target_root,
                enable_ai=enable_ai,
                model_override=model_choice,
                output_dir=output_dir,
                ai_config=ai_config,
                research_report=research_report,
            )
        except Exception as exc:
            warnings.append(f"AI enrichment warning: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 5: Render Reports & Telemetry
    # ─────────────────────────────────────────────────────────────────────────
    with telemetry.time_operation("report_generation"):
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        inventory_md = render_inventory(decisions, str(target_root))
        gaps_md = render_gaps(decisions, str(target_root))
        misconfig_md = render_misconfigurations(decisions, str(target_root))

        remediation_path_str: Optional[str] = None
        if ai_enrichment:
            remediation_md = render_remediation_markdown(ai_enrichment, decisions, str(target_root))
            rem_path = output_dir / "04-remediation.md"
            rem_path.write_text(remediation_md, encoding="utf-8")
            remediation_path_str = str(rem_path)

            if ai_enrichment.executive_summary:
                mode_str = "Live Inference" if not ai_enrichment.is_cached else "Offline Cached"
                model_label = ai_enrichment.model if ai_enrichment.model != "none" else "AI"
                ai_banner = f"> **AI Architectural Summary** ({model_label} - {mode_str}): {ai_enrichment.executive_summary}\n\n"
                inventory_md = f"{ai_banner}{inventory_md}"

        try:
            telemetry.finalize()
            telemetry_md = telemetry.render_markdown_summary()
        except Exception as exc:
            telemetry_md = f"*(Telemetry generation error: {exc})*"
            warnings.append(f"Telemetry finalization warning: {exc}")

        inventory_with_telemetry = f"{inventory_md}\n\n---\n\n{telemetry_md}\n"

        inv_path = output_dir / "01-inventory.md"
        gaps_path = output_dir / "02-gaps.md"
        misconfig_path = output_dir / "03-misconfigurations.md"
        telemetry_json_path = output_dir / "telemetry.json"

        inv_path.write_text(inventory_with_telemetry, encoding="utf-8")
        gaps_path.write_text(gaps_md, encoding="utf-8")
        misconfig_path.write_text(misconfig_md, encoding="utf-8")

        # Telemetry write is resilient and non-blocking
        saved_telemetry_path: str | None = None
        try:
            telemetry_json_path.write_text(
                json.dumps(telemetry.to_dict(), indent=2),
                encoding="utf-8",
            )
            saved_telemetry_path = str(telemetry_json_path)
        except Exception as exc:
            warnings.append(f"Telemetry file persistence error: {exc}")

    return AuditResult(
        target_root=str(target_root),
        timestamp=timestamp,
        decisions=decisions,
        inventory_path=str(inv_path),
        gaps_path=str(gaps_path),
        misconfigurations_path=str(misconfig_path),
        remediation_path=remediation_path_str,
        telemetry_path=saved_telemetry_path,
        telemetry=telemetry,
        ai_enrichment=ai_enrichment,
        warnings=warnings,
    )
