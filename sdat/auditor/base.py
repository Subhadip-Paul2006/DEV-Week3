"""Base auditor protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..models import Decision, Signal


@dataclass
class TargetContext:
    root: str
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)


class Auditor(ABC):
    """Abstract base for all auditor adapters."""

    @abstractmethod
    def audit(
        self,
        signals: list[Signal],
        context: TargetContext,
    ) -> list[Decision]:
        """Evaluate signals and return decisions."""
