"""Signal rules — YAML definitions of how to evaluate concepts from file signals.

Each rule file in ``config/rules/signals/`` corresponds to one concept.
The rule engine reads these files, applies them to scan signals, and produces
``Decision`` objects.

Rule file format (YAML)::

    concept_id: foundation.caching
    requires_any:
      signals: [foundation.caching.presence.redis, foundation.caching.presence.memcache]
      min_confidence: 0.5
    absence_signals: [foundation.caching.absence]
    misconfiguration_signals: [foundation.caching.misconfig.no-ttl]
    anti_patterns: [foundation.caching.anti.lru-without-eviction]
    recommendation: "Add Redis with a sensible TTL."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class SignalRule:
    """One rule entry loaded from a YAML rule file."""
    concept_id: str
    requires_any: List[str] = field(default_factory=list)
    requires_all: List[str] = field(default_factory=list)
    min_confidence: float = 0.5
    absence_signals: List[str] = field(default_factory=list)
    misconfiguration_signals: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    recommendation: str = ""

    def evaluate(
        self,
        present_signal_ids: set[str],
        absent_signal_ids: set[str],
        misconfig_signal_ids: set[str],
        anti_signal_ids: set[str],
    ) -> tuple[str, float]:
        """Return (status, confidence) for this rule given the observed signals.

        Returns one of:
            ``"implemented"`` — all required signals are present.
            ``"missing"``     — absence signals dominate.
            ``"misconfigured"`` — misconfiguration signals dominate.
            ``"n/a"``         — nothing found either way.

        Status priority: misconfigured > missing > implemented > n/a.
        """
        has_implemented = self._check_requires(present_signal_ids)
        has_missing = bool(self.absence_signals) and bool(
            absent_signal_ids.intersection(set(self.absence_signals))
        )
        has_misconfig = bool(self.misconfiguration_signals) and bool(
            misconfig_signal_ids.intersection(set(self.misconfiguration_signals))
        )
        has_anti = bool(self.anti_patterns) and bool(
            anti_signal_ids.intersection(set(self.anti_patterns))
        )

        # Priority order: misconfigured > missing > implemented > n/a
        if has_misconfig or has_anti:
            confidence = 0.8 if has_anti else 0.7
            return "misconfigured", confidence
        if has_missing and not has_implemented:
            return "missing", 0.9
        if has_implemented:
            return "implemented", 0.85
        return "n/a", 0.0

    def _check_requires(self, present_signal_ids: set[str]) -> bool:
        required = set(self.requires_any) or set(self.requires_all)
        if not required:
            return False
        if self.requires_any:
            return bool(required.intersection(present_signal_ids))
        # requires_all
        return required.issubset(present_signal_ids)


def load_rules(rules_dir: str | Path) -> List[SignalRule]:
    """Load all rule YAML files from the given directory."""
    rules_path = Path(rules_dir)
    if not rules_path.exists():
        return []
    rules: List[SignalRule] = []
    for yaml_file in sorted(rules_path.glob("*.yaml")):
        data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
        if data:
            rules.append(SignalRule(**data))
    return rules
