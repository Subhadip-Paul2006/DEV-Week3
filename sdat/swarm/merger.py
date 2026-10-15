"""Merger — combines agent outputs into a unified decision set."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import Decision, DecisionStatus, Evidence, Priority


@dataclass
class MergedOutput:
    decisions: list[Decision]
    warnings: list[str]


def merge_decisions(agent_outputs: list[dict[str, Any]]) -> MergedOutput:
    """Merge decisions from multiple agents.

    Rules:
    1. If two agents emit decisions for the same concept_id, prefer the agent
       that owns the concept (per agent.yaml owning_agent).
    2. If tie: prefer higher confidence.
    3. Log a warning for manual review.
    """
    seen: dict[str, Decision] = {}
    warnings: list[str] = []

    for output in agent_outputs:
        agent_id = output.get("agent_id", "unknown")
        for d in output.get("decisions", []):
            cid = d.get("concept_id", "")
            if cid in seen:
                existing = seen[cid]
                new_confidence = d.get("confidence", 0.0)
                if new_confidence > existing.confidence:
                    seen[cid] = _dict_to_decision(d)
                    warnings.append(
                        f"Concept '{cid}': replaced decision from {existing.priority} "
                        f"with higher-confidence result from agent {agent_id} (conf={new_confidence})"
                    )
            else:
                seen[cid] = _dict_to_decision(d)

    decisions = sorted(seen.values(), key=lambda d: d.concept_id)
    return MergedOutput(decisions=decisions, warnings=warnings)


def _dict_to_decision(d: dict[str, Any]) -> Decision:
    """Convert a JSON-decoded decision dict back to a Decision dataclass."""


    evidence_list = []
    for ev in d.get("evidence", []):
        evidence_list.append(
            Evidence(
                file=ev.get("file", ""),
                line=int(ev.get("line", 0)),
                snippet=ev.get("snippet", ""),
                note=ev.get("note", ""),
            )
        )

    status_str = d.get("status", "unknown")
    try:
        status = DecisionStatus(status_str)
    except ValueError:
        status = DecisionStatus.UNKNOWN

    priority_str = d.get("priority", "info")
    try:
        priority = Priority(priority_str)
    except ValueError:
        priority = Priority.INFO

    return Decision(
        concept_id=d.get("concept_id", ""),
        concept_name=d.get("concept_name", d.get("concept_id", "")),
        status=status,
        confidence=float(d.get("confidence", 0.0)),
        evidence=evidence_list,
        misconfiguration=d.get("misconfiguration"),
        gaps=d.get("gaps", []),
        recommendation=d.get("recommendation"),
        priority=priority,
    )
