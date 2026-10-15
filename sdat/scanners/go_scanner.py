"""Go scanner for SDAT — conforms to LanguageScanner protocol.

This module exposes GoScanner, which connects directly to the comprehensive
pattern-detection engine in sdat.scanners.go.
"""

from __future__ import annotations

from .go import (
    GoScanner,
    _scan_go_evidence,
    _scan_go_file,
    discover_go_files,
    scan_go_project,
    scan_go_project_evidence,
)

__all__ = [
    "GoScanner",
    "_scan_go_evidence",
    "_scan_go_file",
    "discover_go_files",
    "scan_go_project",
    "scan_go_project_evidence",
]
