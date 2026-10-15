"""Renderer — produces three deterministic markdown reports from decisions.

Pure templating. No LLM calls. Byte-identical output for identical input.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..models import Decision, DecisionStatus, Priority

SDAT_VERSION = "0.1.0"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _build_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def _decision_to_dict(d: Decision) -> dict:
    """Convert a Decision dataclass to a plain dict for the templates."""
    return {
        "concept_id": d.concept_id,
        "concept_name": d.concept_name,
        "status": d.status.value,
        "priority": d.priority.value,
        "confidence": d.confidence,
        "evidence": [
            {"file": e.file, "line": e.line, "snippet": e.snippet, "note": e.note}
            for e in d.evidence
        ],
        "misconfiguration": d.misconfiguration,
        "gaps": d.gaps,
        "recommendation": d.recommendation,
    }


def _category_for(concept_id: str) -> str:
    """Extract a category label from a concept_id (e.g. 'foundation.caching' → 'foundation')."""
    if "." in concept_id:
        return concept_id.split(".", 1)[0].replace("_", " ").title()
    return "Uncategorized"


def _group_by_category(decisions: list[Decision]) -> dict[str, list[dict]]:
    """Group decisions by category, sorted by priority within each."""
    out: dict[str, list[dict]] = {}
    priority_order = {
        Priority.CRITICAL: 0,
        Priority.HIGH: 1,
        Priority.MEDIUM: 2,
        Priority.LOW: 3,
        Priority.INFO: 4,
        Priority.N_A: 5,
    }
    for d in decisions:
        cat = _category_for(d.concept_id)
        out.setdefault(cat, []).append(_decision_to_dict(d))
    for cat, items in out.items():
        items.sort(key=lambda x: (priority_order.get(Priority(x["priority"]), 99), x["concept_name"]))
    return out


def render_inventory(decisions: list[Decision], target_root: str) -> str:
    """Render the 01-inventory.md report (only IMPLEMENTED decisions)."""
    env = _build_env()
    tpl = env.get_template("inventory.md.j2")
    implemented = [d for d in decisions if d.status == DecisionStatus.IMPLEMENTED]
    grouped = _group_by_category(implemented)
    return tpl.render(
        findings_by_category=grouped,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        target_root=target_root,
        sdat_version=SDAT_VERSION,
    )


def render_gaps(decisions: list[Decision], target_root: str) -> str:
    """Render the 02-gaps.md report (only MISSING decisions)."""
    env = _build_env()
    tpl = env.get_template("gaps.md.j2")
    missing = [d for d in decisions if d.status == DecisionStatus.MISSING]
    grouped = _group_by_category(missing)
    return tpl.render(
        findings_by_category=grouped,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        target_root=target_root,
        sdat_version=SDAT_VERSION,
    )


def render_misconfigurations(decisions: list[Decision], target_root: str) -> str:
    """Render the 03-misconfigurations.md report (only MISCONFIGURED decisions)."""
    env = _build_env()
    tpl = env.get_template("misconfigurations.md.j2")
    misconfigured = [d for d in decisions if d.status == DecisionStatus.MISCONFIGURED]
    grouped = _group_by_category(misconfigured)
    return tpl.render(
        findings_by_category=grouped,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        target_root=target_root,
        sdat_version=SDAT_VERSION,
    )


def write_reports(
    decisions: list[Decision],
    target_root: str,
    output_dir: str | os.PathLike = "docs/audit",
) -> dict[str, str]:
    """Render all three reports and write them to output_dir. Returns {name: path}."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reports = {
        "01-inventory.md": render_inventory(decisions, target_root),
        "02-gaps.md": render_gaps(decisions, target_root),
        "03-misconfigurations.md": render_misconfigurations(decisions, target_root),
    }

    written: dict[str, str] = {}
    for filename, content in reports.items():
        path = out_dir / filename
        path.write_text(content, encoding="utf-8")
        written[filename] = str(path)

    return written