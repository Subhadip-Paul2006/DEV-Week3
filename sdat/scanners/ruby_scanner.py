"""Ruby scanner — Phase 0 stub. Real implementation: Phase 4."""

from __future__ import annotations

from pathlib import Path

from ..models import Signal


class RubyScanner:
    language_id = "ruby"
    file_extensions = (".rb",)

    def discover_files(self, root: Path) -> list[Path]:
        if not root.exists() or not root.is_dir():
            return []
        return sorted(list(root.rglob("*.rb")))

    def extract_signals(self, files: list[Path]) -> list[Signal]:
        return []
