"""Svelte scanner — Phase 0 stub. Real implementation: Phase 5."""

from __future__ import annotations

from pathlib import Path

from ..models import Signal


class SvelteScanner:
    language_id = "svelte"
    file_extensions = (".svelte",)

    def discover_files(self, root: Path) -> list[Path]:
        if not root.exists() or not root.is_dir():
            return []
        return sorted(list(root.rglob("*.svelte")))

    def extract_signals(self, files: list[Path]) -> list[Signal]:
        return []
