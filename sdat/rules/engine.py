"""Rule engine — converts scan signals into audited decisions.

The rule engine:
1. Loads all signal rules from config/rules/signals/*.yaml
2. Groups signals by concept_id
3. Applies each rule to produce a Decision.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from sdat.concepts import CONCEPTS_BY_ID
from sdat.models import Decision, DecisionStatus, Evidence, FileSignals, Signal, SignalKind
from sdat.rules.signals import load_rules


def get_default_rules_dir() -> Path:
    """Return the canonical path to signal rules, resolving relative to package root."""
    pkg_rules = Path(__file__).resolve().parent.parent.parent / "config" / "rules" / "signals"
    if pkg_rules.exists():
        return pkg_rules
    cwd_rules = Path("config/rules/signals").resolve()
    if cwd_rules.exists():
        return cwd_rules
    return pkg_rules


def build_decisions(
    file_signals: List[FileSignals],
    project_type: str = "backend",
    rules_dir: Path | str | None = None,
) -> List[Decision]:
    """Run the rule engine over collected signals.

    Args:
        file_signals: All signals collected by the scanner phase.
        project_type: Project category (backend, frontend, ml, etc.) — future: filter concepts.
        rules_dir: Optional custom rules directory. If None, resolves to package config.

    Returns:
        List of Decision objects, one per evaluated concept.
    """
    # Load signal rules from canonical package directory
    rules_path = Path(rules_dir) if rules_dir else get_default_rules_dir()
    rules = load_rules(rules_path)

    # Index signals by concept_id, kind
    presence_by_concept: dict[str, List[Signal]] = {}
    absence_by_concept: dict[str, List[Signal]] = {}
    weakness_by_concept: dict[str, List[Signal]] = {}

    for fs in file_signals:
        for sig in fs.signals:
            if sig.kind == SignalKind.PRESENCE:
                presence_by_concept.setdefault(sig.concept_id, []).append(sig)
            elif sig.kind == SignalKind.ABSENCE:
                absence_by_concept.setdefault(sig.concept_id, []).append(sig)
            elif sig.kind == SignalKind.WEAKNESS:
                weakness_by_concept.setdefault(sig.concept_id, []).append(sig)
            elif sig.kind == SignalKind.CONFIG:
                # Treat config signals as presence for now
                presence_by_concept.setdefault(sig.concept_id, []).append(sig)

    decisions: List[Decision] = []

    for rule in rules:
        concept = CONCEPTS_BY_ID.get(rule.concept_id)
        if not concept:
            continue

        presence_sigs = presence_by_concept.get(rule.concept_id, [])
        absence_sigs = absence_by_concept.get(rule.concept_id, [])
        weakness_sigs = weakness_by_concept.get(rule.concept_id, [])

        has_presence = bool(presence_sigs)
        has_absence = bool(absence_sigs)
        has_weakness = bool(weakness_sigs)

        # Status priority: MISCONFIGURED > MISSING > IMPLEMENTED > UNKNOWN
        if has_weakness and has_presence:
            status = DecisionStatus.MISCONFIGURED
            confidence = 0.8
            misconfig_str = "; ".join(s.evidence for s in weakness_sigs[:3])
        elif has_weakness and not has_presence:
            status = DecisionStatus.MISCONFIGURED
            confidence = 0.7
            misconfig_str = "; ".join(s.evidence for s in weakness_sigs[:3])
        elif has_presence and has_absence:
            # Mixed: presence dominates in some files, absence in others
            # If we have presence, treat as IMPLEMENTED
            status = DecisionStatus.IMPLEMENTED
            confidence = 0.75
            misconfig_str = ""
        elif has_presence:
            status = DecisionStatus.IMPLEMENTED
            confidence = 0.85
            misconfig_str = ""
        elif has_absence:
            status = DecisionStatus.MISSING
            confidence = 0.9
            misconfig_str = ""
        else:
            status = DecisionStatus.UNKNOWN
            confidence = 0.0
            misconfig_str = ""

        # Build evidence list
        evidence_list: List[Evidence] = []
        for sig in presence_sigs[:5]:
            line = sig.line_range[0] if sig.line_range else 1
            evidence_list.append(Evidence(
                file=str(sig.file_path),
                line=line,
                snippet=sig.evidence[:200],
            ))
        for sig in weakness_sigs[:3]:
            line = sig.line_range[0] if sig.line_range else 1
            evidence_list.append(Evidence(
                file=str(sig.file_path),
                line=line,
                snippet=sig.evidence[:200],
                note="misconfiguration",
            ))
        for sig in absence_sigs[:3]:
            line = sig.line_range[0] if sig.line_range else 1
            evidence_list.append(Evidence(
                file=str(sig.file_path),
                line=line,
                snippet=sig.evidence[:200],
                note="verified absence",
            ))

        # Build gaps list (what's missing)
        gaps = []
        if status in (DecisionStatus.MISSING, DecisionStatus.UNKNOWN):
            gaps = rule.requires_any + rule.requires_all

        decision = Decision(
            concept_id=concept.id,
            concept_name=concept.name,
            status=status,
            confidence=confidence,
            priority=concept.priority,
            evidence=evidence_list,
            misconfiguration=misconfig_str if misconfig_str else None,
            gaps=gaps,
            recommendation=rule.recommendation,
        )
        decisions.append(decision)

    return decisions
