"""TypeScript scanner for SDAT — conforms to LanguageScanner protocol.

This module exposes TypeScriptScanner, which connects directly to the comprehensive
pattern-detection engine in sdat.scanners.typescript.
"""

from __future__ import annotations

from .typescript import (
    TypeScriptScanner,
    _scan_typescript_evidence,
    _scan_typescript_file,
    discover_typescript_files,
    scan_typescript_project,
    scan_typescript_project_evidence,
)

__all__ = [
    "TypeScriptScanner",
    "_scan_typescript_evidence",
    "_scan_typescript_file",
    "discover_typescript_files",
    "scan_typescript_project",
    "scan_typescript_project_evidence",
]

