"""Java/Kotlin scanner for SDAT — conforms to LanguageScanner protocol."""

from __future__ import annotations

from .java import (
    JavaScanner,
    _scan_java_evidence,
    _scan_java_file,
    discover_java_files,
    scan_java_project,
    scan_java_project_evidence,
)

__all__ = [
    "JavaScanner",
    "_scan_java_evidence",
    "_scan_java_file",
    "discover_java_files",
    "scan_java_project",
    "scan_java_project_evidence",
]
