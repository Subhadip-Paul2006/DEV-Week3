"""Base protocol for SDAT language scanners."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from sdat.models import EvidenceFact, FileEvidence, FileSignals, Signal


@runtime_checkable
class LanguageScanner(Protocol):
    """Protocol implemented by all language-specific source code scanners."""

    language_id: str
    file_extensions: tuple[str, ...]

    def discover_files(
        self,
        root: Path | str,
        exclude_dirs: set[str] | None = None,
    ) -> list[Path]:
        """Discover source files matching this scanner's extensions under root."""
        ...

    # Phase 2.5 Common Evidence Model (canonical methods)
    def extract_evidence(self, files: list[Path]) -> list[EvidenceFact]:
        """Extract concept-agnostic EvidenceFacts from a collection of source files."""
        ...

    def scan_file_evidence(self, file_path: Path | str) -> list[EvidenceFact]:
        """Scan a single source file and return detected EvidenceFacts."""
        ...

    def scan_project_evidence(
        self,
        root: Path | str,
        exclude_dirs: set[str] | None = None,
    ) -> list[FileEvidence]:
        """Scan an entire project directory and return FileEvidence per file."""
        ...

    # Legacy Signal Protocol (backward compatibility)
    def extract_signals(self, files: list[Path]) -> list[Signal]:
        """Extract signals from a collection of source files."""
        ...

    def scan_file(self, file_path: Path | str) -> list[Signal]:
        """Scan a single source file and return detected signals."""
        ...

    def scan_project(
        self,
        root: Path | str,
        exclude_dirs: set[str] | None = None,
    ) -> list[FileSignals]:
        """Scan an entire project directory and return FileSignals per file."""
        ...

