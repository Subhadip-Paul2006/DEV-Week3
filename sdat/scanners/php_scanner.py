"""PHP scanner for SDAT — conforms to LanguageScanner protocol."""

from __future__ import annotations

from .php import (
    PhpScanner,
    _scan_php_evidence,
    _scan_php_file,
    discover_php_files,
    scan_php_project,
    scan_php_project_evidence,
)

__all__ = [
    "PhpScanner",
    "_scan_php_evidence",
    "_scan_php_file",
    "discover_php_files",
    "scan_php_project",
    "scan_php_project_evidence",
]
