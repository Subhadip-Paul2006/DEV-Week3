"""Python scanner for SDAT — conforms to LanguageScanner protocol.

This module exposes PythonScanner, which connects directly to the comprehensive
pattern-detection engine in sdat.scanners.python.
"""

from __future__ import annotations

from .python import (
    PythonScanner,
    _scan_python_evidence,
    _scan_python_file,
    discover_python_files,
    scan_python_project,
    scan_python_project_evidence,
)

__all__ = [
    "PythonScanner",
    "_scan_python_evidence",
    "_scan_python_file",
    "discover_python_files",
    "scan_python_project",
    "scan_python_project_evidence",
]